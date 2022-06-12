#python script to harvest info from urban exploring sites and add it to a database so that it can be displayed on a map

import argparse
from datetime import datetime, timezone
from math import radians, cos, sin, asin, sqrt

from db import db
from tags import add_tag
import xenforo as xf


def main() -> None:
    db.connect()
    
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument('--add', nargs=2)#--add "place name" "lat, long"
    parser.add_argument('--ref', nargs="*")#--ref "url" "place_id"
    parser.add_argument('--locate', '-l', type=str, nargs="*")
    parser.add_argument('--tag', nargs=2)#--tag "id" "tag"
    parser.add_argument('--delete', type=int)#--delete <place_id>
    args = parser.parse_args()


    if args.add:
        add_place(args.add)
        return
    elif args.ref:
        add_ref(args.ref)
        return
    elif args.locate:
        for place in args.locate:
            for x in db.get_cur().execute("""SELECT places.row_id, places.name FROM tags_ft 
                LEFT JOIN tag_rel ON tag_rel.tag_id=tags_ft.rowid
                LEFT JOIN places ON places.row_id=tag_rel.place_id
                WHERE tag match ?
                GROUP BY places.row_id""", [f"{place.strip()}"]):
                print(f"[{x['row_id']}] {x['name']}")
        return
    elif args.tag:
        add_tag(args.tag[0], args.tag[1])
        return
    elif args.delete:
        db.get_cur().execute("DELETE FROM places WHERE row_id = ?", [args.delete])
        tag_id = db.get_cur().execute("SELECT tag_id FROM tag_rel WHERE place_id = ?", [args.delete]).fetchone()['tag_id']
        db.get_cur().execute("DELETE FROM tag_rel WHERE place_id = ?", [args.delete])
        db.get_cur().execute("DELETE FROM tags WHERE row_id = ? AND (SELECT COUNT(*) FROM tag_rel WHERE tag_id = ?) = 0", [tag_id, tag_id])
        db.get_cur().execute("COMMIT")

        return

    xxviii_dayslater = xf.xenforo("https://www.28dayslater.co.uk/forum/", [
        "noteworthy-reports.115/",
        "asylums-and-hospitals.4/",
        "high-stuff.35/",
        "industrial-sites.6/",
        "leisure-sites.7/",
        "residential-sites.92/",
        "military-sites.5/",
        "mines-and-quarries.95/",
        "roc-posts.50/",
        "restored-roc-posts.82/",
        "theatres-and-cinemas.78/",
        "uk-draining-forum.94/",
        "underground-sites.29/",
        "european-and-international-sites.46/",
        "other-sites.8/",
        "leads-rumours-and-news.57/",
        "photo-threads.158/",
        "diehardlove.122/",
        "downfallen.121/",
        "solomon.123/"
    ])
    xxviii_dayslater.crawl()


    oblivionstate = xf.xenforo("https://www.oblivionstate.com/community/forums/", [
        "industrial-locations.11/",
        "manors-mansions-residential.26/",
        "medical-institutions.12/",
        "public-buildings-education-leisure.13/",
        "underground-explores.45/",
        "military-sites.10/",
        "high-places.54/",
        "religious-sites.27/",
        "anything-else.16/",
        "short-reports.31/",
        "photo-only-threads.33/"
    ])
    oblivionstate.crawl()


    derelictplaces = xf.xenforo("https://www.derelictplaces.co.uk/forums/", [
        "general-exploration-forum.82/",
        "industrial-sites.64/",
        "military-sites.63/",
        "hospitals-asylums.62/",
        "misc-sites.70/",
        "residential-sites.68/",
        "rural-sites.61/",
        "overseas-sites.143/",
        "leisure-sites.66/",
        "underground-sites.139/"
    ])
    derelictplaces.crawl()
    
    return


def add_ref(args):
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument("url", type=str)
    parser.add_argument("pid", type=int, nargs="*")
    args = parser.parse_args(args)

    x = xf.xenforo("https://www.28dayslater.co.uk/forum/", [])
    thread = x.get_thread(args.url)
    title = thread[0]
    thread_date = thread[2]
    
    dt = datetime.now(timezone.utc).isoformat(timespec="seconds")
    #need the title and date

    db.get_cur().execute("BEGIN")
    for pid in args.pid:
        db.get_cur().execute("INSERT INTO refs(url, place_id, title, date_inserted, date_post) VALUES (?, ?, ?, ?, ?)", [args.url, int(pid), title, dt, thread_date])
    db.get_cur().execute("COMMIT")
    return


def add_place(args):
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument("name", type=str)
    parser.add_argument("latlng", type=str)
    args = parser.parse_args(args)

    coords = list(map(float, args.latlng.split(',')))

    #clamp to 6 decimals, don't need higher precision
    lat = float(f"{coords[0]:.6f}")
    lng = float(f"{coords[1]:.6f}")
    dt = datetime.now(timezone.utc).isoformat(timespec="seconds")

    #get a list of places close by (approx within 1-2km in the UK)
    rng = 0.05
    db.get_cur().execute("SELECT row_id, name, long, lat FROM places WHERE long > ? AND long < ? AND lat > ? AND lat < ?", [lng-rng, lng+rng, lat-rng, lat+rng])
    nearby = db.get_cur().fetchall()
    if len(nearby) != 0:
        print(f"{len(nearby)} nearby")
        for i in nearby:
            print(f"[{i['row_id']}] ({haversine(i['long'], i['lat'], lng, lat)}) miles: {i['name']}")

    #insert the place into the db and get the place_id for it
    ins = db.get_cur().execute("INSERT INTO places(date_inserted, name, lat, long) VALUES (?, ?, ?, ?)", [dt, args.name, lat, lng]).rowcount
    db.get_cur().execute("SELECT row_id FROM places WHERE name = ? and lat = ? and long = ?", [args.name, lat, lng])
    res = db.get_cur().fetchone()

    #add a tag from the name of the place
    add_tag(res["row_id"], args.name)
    print(f"Inserted {args.name} as ID {res['row_id']}")
    return


def haversine(lon1, lat1, lon2, lat2):
    """
    Calculate the great circle distance between two points 
    on the earth (specified in decimal degrees)
    """
    # convert decimal degrees to radians 
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
    # haversine formula 
    dlon = lon2 - lon1 
    dlat = lat2 - lat1 
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a)) 
    # Radius of earth in kilometers is 6371
    km = 6371 * c
    mi = 3959 * c
    return float(f"{mi:.2f}")


if __name__ == "__main__":
    main()
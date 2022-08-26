#python script to harvest info from urban exploring sites and add it to a database so that it can be displayed on a map

import argparse
from datetime import datetime, timezone
from math import radians, cos, sin, asin, sqrt

from db import db
from tags import add_tag
import xenforo as xf
import wordpress as wp
import reddit as red
import tomlkit


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

    crawlers()
    
    return


def crawlers():
    with open("config.cfg", mode="rt", encoding="utf-8") as fp:
        cfg = tomlkit.load(fp)
    
    if cfg.get("crawler") == None:
        return

    for c_name in cfg["crawler"]:
        for i, c in enumerate(cfg["crawler"][c_name]):
            x = None
            if c_name == "reddit":
                x = red.red(c, i)
            elif c_name == "xenforo":
                x = xf.xenforo(c, i)
            elif c_name == "wordpress":
                x = wp.wordpress(c, i)

            if x != None:
                x.crawl()

    return


def add_ref(args):
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument("url", type=str)
    parser.add_argument("pid", type=int, nargs="*")
    args = parser.parse_args(args)


    #check if it exists in the db already, if so, just clone it.
    db.get_cur().execute("SELECT url, title, date_inserted, date_post FROM refs where url = ?", [args.url])
    cur = db.get_cur().fetchone()
    if cur:
        db.get_cur().execute("BEGIN")
        for pid in args.pid:
            db.get_cur().execute("""INSERT OR IGNORE INTO refs(url, place_id, title, date_inserted, date_post) 
                VALUES (?, ?, ?, ?, ?)""",
                [args.url, int(pid), cur["title"], cur["date_inserted"], cur["date_post"]])
        db.get_cur().execute("COMMIT")
        return

    #need to redo the code below, now there are more crawlers, it's just wrong.
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
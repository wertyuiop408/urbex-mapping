#python script to harvest info from urban exploring sites and add it to a database so that it can be displayed on a map

import argparse
from datetime import datetime, timezone
from math import radians, cos, sin, asin, sqrt

from db import db
import xxviii_dayslater as d2l


def main() -> None:
    db.connect()
    
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument('--add', nargs=2)
    parser.add_argument('--ref', nargs=2)
    args = parser.parse_args()


    if args.add:
        add_place(args.add)
        return
    elif args.ref:
        add_ref(args.ref)
        return

    x = d2l.xxviii_dayslater()
    x.crawl()
    
    return


def add_ref(args):
    x = d2l.xxviii_dayslater()
    thread = x.get_thread(args[0])
    title = thread[0]
    thread_date = thread[2]
    
    url = args[0]
    dt = datetime.now(timezone.utc).isoformat(timespec="seconds")
    #need the title and date
    db.get_cur().execute("INSERT INTO refs(url, place_id, title, date_inserted, date_post) VALUES (?, ?, ?, ?, ?)", [url, int(args[1]), title, dt, thread_date])

    return


def add_place(args):
    name = args[0]
    coords = (args[1]).split(',')
    lat = float(coords[0])
    lng = float(coords[1])
    dt = datetime.now(timezone.utc).isoformat(timespec="seconds")

    rng = 0.05
    db.get_cur().execute("SELECT row_id, name, long, lat FROM places WHERE long > ? AND long < ? AND lat > ? AND lat < ?", [lng-rng, lng+rng, lat-rng, lat+rng])
    nearby = db.get_cur().fetchall()
    if len(nearby) != 0:
        print(f"{len(nearby)} nearby")
        for i in nearby:
            print(f"[{i['row_id']}] ({haversine(i['long'], i['lat'], lng, lat)}) miles: {i['name']}")

    ins = db.get_cur().execute("INSERT INTO places(date_inserted, name, lat, long) VALUES (?, ?, ?, ?)", [dt, name, lat, lng]).rowcount
    db.get_cur().execute("SELECT row_id FROM places WHERE name = ? and lat = ? and long = ?", [name, lat, lng])
    res = db.get_cur().fetchone()
    print(f"Inserted {name} as ID {res['row_id']}")
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
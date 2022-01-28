#python script to harvest info from urban exploring sites and add it to a database so that it can be displayed on a map

import argparse
from datetime import datetime, timezone

from db import db
import xxviii_dayslater as d2l


def main() -> None:
    db.create_tables()
    
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
    db.get_cur().execute("SELECT row_id, name FROM places WHERE long > ? AND long < ? AND lat > ? AND lat < ?", [lng-rng, lng+rng, lat-rng, lat+rng])
    nearby = db.get_cur().fetchall()
    if len(nearby) != 0:
        print(f"{len(nearby)} nearby")
        [print(f"* [{i['row_id']}] {i['name']}") for i in nearby]


    ins = db.get_cur().execute("INSERT INTO places(date_inserted, name, lat, long) VALUES (?, ?, ?, ?)", [dt, name, lat, lng]).rowcount
    db.get_cur().execute("SELECT row_id FROM places WHERE name = ? and lat = ? and long = ?", [name, lat, lng])
    res = db.get_cur().fetchone()
    print(f"Inserted {name} as ID {res['row_id']}")

if __name__ == "__main__":
    main()
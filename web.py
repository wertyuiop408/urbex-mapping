#webs.py
#https://flask.palletsprojects.com/en/2.1.x/
import json
import sqlite3

from flask import Flask, render_template




app = Flask(__name__, template_folder='')

@app.route("/")
@app.route("/index.html")
def index():
    return render_template("index.html")


@app.route("/bounds/<ne_lat>/<ne_lng>/<sw_lat>/<sw_lng>")
def map(ne_lat, ne_lng, sw_lat, sw_lng):
    with sqlite3.connect("urbex.db") as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        cur.execute("""SELECT row_id, name, lat, long
            FROM places
            WHERE lat < ? and lat > ? and long < ? and long > ?
            AND (places.status NOT IN (1, 4) OR places.status IS NULL)""",
            [ne_lat, sw_lat, ne_lng, sw_lng])
        res = cur.fetchall()
    print(f"found {len(res)} results")

    geojson = {
        'type': 'FeatureCollection',
        'features': list()
    }
    for x in res:
        tags = get_tags(cur, x["row_id"])
        yy = {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [x["long"], x["lat"]]
            },
            "properties": {
                "name": x['name'],
                "pid": x['row_id'],
                "loc": tags
            }
        }
        geojson["features"].append(yy)
    json_out = json.dumps(geojson)
    return json_out


@app.route("/search/<query>")
def search(query):
    with sqlite3.connect("urbex.db") as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("""SELECT places.row_id, places.name, places.lat, places.long FROM tags_ft 
            LEFT JOIN tag_rel ON tag_rel.tag_id=tags_ft.rowid
            LEFT JOIN places ON places.row_id=tag_rel.place_id
            WHERE tag match ?
            AND (places.status NOT IN (1, 4) OR places.status IS NULL)
            GROUP BY places.row_id
            LIMIT 5""", [query])

        geojson = {
            'type': 'FeatureCollection',
            'features': list()
        }

        places = cur.fetchall()
        for row in places:
            

            tags = get_tags(cur, row["row_id"])
            yy = {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [row["long"], row["lat"]]
                },
                "properties": {
                    "name": row['name'],
                    "pid": row['row_id'],
                    "loc": tags
                }
            }
            geojson["features"].append(yy)
        json_out = json.dumps(geojson)

    return json_out


def get_tags(cur, place_id):
    tag_arr = []
    for tag in cur.execute("""SELECT * from tag_rel 
        JOIN tags_ft on tag_rel.tag_id=tags_ft.ROWID
        WHERE place_id = ?
        AND tags_ft.tag MATCH "city OR county" """, [place_id]):

        tag_split = tag["tag"].split(":")
        if tag_split[0] == "county":
            tag_arr.append(tag_split[1])
        elif tag_split[0] == "city":
            tag_arr.insert(0, tag_split[1])

    return  ", ".join(tag_arr)

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

        cur.execute("select row_id, name, lat, long from places where lat < ? and lat > ? and long < ? and long > ?", [ne_lat, sw_lat, ne_lng, sw_lng])
        res = cur.fetchall()
    print(f"found {len(res)} results")

    geojson = {
        'type': 'FeatureCollection',
        'features': list()
    }
    for x in res:
        yy = {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [x["long"], x["lat"]]
            },
            "properties": {
                "name": x['name'],
                "pid": x['row_id']
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
        cur.execute("SELECT row_id, name, lat, long FROM places WHERE LOWER(name) LIKE ?", [f"%{query}%"])

        geojson = {
            'type': 'FeatureCollection',
            'features': list()
        }

        for row in cur.fetchall():
            yy = {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [row["long"], row["lat"]]
                },
                "properties": {
                    "name": row['name'],
                    "pid": row['row_id']
                }
            }
            geojson["features"].append(yy)
        json_out = json.dumps(geojson)

    return json_out
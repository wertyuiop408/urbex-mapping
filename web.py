#webs.py
#https://flask.palletsprojects.com/en/2.1.x/
import json

from flask import Flask, render_template

from db import db


app = Flask(__name__, template_folder='')

@app.route("/")
@app.route("/index.html")
def index():
    return render_template("index.html")


@app.route("/bounds/<ne_lat>/<ne_lng>/<sw_lat>/<sw_lng>")
def map(ne_lat, ne_lng, sw_lat, sw_lng):
    db.connect()
    print(ne_lat, ne_lng, sw_lat, sw_lng)

    db.get_cur().execute("select row_id, name, lat, long from places where lat < ? and lat > ? and long < ? and long > ?", [ne_lat, sw_lat, ne_lng, sw_lng])
    res = db.get_cur().fetchall()
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

    db.conn.close()
    return json_out
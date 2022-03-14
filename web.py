#web.py
from http.server import BaseHTTPRequestHandler, HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import parse_qs, urlparse
from datetime import datetime, timezone

import argparse
import time
import json

from db import db

hostname = "localhost"
server_port = 8080

class MyServer(SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def do_GET(self):
        if self.path == "/":
            self.send_response(200)
            self.path = "index.html"
            return SimpleHTTPRequestHandler.do_GET(self)
        elif self.path.startswith("/bounds?"):
            self.send_response(200)
            self.map_query()

        else:
            self.send_response(404)
            return


    def map_query(self) -> None:
        self.send_header("Content-type", "application/json")
        self.end_headers()


        
        query_parse = parse_qs(urlparse(self.path).query)
        print(self.path)
        query = [query_parse['neLat'][0], query_parse['swLat'][0], query_parse['neLng'][0], query_parse['swLng'][0]]
        db.get_cur().execute("select row_id, name, lat, long from places where lat < ? and lat > ? and long < ? and long > ?", query)
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
        self.wfile.write(bytes(json_out, "utf-8"))


def data_file() -> None:
    out_file = "data.json"
    geojson = {
        'type': 'FeatureCollection',
        'features': list()
    }

    #1 = demolished
    db.get_cur().execute("SELECT * FROM places WHERE status IS NULL OR status IS NOT 1")
    for row in db.get_cur().fetchall():
        
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
    with open(out_file, "w") as fp:
        tt = datetime.now(timezone.utc).isoformat(timespec="seconds")
        fp.write(f"//{tt}\n")
        fp.write(json_out)

    return


def main() -> None:
    db.connect()
    
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument('--dump', action="store_true")
    args = parser.parse_args()

    print(args)
    if args.dump:
        data_file()
        return

    webServer = HTTPServer((hostname, server_port), MyServer)
    print(f"Server started http://{hostname}:{server_port}")

    try:
        webServer.serve_forever()
    except KeyboardInterrupt:
        pass

    webServer.server_close()
    print("Server stopped.")


if __name__ == "__main__":
    main()
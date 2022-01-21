#web.py
from http.server import BaseHTTPRequestHandler, HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import parse_qs, urlparse
import time
import json
import sqlite3

hostname = "localhost"
server_port = 8080



class MyServer(SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def do_GET(self):
        self.send_response(200)

        if self.path == "/":
            self.path = "index.html"
            return SimpleHTTPRequestHandler.do_GET(self)
        else:
            self.send_header("Content-type", "application/json")
            self.end_headers()


            
            query_parse = parse_qs(urlparse(self.path).query)
            print(self.path)
            query = [query_parse['neLat'][0], query_parse['swLat'][0], query_parse['neLng'][0], query_parse['swLng'][0]]
            cur.execute("select name, lat, long from places where lat < ? and lat > ? and long < ? and long > ?", query)
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
                        "name": x['name']
                    }
                }
                geojson["features"].append(yy)


            json_out = json.dumps(geojson)
            self.wfile.write(bytes(json_out, "utf-8"))

            """
            long is hori
            lat is vert
            """
            #print(parse_qs(f"http://localhost{self.path}"))

def main() -> None:
    global cur
    conn = sqlite3.connect('urbex.db')
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()


    webServer = HTTPServer((hostname, server_port), MyServer)
    print(f"Server started http://{hostname}:{server_port}")

    try:
        webServer.serve_forever()
    except KeyboardInterrupt:
        pass

    webServer.server_close()
    #close db
    conn.commit()
    conn.close()
    print("Server stopped.")



if __name__ == "__main__":
    main()
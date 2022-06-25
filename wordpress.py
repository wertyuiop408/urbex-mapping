import argparse
import configparser
import json
import math
from datetime import datetime, timezone
from urllib.parse import urlsplit, urljoin

import requests
from bs4 import BeautifulSoup

from db import db


class wordpress:
    def __init__(self, url=""):
        """
        https://developer.wordpress.org/rest-api/reference/posts/#list-posts

        The WP Rest API sends the total count(found_posts) property from WP_Query. in a header called X-WP-Total.
            X-WP-Total:71
            X-WP-TotalPages:8


        """
        if url == "":
            return

        self.base_url = url
        self.config = configparser.ConfigParser()
        self.config.read("config.cfg")
        if not self.config.has_section("CRAWLERS"):
            self.config.add_section("CRAWLERS")
        return


    def crawl(self):
        fp = self.pagination()
        for page in range(1, math.ceil(fp[1]/100)+1):
            self.pagination(page, 100)
        self.write_config()
        return


    def pagination(self, page=1, per_page=10):
        _url = urljoin(self.base_url, f"/wp-json/wp/v2/posts?per_page={per_page}&page={page}")

        hostname = f"wp_{urlsplit(self.base_url).hostname}"
        if hostname in self.config["CRAWLERS"]:
            _url += f"&after={self.config['CRAWLERS'][hostname]}"

        fp = requests.get(_url)
        
        total = int(fp.headers["X-WP-Total"])
        content = json.loads(fp.content)
        count = len(content)
        

        sql_stmnt = """INSERT OR IGNORE INTO refs(url, title, date_inserted, date_post) 
            SELECT ?, ?, ?, ? WHERE NOT EXISTS (SELECT 1 FROM refs WHERE url = ?1)"""

        crawl_date = datetime.now(timezone.utc).isoformat(timespec="seconds")
        arr = list()

        for item in content:
            arr.append([
                item["link"],
                item["title"]["rendered"],
                crawl_date,
                item["date"]
            ])

        ins = db.get_cur().executemany(sql_stmnt, arr).rowcount
        print(f"inserted {ins} records")

        return (count, total)


    def insert(self, url):
        """
        Insert a single reference URL
        """
        db.get_cur().execute("SELECT row_id FROM refs WHERE url = ?", [url])
        res = db.get_cur().fetchone()
        
        if res is not None:
            print("already exists")
            return

        page = requests.get(url)
        soup = BeautifulSoup(page.content, "html.parser")
        title = soup.find("meta", property="og:title")["content"]
        _url = soup.find("meta", property="og:url")["content"]
        pt = soup.find("meta", property="article:published_time")["content"]

        sql_stmnt = """INSERT OR IGNORE INTO refs(url, title, date_inserted, date_post) 
            SELECT ?, ?, ?, ? WHERE NOT EXISTS (SELECT 1 FROM refs WHERE url = ?1)"""

        crawl_date = datetime.now(timezone.utc).isoformat(timespec="seconds")
        db.get_cur().execute(sql_stmnt, [_url, title, crawl_date, pt])

        return


    def write_config(self) -> None:
        write_time = datetime.now().isoformat(timespec="seconds")
        hostname = f"wp_{urlsplit(self.base_url).hostname}"
        self.config.set("CRAWLERS", hostname, str(write_time))

        with open('config.cfg', 'w') as configfile:
            self.config.write(configfile)
        return

      
if __name__ == "__main__":
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument('site')
    args = parser.parse_args()

    db.connect()
    x = wordpress(args.site)
    x.crawl()
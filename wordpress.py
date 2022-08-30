import json
import math
from datetime import datetime, timezone
from urllib.parse import urlsplit, urljoin

import requests
from bs4 import BeautifulSoup
import tomlkit
import urllib3

from db import db


#disable warnings in requests about SSL certs being invalid
urllib3.disable_warnings()


class wordpress:
    def __init__(self, cfg, index = 0) -> None:
        """
        https://developer.wordpress.org/rest-api/reference/posts/#list-posts

        The WP Rest API sends the total count(found_posts) property from WP_Query. in a header called X-WP-Total.
            X-WP-Total:71
            X-WP-TotalPages:8


        """
        self.cfg = cfg
        self.index = index
        return


    def crawl(self):
        fp = self.pagination()
        for page in range(1, math.ceil(fp[1]/100)+1):
            self.pagination(page, 100)
        write_time = datetime.now().isoformat(timespec="seconds")
        self.cfg["lc"] = write_time
        self.write_config()
        return


    def pagination(self, page=1, per_page=10):
        _url = urljoin(self.cfg["url"], f"wp-json/wp/v2/posts?per_page={per_page}&page={page}")

        if self.cfg.get("lc") != None:
            _url += f"&after={self.cfg['lc']}"

        fp = requests.get(_url, verify=False)
        if page == 1:
            print(f"[{fp.status_code}] "+ urljoin(self.cfg["url"], "/"))

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
        print(f"    inserted {ins} records")

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

        page = requests.get(url, verify=False)
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
        """
        Saves the changes to the configuration to file.
        The changes are the latest times of the crawl for each subreddit
        """
        with open("config.cfg", mode="r+t", encoding="utf-8") as fp:
            cfg = tomlkit.load(fp)
            fp.seek(0)

            # update the crawlers config and write to file
            cfg["crawler"]["wordpress"][self.index].update(self.cfg)
            fp.write(tomlkit.dumps(cfg))
        return

      
if __name__ == "__main__":
    """
    #not really needed with the config now
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument('site')
    args = parser.parse_args()
    """
    db.connect()

    with open("config.cfg", mode="rt", encoding="utf-8") as f:
        conf = tomlkit.load(f)

    if conf.get("crawler", {}).get("wordpress") == None:
        print("No wordpress entry found")
        exit()

    for index, wp in enumerate(conf["crawler"]["wordpress"]):
        x = wordpress(wp, index)
        x.crawl()
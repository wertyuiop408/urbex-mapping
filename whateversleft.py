import json
import math
from datetime import datetime, timezone

import requests
from bs4 import BeautifulSoup

from db import db


class whateversleft:
    def __init__(self):
        """
        this site seems to be based off of word-press
        https://developer.wordpress.org/rest-api/reference/posts/#list-posts

        The WP Rest API sends the total count(found_posts) property from WP_Query. in a header called X-WP-Total.
            X-WP-Total:71
            X-WP-TotalPages:8


        """
        self.base_url = "https://www.whateversleft.co.uk"
        return

    def crawl(self):

        fp = self.pagination()
        print(fp)
        for page in range(1, math.ceil(fp[1]/100)+1):
            self.pagination(page, 100)

        return

    def pagination(self, page=1, per_page=10):
        #for each page
        #get, and insert to db (if possible)
        #is there more?
        print(page)
        _url = f"{self.base_url}/wp-json/wp/v2/posts?per_page={per_page}&page={page}"
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


    def get_page(self, url):
        db.get_cur().execute("SELECT row_id FROM refs WHERE url = ?", [url])
        res = db.get_cur().fetchone()
        
        if res is not None:
            return

        page = requests.get(url)
        soup = BeautifulSoup(sitemap.content, "html.parser")

      
if __name__ == "__main__":
    db.connect()
    x = whateversleft()
    x.crawl()
    #x.get_page("https://www.whateversleft.co.uk/underground/roc-post/")
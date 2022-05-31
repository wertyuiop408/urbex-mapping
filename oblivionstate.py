from datetime import datetime, timezone
from urllib.parse import urlparse, urljoin
from collections import namedtuple
import string
import requests

from bs4 import BeautifulSoup

from db import db


class oblivionstate:
    base_url = "https://www.oblivionstate.com/community/forums/"
    suffix_url = "?order=post_date&direction=desc"
    sections = [
        "industrial-locations.11/",
        "manors-mansions-residential.26/",
        "medical-institutions.12/",
        "public-buildings-education-leisure.13/",
        "underground-explores.45/",
        "military-sites.10/",
        "high-places.54/",
        "religious-sites.27/",
        "anything-else.16/",
        "short-reports.31/",
        "photo-only-threads.33/"
    ]


    def __init__(self) -> None:
        #use this var to force looking through sections we already have crawled
        self.force = False
        return


    def crawl(self) -> None:
        #total entries
        total_in = 0

        #crawl each section listed in the list
        for section in self.sections:
            sect = self.crawl_section(section)
            total_in += sect[0]
            print(f"{section} Inserted {sect[0]}/{sect[1]} rows from {sect[2]}/{sect[3]} pages")

        print(f"Total inserted: {total_in}")
        return


    def crawl_section(self, section: str, page: int = 1) -> tuple:
        print(f"{section} starting crawl")

        # we still want to allow duplicate url in general, but for crawling, we only want to have 1
        sql_stmnt = """INSERT OR IGNORE INTO refs(url, title, date_inserted, date_post) 
            SELECT ?, ?, ?, ? WHERE NOT EXISTS (SELECT 1 FROM refs WHERE url = ?1)"""
        total_entries = 0
        inserted_entries = 0
        max_pages = 0

        while True:
            abs_url = f"{self.base_url}{section}page-{page}{self.suffix_url}"
            entry = self.get_section_page(abs_url)

            #make sure that if the page fails, then we stop crawling that section
            if entry["status_code"] != 200:
                print(f"[{entry['status_code']}]{section} Page:{page}")
                break

            max_pages = entry["max_pages"]
            db.get_cur().execute("BEGIN")
            inserted_count = db.get_cur().executemany(sql_stmnt, entry["data"]).rowcount
            db.get_cur().execute("COMMIT")
            
            inserted_entries += inserted_count
            total_entries += len(entry["data"])


            if inserted_count == 0 and self.force == False:
                #print(f"{section} 0 entries inserted")
                break

            if inserted_count < len(entry["data"]):
                print(f"{section}, page {page} missing entries. {inserted_count}/{len(entry['data'])} inserted")

            page += 1
            if page > max_pages:
                break

        return (inserted_entries, total_entries, page, max_pages)



    def get_section_page(self, direct_url: str) -> dict:
        page = requests.get(direct_url)

        if page.status_code != 200:
            return {'status_code':page.status_code}

        crawl_date = datetime.now(timezone.utc).isoformat(timespec="seconds")
        soup = BeautifulSoup(page.content, "html.parser")
        list_of_threads = soup.select(".structItemContainer-group > .structItem--thread")
        max_pages = int(soup.select("ul.pageNav-main > li.pageNav-page:nth-last-of-type(1) > a")[0].text)
        ret_list = list()


        for x in list_of_threads:
            title = str(x.select_one(".structItem-title").get_text().strip())
            thread_url = urljoin(direct_url, x.select_one(".structItem-title > a:last-of-type").get("href"))
            thread_date = x.select_one("time").get("datetime")

            ret_list.append([thread_url, title, crawl_date, thread_date])

        return {"status_code":page.status_code, "max_pages": max_pages, "data": ret_list}



    def get_thread(self, url: str) -> None:
        return



if __name__ == "__main__":
    db.connect()
    os = oblivionstate()
    os.crawl()
    
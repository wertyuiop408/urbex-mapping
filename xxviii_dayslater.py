#dlater.py
from datetime import datetime, timezone
from urllib.parse import urlparse, urljoin
from collections import namedtuple
import string
import requests
from bs4 import BeautifulSoup
from db import db


class xxviii_dayslater:

    base_url = "https://www.28dayslater.co.uk/forum/"
    suffix_url = "?order=post_date&direction=desc"
    sections = [
        "noteworthy-reports.115/",
        "asylums-and-hospitals.4/",
        "high-stuff.35/",
        "industrial-sites.6/",
        "leisure-sites.7/",
        "residential-sites.92/",
        "military-sites.5/",
        "mines-and-quarries.95/",
        "roc-posts.50/",
        "restored-roc-posts.82/",
        "theatres-and-cinemas.78/",
        "uk-draining-forum.94/",
        "underground-sites.29/",
        "european-and-international-sites.46/",
        "other-sites.8/",
        "leads-rumours-and-news.57/",
        "photo-threads.158/",
        "diehardlove.122/",
        "downfallen.121/",
        "solomon.123/"
    ]

    def __init__(self):
        self.force = False
        return


    def crawl(self):
        for section in self.sections:
            self.crawl_section(section)
        return


    def crawl_section(self, section, page = 1) -> None:
        print(f"{section} starting crawl")
        sql_stmnt = "INSERT OR IGNORE INTO refs(url, title, date_inserted, date_post) VALUES (?, ? ,? ,?)"
        total_entries = 0
        inserted_entries = 0
        max_pages = 0

        while True:
            abs_url = f"{self.base_url}{section}page-{page}{self.suffix_url}"
            entry = self.get_section_page(abs_url)

            if entry["status_code"] != 200:
                print(f"[{entry['status_code']}]{section} Page:{page}")
                break

            max_pages = int(entry["max_pages"])
            db.get_cur().execute("BEGIN")
            inserted_count = db.get_cur().executemany(sql_stmnt, entry["data"]).rowcount
            db.get_cur().execute("COMMIT")
            inserted_entries += inserted_count
            total_entries += len(entry["data"])
            if inserted_count == 0 and self.force == False:
                print(f"{section} 0 entries inserted")
                return

            if inserted_count < len(entry["data"]):
                print(f"{section}, page {page} missing entries. {inserted_count}/{len(entry['data'])} inserted")

            page += 1
            if page > max_pages:
                break

        print(f"{section} Inserted {inserted_entries}/{total_entries} rows from {page}/{max_pages} pages")
        return


    def get_section_page(self, direct_url):
        page = requests.get(direct_url)

        if page.status_code != 200:
            return {'status_code':page.status_code}

        crawl_date = datetime.now(timezone.utc).isoformat(timespec="seconds")
        soup = BeautifulSoup(page.content, "html.parser")
        list_of_threads = soup.select(".structItemContainer-group > .structItem--thread")
        max_pages = soup.select("ul.pageNav-main > li.pageNav-page:nth-last-of-type(1) > a")[0].text
        ret_list = list()


        for x in list_of_threads:
            title = str(x.select_one(".structItem-title").get_text().strip())
            thread_url = urljoin(direct_url, x.select_one(".structItem-title > a:last-of-type").get("href"))
            thread_date = x.select_one("time").get("datetime")

            ret_list.append([thread_url, title, crawl_date, thread_date])

        return {"status_code":page.status_code, "max_pages": max_pages, "data": ret_list}



    def get_thread(self) -> None:
        page = requests.get(url)
        soup = BeautifulSoup(page.content, "html.parser")
        name = soup.select_one(".p-title-value").text
        tags = [i.text for i in soup.select(".tagItem")]
        print(name, tags)
        raise NotImplementedError
        return


    def check_db():
        return

#x = xxviii_dayslater()
# import xxviii_dayslater as d2l
# d2l.xxviii_dayslater()
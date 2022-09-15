from datetime import datetime, timezone
from urllib.parse import urlparse, urljoin
from collections import namedtuple
import string

import requests
from bs4 import BeautifulSoup
import tomlkit
import urllib3

#disable warnings in requests about SSL certs being invalid
urllib3.disable_warnings()


from db import db


class xenforo:
    
    suffix_url = "?order=post_date&direction=desc"
    

    def __init__(self, cfg, index=0) -> None:
        self.cfg = cfg
        self.index = index
        #use this var to force looking through sections we already have crawled
        self.force = False

        return


    def crawl(self) -> None:
        #total entries
        total_in = 0
        _url = urljoin(self.cfg["url"], "/")
        print(_url)

        #crawl each section listed in the list
        for i, section in enumerate(self.cfg["subs"]):
            sect = self.crawl_section(section)
            write_time = datetime.now().isoformat(timespec="seconds")
            section.insert(1, write_time)
            self.cfg["subs"][i] = section[:2]
            self.write_config()

            total_in += sect[0]
            print(f"    {section[0]} Inserted {sect[0]}/{sect[1]} rows from {sect[2]}/{sect[3]} pages")

        print(f"    Total inserted: {total_in}")
        return


    def crawl_section(self, section_arr: list, page: int = 1) -> tuple:
        # quick fix, index 1 is a time (if it exists) of last crawl
        section = section_arr[0]

        # we still want to allow duplicate url in general, but for crawling, we only want to have 1
        sql_stmnt = """INSERT OR IGNORE INTO refs(url, title, date_inserted, date_post) 
            SELECT ?, ?, ?, ? WHERE NOT EXISTS (SELECT 1 FROM refs WHERE url = ?1)"""
        total_entries = 0
        inserted_entries = 0
        max_pages = 0

        while True:
            abs_url = f"{self.cfg['url']}{section}page-{page}{self.suffix_url}"
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
        page = requests.get(direct_url, verify=False)

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



    def get_thread(self, url: str) -> list:
        page = requests.get(url, verify=False)
        soup = BeautifulSoup(page.content, "html.parser")
        name = soup.select_one(".p-title-value").text
        thread_date = soup.select_one(".u-concealed > time").get("datetime")

        tags = [i.text for i in soup.select(".tagItem")]
        return [name, tags, thread_date]


    def write_config(self) -> None:
        """
        Saves the changes to the configuration to file.
        The changes are the latest times of the crawl for each subreddit
        """
        with open("config.cfg", mode="r+t", encoding="utf-8") as fp:
            cfg = tomlkit.load(fp)
            fp.seek(0)

            # update the crawlers config and write to file
            cfg["crawler"]["xenforo"][self.index].update(self.cfg)
            fp.write(tomlkit.dumps(cfg))
        return


if __name__ == "__main__":
    db.connect()

    with open("config.cfg", mode="rt", encoding="utf-8") as f:
        conf = tomlkit.load(f)

    if conf.get("crawler", {}).get("xenforo") == None:
        print("No forum entry found")
        exit()

    for index, forum in enumerate(conf["crawler"]["xenforo"]):
        x = xenforo(forum, index)
        x.crawl()
    
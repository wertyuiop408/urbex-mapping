#python script to harvest info from urban exploring sites and add it to a database so that it can be displayed on a map

from datetime import datetime, timezone
from urllib.parse import urlparse, urljoin
import string
import requests
import sqlite3
from bs4 import BeautifulSoup

def main() -> None:
    global cur
    conn = sqlite3.connect('urbex.db')
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    createTables()
    #getThread('https://www.28dayslater.co.uk/threads/porth-wen-brickworks-anglesey-north-wales-january-2022.131644/')
    get_forum_section("https://www.28dayslater.co.uk/forum/industrial-sites.6/?order=post_date&direction=desc")

    #close db
    conn.commit()
    conn.close()
    return


def createTables() -> None:
    #use text for date, this way we can never run into unsolvable practices, such as y2k, or government deciding years don't exist (looking at you russia)
    #ISO 8601 for the date ofc though
    cur.execute("""CREATE TABLE IF NOT EXISTS "places" (
        row_id INTEGER PRIMARY KEY,
        date_inserted TEXT,
        last_updated TEXT,
        name TEXT,
        long REAL,
        lat REAL,
        notes TEXT,
        status INTEGER
        )""")


    cur.execute("""CREATE TABLE IF NOT EXISTS "parking" (
        place_id INTEGER,
        lat REAL,
        long REAL,
        paid INTEGER,
        FOREIGN KEY ("place_id") REFERENCES places("row_id")
        )""")


    #are tags categories?
    cur.execute("""CREATE TABLE IF NOT EXISTS "tags" (
        place_id INTEGER,
        tag TEXT,
        UNIQUE("place_id", "tag"),
        FOREIGN KEY ("place_id") REFERENCES places("row_id")
        )""")


    #handle our data sources for parsing
    cur.execute("""CREATE TABLE IF NOT EXISTS "refs" (
        row_id INTEGER PRIMARY KEY,
        url TEXT,
        title TEXT,
        place_id INTEGER,
        date_inserted TEXT,
        date_scrape TEXT,
        raw TEXT,
        UNIQUE("url")
        )""")

    #create a table to handle changes and modifications?
    return


def get_forum_section(url: str, page: int = 1) -> None:
    url_parse = urlparse(url)
    starting_page = url_parse._replace(path=f"{url_parse.path}page-{page}").geturl()
    max_pages = get_forum_section_page(starting_page)
    #xx = xurl.path.strip('/').split('/')


    for i in range(page+1, max_pages + 1):
        print(f"crawling page {i} of {max_pages}")
        xx = url_parse._replace(path=f"{url_parse.path}page-{i}").geturl()
        get_forum_section_page(xx)    
    return


def get_forum_section_page(url: str) -> int:
    #https://www.28dayslater.co.uk/forum/industrial-sites.6/page-2?order=post_date&direction=desc
    page = requests.get(url)
    soup = BeautifulSoup(page.content, "html.parser")
    list_of_threads = soup.select(".structItemContainer-group > .structItem--thread")
    crawl_date = datetime.now(timezone.utc).isoformat(timespec="seconds")

    max_pages = soup.select("ul.pageNav-main > li.pageNav-page:nth-last-of-type(1) > a")[0].text

    for x in list_of_threads:
        title = str(x.select_one(".structItem-title").get_text().strip())
        thread_url = x.select("a")[0].get("href")
        thread_url_abs = urljoin(url, thread_url)

        err_count = 0
        try:
            cur.execute("INSERT INTO refs VALUES (NULL, ?, ?, NULL, ?, NULL, NULL)", (thread_url_abs, title, crawl_date))
        except Exception:
            #find out the real exception type later
            err_count++


    return int(max_pages)


def getThread(url:str) -> None:
    page = requests.get(url)
    soup = BeautifulSoup(page.content, "html.parser")
    name = soup.select_one(".p-title-value").text
    tags = [i.text for i in soup.select(".tagItem")]
    print(name, tags)

    


if __name__ == "__main__":
    main()
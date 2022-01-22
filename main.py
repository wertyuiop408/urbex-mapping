#python script to harvest info from urban exploring sites and add it to a database so that it can be displayed on a map

from datetime import datetime, timezone
from urllib.parse import urlparse, urljoin
from collections import namedtuple
import string
import requests
import sqlite3
from bs4 import BeautifulSoup
from db import create_tables

def main() -> None:
    global cur
    conn = sqlite3.connect('urbex.db')
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    create_tables(cur)
    
    #getThread('https://www.28dayslater.co.uk/threads/porth-wen-brickworks-anglesey-north-wales-january-2022.131644/')
    #get_forum_section("https://www.28dayslater.co.uk/forum/industrial-sites.6/?order=post_date&direction=desc")
    get_2dl()

    #close db
    conn.commit()
    conn.close()
    return


def get_2dl() -> None:
    base_url = "https://www.28dayslater.co.uk/forum/"
    suffix_url = "?order=post_date&direction=desc"

    url_list = [
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

    for i in url_list:
        section_url = f"{base_url}{i}{suffix_url}"
        get_forum_section(section_url)
    return


def get_forum_section(url: str, page: int = 1) -> None:
    url_parse = urlparse(url)
    starting_page = url_parse._replace(path=f"{url_parse.path}page-{page}").geturl()
    max_pages = get_forum_section_page(starting_page).max_pages
    #xx = xurl.path.strip('/').split('/')
    print(f"crawling {url_parse.path} -- {max_pages} pages")


    for i in range(page+1, max_pages + 1):
        xx = url_parse._replace(path=f"{url_parse.path}page-{i}").geturl()
        get = get_forum_section_page(xx)
        print(f"[{get.status_code}]crawling page {i} of {max_pages}")

        if get.error_cnt == get.thread_cnt:
            print(f"breaking on page {i} (possibly no newer threads)")
            break
    return


def get_forum_section_page(url: str) -> int:
    nt = namedtuple('gfsp', ["max_pages", "error_cnt", "thread_cnt", "status_code"])

    #https://www.28dayslater.co.uk/forum/industrial-sites.6/page-2?order=post_date&direction=desc
    page = requests.get(url)
    soup = BeautifulSoup(page.content, "html.parser")
    list_of_threads = soup.select(".structItemContainer-group > .structItem--thread")
    crawl_date = datetime.now(timezone.utc).isoformat(timespec="seconds")

    max_pages = soup.select("ul.pageNav-main > li.pageNav-page:nth-last-of-type(1) > a")[0].text
    err_count = 0
    cur.execute("BEGIN")

    for x in list_of_threads:
        title = str(x.select_one(".structItem-title").get_text().strip())
        thread_url = x.select("a")[0].get("href")
        thread_url_abs = urljoin(url, thread_url)
        thread_date = x.select_one("time").get("datetime")
                
        try:
            cur.execute("INSERT INTO refs VALUES (NULL, ?, ?, NULL, ?, NULL, ?, NULL)", (thread_url_abs, title, crawl_date, thread_date))
        except Exception:
            #find out the real exception type later
            err_count = err_count+1
    cur.execute("COMMIT")

    return nt(int(max_pages), err_count, len(list_of_threads), page.status_code)


def getThread(url:str) -> None:
    page = requests.get(url)
    soup = BeautifulSoup(page.content, "html.parser")
    name = soup.select_one(".p-title-value").text
    tags = [i.text for i in soup.select(".tagItem")]
    print(name, tags)

    


if __name__ == "__main__":
    main()
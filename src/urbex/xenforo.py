import asyncio
import time
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import urljoin, urlparse

from aiohttp.client import ClientSession
from bs4 import BeautifulSoup, Tag
from config import config
from db_tables import refs
from spider import *
from yarl import URL


class xenforo(spider):
    suffix_url = "?order=post_date&direction=desc"

    def __init__(self, url_: str, sess: ClientSession) -> None:
        self.sess = sess  # type: ClientSession
        self.crawl_times = dict()  # type: ignore

        self.base_url = url_.strip(" ").rstrip("/") + "/"
        # self.crawl()

    def crawl(self) -> None:
        conf = config()
        index = conf.get_crawler_index(self.base_url)

        subs = conf.cfg["crawler"]
        if not isinstance(subs, dict):
            return

        subs = subs["xenforo"]
        if not isinstance(subs, list):
            return

        subs = subs[index]["subs"]
        if not isinstance(subs, list):
            return

        for i, v in enumerate(subs):
            _url = self.base_url + subs[i][0] + self.suffix_url
            self._add_url(_url, partial(self.parse_section, nxt=True))
        return

    def get_config_time(self, section: str) -> Optional[str]:
        conf = config()
        crawler_index = conf.get_crawler_index(self.base_url)
        if crawler_index == -1:
            return None

        subs = conf.cfg["crawler"]
        if not isinstance(subs, dict):
            return None

        subs = subs["xenforo"]
        if not isinstance(subs, list):
            return None

        sub_index = conf.get_sub_index(subs[crawler_index], section)
        if sub_index == -1:
            return None

        subs = subs[crawler_index]["subs"]
        if not isinstance(subs, list):
            return None

        if len(subs[sub_index]) < 2:
            return None

        try:
            lc = datetime.fromisoformat(str(subs[sub_index][1])).astimezone(
                timezone.utc
            )
        except Exception:
            lc = None
        return lc

    def write_config_time(self, section: str, time_: str) -> None:
        conf = config()
        crawler_index = conf.get_crawler_index(self.base_url)
        if crawler_index == -1:
            return

        subs = conf.cfg["crawler"]
        if not isinstance(subs, dict):
            return

        subs = subs["xenforo"]
        if not isinstance(subs, list):
            return

        sub_index = conf.get_sub_index(subs[crawler_index], section)

        subs = subs[crawler_index]["subs"]
        if not isinstance(subs, list):
            return

        subs[sub_index] = [section, time_]
        conf.save()
        return

    async def parser(self, res, *cb1, **cb2):
        # based on the url, decide which parser to use
        if res.url.parts[1] == "forum":
            return await self.parse_section(res, *cb1, **cb2)

        elif res.url.parts[1] == "threads":
            return await self.parse_thread(res, *cb1, **cb2)

        else:
            return self.save_url(res)
        return

    async def parse_section(self, res, *cb1, **cb2) -> None:
        crawl_date = datetime.now(timezone.utc).isoformat(timespec="seconds")

        # get the section name, and page number from the url
        _url = res.url
        _url_path_split = [s for s in _url.path.split("/") if s]

        if _url_path_split[0] != "forum":
            return

        section = _url_path_split[1]

        txt = await res.text()
        soup = BeautifulSoup(txt, "lxml")
        list_of_threads = soup.select(
            ".structItemContainer-group > .structItem--thread"
        )
        curr_page = int(
            soup.select("ul.pageNav-main > li.pageNav-page--current > a")[0].text
        )
        max_pages = int(
            soup.select("ul.pageNav-main > li.pageNav-page:nth-last-of-type(1) > a")[
                0
            ].text
        )

        # get date of first non stickied post
        first_post_date2 = soup.select(
            ".structItemContainer-group.js-threadList > .structItem--thread"
        )[0].select_one("time")
        if not isinstance(first_post_date2, Tag):
            return
        first_post_date = str(first_post_date2.get("datetime"))

        ret_list = list()
        for x in list_of_threads:
            lot_title = ""
            lot_url = ""
            lot_date_post = ""
            lot_date_inserted = ""

            lot_title_select = x.select_one(".structItem-title")
            if isinstance(lot_title_select, Tag):
                lot_title = str(lot_title_select.get_text().strip())

            lot_url_select = x.select_one(".structItem-title > a:last-of-type")
            if isinstance(lot_url_select, Tag):
                lot_url = urljoin(str(_url), str(lot_url_select.get("href")))

            lot_date_post_select = x.select_one("time")
            if isinstance(lot_date_post_select, Tag):
                lot_date_post = str(lot_date_post_select.get("datetime"))

            # check if one at least has some data
            if all(
                i == "" for i in [lot_title, lot_url, lot_date_post, lot_date_inserted]
            ):
                return

            data = refs(
                title=lot_title.strip().replace("\n", " "),
                url=lot_url,
                date_post=lot_date_post,
                date_inserted=crawl_date,
            )
            ret_list.append(data)
        self.save_to_db(ret_list)

        if cb2.get("nxt"):
            self.next_urls(section, curr_page, max_pages, first_post_date, crawl_date)
        return ret_list

    async def parse_thread(self, res, *cb1, **cb2) -> None:
        crawl_date = datetime.now(timezone.utc).isoformat(timespec="seconds")

        txt = await res.text()
        soup = BeautifulSoup(txt, "lxml")
        title = soup.select_one("div.p-title").get_text().replace("\xa0", " ").strip()
        thread_date = soup.select_one("div.p-description time").get("datetime")
        data = refs(
            title=title,
            url=str(res.url),
            date_post=thread_date,
            date_inserted=crawl_date,
        )

        self.save_to_db([data])
        return data

    def next_urls(self, section, page_no, max_pages, first_post_date, crawl_date):
        # cheesy hack for timezone fix to ISO8601
        if first_post_date[-5] == "+":
            first_post_date = first_post_date[:-2] + ":" + first_post_date[-2:]

        post_date = datetime.fromisoformat(first_post_date)

        if page_no == 1:
            self.crawl_times[section] = crawl_date

        gct = self.get_config_time(section + "/")

        # if the config is newer than the post
        if gct != None and gct > post_date:
            self.write_config_time(section + "/", self.crawl_times[section])
            return

        # generate next batch of section urls to crawl.
        url_limit = getattr(self.sess._connector, "limit_per_host", 5)
        if url_limit == 0:
            url_limit = 5

        for i in range(1, url_limit + 1):
            nxt_page = page_no + i

            if nxt_page > max_pages:
                self.write_config_time(section + "/", self.crawl_times[section])
                break
            nxt = False

            if i == url_limit:
                nxt = True
            _url = self.base_url + section + "/page-" + str(nxt_page) + self.suffix_url
            self._add_url(_url, partial(self.parse_section, nxt=nxt))

        return

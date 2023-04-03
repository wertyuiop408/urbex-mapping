from datetime import datetime, timezone
import time
from urllib.parse import urlparse, urljoin
import asyncio
from typing import Optional

from spider import *
from bs4 import BeautifulSoup
from bs4 import Tag
from yarl import URL
from aiohttp.client import ClientSession

from db_tables import refs
from config import config


class xenforo(spider):
    suffix_url = "?order=post_date&direction=desc"

    def __init__(self, url_: str, sess: ClientSession) -> None:
        self.sess = sess  # type: ClientSession
        self.crawl_times = dict()  # type: ignore

        self.base_url = url_.strip(" ").rstrip("/") + "/"
        #self.crawl()

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
            lc = datetime.fromisoformat(str(subs[sub_index][1])).astimezone(timezone.utc)
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

    async def parse_section(self, res, *cb1, **cb2) -> None:
        crawl_date = datetime.now(timezone.utc).isoformat(timespec="seconds")

        # get the section name, and page number from the url
        _url = res.url
        _url_path_split = [s for s in _url.path.split("/") if s]

        if _url_path_split[0] != "forum":
            return

        section = _url_path_split[1]
        if self.crawl_times.get(section) == None:
            self.crawl_times[section] = crawl_date
            #write the config here

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

        # cheesy hack for timezone fix to ISO8601
        if first_post_date[-5] == "+":
            first_post_date = first_post_date[:-2] + ":" + first_post_date[-2:]

        post_date = datetime.fromisoformat(first_post_date)
        gct = self.get_config_time(section + "/")

        # is it older
        if gct != None:
            if post_date < gct:
                #self.write_config_time(section + "/", self.crawl_times[section])
                cb2["nxt"] = False

        # generate next batch of section urls to crawl.
        url_limit = getattr(self.sess._connector, "limit_per_host", 5)
        if url_limit == 0:
            url_limit = 5

        if cb2.get("nxt"):
            for i in range(0, url_limit):
                # if there are no more pages in section, then stop
                if (curr_page + i + 1) > max_pages:
                    break

                _url = (
                    self.base_url
                    + section
                    + "/page-"
                    + str(curr_page + i)
                    + self.suffix_url
                )

                # set the last one of each batch
                nxt = False
                if i + 1 == url_limit:
                    nxt = True
                self._add_url(_url, partial(self.parse_section, nxt=nxt))

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
            ret_list.append(data.__dict__)
        self.save_to_db(ret_list)

        return ret_list

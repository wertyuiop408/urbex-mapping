import asyncio
import math
import re
from datetime import datetime, timezone
from urllib.parse import urljoin, urlparse

from aiohttp.client import ClientSession
from config import config
from db_tables import refs
from spider import *


class wordpress(spider):
    def __init__(self, url_: str, sess: ClientSession) -> None:
        self.sess = sess  # type: ClientSession
        self.crawl_time = None

        self.base_url = url_.strip(" ").rstrip("/") + "/"

    def get_config_time(self):
        conf = config()
        crawler_index = conf.get_crawler_index(self.base_url, "wordpress")

        if crawler_index == -1:
            return None

        subs = conf.cfg["crawler"]
        if not isinstance(subs, dict):
            return None

        subs = subs["wordpress"]
        if not isinstance(subs, list):
            return None

        lc = subs[crawler_index]["lc"]
        if not isinstance(lc, str):
            return None

        try:
            lc = datetime.fromisoformat(str(lc))
        except Exception:
            lc = None
        return lc

    async def parser(self, res, *cb1, **cb2):
        if res.url.path == "/":
            url_ = (
                self.base_url
                + "wp-json/wp/v2/posts?per_page="
                + str(100)
                + "&page="
                + str(1)
            )
            self._add_url(url_, partial(self.parse, nxt=True))
            return

        elif re.match(re.compile(r"^/wp-json/wp/v2/posts/?$"), res.url.path):
            return await self.parse(res, *cb1, **cb2)

        elif re.match(re.compile(r"^/wp-json/wp/v2/posts/.+"), res.url.path):
            return await self.parse_post(res, *cb1, **cb2)

        else:
            self.save_url(res)
        return

    async def parse(self, res, *cb1, **cb2):
        crawl_date = datetime.now(timezone.utc).isoformat(timespec="seconds")
        results_per_page = 10

        # check it's valid
        header_wptotal = res.headers.get("X-WP-Total")
        if not header_wptotal:
            return

        try:
            content = await res.json()
        except Exception:
            return

        ret_list = list()
        for row in content:
            if not isinstance(row, dict):
                return

            data = refs(
                title=row["title"]["rendered"],
                url=row["link"],
                date_post=row["date"],
                date_inserted=crawl_date,
            )
            ret_list.append(data)
        self.save_to_db(ret_list)

        if cb2.get("nxt"):
            first_post_date = str(content[0].get("date"))
            curr_page_no = int(res.url.query.get("page", 1))
            max_pages = math.ceil(int(header_wptotal) / results_per_page)
            self.next_urls(
                curr_page_no, max_pages, results_per_page, first_post_date, crawl_date
            )

        return ret_list

    async def parse_post(self, res, *cb1, **cb2):
        crawl_date = datetime.now(timezone.utc).isoformat(timespec="seconds")
        content = await res.json()
        data = refs(
            title=content["title"]["rendered"],
            url=content["link"],
            date_post=content["date"],
            date_inserted=crawl_date,
        )

        self.save_to_db([data])
        return data

    def next_urls(
        self, page_no, max_pages, results_per_page, first_post_date, crawl_date
    ):
        post_date = datetime.fromisoformat(first_post_date)
        gct = self.get_config_time()

        if page_no == 1:
            self.crawl_time = crawl_date

        if gct != None and gct > post_date:
            self.write_config_time(self.crawl_time)
            return

        # number of urls to generate
        url_limit = getattr(self.sess._connector, "limit_per_host", 5)
        if url_limit == 0:
            url_limit = 5

        for i in range(1, url_limit + 1):
            nxt_page = page_no + i

            if nxt_page > max_pages:
                self.write_config_time(self.crawl_time)
                break
            nxt = False

            if i == url_limit:
                nxt = True
            _url = (
                self.base_url
                + "wp-json/wp/v2/posts?per_page="
                + str(results_per_page)
                + "&page="
                + str(nxt_page)
            )
            self._add_url(_url, partial(self.parse, nxt=nxt))

        return

    def write_config_time(self, time_=""):
        conf = config()
        crawler_index = conf.get_crawler_index(self.base_url, "wordpress")

        if crawler_index == -1:
            return None

        item = conf.cfg["crawler"]["wordpress"][crawler_index]
        item["lc"] = time_
        conf.save()
        return

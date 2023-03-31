import asyncio
from datetime import datetime, timezone
import math
from urllib.parse import urlparse, urljoin

from aiohttp.client import ClientSession

from db_tables import refs
from config import config
from spider import *


class wordpress(spider):
    def __init__(self, url_: str, sess: ClientSession) -> None:
        self.sess = sess  # type: ClientSession
        self.crawl_times = dict()  # type: ignore

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
        return lc

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
            ret_list.append(data.__dict__)
        self.save_to_db(ret_list)

        # if the post is older than the last time we crawled, then don't bother crawling more
        #if nxt is set to False, then this code is redundant
        first_post_date = str(content[0].get("date"))
        post_date = datetime.fromisoformat(first_post_date)
        gct = self.get_config_time()

        if gct != None:
            config_date = datetime.fromisoformat(str(gct))
            if post_date < config_date:
                cb2["nxt"] = False

        # generate next batch of section urls to crawl.
        if cb2.get("nxt"):
            curr_page_no = int(res.url.query["page"])
            max_pages = math.ceil(int(header_wptotal) / results_per_page)

            # number of urls to generate
            url_limit = getattr(self.sess._connector, "limit_per_host", 5)
            if url_limit == 0:
                url_limit = 5

            for i in range(0, url_limit):
                # don't exceed max pages
                if (curr_page_no + i + 1) > max_pages:
                    break

                _url = (
                    self.base_url
                    + "wp-json/wp/v2/posts?per_page="
                    + str(results_per_page)
                    + "&page="
                    + str(curr_page_no + i + 1)
                )

                nxt = False
                if i + 1 == url_limit:
                    nxt = True
                self._add_url(_url, partial(self.parse, nxt=nxt))

        return ret_list

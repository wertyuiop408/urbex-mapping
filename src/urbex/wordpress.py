import asyncio
from aiohttp.client import ClientSession
from datetime import datetime, timezone

from db_tables import refs
from spider import *


class wordpress(spider):
    def __init__(self, url_: str, sess: ClientSession) -> None:
        self.sess = sess  # type: ClientSession
        self.crawl_times = dict()  # type: ignore

        self.base_url = url_.strip(" ").rstrip("/") + "/"

    async def parse(self, res, *cb1, **cb2):
        crawl_date = datetime.now(timezone.utc).isoformat(timespec="seconds")

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
        return ret_list

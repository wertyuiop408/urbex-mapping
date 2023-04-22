import asyncio
from abc import ABC
from dataclasses import asdict
from datetime import datetime, timezone
from functools import partial
from typing import Any

from aiohttp.client import ClientSession
from db_base import session_factory
from db_tables import refs
from sqlalchemy import text

TASKS = set()


class spider(ABC):
    sess: ClientSession
    errors: int = 0
    completed_count = 0
    columns = refs.__table__.columns.keys()
    columns_str = ", ".join(columns[1:])
    columns_named = ":" + ", :".join(columns[1:])

    def _add_url(self, url_: str, callback=None) -> None:
        print(f"adding {url_}")
        tt = asyncio.create_task(self.get_url(url_, callback))
        TASKS.add(tt)
        tt.add_done_callback(TASKS.discard)

    async def get_url(self, url_: str, callback=None):
        print(f"getting {url_}")
        try:
            async with self.sess.get(url_) as res:
                awaited = await self.handle_callback(res, callback)
                self.completed_count += 1
                return (res, awaited)
        except Exception as e:
            self.errors += 1
            self.completed_count += 1
            print("error", url_)
            print(e)
            return (e, None)

    async def handle_callback(self, res, callback=None):
        if callback == None:
            return

        if callback:
            if not isinstance(callback, partial):
                callback = partial(callback)

        part = partial(callback.func, res, *callback.args, **callback.keywords)
        return await part()

    def save_to_db(self, data_arr: list[dict[str, Any]]) -> int:
        # orm kind of sucks for this
        sql_stmnt = text(
            f"INSERT OR IGNORE INTO refs({spider.columns_str}) VALUES ({spider.columns_named})"
        )

        data_arr = [asdict(row) for row in data_arr]
        session = session_factory()
        session.begin()
        res = session.execute(sql_stmnt, data_arr).rowcount
        session.commit()
        return res

    def save_url(self, res):
        crawl_date = datetime.now(timezone.utc).isoformat(timespec="seconds")
        data = refs(url=str(res.url), date_inserted=crawl_date)

        self.save_to_db([data])
        return data

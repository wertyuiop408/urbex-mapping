from abc import ABC, abstractmethod
from functools import partial

import aiohttp
import asyncio

from sqlalchemy import text
from db_base import session_factory
from aiohttp.client import ClientSession
from typing import Callable, Any

TASKS = set()
COUNTER = 0


class spider(ABC):
    sess: ClientSession

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
                return (res, awaited)
        except Exception as e:
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
        sql_stmnt = text(
            """INSERT OR IGNORE INTO refs(url, title, date_inserted, date_post) 
            SELECT :url, :title, :date_inserted, :date_post WHERE NOT EXISTS (SELECT 1 FROM refs WHERE url = :url)"""
        )

        session = session_factory()
        session.begin()
        res = session.execute(sql_stmnt, data_arr).rowcount
        session.commit()
        return res

import asyncio

import aiohttp
from config import config
from spider import TASKS
from wordpress import wordpress
from xenforo import xenforo


async def main() -> None:
    conf = config()
    CONN = aiohttp.TCPConnector(limit_per_host=3)
    async with aiohttp.ClientSession(connector=CONN) as session:
        for crawler in conf.cfg.get("crawler"):
            for site in conf.cfg["crawler"].get(crawler):
                url_ = site.get("url")

                if crawler == "xenforo":
                    x = xenforo(url_, session)
                elif crawler == "wordpress":
                    x = wordpress(url_, session)
                else:
                    x = spider(url_, session)
                x.crawl()

        while TASKS:
            op = await asyncio.gather(*TASKS)


if __name__ == "__main__":
    asyncio.run(main())

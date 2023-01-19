import aiohttp
import asyncio
import time

from xenforo import xenforo
from spider import TASKS

async def main():
    start = time.time()
    CONN = aiohttp.TCPConnector(limit_per_host=3)

    async with aiohttp.ClientSession(connector=CONN) as session:
        xenforo("https://www.28dayslater.co.uk/forum/", session)

        print(f"---- {(time.time() - start)} fini urbexForum ----")
        while TASKS:
            op = await asyncio.gather(*TASKS)
        print(f"---- {(time.time() - start)} fini TASKS ----")

if __name__ == "__main__":
    asyncio.run(main())
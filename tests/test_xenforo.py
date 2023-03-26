import asyncio
import builtins
from functools import partial
from unittest.mock import patch, mock_open

from config import config
from xenforo import xenforo
from db_base import session_factory
from db_tables import refs

import pytest
import aiohttp
from aioresponses import aioresponses


URL_ = "https://example.com"
SECT_MAX_PAGES = 215
SECT_DATA_LEN = 10
SECTION_URL = "https://www.28dayslater.co.uk/forum/noteworthy-reports.115/"
THREAD_URL = (
    "https://www.28dayslater.co.uk/threads/fryars-estate-laird-end-dec-21.133581/"
)
BASE_URL = "https://www.28dayslater.co.uk/forum/"
THREAD_DATA = [
    {
        "title": "Lead or Rumour info - Newcastle Under Lyme Savoy / Metropolis Nightclub",
        "url": "https://www.28dayslater.co.uk/threads/newcastle-under-lyme-savoy-metropolis-nightclub.75172/",
        "date_post": "2012-10-19T12:54:54+0100",
    },
    {
        "title": "Lead or Rumour info - Glasgow Savoy Cinema",
        "url": "https://www.28dayslater.co.uk/threads/glasgow-savoy-cinema.75170/",
        "date_post": "2012-10-19T12:45:19+0100",
    },
    {
        "title": "Lead or Rumour info - Rochdale Kings Bingo",
        "url": "https://www.28dayslater.co.uk/threads/rochdale-kings-bingo.75169/",
        "date_post": "2012-10-19T12:43:30+0100",
    },
    {
        "title": "Lead or Rumour info - Fleetwood Victoria Theatre",
        "url": "https://www.28dayslater.co.uk/threads/fleetwood-victoria-theatre.75168/",
        "date_post": "2012-10-19T12:27:34+0100",
    },
    {
        "title": "Lead or Rumour info - Ebbw Vale Workman's Hall - South Wales",
        "url": "https://www.28dayslater.co.uk/threads/ebbw-vale-workmans-hall-south-wales.75167/",
        "date_post": "2012-10-19T12:21:48+0100",
    },
    {
        "title": "Lead or Rumour info - ABC Cinema - Crawley",
        "url": "https://www.28dayslater.co.uk/threads/abc-cinema-crawley.75166/",
        "date_post": "2012-10-19T12:08:09+0100",
    },
    {
        "title": "Lead or Rumour info - Redhill Cinema / Nightclub",
        "url": "https://www.28dayslater.co.uk/threads/redhill-cinema-nightclub.75165/",
        "date_post": "2012-10-19T12:03:41+0100",
    },
    {
        "title": "Lead or Rumour info - Norris Green Gala / Regal - Liverpool",
        "url": "https://www.28dayslater.co.uk/threads/norris-green-gala-regal-liverpool.75164/",
        "date_post": "2012-10-19T10:37:58+0100",
    },
    {
        "title": "Lead or Rumour info - Pitsea Gala Bingo Hall",
        "url": "https://www.28dayslater.co.uk/threads/pitsea-gala-bingo-hall.75163/",
        "date_post": "2012-10-19T10:23:44+0100",
    },
    {
        "title": "Lead or Rumour info - Staveley Regal",
        "url": "https://www.28dayslater.co.uk/threads/staveley-regal.75162/",
        "date_post": "2012-10-19T09:57:00+0100",
    },
]


@pytest.fixture
def mock():
    with aioresponses() as m:
        yield m


async def test_200_section(mock):
    with open("tests/28dl_section.html", "r") as fp:
        file_data = fp.read()

    mock.get(SECTION_URL, status=200, body=file_data)

    async with aiohttp.ClientSession() as session:
        xen = xenforo(BASE_URL, session)
        # callback is needed, otherwise the connection is closed?
        res, cb = await xen.get_url(SECTION_URL, partial(xen.parse_section, nxt=False))

        assert len(cb) == 10

        for x in zip(THREAD_DATA, cb):
            assert x[0]["title"] == x[1]["title"]
            assert x[0]["url"] == x[1]["url"]
            assert x[0]["date_post"] == x[1]["date_post"]


async def test_db_section(mock):
    with open("tests/28dl_section.html", "r") as fp:
        file_data = fp.read()

    mock.get(SECTION_URL, status=200, body=file_data)

    async with aiohttp.ClientSession() as session:
        xen = xenforo(BASE_URL, session)
        # callback is needed, otherwise the connection is closed?
        res, cb = await xen.get_url(SECTION_URL, partial(xen.parse_section, nxt=False))
        db_sess = session_factory()
        db_count = db_sess.query(refs).count()
        assert db_count == 10


async def test_empty_page(mock):
    mock.get(SECTION_URL, status=200, body="<html>")
    async with aiohttp.ClientSession() as session:
        xen = xenforo(BASE_URL, session)
        res, cb = await xen.get_url(SECTION_URL, partial(xen.parse_section, nxt=False))
        assert cb == None


async def test_error_page(mock):
    with open("tests/28dl_error.html", "r") as fp:
        file_data = fp.read()

    mock.get(SECTION_URL, status=200, body=file_data)
    async with aiohttp.ClientSession() as session:
        xen = xenforo(BASE_URL, session)
        res, cb = await xen.get_url(SECTION_URL, partial(xen.parse_section, nxt=False))
        assert cb == None


async def test_thread_page(mock):
    with open("tests/28dl_thread.html", "r") as fp:
        file_data = fp.read()

    mock.get(SECTION_URL, status=200, body=file_data)
    async with aiohttp.ClientSession() as session:
        xen = xenforo(BASE_URL, session)
        res, cb = await xen.get_url(SECTION_URL, partial(xen.parse_section, nxt=False))
        assert cb == None


@pytest.mark.parametrize(
    "input_",
    (
        """[crawler]
[[crawler.xenforo]]
site = "example"
url = "https://www.example.co.uk/forum/"
""",
        """
[[crawler.xenforo]]
url = "https://www.example.co.uk/forum/"
""",
        """
[[crawler]]
url = "https://www.example.co.uk/forum/"
""",
        "",
        "2",
    ),
)
async def test_config(input_):
    with patch("builtins.open", mock_open(read_data=input_)) as m:
        conf = config()
        x = conf.get_crawler_index("https://www.example.co.uk/forum/")
        assert x == -1 or x == 0
        assert conf.get_crawler_index("") == -1
        assert conf.get_crawler_index(2) == -1
        assert conf.get_crawler_index("www.example.co.uk/forum/") == -1
        assert conf.get_crawler_index("https://www.example.co.uk/") == -1


data = [
    """[[crawler.xenforo]]
        url = "https://www.28dayslater.co.uk/forum/"
        subs = [   
            ["example", "2023-02-08T17:48:08+00:00"]
        ]""",
    "",
    "2"
    """[[crawler.xenforo]]
        url = "https://www.28dayslater.co.uk/forum/"
        subs = [2]""",
    """[[crawler.xenforo]]
        url = "https://www.28dayslater.co.uk/forum/"
        subs = [[2]]""",
]


@pytest.mark.parametrize("input_", data)
async def test_config_time(mock, input_):
    with open("tests/28dl_section.html", "r") as fp:
        file_data = fp.read()

    mock.get(SECTION_URL, status=200, body=file_data)
    with patch("builtins.open", mock_open(read_data=input_)) as m:
        async with aiohttp.ClientSession() as session:
            xen = xenforo(BASE_URL, session)

            if input_ == data[0]:
                assert xen.get_config_time("example") == "2023-02-08T17:48:08+00:00"
            else:
                assert xen.get_config_time("example") == None

            input2 = ["example/", "", "bar", 2]
            out = []
            for x in input2:
                assert xen.get_config_time(x) == None


# Always keep this at the end
async def test_live():
    async with aiohttp.ClientSession() as session:
        xen = xenforo(BASE_URL, session)
        res, cb = await xen.get_url(SECTION_URL, partial(xen.parse_section, nxt=False))
        assert res.status == 200
        assert len(cb) == 11

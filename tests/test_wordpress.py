import asyncio
import builtins
from functools import partial
from unittest.mock import patch, mock_open
import re

from wordpress import wordpress
from db_base import session_factory
from db_tables import refs
from spider import TASKS

import pytest
import aiohttp
from aioresponses import aioresponses


URL_ = "https://example.com"
SECT_MAX_PAGES = 215
SECT_DATA_LEN = 10

BASE_URL = "https://www.whateversleft.co.uk/"
POST_URL = "https://www.whateversleft.co.uk/wp-json/wp/v2/posts?per_page=10&page=1"
POSTS_DATA = [
    {
        "title": "Bank of England House, Bristol",
        "url": "https://www.whateversleft.co.uk/other/bank-of-england-house-bristol/",
        "date_post": "2022-09-20T19:08:06",
    },
    {
        "title": "Springfield Hospital, Tooting",
        "url": "https://www.whateversleft.co.uk/asylums/springfield-hospital-tooting/",
        "date_post": "2021-02-12T17:29:24",
    },
    {
        "title": "Brislington War Room, Region 7, Bristol",
        "url": "https://www.whateversleft.co.uk/underground/brislington-war-room-region-7-bristol/",
        "date_post": "2020-10-05T13:03:47",
    },
    {
        "title": "Bomb Proof Records Room, Bristol",
        "url": "https://www.whateversleft.co.uk/underground/bomb-proof-records-room-bristol/",
        "date_post": "2020-06-29T11:00:31",
    },
    {
        "title": "Shedload, Bristol",
        "url": "https://www.whateversleft.co.uk/industrial/shedload-bristol/",
        "date_post": "2020-04-04T13:40:25",
    },
    {
        "title": "Whitchurch Hospital, Cardiff",
        "url": "https://www.whateversleft.co.uk/asylums/whitchurch-hospital-cardiff/",
        "date_post": "2019-03-16T20:29:03",
    },
    {
        "title": "Bristol Royal Infirmary &#8211; Old Building, Bristol",
        "url": "https://www.whateversleft.co.uk/hospitals/bristol-royal-infirmary-old-building-bristol/",
        "date_post": "2018-10-01T14:05:01",
    },
    {
        "title": "Sunnyside Royal Hospital, Montrose",
        "url": "https://www.whateversleft.co.uk/asylums/sunnyside-royal-hospital-montrose-2/",
        "date_post": "2018-04-22T20:36:56",
    },
    {
        "title": "Plaza Cinema, Port Talbot",
        "url": "https://www.whateversleft.co.uk/leisure/plaza-cinema-port-talbot/",
        "date_post": "2018-01-28T18:20:41",
    },
    {
        "title": "Robert Fletcher &#038; Son Ltd &#8211; Greenfield, Oldham",
        "url": "https://www.whateversleft.co.uk/industrial/robert-fletcher-son-ltd-greenfield-oldham/",
        "date_post": "2018-01-23T16:45:04",
    },
]


@pytest.fixture
def mock():
    with aioresponses() as m:
        yield m


async def test_200_posts(mock):
    with open("tests/wp_posts.json", "r") as fp:
        file_data = fp.read()

    mock.get(POST_URL, status=200, body=file_data, headers={"X-WP-Total": "10"})
    async with aiohttp.ClientSession() as session:
        wp = wordpress(BASE_URL, session)
        res, cb = await wp.get_url(POST_URL, partial(wp.parse, nxt=False))

        assert len(cb) == 10

        for x in zip(POSTS_DATA, cb):
            assert x[0]["title"] == x[1]["title"]
            assert x[0]["url"] == x[1]["url"]
            assert x[0]["date_post"] == x[1]["date_post"]


async def test_200_no_wpheader(mock):
    with open("tests/wp_posts.json", "r") as fp:
        file_data = fp.read()

    mock.get(POST_URL, status=200, body=file_data)
    async with aiohttp.ClientSession() as session:
        wp = wordpress(BASE_URL, session)
        res, cb = await wp.get_url(POST_URL, partial(wp.parse, nxt=False))
        assert cb == None


async def test_db_section(mock):
    with open("tests/wp_posts.json", "r") as fp:
        file_data = fp.read()

    mock.get(POST_URL, status=200, body=file_data, headers={"X-WP-Total": "71"})
    mock.get(POST_URL, status=200, body=file_data, headers={"X-WP-Total": "71"})
    async with aiohttp.ClientSession() as session:
        wp = wordpress(BASE_URL, session)
        res, cb = await wp.get_url(POST_URL, partial(wp.parse, nxt=False))

        db_sess = session_factory()
        db_count = db_sess.query(refs).count()
        assert db_count == 10

        # check for duplicate entries
        await wp.get_url(POST_URL, partial(wp.parse, nxt=False))
        db_count = db_sess.query(refs).count()
        assert db_count == 10


async def test_empty_page(mock):
    mock.get(POST_URL, status=200, body="<html>", headers={"X-WP-Total": "10"})
    async with aiohttp.ClientSession() as session:
        wp = wordpress(BASE_URL, session)
        res, cb = await wp.get_url(POST_URL, partial(wp.parse, nxt=False))
        assert cb == None


async def test_error_page(mock):
    with open("tests/wp_posts_error.json", "r") as fp:
        file_data = fp.read()

    mock.get(POST_URL, status=400, body=file_data, headers={"X-WP-Total": "10"})
    async with aiohttp.ClientSession() as session:
        wp = wordpress(BASE_URL, session)
        res, cb = await wp.get_url(POST_URL, partial(wp.parse, nxt=False))
        assert cb == None


async def test_next(mock):
    with open("tests/wp_posts.json", "r") as fp:
        file_data = fp.read()
    pattern = re.compile(
        r"^https://www\.whateversleft\.co\.uk/wp-json/wp/v2/posts\?.*$"
    )
    mock.get(
        pattern, status=200, body=file_data, headers={"X-WP-Total": "71"}, repeat=True
    )

    async with aiohttp.ClientSession() as session:
        wp = wordpress(BASE_URL, session)
        wp._add_url(POST_URL, partial(wp.parse, nxt=True))
        while TASKS:
            op = await asyncio.gather(*TASKS)

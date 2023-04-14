import asyncio
import builtins
import re
from datetime import datetime, timezone
from functools import partial
from unittest.mock import mock_open, patch

import aiohttp
import pytest
from aioresponses import aioresponses
from db_base import session_factory
from db_tables import refs
from spider import TASKS
from sqlalchemy import text
from wordpress import wordpress

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


@pytest.fixture(scope="session")
def posts_json():
    with open("tests/wp_posts.json", "r") as fp:
        return fp.read()


async def test_200_posts(mock, posts_json):
    # Test to make sure parsing correctly works and correct info is returned
    # mock config to prevent any false errors or unintended consequences
    mock.get(POST_URL, status=200, body=posts_json, headers={"X-WP-Total": "10"})
    with patch("builtins.open", mock_open(read_data="")) as m:
        async with aiohttp.ClientSession() as session:
            wp = wordpress(BASE_URL, session)
            res, cb = await wp.get_url(POST_URL, partial(wp.parse, nxt=False))

            assert len(cb) == 10

            for x in zip(POSTS_DATA, cb):
                assert x[0]["title"] == x[1]["title"]
                assert x[0]["url"] == x[1]["url"]
                assert x[0]["date_post"] == x[1]["date_post"]
            assert wp.errors == 0


async def test_200_no_wpheader(mock, posts_json):
    # Test to make sure parsing fails gracefully when there is no header for total posts
    # should fail before logic for config, so no mock config needed
    mock.get(POST_URL, status=200, body=posts_json)
    async with aiohttp.ClientSession() as session:
        wp = wordpress(BASE_URL, session)
        res, cb = await wp.get_url(POST_URL, partial(wp.parse, nxt=False))
        assert cb == None


async def test_db_section(mock, posts_json):
    # Tests to ensure that data is entered into the database, and that duplicates are not entered.
    mock.get(
        POST_URL, status=200, body=posts_json, headers={"X-WP-Total": "71"}, repeat=True
    )
    with patch("builtins.open", mock_open(read_data="")) as m:
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
            assert wp.errors == 0


async def test_empty_page(mock):
    # Test to ensure parsing fails graacefully when the page is clearly not wordpress
    # should fail before logic for config, so no mock config needed
    mock.get(POST_URL, status=200, body="<html>", headers={"X-WP-Total": "10"})
    async with aiohttp.ClientSession() as session:
        wp = wordpress(BASE_URL, session)
        res, cb = await wp.get_url(POST_URL, partial(wp.parse, nxt=False))
        assert cb == None


async def test_error_page(mock):
    # Test to ensure that parsing fails gracefully when wordpress throws an error
    with open("tests/wp_posts_error.json", "r") as fp:
        file_data = fp.read()

    mock.get(POST_URL, status=400, body=file_data)
    async with aiohttp.ClientSession() as session:
        wp = wordpress(BASE_URL, session)
        res, cb = await wp.get_url(POST_URL, partial(wp.parse, nxt=False))
        assert cb == None


async def test_next(mock, posts_json):
    # Test to ensure that parsing will paginate when asked to
    pattern = re.compile(
        r"^https://www\.whateversleft\.co\.uk/wp-json/wp/v2/posts\?.*$"
    )
    mock.get(
        pattern, status=200, body=posts_json, headers={"X-WP-Total": "71"}, repeat=True
    )
    with patch("builtins.open", mock_open(read_data="")) as m:
        async with aiohttp.ClientSession() as session:
            wp = wordpress(BASE_URL, session)
            wp._add_url(POST_URL, partial(wp.parse, nxt=True))
            while TASKS:
                op = await asyncio.gather(*TASKS)
            assert wp.errors == 0

            # ceil of wp-total/10
            assert wp.completed_count == 8


@pytest.mark.parametrize(
    "input_",
    [
        """[[crawler.wordpress]]
        url = "https://www.whateversleft.co.uk/"
        lc = ""
    """,
        """[[crawler.wordpress]]
        url = "https://www.whateversleft.co.uk/"
        lc = "2011-10-19T12:54:54"
    """,
    ],
)
async def test_next_url(mock, posts_json, input_):
    # Test to ensure that parsing will paginate when asked to
    pattern = re.compile(
        r"^https://www\.whateversleft\.co\.uk/wp-json/wp/v2/posts\?.*$"
    )
    mock.get(
        pattern, status=200, body=posts_json, headers={"X-WP-Total": "71"}, repeat=True
    )

    with patch("builtins.open", mock_open(read_data=input_)) as m:
        async with aiohttp.ClientSession() as session:
            wp = wordpress(BASE_URL, session)
            crawl_date = datetime.now(timezone.utc).isoformat(timespec="seconds")
            wp.next_urls(1, 30, 10, "2012-10-19T12:54:54", crawl_date)
            for x in TASKS:
                x.cancel()
            # no call to write, and 5 tasks created
            assert m().write.call_args_list == []
            assert len(TASKS) == 5


async def test_next_newer(mock, posts_json):
    # Test to ensure that parsing will paginate when asked to
    pattern = re.compile(
        r"^https://www\.whateversleft\.co\.uk/wp-json/wp/v2/posts\?.*$"
    )
    mock.get(
        pattern, status=200, body=posts_json, headers={"X-WP-Total": "71"}, repeat=True
    )
    input_ = """[[crawler.wordpress]]
        url = "https://www.whateversleft.co.uk/"
        lc = "2013-10-19T12:54:54"
    """
    with patch("builtins.open", mock_open(read_data=input_)) as m:
        async with aiohttp.ClientSession() as session:
            wp = wordpress(BASE_URL, session)
            crawl_date = datetime.now(timezone.utc).isoformat(timespec="seconds")
            wp.next_urls(1, 30, 10, "2012-10-19T12:54:54", crawl_date)
            for x in TASKS:
                x.cancel()

            assert m().write.call_args_list
            len(TASKS) == 0


async def test_next_end(mock, posts_json):
    # Test to ensure that parsing will paginate when asked to
    pattern = re.compile(
        r"^https://www\.whateversleft\.co\.uk/wp-json/wp/v2/posts\?.*$"
    )
    mock.get(
        pattern, status=200, body=posts_json, headers={"X-WP-Total": "71"}, repeat=True
    )
    input_ = """[[crawler.wordpress]]
        url = "https://www.whateversleft.co.uk/"
        lc = "2011-10-19T12:54:54"
    """
    with patch("builtins.open", mock_open(read_data=input_)) as m:
        async with aiohttp.ClientSession() as session:
            wp = wordpress(BASE_URL, session)
            crawl_date = datetime.now(timezone.utc).isoformat(timespec="seconds")
            wp.next_urls(1, 3, 10, "2012-10-19T12:54:54", crawl_date)
            for x in TASKS:
                x.cancel()

            assert len(TASKS) == 2
            assert m().write.call_args_list


async def test_next_single(mock, posts_json):
    # Test to ensure that parsing will paginate when asked to
    pattern = re.compile(
        r"^https://www\.whateversleft\.co\.uk/wp-json/wp/v2/posts\?.*$"
    )
    mock.get(
        pattern, status=200, body=posts_json, headers={"X-WP-Total": "71"}, repeat=True
    )
    input_ = """[[crawler.wordpress]]
        url = "https://www.whateversleft.co.uk/"
        lc = "2011-10-19T12:54:54"
    """
    with patch("builtins.open", mock_open(read_data=input_)) as m:
        async with aiohttp.ClientSession() as session:
            wp = wordpress(BASE_URL, session)
            crawl_date = datetime.now(timezone.utc).isoformat(timespec="seconds")
            wp.next_urls(1, 1, 10, "2012-10-19T12:54:54", crawl_date)
            for x in TASKS:
                x.cancel()

            assert len(TASKS) == 0
            assert m().write.call_args_list


data = [
    """[[crawler.wordpress]]
        url = "https://www.whateversleft.co.uk/"
        lc = "2023-02-08T17:48:08"
    """,
    "",
    None,
    "2",
    """[[crawler.wordpress]]
        url = "https://www.whateversleft.co.uk"
    """,
    """[[crawler.wordpress]]
        url = "https://www.whateversleft.co.uk"
        lc = [[2]]""",
]


@pytest.mark.parametrize("input_", data)
async def test_config_time(mock, input_, posts_json):
    # Test multiple configs and ensure get_config_time fails gracefully or returns a string
    mock.get(POST_URL, status=200, body=posts_json, headers={"X-WP-Total": "71"})
    with patch("builtins.open", mock_open(read_data=input_)) as m:
        async with aiohttp.ClientSession() as session:
            wp = wordpress(BASE_URL, session)

            if input_ == data[0]:
                tmp = wp.get_config_time()
                assert isinstance(tmp, datetime)
                assert tmp == datetime(2023, 2, 8, 17, 48, 8)
            else:
                assert wp.get_config_time() == None


async def test_config(mock, posts_json):
    # Test to ensure logic is being followed, cancel pagination if post are older than last scan
    input_ = data[0]

    mock.get(POST_URL, status=200, body=posts_json, headers={"X-WP-Total": "71"})
    with patch("builtins.open", mock_open(read_data=input_)) as m:
        async with aiohttp.ClientSession() as session:
            wp = wordpress(BASE_URL, session)
            res, cb = await wp.get_url(POST_URL, partial(wp.parse, nxt=True))
            assert wp.completed_count == 1
            mock.assert_called_once()


async def test_malformed_config_date(mock, posts_json):
    # Test to ensure a malformed date in the config causes no issues
    input_ = """[[crawler.wordpress]]
        url = "https://www.whateversleft.co.uk/"
        lc = "2023-02-08T17:482"
    """
    mock.get(POST_URL, status=200, body=posts_json, headers={"X-WP-Total": "71"})
    with patch("builtins.open", mock_open(read_data=input_)) as m:
        async with aiohttp.ClientSession() as session:
            wp = wordpress(BASE_URL, session)
            res, cb = await wp.get_url(POST_URL, partial(wp.parse, nxt=False))
            assert cb != None


async def test_200_post(mock):
    with open("tests/wp_post.json", "r") as fp:
        posts_json = fp.read()
    mock.get(POST_URL, status=200, body=posts_json, headers={"X-WP-Total": "10"})
    with patch("builtins.open", mock_open(read_data="")) as m:
        async with aiohttp.ClientSession() as session:
            wp = wordpress(BASE_URL, session)
            res, cb = await wp.get_url(POST_URL, partial(wp.parse_post, nxt=False))
            assert res.status == 200


# Always keep this at the end
async def test_live():
    db_sess = session_factory()
    db_sess.execute(text("DELETE FROM refs"))
    with patch("builtins.open", mock_open(read_data="")) as m:
        async with aiohttp.ClientSession() as session:
            wp = wordpress(BASE_URL, session)
            res, cb = await wp.get_url(POST_URL, partial(wp.parse, nxt=False))

            assert res.status == 200
            assert len(cb) == 10
            assert wp.errors == 0

            db_count = db_sess.query(refs).count()
            assert db_count == 10


async def _test_live_next():
    db_sess = session_factory()
    db_sess.execute(text("DELETE FROM refs"))
    with patch("builtins.open", mock_open(read_data="")) as m:
        async with aiohttp.ClientSession() as session:
            wp = wordpress(BASE_URL, session)
            wp._add_url(POST_URL, partial(wp.parse, nxt=True))

            while TASKS:
                op = await asyncio.gather(*TASKS)

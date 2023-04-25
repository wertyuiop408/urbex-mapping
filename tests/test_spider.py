from functools import partial
from unittest.mock import mock_open, patch

import aiohttp
import pytest
from aiohttp.http_exceptions import HttpProcessingError
from aioresponses import aioresponses
from config import config
from db_base import session_factory
from db_tables import refs
from spider import spider
from sqlalchemy import text

URL_ = "https://example.com"


async def empty(res):
    return


async def empty_kw(res, nxt=True):
    return


async def empty_arg(res, foo):
    return


async def empty_all(res, foo, nxt=True):
    return


@pytest.fixture
def mock():
    with aioresponses() as m:
        yield m


async def test_404_200(mock):
    mock.get(URL_, status=404)
    mock.get(URL_, status=200)
    async with aiohttp.ClientSession() as session:
        x = spider()
        x.sess = session
        y = await x.get_url(URL_)
        y2 = await x.get_url(URL_)

        assert y[0].status == 404
        assert y2[0].status == 200


async def test_404_200_cb(mock):
    mock.get(URL_, status=404)
    mock.get(URL_, status=200)
    async with aiohttp.ClientSession() as session:
        x = spider()
        x.sess = session
        y = await x.get_url(URL_, empty)
        y2 = await x.get_url(URL_, empty)

        assert y[0].status == 404
        assert y2[0].status == 200


@pytest.mark.parametrize(
    "input_",
    (
        empty,
        partial(empty),
        partial(empty_kw, nxt=False),
        partial(empty_arg, "2"),
        partial(empty_all, 2, nxt=False),
    ),
)
async def test_cb_noargs(mock, input_):
    async with aiohttp.ClientSession() as session:
        x = spider()
        x.sess = session
        mock.get(URL_, status=200)
        y = await x.get_url(URL_)

        await x.handle_callback(y[0], input_)


async def test_except(mock):
    mock.get(URL_, exception=HttpProcessingError(message="generic error"))
    async with aiohttp.ClientSession() as session:
        x = spider()
        x.sess = session
        y = await x.get_url(URL_)

        assert type(y) == tuple
        assert type(y[0]) == HttpProcessingError


@pytest.mark.parametrize(
    "input_",
    (
        """
        [[crawler]]
            url = "https://www.example.co.uk/"
        """,
        "",
        "2",
        None,
    ),
)
async def test_get_crawler_index_cfg(input_):
    with patch("builtins.open", mock_open(read_data=input_)) as m:
        conf = config()
        assert conf.get_crawler_index("https://www.example.co.uk/") == -1


async def test_get_crawler_index():
    input_ = """
        [crawler]
            [[crawler.xenforo]]
                site = "example"
                url = "https://www.example.co.uk/"
        """
    with patch("builtins.open", mock_open(read_data=input_)) as m:
        conf = config()
        assert conf.get_crawler_index("https://www.example.co.uk/") == 0
        assert conf.get_crawler_index("https://www.example.co.uk") == 0
        assert conf.get_crawler_index("http://www.example.co.uk/") == 0
        assert conf.get_crawler_index("www.example.co.uk/") == 0
        assert conf.get_crawler_index("www.example.co.uk") == 0
        assert conf.get_crawler_index("www.example.com") == -1


async def test_save(mock):
    db_sess = session_factory()
    db_sess.execute(text("DELETE FROM refs"))
    mock.get(URL_, status=200, body="")
    async with aiohttp.ClientSession() as session:
        x = spider()
        x.sess = session

        resp = await x.sess.get(URL_)
        assert resp.status == 200
        x.save_url(resp)
        db_count = db_sess.query(refs).count()
        assert db_count == 1

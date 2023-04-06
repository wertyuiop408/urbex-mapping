import asyncio
from functools import partial
from unittest.mock import patch, mock_open

import pytest
import aiohttp
from aiohttp.http_exceptions import HttpProcessingError
from aioresponses import aioresponses

from config import config
from spider import spider

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

        assert y.status == 404
        assert y2.status == 200


async def test_404_200_cb(mock):
    mock.get(URL_, status=404)
    mock.get(URL_, status=200)
    async with aiohttp.ClientSession() as session:
        x = spider()
        x.sess = session
        y = await x.get_url(URL_, empty)
        y2 = await x.get_url(URL_, empty)

        assert y.status == 404
        assert y2.status == 200


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

        await x.handle_callback(y, input_)


async def test_except(mock):
    mock.get(URL_, exception=HttpProcessingError(message="generic error"))
    async with aiohttp.ClientSession() as session:
        x = spider()
        x.sess = session
        y = await x.get_url(URL_)
        # maybe have an status for the call? S_Status=OK?
        assert y.status == 404


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
async def test_get_crawler_index(input_):
    with patch("builtins.open", mock_open(read_data=input_)) as m:
        conf = config()
        x = conf.get_crawler_index("https://www.example.co.uk/forum/")
        assert x == -1 or x == 0
        assert conf.get_crawler_index("") == -1
        assert conf.get_crawler_index(2) == -1
        assert conf.get_crawler_index("www.example.co.uk/forum/") == -1
        assert conf.get_crawler_index("https://www.example.co.uk/") == -1

from datetime import datetime, timezone
import time
from urllib.parse import urlparse, urljoin
import asyncio

from spider import *
from bs4 import BeautifulSoup
from yarl import URL

from db_tables import refs
from config import config

class xenforo(spider):
    suffix_url = "?order=post_date&direction=desc"

    def __init__(self, _url, sess):
        self.sess = sess
        self.crawl_times = dict()
        
        self.base_url = _url.strip(" ").rstrip("/") + "/"
        self.crawl()

    def crawl(self):
        conf = config()
        index = conf.get_crawler_index(self.base_url)
        subs = conf.cfg["crawler"]["xenforo"][index]["subs"]
        for i, v in enumerate(subs):
            _url = self.base_url + subs[i][0] + self.suffix_url
            self._add_url(_url, self.parse_section, nxt=True)
        return


    def get_section(self, section, page=1, count=1):
        _url = self.base_url + section + "page-" + str(page) + self.suffix_url
        self._add_url(_url, self.parse_section)
        return

    def get_config_time(self, section):
        conf = config()
        crawler_index = conf.get_crawler_index(self.base_url)
        if crawler_index == -1:
            return -1

        try:
            sub_index = conf.get_sub_index(conf.cfg["crawler"]["xenforo"][crawler_index], section)
            return conf.cfg["crawler"]["xenforo"][crawler_index]["subs"][sub_index][1]
        except Exception:
            return None


    def write_config_time(self, section, time_):
        conf = config()
        crawler_index = conf.get_crawler_index(self.base_url)
        if crawler_index == -1:
            return -1

        sub_index = conf.get_sub_index(conf.cfg["crawler"]["xenforo"][crawler_index], section)
        conf.cfg["crawler"]["xenforo"][crawler_index]["subs"][sub_index] = [section, time_]
        conf.save()
        return


    async def parse_section(self, res, *cb1, **cb2):
        crawl_date = datetime.now(timezone.utc).isoformat(timespec="seconds")

        #get the section name, and page number from the url
        _url = res.url
        _url_path_split = [s for s in _url.path.split("/") if s]

        if _url_path_split[0] != "forum":
            return

        section = _url_path_split[1]
        if self.crawl_times.get(section) == None:
            self.crawl_times[section] = crawl_date
        
        txt = await res.text()
        soup = BeautifulSoup(txt, "lxml")
        list_of_threads = soup.select(".structItemContainer-group > .structItem--thread")
        curr_page = int(soup.select("ul.pageNav-main > li.pageNav-page--current > a")[0].text)
        max_pages = int(soup.select("ul.pageNav-main > li.pageNav-page:nth-last-of-type(1) > a")[0].text)

        #get date of first non stickied post
        first_post_date = soup.select(".structItemContainer-group.js-threadList > .structItem--thread")[0].select_one("time").get("datetime")

        #cheesy hack for timezone fix to ISO8601
        if first_post_date[-5] == "+":
            first_post_date = first_post_date[:-2] + ":" + first_post_date[-2:]

        post_date = datetime.fromisoformat(first_post_date)
        gct = self.get_config_time(section+"/")

        #is it older
        if gct != None:
            config_date = datetime.fromisoformat(gct).astimezone(timezone.utc)
            if post_date < config_date:
                self.write_config_time(section+"/", self.crawl_times[section])
                cb2["nxt"] = False

        #generate next batch of section urls to crawl.
        url_limit = getattr(self.sess._connector, "limit_per_host", 5)
        if cb2.get("nxt"):
            for i in range(1, url_limit+1):

                #if there are no more pages in section, then stop
                if curr_page + i > max_pages:
                    self.write_config_time(section+"/", self.crawl_times[section])
                    break

                _url = self.base_url + section + "/page-" + str(curr_page + i) + self.suffix_url

                #set the last one of each batch
                nxt = False
                if i == url_limit:
                    nxt = True
                self._add_url(_url, self.parse_section, nxt=nxt)

        ret_list = list()
        for x in list_of_threads:
            data = refs(
                title = str(x.select_one(".structItem-title").get_text().strip()).replace("\n", " "),
                url = urljoin(str(_url), x.select_one(".structItem-title > a:last-of-type").get("href")),
                date_post = x.select_one("time").get("datetime"),
                date_inserted = crawl_date
                )
            ret_list.append(data.__dict__)
        self.save_to_db(ret_list)

        return




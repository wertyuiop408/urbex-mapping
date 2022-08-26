from datetime import datetime, timezone
from urllib.parse import urlparse, urljoin
#import configparser

import praw
from psaw import PushshiftAPI
import hvac
import tomlkit

from db import db

class red:


    def __init__(self, cfg, index=0) -> None:
        self.cfg = cfg
        self.index = index

        vault = hvac.Client(url='http://localhost:8200')
        creds = vault.secrets.kv.read_secret(path="reddit", mount_point="kv")["data"]["data"]
        self.limit = 1000
        self.reddit = praw.Reddit(
            client_id=creds["client_id"],
            client_secret=creds["client_secret"],
            password=creds["password"],
            user_agent="Urbex Mapping",
            username=creds["username"],
        )
        return


    def crawl(self) -> None:
        for i, sub in enumerate(self.cfg["subs"]):
            self.crawl_sub_psaw(sub)
            write_time = int(datetime.now().timestamp())
            sub.insert(1, write_time)
            self.cfg["subs"][i] = sub[:2]
            self.write_config()
        
        self.stream_subs()
        return
        

    def stream_subs(self) -> None:
        """
        Creates a stream of new thread submissiosn to the subreddits in self.subs and adds the threads link and title to the database.
        """
        sql_stmnt = """INSERT OR IGNORE INTO refs(url, title, date_inserted, date_post) 
            SELECT ?, ?, ?, ? WHERE NOT EXISTS (SELECT 1 FROM refs WHERE url = ?1)"""

        try:
            subs = self.reddit.subreddit("+".join([x[0] for x in self.cfg["subs"]]))
            
            for thread in subs.stream.submissions():
                db.get_cur().execute("BEGIN")
                crawl_date = datetime.now(timezone.utc).isoformat(timespec="seconds")
                thread_details = self.parse_results(thread.permalink, thread.title, crawl_date, thread.created_utc)
                xx = db.get_cur().execute(sql_stmnt, thread_details).rowcount
                if xx == 1:
                    print(f"Inserted {thread.title}")
                db.get_cur().execute("COMMIT")

        except Exception as err:
            print("Error")
            print(err)
            return
        except KeyboardInterrupt:
            pass
        

    def crawl_sub_psaw(self, sub_arr: list) -> None:
        """
        Crawls the subreddit using pushshift.io (PSAW) and adds the threads link and title to the database.

        sub - Subreddit name
        """
        api = PushshiftAPI()

        sub = sub_arr[0]
        ss_args = {"subreddit": sub}
        if len(sub_arr) == 2:
            ss_args.update({"after": sub_arr[1]})


        gen = api.search_submissions(**ss_args)
        inserted_count = 0
        sql_stmnt = """INSERT OR IGNORE INTO refs(url, title, date_inserted, date_post) 
            SELECT ?, ?, ?, ? WHERE NOT EXISTS (SELECT 1 FROM refs WHERE url = ?1)"""

        cache = list()
        for thread in gen:
            crawl_date = datetime.now(timezone.utc).isoformat(timespec="seconds")
            cache.append(self.parse_results(thread.permalink, thread.title, crawl_date, thread.created_utc))


            if len(cache) >= 1000:
                db.get_cur().execute("BEGIN")
                inserted_count += db.get_cur().executemany(sql_stmnt, cache).rowcount
                db.get_cur().execute("COMMIT")
                cache.clear()

        if len(cache) != 0:
            db.get_cur().execute("BEGIN")
            inserted_count += db.get_cur().executemany(sql_stmnt, cache).rowcount
            db.get_cur().execute("COMMIT")
        
        #self.write_config(sub)
        print(f"Crawled '{sub}' subreddit: {inserted_count} inserted")

        return


    def crawl_sub(self, sub: str) -> None:
        """
        Crawls the subreddit using the reddit API (PRAW) and adds the threads link and title to the database.
    
        sub - Subreddit name
        """

        sql_stmnt = """INSERT OR IGNORE INTO refs(url, title, date_inserted, date_post) 
            SELECT ?, ?, ?, ? WHERE NOT EXISTS (SELECT 1 FROM refs WHERE url = ?1)"""


        time_filters = ["all", "day", "hour", "month", "week", "year"]
        inserted_count = 0

        sub = self.reddit.subreddit(sub)

        try:

            for time_filter in time_filters:
                crawl_date = datetime.now(timezone.utc).isoformat(timespec="seconds")
                thread_list = list()

                for thread in sub.top(time_filter=time_filter, limit=self.limit):
                    thread_list.append(self.parse_results(thread.permalink, thread.title, crawl_date, thread.created_utc))

                db.get_cur().execute("BEGIN")
                inserted_count += db.get_cur().executemany(sql_stmnt, thread_list).rowcount
                db.get_cur().execute("COMMIT")



            thread_list = list()
            for thread in sub.new(limit=self.limit):
                thread_list.append(self.parse_results(thread.permalink, thread.title, crawl_date, thread.created_utc))

            db.get_cur().execute("BEGIN")
            inserted_count += db.get_cur().executemany(sql_stmnt, thread_list).rowcount
            db.get_cur().execute("COMMIT")

        except Exception as err:
            print("error")
            print(err)

        print(f"Inserted {inserted_count} reddit entries")
        return


    def parse_results(self, permalink: str, title: str, crawl_date: str, created_utc: int) -> list[str, str, str, str]:
        """
        Returns a list of the parameters after formatting them, permalink URL to an absolute URL, and create_utc to an ISO 8601 format

            permalink - relative thread url
            title - title of the thread
            crawl_date - ISO 8601
            created_utc - unix timestamp
        """
        thread_url = f"https://reddit.com{permalink}".lower()
        iso_date = datetime.fromtimestamp(created_utc, timezone.utc).isoformat(timespec="seconds")
        return [thread_url, title, crawl_date, iso_date]


    def write_config(self) -> None:
        """
        Saves the changes to the configuration to file.
        The changes are the latest times of the crawl for each subreddit
        """
        with open("config.cfg", mode="r+t", encoding="utf-8") as fp:
            cfg = tomlkit.load(fp)
            fp.seek(0)

            # update the crawlers config and write to file
            cfg["crawler"]["reddit"][self.index].update(self.cfg)
            fp.write(tomlkit.dumps(cfg))
        return


if __name__ == "__main__":
    db.connect()
    with open("config.cfg", mode="rt", encoding="utf-8") as f:
        conf = tomlkit.load(f)

    if conf.get("crawler", {}).get("reddit") == None:
        print("missing")
        exit()

    x = red(conf["crawler"]["reddit"][0])
    x.crawl()
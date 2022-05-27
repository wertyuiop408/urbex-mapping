from datetime import datetime, timezone
from urllib.parse import urlparse, urljoin

import praw
from psaw import PushshiftAPI

from db import db
import config #creds

class red:
    #list of subreddits to crawl
    subs = [
        "abandoned",
        "abandonedporn",
        "urbanexploration",
        "Urbex",
        "AbandonedAsylums",
        "Asylums",
        "AbandonedNJ",
        "Deserted",
        "reclaimedbynature",
        "UET",
        "OntarioAbandoned"
    ]

    def __init__(self):
        self.limit = 1000
        self.reddit = praw.Reddit(
            client_id=config.client_id,
            client_secret=config.client_secret,
            password=config.password,
            user_agent=config.user_agent,
            username=config.username,
        )

        return


    def crawl(self, first_run=False):
        if first_run:
            for sub in self.subs:
                self.crawl_sub_psaw(sub)

        self.stream_subs()
        

    def stream_subs(self):
        sql_stmnt = """INSERT OR IGNORE INTO refs(url, title, date_inserted, date_post) 
            SELECT ?, ?, ?, ? WHERE NOT EXISTS (SELECT 1 FROM refs WHERE url = ?1)"""

        try:
            subs = self.reddit.subreddit("+".join(self.subs))
            
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
        

    def crawl_sub_psaw(self, sub):
        api = PushshiftAPI()
        gen = api.search_submissions(subreddit=sub)
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
        
        print(f"Crawled '{sub}' subreddit: {inserted_count} inserted")
        return


    def crawl_sub(self, sub):
        if sub == None:
            return

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


    def parse_results(self, permalink, title, crawl_date, created_utc):
        thread_url = f"https://reddit.com{permalink}".lower()
        iso_date = datetime.fromtimestamp(created_utc, timezone.utc).isoformat(timespec="seconds")
        return [thread_url, title, crawl_date, iso_date]


if __name__ == "__main__":
    db.connect()
    x = red()
    x.crawl()
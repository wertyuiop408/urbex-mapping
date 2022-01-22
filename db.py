import sqlite3

__all__ = ["db"]


class _db(object):
    def __init__(self) -> None:
        self.conn = sqlite3.connect('urbex.db')
        self.conn.row_factory = sqlite3.Row
        self.cur = self.conn.cursor()
        return

    def __del__(self) -> None:
        self.conn.commit()
        self.conn.close()
        return

    def get_cur(self):
        return self.cur

    def create_tables(self) -> None:
        #use text for date, this way we can never run into unsolvable practices, such as y2k, or government deciding years don't exist (looking at you russia)
        #ISO 8601 for the date ofc though
        self.cur.execute("""CREATE TABLE IF NOT EXISTS "places" (
            row_id INTEGER PRIMARY KEY,
            date_inserted TEXT,
            last_updated TEXT,
            name TEXT,
            long REAL,
            lat REAL,
            notes TEXT,
            status INTEGER
            )""")


        self.cur.execute("""CREATE TABLE IF NOT EXISTS "parking" (
            place_id INTEGER,
            lat REAL,
            long REAL,
            paid INTEGER,
            FOREIGN KEY ("place_id") REFERENCES places("row_id")
            )""")


        #are tags categories?
        self.cur.execute("""CREATE TABLE IF NOT EXISTS "tags" (
            place_id INTEGER,
            tag TEXT,
            UNIQUE("place_id", "tag"),
            FOREIGN KEY ("place_id") REFERENCES places("row_id")
            )""")


        #handle our data sources for parsing
        self.cur.execute("""CREATE TABLE IF NOT EXISTS "refs" (
            row_id INTEGER PRIMARY KEY,
            url TEXT,
            title TEXT,
            place_id INTEGER,
            date_inserted TEXT, /* date we inserted the entry into the db*/
            date_scrape TEXT, /* date that the full thread was scraped */
            date_post TEXT, /* date that a thread was posted */
            raw TEXT,
            UNIQUE("url")
            )""")

        #create a table to handle changes and modifications?
        return


db = _db()
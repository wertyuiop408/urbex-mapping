def create_tables(cur) -> None:
    #use text for date, this way we can never run into unsolvable practices, such as y2k, or government deciding years don't exist (looking at you russia)
    #ISO 8601 for the date ofc though
    cur.execute("""CREATE TABLE IF NOT EXISTS "places" (
        row_id INTEGER PRIMARY KEY,
        date_inserted TEXT,
        last_updated TEXT,
        name TEXT,
        long REAL,
        lat REAL,
        notes TEXT,
        status INTEGER
        )""")


    cur.execute("""CREATE TABLE IF NOT EXISTS "parking" (
        place_id INTEGER,
        lat REAL,
        long REAL,
        paid INTEGER,
        FOREIGN KEY ("place_id") REFERENCES places("row_id")
        )""")


    #are tags categories?
    cur.execute("""CREATE TABLE IF NOT EXISTS "tags" (
        place_id INTEGER,
        tag TEXT,
        UNIQUE("place_id", "tag"),
        FOREIGN KEY ("place_id") REFERENCES places("row_id")
        )""")


    #handle our data sources for parsing
    cur.execute("""CREATE TABLE IF NOT EXISTS "refs" (
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

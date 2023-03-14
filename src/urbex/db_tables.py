from sqlalchemy import Integer
from sqlalchemy import REAL
from sqlalchemy import Column
from sqlalchemy import ForeignKey
from sqlalchemy import UniqueConstraint
from sqlalchemy import DDL
from sqlalchemy import Text

from db_base import Base, session_factory


class places(Base):
    __tablename__ = "places"
    row_id = Column(Integer, primary_key=True)
    date_inserted = Column(Text)
    last_updated = Column(Text)
    name = Column(Text)
    long = Column(Text)
    lat = Column(REAL)
    notes = Column(REAL)
    status = Column(Integer)

    def __repr__(self):
        return f"places(row_id={self.row_id!r}, date_inserted={self.date_inserted!r}, last_inserted={self.last_inserted!r}, name={self.name!r}, long={self.long!r}, lat={self.lat!r}, notes={self.notes!r},status={self.status!r})"


class parking(Base):
    __tablename__ = "parking"
    rowid = Column(Integer, primary_key=True)
    place_id = Column(Integer, ForeignKey("places.row_id"))
    lat = Column(REAL)
    long = Column(REAL)
    paid = Column(Integer)

    # FOREIGN KEY ("place_id") REFERENCES places("row_id")

    # are tags categories?


class tag_rel(Base):
    __tablename__ = "tag_rel"
    rowid = Column(Integer, primary_key=True)
    place_id = Column(Integer, ForeignKey("places.row_id"))
    tag_id = Column(Integer, ForeignKey("tags.row_id"))
    __table_args__ = (UniqueConstraint("place_id", "tag_id"),)
    # FOREIGN KEY("place_id") REFERENCES places("row_id"),
    # FOREIGN KEY("tag_id") REFERENCES tags("row_id"),
    # UNIQUE("place_id", "tag_id")


class tags(Base):
    __tablename__ = "tags"
    row_id = Column(Integer, primary_key=True)
    tag = Column(Text, unique=True)
    # UNIQUE("tag")


# handle our data sources for parsing
class refs(Base):
    __tablename__ = "refs"
    row_id = Column(Integer, primary_key=True)
    url = Column(Text)
    title = Column(Text)
    place_id = Column(Integer, default=0)  # DEFAULT 0, -- didn't default????
    date_inserted = Column(Text)  # date we inserted the entry into the db*/
    date_scrape = Column(Text)  # date that the full thread was scraped */
    date_post = Column(Text)  # date that a thread was posted */
    raw = Column(Text)
    __table_args__ = (UniqueConstraint("url", "place_id", name="dupes"),)
    # CONSTRAINT dupes UNIQUE("url", "place_id")


session = session_factory()
session.execute(
    """CREATE VIRTUAL TABLE IF NOT EXISTS tags_ft USING fts5(
            content=tags,
            content_rowid=row_id,
            tag
        )"""
)

t1 = """CREATE TRIGGER IF NOT EXISTS tags_ai AFTER INSERT ON tags BEGIN
        INSERT INTO tags_ft(rowid, tag) VALUES (new.row_id, new.tag);
        END;"""


t2 = """CREATE TRIGGER IF NOT EXISTS tags_ad AFTER DELETE ON tags BEGIN
        INSERT INTO tags_ft(tags_ft, rowid, tag) VALUES('delete', old.row_id, old.tag);
        END;"""


t3 = """CREATE TRIGGER IF NOT EXISTS tags_au AFTER UPDATE ON tags BEGIN
        INSERT INTO tags_ft(tags_ft, rowid, tag) VALUES('delete', old.row_id, old.tag);
        INSERT INTO tags_ft(rowid, tag) VALUES (new.row_id, new.tag);
        END;
        """
session.execute(t1)
session.execute(t2)
session.execute(t3)

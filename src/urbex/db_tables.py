from typing import Optional

from db_base import Base, session_factory
from sqlalchemy import DDL, REAL, ForeignKey, Integer, Text, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column


class places(Base):
    __tablename__ = "places"
    row_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    date_inserted: Mapped[Optional[str]] = mapped_column(Text)
    last_updated: Mapped[Optional[str]] = mapped_column(Text)
    name: Mapped[Optional[str]] = mapped_column(Text)
    long: Mapped[Optional[int]] = mapped_column(REAL)
    lat: Mapped[Optional[int]] = mapped_column(REAL)
    notes: Mapped[Optional[str]] = mapped_column(TEXT)
    status: Mapped[int] = mapped_column(Integer)

    def __repr__(self):
        return f"places(row_id={self.row_id!r}, date_inserted={self.date_inserted!r}, last_inserted={self.last_inserted!r}, name={self.name!r}, long={self.long!r}, lat={self.lat!r}, notes={self.notes!r},status={self.status!r})"


class tag_rel(Base):
    __tablename__ = "tag_rel"
    rowid: Mapped[int] = mapped_column(Integer, primary_key=True)
    place_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("places.row_id")
    )
    tag_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("tags.row_id"))
    __table_args__ = (UniqueConstraint("place_id", "tag_id"),)
    # FOREIGN KEY("place_id") REFERENCES places("row_id"),
    # FOREIGN KEY("tag_id") REFERENCES tags("row_id"),
    # UNIQUE("place_id", "tag_id")


class tags(Base):
    __tablename__ = "tags"
    row_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tag: Mapped[Optional[str]] = mapped_column(Text, unique=True)
    # UNIQUE("tag")


# handle our data sources for parsing
class refs(Base):
    __tablename__ = "refs"
    row_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    url: Mapped[Optional[str]] = mapped_column(Text)
    title: Mapped[Optional[str]] = mapped_column(Text)
    place_id: Mapped[Optional[int]] = mapped_column(Integer, server_default=text("0"))
    date_inserted: Mapped[Optional[str]] = mapped_column(
        Text
    )  # date we inserted the entry into the db*/
    date_scrape: Mapped[Optional[str]] = mapped_column(
        Text
    )  # date that the full thread was scraped */
    date_post: Mapped[Optional[str]] = mapped_column(
        Text
    )  # date that a thread was posted */
    raw: Mapped[Optional[str]] = mapped_column(Text)
    __table_args__ = (UniqueConstraint("url", "place_id", name="dupes"),)
    # CONSTRAINT dupes UNIQUE("url", "place_id")


session = session_factory()
session.execute(
    text(
        """CREATE VIRTUAL TABLE IF NOT EXISTS tags_ft USING fts5(
            content=tags,
            content_rowid=row_id,
            tag
        )"""
    )
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
session.execute(text(t1))
session.execute(text(t2))
session.execute(text(t3))

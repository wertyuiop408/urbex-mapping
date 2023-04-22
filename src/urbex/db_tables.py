from typing import List, Optional

from db_base import Base, session_factory
from sqlalchemy import (
    DDL,
    REAL,
    Column,
    ForeignKey,
    Integer,
    Table,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing_extensions import Annotated

intpk = Annotated[int, mapped_column(Integer, primary_key=True, init=False)]
txt = Annotated[Optional[str], mapped_column(Text, default=None)]

# note for a Core table, we use the sqlalchemy.Column construct,
# not sqlalchemy.orm.mapped_column
association_table = Table(
    "place_rel",
    Base.metadata,
    Column("ref_id", ForeignKey("refs.row_id"), primary_key=True),
    Column("place_id", ForeignKey("places.row_id"), primary_key=True),
)


class places(Base):
    __tablename__ = "places"
    row_id: Mapped[intpk]
    date_inserted: Mapped[txt]
    last_updated: Mapped[txt]
    name: Mapped[txt]
    long: Mapped[Optional[int]] = mapped_column(REAL, default=None)
    lat: Mapped[Optional[int]] = mapped_column(REAL, default=None)
    notes: Mapped[txt]
    status: Mapped[int] = mapped_column(Integer, default=None)

    assoc_ref: Mapped[List["refs"]] = relationship(
        back_populates="assoc_place", secondary=association_table, default_factory=list
    )


class tag_rel(Base):
    __tablename__ = "tag_rel"
    rowid: Mapped[intpk]
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
    row_id: Mapped[intpk]
    tag: Mapped[Optional[str]] = mapped_column(Text, unique=True)
    # UNIQUE("tag")


# handle our data sources for parsing
class refs(Base):
    __tablename__ = "refs"
    row_id: Mapped[intpk]
    url: Mapped[txt] = mapped_column(unique=True)
    title: Mapped[txt]
    date_inserted: Mapped[txt]  # date we inserted the entry into the db*/
    date_post: Mapped[txt]  # date that a thread was posted */
    assoc_place: Mapped[List["places"]] = relationship(
        back_populates="assoc_ref", secondary=association_table, default_factory=list
    )
    # __table_args__ = (UniqueConstraint("url", "place_id", name="dupes"),)
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

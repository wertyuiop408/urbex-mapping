from typing import List, Optional

from db_base import Base, session_factory
from sqlalchemy import REAL, Column, ForeignKey, Integer, Table, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship, scoped_session
from typing_extensions import Annotated

__schema_version__ = "0.2.4"

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
assoc_tag_table = Table(
    "tag_rel",
    Base.metadata,
    Column("tag_id", ForeignKey("tags.row_id"), primary_key=True),
    Column("place_id", ForeignKey("places.row_id"), primary_key=True),
)


class places(Base):
    __tablename__ = "places"
    row_id: Mapped[intpk]
    date_inserted: Mapped[txt]
    last_updated: Mapped[txt]
    name: Mapped[txt]
    notes: Mapped[txt]
    long: Mapped[Optional[int]] = mapped_column(REAL, default=None)
    lat: Mapped[Optional[int]] = mapped_column(REAL, default=None)

    status: Mapped[Optional[int]] = mapped_column(Integer, default=None)

    assoc_ref: Mapped[List["refs"]] = relationship(
        back_populates="assoc_place", secondary=association_table, default_factory=list
    )
    assoc_tag: Mapped[List["tags"]] = relationship(
        back_populates="assoc_place", secondary=assoc_tag_table, default_factory=list
    )


class tags(Base):
    __tablename__ = "tags"
    row_id: Mapped[intpk]
    tag: Mapped[Optional[str]] = mapped_column(Text, unique=True)
    assoc_place: Mapped[List["places"]] = relationship(
        back_populates="assoc_tag", secondary=assoc_tag_table, default_factory=list
    )


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


Session = scoped_session(session_factory)
with Session() as db:
    db.execute(
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
    db.execute(text(t1))
    db.execute(text(t2))
    db.execute(text(t3))
    db.execute(
        text("CREATE INDEX IF NOT EXISTS tag_edge_idx ON tag_rel(tag_id, place_id)")
    )
    db.execute(
        text("CREATE INDEX IF NOT EXISTS place_edge_idx on place_rel(ref_id, place_id)")
    )
    db.commit()
Session.remove()

import sys

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

db_uri = "sqlite+pysqlite:///urbex.db"
if "pytest" in sys.modules:
    db_uri = "sqlite+pysqlite:///:memory:"

engine = create_engine(db_uri)
# use session_factory() to get a new Session
_SessionFactory = sessionmaker(engine, future=True)


class Base(DeclarativeBase):
    pass


def session_factory() -> Session:
    Base.metadata.create_all(engine)
    return _SessionFactory()

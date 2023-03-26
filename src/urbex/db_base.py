from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import Session

engine = create_engine("sqlite+pysqlite:///urbex.db")  # , echo=True)
# use session_factory() to get a new Session
_SessionFactory = sessionmaker(engine, future=True)

Base = declarative_base()


def session_factory() -> Session:
    Base.metadata.create_all(engine)
    return _SessionFactory()
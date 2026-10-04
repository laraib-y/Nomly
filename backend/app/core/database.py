from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings

_engine: Engine | None = None
SessionLocal: sessionmaker[Session] | None = None


def make_engine(url: str) -> Engine:
    """Create a SQLAlchemy engine for MySQL, TiDB Cloud, or SQLite tests.

    TiDB Cloud requires TLS. Add ``ssl=true`` to DATABASE_URL, or use a
    ``tidbcloud.com`` host, and the PyMySQL driver will negotiate SSL.
    """

    if not url:
        raise RuntimeError(
            "DATABASE_URL is not set. Copy .env.example to .env and point it at MySQL or TiDB Cloud."
        )

    database_url = make_url(url)
    connect_args: dict = {}

    if database_url.drivername.startswith("sqlite"):
        connect_args["check_same_thread"] = False
        return create_engine(database_url, connect_args=connect_args)

    query = dict(database_url.query)
    ssl_flag = str(query.pop("ssl", "false")).lower()
    use_ssl = ssl_flag == "true" or "tidbcloud.com" in (database_url.host or "")
    if use_ssl:
        database_url = database_url.set(query=query)
        connect_args["ssl"] = {"check_hostname": False}

    return create_engine(
        database_url,
        pool_pre_ping=True,
        pool_recycle=3600,
        connect_args=connect_args,
    )


def get_engine() -> Engine:
    global _engine, SessionLocal
    if _engine is None:
        _engine = make_engine(get_settings().database_url)
        SessionLocal = sessionmaker(bind=_engine, autoflush=False, autocommit=False, expire_on_commit=False)
    return _engine


def open_session() -> Session:
    get_engine()
    if SessionLocal is None:
        raise RuntimeError("Database session factory is not initialized")
    return SessionLocal()


def get_db() -> Generator[Session, None, None]:
    db = open_session()
    try:
        yield db
    finally:
        db.close()

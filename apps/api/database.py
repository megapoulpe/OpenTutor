"""Database engine and session management.

SQLite-only local mode.
"""

import logging
import time

from sqlalchemy import event
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import StaticPool, NullPool

from config import settings

_db_logger = logging.getLogger("opentutor.db")

_is_sqlite = settings.database_url.startswith("sqlite")

_engine_kwargs: dict = {"echo": False, "hide_parameters": True}
if _is_sqlite:
    _sqlite_url = make_url(settings.database_url)
    # Only in-memory databases need a shared connection. File databases use
    # SQLAlchemy's async queue pool so overlapping requests have isolated
    # transactions: one request's rollback must not erase another's writes.
    if _sqlite_url.database in (None, "", ":memory:") or _sqlite_url.query.get("mode") == "memory":
        _engine_kwargs["poolclass"] = StaticPool
    _engine_kwargs["connect_args"] = {"check_same_thread": False}
else:
    _engine_kwargs["pool_size"] = settings.database_pool_size
    _engine_kwargs["max_overflow"] = settings.database_max_overflow
    _engine_kwargs["pool_timeout"] = 30
    _engine_kwargs["pool_recycle"] = 1800
    _engine_kwargs["pool_pre_ping"] = True
    _engine_kwargs["connect_args"] = {"sslmode": settings.database_ssl_mode}
    if settings.database_ssl_root_cert:
        _engine_kwargs["connect_args"]["sslrootcert"] = settings.database_ssl_root_cert
    if settings.database_pool_mode == "transaction":
        for _key in ("pool_size", "max_overflow", "pool_timeout", "pool_recycle"):
            _engine_kwargs.pop(_key, None)
        _engine_kwargs["poolclass"] = NullPool
        _engine_kwargs["connect_args"]["prepare_threshold"] = None

engine = create_async_engine(settings.database_url, **_engine_kwargs)

# Enable WAL mode and performance pragmas for SQLite
if _is_sqlite:
    @event.listens_for(engine.sync_engine, "connect")
    def _set_sqlite_pragma(dbapi_conn, connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.execute("PRAGMA busy_timeout=5000")
        cursor.execute("PRAGMA cache_size=-64000")  # 64MB
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# Slow query logging (>500ms) via sync engine events
_SLOW_QUERY_THRESHOLD_MS = 500


@event.listens_for(engine.sync_engine, "before_cursor_execute")
def _before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    conn.info["query_start_time"] = time.monotonic()


@event.listens_for(engine.sync_engine, "after_cursor_execute")
def _after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    start = conn.info.pop("query_start_time", None)
    if start is None:
        return
    elapsed_ms = (time.monotonic() - start) * 1000
    if elapsed_ms > _SLOW_QUERY_THRESHOLD_MS:
        _db_logger.warning(
            "Slow query: %.0fms | %s",
            elapsed_ms,
            statement[:200],
        )


def is_sqlite() -> bool:
    """Return True if the database backend is SQLite."""
    return _is_sqlite


class Base(DeclarativeBase):
    pass


# Ensure naive datetimes from SQLite are treated as UTC when loaded.
# This prevents ISO 8601 date-time schema violations in API responses.
@event.listens_for(Base, "load", propagate=True)
def _attach_utc_to_naive_datetimes(target, context):
    """Attach UTC timezone to any naive datetime attributes after ORM load."""
    from datetime import datetime as _dt, timezone as _tz

    for attr in type(target).__table__.columns:
        if str(attr.type) in ("DATETIME", "TIMESTAMP"):
            val = getattr(target, attr.key, None)
            if isinstance(val, _dt) and val.tzinfo is None:
                object.__setattr__(target, attr.key, val.replace(tzinfo=_tz.utc))


async def get_db() -> AsyncSession:
    async with async_session() as session:
        yield session


import models  # noqa: E402,F401  # Register ORM models with Base.metadata

"""Opt-in real PostgreSQL checks. Use a dedicated database ending in _test."""
import asyncio
import os
from pathlib import Path
import subprocess
import sys
import uuid

import pytest

URL = os.environ.get("POSTGRES_TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(not URL, reason="POSTGRES_TEST_DATABASE_URL not configured")


def test_fresh_migrations_are_repeatable_and_private():
    import psycopg
    from sqlalchemy.engine import make_url
    url = make_url(URL)
    assert url.database.endswith("_test"), "Use a dedicated integration database"
    env = dict(os.environ, DATABASE_URL=URL, DATABASE_SSL_MODE="disable")
    api = Path(__file__).resolve().parents[1] / "apps" / "api"
    for _ in range(2):
        result = subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"], cwd=api, env=env, capture_output=True, text=True)
        assert result.returncode == 0, result.stderr
    with psycopg.connect(URL.replace("postgresql+psycopg:", "postgresql:")) as db:
        assert db.execute("SELECT version_num FROM alembic_version").fetchone()[0] == "20261107_0027"
        rows = db.execute("SELECT tablename, rowsecurity FROM pg_tables WHERE schemaname='public' AND tablename != 'alembic_version'").fetchall()
        assert len(rows) == 33
        assert all(row[1] for row in rows), [row for row in rows if not row[1]]


def test_orm_transactions_json_uuid_and_owner_isolation():
    from sqlalchemy import select, delete
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
    from models.user import User
    from models.course import Course
    from models.content import CourseContentTree
    from services.search.strategies import keyword_search
    from services.course_access import get_course_or_404
    from libs.exceptions import NotFoundError

    async def check():
        engine = create_async_engine(URL.replace("postgresql://", "postgresql+psycopg://"), connect_args={"sslmode": "disable"})
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        owner, other = uuid.uuid4(), uuid.uuid4()
        course_id = uuid.uuid4()
        try:
            async with sessions() as db:
                db.add_all([User(id=owner), User(id=other)])
                await db.flush()
                db.add(Course(id=course_id, user_id=owner, name="PDF course", metadata_={"notes": ["revision"]}))
                await db.commit()
                db.add(CourseContentTree(course_id=course_id, title="Fractions", content="A fraction has a numerator and a denominator"))
                await db.commit()
                assert (await keyword_search(db, course_id, "numerator"))[0]["title"] == "Fractions"
            async with sessions() as first, sessions() as second:
                course = await get_course_or_404(first, course_id, user_id=owner)
                assert course.metadata_["notes"] == ["revision"]
                assert isinstance(course.user_id, uuid.UUID)
                with pytest.raises(NotFoundError):
                    await get_course_or_404(second, course_id, user_id=other)
                await second.rollback()
                assert (await first.execute(select(Course).where(Course.id == course_id))).scalar_one().name == "PDF course"
        finally:
            async with sessions() as db:
                await db.execute(delete(User).where(User.id.in_((owner, other))))
                await db.commit()
            await engine.dispose()

    with asyncio.Runner(loop_factory=asyncio.SelectorEventLoop if sys.platform == "win32" else None) as runner:
        runner.run(check())

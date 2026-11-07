"""Opt-in real PostgreSQL checks. Use a dedicated database ending in _test."""
import asyncio
import os
from pathlib import Path
import subprocess
import sys
import uuid

import pytest

URL = os.environ.get("POSTGRES_TEST_DATABASE_URL")
if URL:
    from sqlalchemy.engine import make_url
    if not (make_url(URL).database or "").endswith("_test"):
        raise RuntimeError("POSTGRES_TEST_DATABASE_URL must target a dedicated database ending in _test")
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


def test_terminal_import_failure_and_cancellation_are_deletable(monkeypatch):
    from unittest.mock import AsyncMock
    from types import SimpleNamespace
    from fastapi import HTTPException
    from sqlalchemy import select, delete
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
    from models.user import User
    from models.course import Course
    from models.agent_task import AgentTask
    from models.ingestion import IngestionJob
    from services.ingestion import queued
    from services.activity import engine_execution, engine_dispatch
    from services.activity.engine_lifecycle import cancel_task
    from routers.upload import delete_uploaded_file

    monkeypatch.setattr(queued, "store_document", AsyncMock(return_value="supabase://documents/fake/reference.pdf"))
    monkeypatch.setattr(queued, "download_document", AsyncMock(side_effect=HTTPException(503, "Storage unavailable")))

    async def check():
        engine = create_async_engine(URL.replace("postgresql://", "postgresql+psycopg://"), connect_args={"sslmode": "disable"})
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        monkeypatch.setattr(engine_execution, "async_session", sessions)
        monkeypatch.setattr(engine_dispatch, "async_session", sessions)
        uid, cid = uuid.uuid4(), uuid.uuid4()
        try:
            async with sessions() as db:
                db.add(User(id=uid))
                await db.flush()
                db.add(Course(id=cid, user_id=uid, name="Failure handling"))
                await db.commit()
                job = await queued.enqueue_document(db, uid, cid, "failure.pdf", b"first document")
                task = (await db.execute(select(AgentTask).where(AgentTask.user_id == uid, AgentTask.task_type == "ingest_document"))).scalar_one()
                task.attempts, task.status = task.max_attempts, "running"
                task_id, job_id = task.id, job.id
                await db.commit()
            await engine_execution.execute_task(task_id)
            async with sessions() as db:
                assert (await db.get(IngestionJob, job_id)).status == "failed"
                await delete_uploaded_file(job_id, SimpleNamespace(id=uid), db)
                next_job = await queued.enqueue_document(db, uid, cid, "cancel.pdf", b"second document")
                task = (await db.execute(select(AgentTask).where(AgentTask.user_id == uid, AgentTask.status == "queued", AgentTask.task_type == "ingest_document"))).scalar_one()
                await cancel_task(task.id, uid, db=db)
                assert (await db.get(IngestionJob, next_job.id)).status == "failed"
                await delete_uploaded_file(next_job.id, SimpleNamespace(id=uid), db)
        finally:
            async with sessions() as db:
                await db.execute(delete(User).where(User.id == uid))
                await db.commit()
            await engine.dispose()

    with asyncio.Runner(loop_factory=asyncio.SelectorEventLoop if sys.platform == "win32" else None) as runner:
        runner.run(check())


def test_pdf_roundtrip_with_private_storage_transport(monkeypatch):
    """Real PDF parsing + SQL; Auth/Storage HTTP deliberately stay offline."""
    import io
    from types import SimpleNamespace
    from unittest.mock import AsyncMock
    import httpx
    from pypdf import PdfWriter
    from pypdf.generic import DictionaryObject, NameObject, DecodedStreamObject
    from sqlalchemy import select, delete
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
    from config import settings
    from models.user import User
    from models.course import Course
    from models.ingestion import IngestionJob
    from models.content import CourseContentTree
    from models.agent_task import AgentTask
    from services import document_storage
    from services.ingestion import pipeline, queued
    from services.ingestion.deletion import delete_owned_objects
    from routers import upload, upload_processing
    from libs.exceptions import NotFoundError

    writer = PdfWriter()
    page = writer.add_blank_page(width=300, height=300)
    page[NameObject("/Resources")] = DictionaryObject({NameObject("/Font"): DictionaryObject({NameObject("/F1"): writer._add_object(DictionaryObject({NameObject("/Type"): NameObject("/Font"), NameObject("/Subtype"): NameObject("/Type1"), NameObject("/BaseFont"): NameObject("/Helvetica")}))})})
    stream = DecodedStreamObject()
    stream.set_data(b"BT /F1 12 Tf 20 250 Td (Fractions have a numerator and denominator.) Tj ET")
    page[NameObject("/Contents")] = writer._add_object(stream)
    buffer = io.BytesIO()
    writer.write(buffer)
    pdf = buffer.getvalue()
    objects = {}

    def storage_request(request):
        key = request.url.path
        if request.method == "POST":
            objects[key] = request.content
            return httpx.Response(200, json={"Key": key})
        if request.method == "DELETE":
            objects.pop(key, None)
            return httpx.Response(200)
        return httpx.Response(200, content=objects[key])

    monkeypatch.setattr(settings, "storage_backend", "supabase")
    monkeypatch.setattr(settings, "app_run_activity_engine", True)
    monkeypatch.setattr(settings, "supabase_url", "https://offline.supabase.co")
    monkeypatch.setattr(settings, "supabase_service_role_key", "offline-fake-key")
    monkeypatch.setattr(document_storage, "_client", lambda: httpx.AsyncClient(transport=httpx.MockTransport(storage_request)))
    monkeypatch.setattr(pipeline, "classify_document", AsyncMock(return_value=("notes", "test")))

    async def check():
        engine = create_async_engine(URL.replace("postgresql://", "postgresql+psycopg://"), connect_args={"sslmode": "disable"})
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        uid, cid = uuid.uuid4(), uuid.uuid4()

        async def finish(course_id, job_id, user_id=None):
            async with sessions() as db:
                job = await db.get(IngestionJob, job_id)
                job.status, job.embedding_status = "completed", "skipped"
                await db.commit()

        monkeypatch.setattr(upload_processing, "_background_embed", finish)
        try:
            async with sessions() as db:
                db.add(User(id=uid))
                await db.flush()
                db.add(Course(id=cid, user_id=uid, name="PDF roundtrip"))
                await db.commit()
                result = await upload.upload_file(None, SimpleNamespace(filename="fractions.pdf", read=AsyncMock(return_value=pdf)), str(cid), SimpleNamespace(id=uid), db)
                job_id = uuid.UUID(result["job_id"])
                assert len(objects) == 1
                await queued.process_document(db, uid, {"job_id": str(job_id)})
            # Reload everything using another connection, like a process restart.
            async with sessions() as db:
                job = await db.get(IngestionJob, job_id)
                assert job.status == "completed"
                assert "numerator" in job.extracted_markdown
                assert job.file_path.startswith("supabase://documents/")
                response = await upload.get_uploaded_file(job_id, SimpleNamespace(id=uid), db)
                assert response.body == pdf
                with pytest.raises(NotFoundError):
                    await upload.get_uploaded_file(job_id, SimpleNamespace(id=uuid.uuid4()), db)
                await upload.delete_uploaded_file(job_id, SimpleNamespace(id=uid), db)
                assert await db.get(IngestionJob, job_id) is None
                assert not (await db.execute(select(CourseContentTree).where(CourseContentTree.course_id == cid))).scalars().all()
                task = (await db.execute(select(AgentTask).where(AgentTask.user_id == uid, AgentTask.task_type == "delete_document_objects"))).scalar_one()
                await delete_owned_objects(uid, task.input_json)
                assert objects == {}
        finally:
            async with sessions() as db:
                await db.execute(delete(User).where(User.id == uid))
                await db.commit()
            await engine.dispose()

    with asyncio.Runner(loop_factory=asyncio.SelectorEventLoop if sys.platform == "win32" else None) as runner:
        runner.run(check())

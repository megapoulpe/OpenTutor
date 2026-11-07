import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest


@pytest.mark.asyncio
async def test_enqueue_compensates_storage_when_database_commit_fails(monkeypatch):
    from services.ingestion import queued
    monkeypatch.setattr(queued, "store_document", AsyncMock(return_value="supabase://documents/object.pdf"))
    remove = AsyncMock()
    monkeypatch.setattr(queued, "delete_document", remove)
    monkeypatch.setattr(queued, "create_task", AsyncMock())
    db = AsyncMock()
    db.execute.return_value = SimpleNamespace(scalar_one_or_none=lambda: None)
    db.add = lambda obj: None
    db.commit.side_effect = RuntimeError("database interrupted")
    with pytest.raises(RuntimeError):
        await queued.enqueue_document(db, uuid.uuid4(), uuid.uuid4(), "notes.pdf", b"pdf")
    remove.assert_awaited_once_with("supabase://documents/object.pdf")


@pytest.mark.asyncio
async def test_queued_worker_checks_owner_before_download(monkeypatch):
    from services.ingestion import queued
    from libs.exceptions import NotFoundError
    monkeypatch.setattr(queued, "get_course_or_404", AsyncMock(side_effect=NotFoundError("Course")))
    download = AsyncMock()
    monkeypatch.setattr(queued, "download_document", download)
    db = AsyncMock()
    job = SimpleNamespace(user_id=uuid.uuid4(), course_id=uuid.uuid4())
    db.get.return_value = job
    with pytest.raises(NotFoundError):
        await queued.process_document(db, job.user_id, {"job_id": str(uuid.uuid4())})
    download.assert_not_awaited()


@pytest.mark.asyncio
async def test_dispatched_document_can_retry_failed_embedding(monkeypatch):
    from services.ingestion import queued
    from routers import upload_processing
    uid = uuid.uuid4()
    job = SimpleNamespace(id=uuid.uuid4(), user_id=uid, course_id=uuid.uuid4(), dispatched=True, status="failed", nodes_created=3)
    db = AsyncMock()
    db.get.return_value = job
    monkeypatch.setattr(queued, "get_course_or_404", AsyncMock())
    download = AsyncMock()
    monkeypatch.setattr(queued, "download_document", download)
    async def complete(*args, **kwargs):
        job.status = "completed"
    monkeypatch.setattr(upload_processing, "_background_embed", AsyncMock(side_effect=complete))
    result, _ = await queued.process_document(db, uid, {"job_id": str(job.id)})
    assert result["nodes_created"] == 3
    download.assert_not_awaited()


@pytest.mark.asyncio
async def test_terminal_task_failure_marks_own_ingestion_failed():
    from services.ingestion.queued import mark_ingestion_terminal
    uid = uuid.uuid4()
    job = SimpleNamespace(user_id=uid, status="uploaded", error_message=None)
    db = AsyncMock()
    db.get.return_value = job
    task = SimpleNamespace(task_type="ingest_document", user_id=uid, input_json={"job_id": str(uuid.uuid4())}, status="failed")
    await mark_ingestion_terminal(db, task)
    assert job.status == "failed"
    assert "failed" in job.error_message.lower()


@pytest.mark.asyncio
async def test_worker_does_not_claim_tasks_while_at_capacity(monkeypatch):
    import asyncio
    from services.activity import engine
    stop = asyncio.Event()
    blocker = asyncio.create_task(asyncio.Event().wait())
    monkeypatch.setattr(engine.settings, "activity_engine_max_concurrency", 1)
    monkeypatch.setattr(engine.settings, "activity_use_redis_notify", False)
    monkeypatch.setattr(engine, "_stop_event", stop)
    monkeypatch.setattr(engine, "_worker_semaphore", asyncio.Semaphore(1))
    monkeypatch.setattr(engine, "_inflight_tasks", {blocker})
    claim = AsyncMock(return_value=[])
    monkeypatch.setattr(engine, "_claim_pending_tasks", claim)
    loop = asyncio.create_task(engine._run_loop())
    try:
        await asyncio.sleep(0.02)
        stop.set()
        await loop
        claim.assert_not_awaited()
    finally:
        blocker.cancel()
        await asyncio.gather(blocker, return_exceptions=True)

"""Document ingestion on the existing SQL-backed activity engine."""
import asyncio
import logging
from pathlib import Path
import tempfile
import uuid

from sqlalchemy import select
import xxhash

from models.ingestion import IngestionJob
from services.activity.task_records import create_task
from services.course_access import get_course_or_404
from services.document_storage import store_document, download_document, delete_document
from libs.exceptions import NotFoundError

logger = logging.getLogger(__name__)


async def enqueue_document(db, user_id, course_id, filename, data):
    digest = xxhash.xxh64(data).hexdigest()
    existing = (await db.execute(select(IngestionJob).where(
        IngestionJob.user_id == user_id, IngestionJob.course_id == course_id,
        IngestionJob.content_hash == digest, IngestionJob.status != "failed",
    ).limit(1))).scalar_one_or_none()
    if existing:
        return existing
    reference = await store_document(user_id, course_id, filename, data)
    job = IngestionJob(id=uuid.uuid4(), user_id=user_id, course_id=course_id,
        course_preset=True, source_type="file", original_filename=filename,
        file_path=reference, file_size=len(data), content_hash=digest,
        status="uploaded", progress_percent=5, phase_label="Queued for extraction",
        embedding_status="pending")
    try:
        db.add(job)
        await db.flush()
        await create_task(db, user_id=user_id, course_id=course_id,
            task_type="ingest_document", title="Import document", status="queued",
            input_json={"job_id": str(job.id)}, max_attempts=2)
        await db.commit()
    except BaseException:
        await db.rollback()
        try:
            await delete_document(reference)
        except Exception:
            logger.exception("Could not remove an uncommitted document object")
        raise
    return job


async def process_document(db, user_id, payload):
    from services.ingestion.pipeline import run_ingestion_pipeline
    from routers.upload_processing import _background_embed

    job = await db.get(IngestionJob, uuid.UUID(payload["job_id"]))
    if not job or job.user_id != user_id:
        raise NotFoundError("Document")
    await get_course_or_404(db, job.course_id, user_id=user_id)
    # Do not redo committed dispatch on a retry after a crash during embedding.
    if not job.dispatched and job.status != "completed":
        data = await download_document(job.file_path)
        suffix = Path(job.original_filename or "document.txt").suffix
        with tempfile.TemporaryDirectory(prefix="opentutor-ingest-") as directory:
            source = Path(directory) / f"source{suffix}"
            await asyncio.to_thread(source.write_bytes, data)
            job = await run_ingestion_pipeline(db=db, user_id=user_id,
                file_path=str(source), filename=job.original_filename,
                course_id=job.course_id, file_bytes=data, existing_job=job)
    if job.status == "failed" and not job.dispatched:
        raise RuntimeError("Document extraction failed; inspect the ingestion job")
    if job.status != "completed":
        await _background_embed(job.course_id, job.id, user_id=user_id)
        await db.refresh(job)
        if job.status == "failed":
            raise RuntimeError("Document post-processing failed")
    return {"job_id": str(job.id), "nodes_created": job.nodes_created or 0}, "Document imported"


async def mark_ingestion_terminal(db, task):
    """Keep polling/deletion usable after a failed or cancelled durable task."""
    if task.task_type != "ingest_document" or task.status not in {"failed", "cancelled", "rejected"}:
        return
    try:
        job_id = uuid.UUID((task.input_json or {})["job_id"])
    except (ValueError, KeyError, TypeError):
        return
    job = await db.get(IngestionJob, job_id)
    if job and job.user_id == task.user_id and job.status != "completed":
        job.status = "failed"
        job.error_message = "Document processing cancelled." if task.status == "cancelled" else "Document processing failed."
        job.phase_label = job.error_message
        job.embedding_status = "failed"

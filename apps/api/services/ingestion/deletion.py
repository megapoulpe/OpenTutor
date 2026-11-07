"""Transactional deletion outbox on the existing activity task table."""
from config import settings
from services.activity.task_records import create_task
from services.document_storage import delete_document
from fastapi import HTTPException


async def queue_document_cleanup(db, user_id, references):
    references = list(dict.fromkeys(ref for ref in references if ref and ref.startswith("supabase://")))
    if references:
        await create_task(db, user_id=user_id, course_id=None,
            task_type="delete_document_objects", title="Delete document objects",
            status="queued", input_json={"references": references}, max_attempts=5)


async def delete_owned_objects(user_id, payload):
    prefix = f"supabase://{settings.supabase_storage_bucket}/{user_id}/"
    references = payload.get("references", [])
    if any(not isinstance(ref, str) or not ref.startswith(prefix) for ref in references):
        raise HTTPException(403, "Invalid document owner")
    for reference in references:
        await delete_document(reference)
    return {"deleted": len(references)}, "Private documents deleted"

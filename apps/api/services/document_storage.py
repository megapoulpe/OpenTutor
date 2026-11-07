"""Private document objects. SQL records remain the authorization boundary.

Only this server uses the Storage service key. Callers must check ownership
before accepting a reference from a database record; never from user input.
"""
import mimetypes
import uuid
from pathlib import PurePosixPath
from urllib.parse import quote

import httpx
from fastapi import HTTPException

from config import settings


def _client():
    return httpx.AsyncClient(timeout=httpx.Timeout(120, connect=10), follow_redirects=False)


def _object_path(reference: str) -> str:
    prefix = f"supabase://{settings.supabase_storage_bucket}/"
    if not reference.startswith(prefix):
        raise HTTPException(400, "Invalid document reference")
    key = reference[len(prefix):]
    if not key or any(part in {"", ".", ".."} for part in key.split("/")) or "\\" in key:
        raise HTTPException(400, "Invalid document reference")
    return f"{quote(settings.supabase_storage_bucket, safe='')}/{quote(key, safe='/')}"


async def _request(method: str, reference: str, **kwargs) -> httpx.Response:
    path = _object_path(reference)
    headers = {"apikey": settings.supabase_service_role_key,
               "Authorization": f"Bearer {settings.supabase_service_role_key}"}
    headers.update(kwargs.pop("headers", {}))
    try:
        async with _client() as client:
            response = await client.request(method, f"{settings.supabase_url.rstrip('/')}/storage/v1/object/{path}", headers=headers, **kwargs)
    except httpx.HTTPError as exc:
        raise HTTPException(503, "Document storage is unavailable") from exc
    if response.status_code == 404 and method == "GET":
        raise HTTPException(404, "Document not found")
    if response.status_code == 404 and method == "DELETE":
        return response  # A retried deletion is idempotent.
    if response.is_error or response.is_redirect:
        raise HTTPException(503, "Document storage request failed")
    return response


async def store_document(user_id: uuid.UUID, course_id: uuid.UUID, filename: str, data: bytes) -> str:
    # Only a suffix survives from the client filename. Keys cannot collide.
    suffix = PurePosixPath(filename.replace("\\", "/")).suffix.lower()
    key = f"{user_id}/{course_id}/{uuid.uuid4().hex}{suffix}"
    reference = f"supabase://{settings.supabase_storage_bucket}/{key}"
    await _request("POST", reference, content=data, headers={
        "Content-Type": mimetypes.guess_type(filename)[0] or "application/octet-stream",
        "x-upsert": "false",
    })
    return reference


async def download_document(reference: str) -> bytes:
    return (await _request("GET", reference)).content


async def delete_document(reference: str) -> None:
    await _request("DELETE", reference)


async def verify_private_bucket() -> None:
    """Fail startup rather than accidentally publish school documents."""
    try:
        async with _client() as client:
            response = await client.get(
                f"{settings.supabase_url.rstrip('/')}/storage/v1/bucket/{quote(settings.supabase_storage_bucket, safe='')}",
                headers={"apikey": settings.supabase_service_role_key,
                         "Authorization": f"Bearer {settings.supabase_service_role_key}"},
            )
        if response.is_error or response.json().get("public") is not False:
            raise RuntimeError("Configure an existing private Supabase document bucket before startup")
    except (httpx.HTTPError, ValueError) as exc:
        raise RuntimeError("Cannot verify the private document bucket") from exc

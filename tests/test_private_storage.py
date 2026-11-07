import uuid
from unittest.mock import AsyncMock

import httpx
import pytest


@pytest.mark.asyncio
async def test_storage_uses_private_objects_and_never_overwrites(monkeypatch):
    from services import document_storage as storage
    from config import settings

    monkeypatch.setattr(settings, "supabase_url", "https://example.supabase.co")
    monkeypatch.setattr(settings, "supabase_service_role_key", "fake-server-key")
    requests = []

    async def handler(request):
        requests.append(request)
        return httpx.Response(200, content=b"%PDF-test")

    monkeypatch.setattr(storage, "_client", lambda: httpx.AsyncClient(transport=httpx.MockTransport(handler)))
    owner, course = uuid.uuid4(), uuid.uuid4()
    reference = await storage.store_document(owner, course, "../school.pdf", b"%PDF-test")
    assert reference.startswith(f"supabase://documents/{owner}/{course}/")
    assert ".." not in reference
    assert requests[0].headers["x-upsert"] == "false"
    assert "/object/public/" not in str(requests[0].url)
    assert await storage.download_document(reference) == b"%PDF-test"


@pytest.mark.asyncio
async def test_invalid_object_reference_never_reaches_network():
    from services.document_storage import download_document
    from fastapi import HTTPException

    with pytest.raises(HTTPException):
        await download_document("supabase://other-bucket/../../secret")


@pytest.mark.asyncio
async def test_storage_failure_does_not_expose_provider_response(monkeypatch):
    from services import document_storage as storage
    from fastapi import HTTPException
    monkeypatch.setattr(storage.settings, "supabase_url", "https://example.supabase.co")
    client = httpx.AsyncClient(transport=httpx.MockTransport(lambda r: httpx.Response(500, text="secret upstream detail")))
    monkeypatch.setattr(storage, "_client", lambda: client)
    with pytest.raises(HTTPException) as error:
        await storage.download_document("supabase://documents/a/b/c.pdf")
    assert error.value.status_code == 503
    assert "secret" not in error.value.detail


@pytest.mark.asyncio
async def test_public_bucket_cannot_start_application(monkeypatch):
    from services import document_storage as storage
    monkeypatch.setattr(storage.settings, "supabase_url", "https://example.supabase.co")
    monkeypatch.setattr(storage, "_client", lambda: httpx.AsyncClient(transport=httpx.MockTransport(lambda r: httpx.Response(200, json={"public": True}))))
    with pytest.raises(RuntimeError, match="private"):
        await storage.verify_private_bucket()

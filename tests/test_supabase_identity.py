import uuid

import httpx
import pytest
from fastapi import HTTPException


@pytest.mark.asyncio
async def test_supabase_identity_is_verified_by_auth_server(monkeypatch):
    from services.auth import supabase
    from config import settings
    uid = str(uuid.uuid4())
    monkeypatch.setattr(settings, "supabase_url", "https://family.supabase.co")
    monkeypatch.setattr(settings, "supabase_publishable_key", "fake-public-key")

    def handle(request):
        assert request.headers["Authorization"] == "Bearer user-token"
        assert str(request.url) == "https://family.supabase.co/auth/v1/user"
        return httpx.Response(200, json={"id": uid, "role": "authenticated", "email": "student@example.com", "is_anonymous": False})

    monkeypatch.setattr(supabase, "_client", lambda: httpx.AsyncClient(transport=httpx.MockTransport(handle)))
    assert (await supabase.get_identity("user-token"))["id"] == uid


@pytest.mark.asyncio
@pytest.mark.parametrize("response", [httpx.Response(401, json={"secret": "detail"}), httpx.Response(200, json={"id": str(uuid.uuid4()), "role": "service_role"})])
async def test_invalid_or_service_identity_cannot_use_app(monkeypatch, response):
    from services.auth import supabase
    monkeypatch.setattr(supabase.settings, "supabase_url", "https://example.supabase.co")
    monkeypatch.setattr(supabase, "_client", lambda: httpx.AsyncClient(transport=httpx.MockTransport(lambda r: response)))
    with pytest.raises(HTTPException) as error:
        await supabase.get_identity("bad-token")
    assert error.value.status_code == 401
    assert "secret" not in error.value.detail

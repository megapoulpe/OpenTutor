"""Supabase Auth verification and token exchange, using the existing HTTP client.

Identity is verified online so both legacy and asymmetric project signing keys
work without sharing a JWT signing secret with this application.
"""
import uuid

import httpx
from fastapi import HTTPException
from config import settings


def _client():
    return httpx.AsyncClient(timeout=15, follow_redirects=False)


async def auth_request(method: str, path: str, *, token: str | None = None, body: dict | None = None):
    headers = {"apikey": settings.supabase_publishable_key}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        async with _client() as client:
            response = await client.request(method, f"{settings.supabase_url.rstrip('/')}/auth/v1/{path}", headers=headers, json=body)
    except httpx.HTTPError as exc:
        raise HTTPException(503, "Authentication service is unavailable") from exc
    if response.status_code >= 500 or response.is_redirect:
        raise HTTPException(503, "Authentication service is unavailable")
    if response.is_error:
        raise HTTPException(401, "Invalid credentials or expired session", headers={"WWW-Authenticate": "Bearer"})
    if response.status_code == 204:
        return {}
    return response.json()


async def get_identity(token: str) -> dict:
    identity = await auth_request("GET", "user", token=token)
    try:
        uuid.UUID(identity["id"])
        if identity.get("role") != "authenticated" or identity.get("is_anonymous"):
            raise ValueError("Not a registered user")
    except (ValueError, KeyError, TypeError) as exc:
        raise HTTPException(401, "Invalid user identity") from exc
    return identity


async def exchange_token(grant_type: str, body: dict) -> dict:
    result = await auth_request("POST", f"token?grant_type={grant_type}", body=body)
    return {key: result[key] for key in ("access_token", "refresh_token", "token_type")}

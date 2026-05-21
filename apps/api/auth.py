"""Supabase JWT auth — FastAPI dependency and middleware."""

from __future__ import annotations

import os
from typing import Optional

import httpx
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

_bearer = HTTPBearer(auto_error=False)

SUPABASE_URL: Optional[str] = None
SUPABASE_ANON_KEY: Optional[str] = None


def _supabase_url() -> str:
    url = os.getenv("SUPABASE_URL") or SUPABASE_URL
    if not url:
        raise EnvironmentError("SUPABASE_URL not set")
    return url.rstrip("/")


def _anon_key() -> str:
    key = os.getenv("SUPABASE_ANON_KEY") or SUPABASE_ANON_KEY
    if not key:
        raise EnvironmentError("SUPABASE_ANON_KEY not set")
    return key


async def _verify_jwt_with_supabase(token: str) -> dict:
    """
    Verify a Supabase JWT by calling auth/v1/user.
    Returns the user dict on success, raises HTTPException on failure.
    """
    url = f"{_supabase_url()}/auth/v1/user"
    headers = {
        "Authorization": f"Bearer {token}",
        "apikey": _anon_key(),
    }
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(url, headers=headers)

    if resp.status_code == 200:
        return resp.json()

    raise HTTPException(status_code=401, detail="Invalid or expired token")


async def require_auth(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
) -> dict:
    """FastAPI dependency — verifies Supabase JWT and returns the user dict."""
    if credentials is None:
        raise HTTPException(status_code=401, detail="Authorization header required")
    return await _verify_jwt_with_supabase(credentials.credentials)

"""One-time game Discord-auth handoff tokens (HMAC)."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import threading
import time
import uuid
from typing import Any

_used_jtis: dict[str, int] = {}
_jti_lock = threading.Lock()


def _b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _b64url_decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)


def _purge_used_jtis(now: int) -> None:
    expired = [jti for jti, exp in _used_jtis.items() if exp <= now]
    for jti in expired:
        _used_jtis.pop(jti, None)


def verify_site_login_token(token: str, secret: str, *, consume: bool = True) -> dict[str, Any]:
    try:
        body, sig = token.split(".", 1)
    except ValueError as exc:
        raise ValueError("Malformed token") from exc

    expected = hmac.new(secret.encode("utf-8"), body.encode("ascii"), hashlib.sha256).digest()
    if not hmac.compare_digest(_b64url_encode(expected), sig):
        raise ValueError("Invalid token signature")

    try:
        payload = json.loads(_b64url_decode(body).decode("utf-8"))
    except (ValueError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("Malformed token payload") from exc

    if not isinstance(payload, dict):
        raise ValueError("Malformed token payload")

    now = int(time.time())
    if int(payload.get("exp", 0)) < now:
        raise ValueError("Token expired")

    discord_id = str(payload.get("discord_id") or "")
    username = str(payload.get("username") or "")
    jti = payload.get("jti")
    ss14_user_id = payload.get("ss14_user_id")
    if not discord_id.isdigit() or not username or not jti:
        raise ValueError("Token missing identity")
    if ss14_user_id:
        try:
            uuid.UUID(str(ss14_user_id))
        except ValueError as exc:
            raise ValueError("Invalid ss14_user_id") from exc

    with _jti_lock:
        _purge_used_jtis(now)
        if consume:
            key = str(jti)
            if key in _used_jtis:
                raise ValueError("Token already used")
            _used_jtis[key] = int(payload.get("exp", now))

    return payload

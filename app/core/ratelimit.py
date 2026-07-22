"""In-memory rate limits, cooldowns, and request body guards."""
from __future__ import annotations

import hashlib
import hmac
import secrets
import threading
import time
from collections import defaultdict, deque
from typing import Deque

from fastapi import HTTPException, Request
from starlette.responses import JSONResponse

from app.config import (
    ANTIBOT_DIFFICULTY,
    ANTIBOT_SECRET,
    MAX_BODY_BYTES,
    MAX_BODY_UPLOAD_BYTES,
)


_lock = threading.Lock()
_hits: dict[str, Deque[float]] = defaultdict(deque)
_cooldowns: dict[str, float] = {}
_last_purge = 0.0


def client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip() or "unknown"
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


def _purge(now: float) -> None:
    global _last_purge
    if now - _last_purge < 30:
        return
    _last_purge = now
    stale_keys = []
    for key, q in _hits.items():
        while q and now - q[0] > 600:
            q.popleft()
        if not q:
            stale_keys.append(key)
    for key in stale_keys:
        _hits.pop(key, None)
    stale_cd = [k for k, until in _cooldowns.items() if until <= now]
    for key in stale_cd:
        _cooldowns.pop(key, None)


def hit(bucket: str, key: str, *, limit: int, window: float) -> tuple[bool, float]:
    """
    Record a hit. Returns (allowed, retry_after_seconds).
    Sliding window: at most `limit` events in the last `window` seconds.
    """
    now = time.monotonic()
    full_key = f"{bucket}:{key}"
    with _lock:
        _purge(now)
        q = _hits[full_key]
        while q and now - q[0] > window:
            q.popleft()
        if len(q) >= limit:
            retry = max(0.1, window - (now - q[0]))
            return False, retry
        q.append(now)
        return True, 0.0


def enforce_rate(
    request: Request,
    bucket: str,
    *,
    limit: int,
    window: float,
    user_key: str | None = None,
    detail: str = "Слишком много запросов. Подождите немного.",
) -> None:
    ip = client_ip(request)
    keys = [f"ip:{ip}"]
    if user_key:
        keys.append(f"user:{user_key}")
    worst_retry = 0.0
    blocked = False
    for key in keys:
        ok, retry = hit(bucket, key, limit=limit, window=window)
        if not ok:
            blocked = True
            worst_retry = max(worst_retry, retry)
    if blocked:
        raise HTTPException(
            status_code=429,
            detail=detail,
            headers={"Retry-After": str(max(1, int(worst_retry + 0.999)))},
        )


def enforce_cooldown(
    key: str,
    seconds: float,
    *,
    detail: str = "Подождите перед следующим действием.",
) -> None:
    now = time.monotonic()
    with _lock:
        until = _cooldowns.get(key, 0.0)
        if until > now:
            raise HTTPException(
                status_code=429,
                detail=detail,
                headers={"Retry-After": str(max(1, int(until - now + 0.999)))},
            )
        _cooldowns[key] = now + seconds


def max_body_for_path(path: str) -> int:
    upload_prefixes = (
        "/api/chat",
        "/api/social/posts",
        "/api/messages/send",
        "/api/support/tickets",
        "/api/social/profile/avatar",
        "/api/admin/support-tickets",
    )
    if any(path.startswith(p) for p in upload_prefixes):
        return MAX_BODY_UPLOAD_BYTES
    return MAX_BODY_BYTES


async def body_limit_middleware(request: Request, call_next):
    path = request.url.path
    limit = max_body_for_path(path)
    cl = request.headers.get("content-length")
    if cl:
        try:
            if int(cl) > limit:
                return JSONResponse(
                    {"detail": f"Тело запроса слишком большое (макс. {limit // (1024 * 1024)} МБ)"},
                    status_code=413,
                )
        except ValueError:
            return JSONResponse({"detail": "Некорректный Content-Length"}, status_code=400)
    return await call_next(request)


# Path rules: (prefix_or_exact, methods, limit, window_sec, per_user)
_API_RULES: list[tuple[str, set[str], int, float, bool]] = [
    ("/api/chat", {"GET"}, 40, 60.0, False),          # poll: ~1/1.5s
    ("/api/chat", {"POST"}, 20, 60.0, True),
    ("/api/messages/conversation", {"GET"}, 45, 60.0, True),
    ("/api/messages/unread-count", {"GET"}, 40, 60.0, True),
    ("/api/messages/dialogs", {"GET"}, 40, 60.0, True),
    ("/api/messages/send", {"POST"}, 30, 60.0, True),
    ("/api/messages/users", {"GET"}, 30, 60.0, True),
    ("/api/social/search", {"GET"}, 30, 60.0, False),
    ("/api/social/feed-updates", {"GET"}, 20, 60.0, False),
    ("/api/social/posts", {"POST"}, 10, 60.0, True),
    ("/api/social/posts/", {"POST"}, 40, 60.0, True),  # likes/comments
    ("/api/support/tickets", {"POST"}, 8, 60.0, True),
    ("/api/auth/challenge", {"GET"}, 20, 60.0, False),
    ("/login", {"GET"}, 10, 60.0, False),
    ("/callback", {"GET"}, 20, 60.0, False),
]

_GLOBAL_API_LIMIT = 180
_GLOBAL_API_WINDOW = 60.0


def _session_user_key(request: Request) -> str | None:
    token = request.cookies.get("session_token")
    if not token:
        return None
    try:
        from app.core.sessions import get_session
        session = get_session(token)
        if session and session.get("discord_id"):
            return str(session["discord_id"])
    except Exception:
        return None
    return None


async def rate_limit_middleware(request: Request, call_next):
    path = request.url.path
    method = request.method.upper()

    if path.startswith("/static"):
        return await call_next(request)

    # Result URL Robokassa — не режем (идемпотентный callback)
    if path.startswith("/api/donations/robokassa/"):
        return await call_next(request)

    ip = client_ip(request)
    user_key = _session_user_key(request)

    if path.startswith("/api") or path in ("/login", "/callback"):
        ok, retry = hit("global", f"ip:{ip}", limit=_GLOBAL_API_LIMIT, window=_GLOBAL_API_WINDOW)
        if not ok:
            return JSONResponse(
                {"detail": "Слишком много запросов с вашего IP."},
                status_code=429,
                headers={"Retry-After": str(max(1, int(retry + 0.999)))},
            )

    for prefix, methods, limit, window, per_user in _API_RULES:
        if method not in methods:
            continue
        if path == prefix or path.startswith(prefix):
            keys = [f"ip:{ip}"]
            if per_user and user_key:
                keys.append(f"user:{user_key}")
            for key in keys:
                ok, retry = hit(f"rule:{prefix}:{method}", key, limit=limit, window=window)
                if not ok:
                    return JSONResponse(
                        {"detail": "Слишком часто. Замедлите запросы."},
                        status_code=429,
                        headers={"Retry-After": str(max(1, int(retry + 0.999)))},
                    )
            break

    return await call_next(request)


# ---------- Antibot PoW challenge ----------

def _sign_challenge(nonce: str, exp: int, difficulty: int) -> str:
    payload = f"{nonce}:{exp}:{difficulty}".encode()
    return hmac.new(ANTIBOT_SECRET.encode(), payload, hashlib.sha256).hexdigest()


def issue_pow_challenge() -> dict:
    nonce = secrets.token_hex(16)
    exp = int(time.time()) + 120
    difficulty = ANTIBOT_DIFFICULTY
    return {
        "nonce": nonce,
        "exp": exp,
        "difficulty": difficulty,
        "sig": _sign_challenge(nonce, exp, difficulty),
    }


def verify_pow_challenge(nonce: str, exp: int, difficulty: int, sig: str, counter: str) -> bool:
    try:
        exp_i = int(exp)
        diff_i = int(difficulty)
        counter_i = int(counter)
    except (TypeError, ValueError):
        return False
    if exp_i < int(time.time()):
        return False
    if diff_i != ANTIBOT_DIFFICULTY:
        return False
    if counter_i < 0 or counter_i > 5_000_000:
        return False
    expected = _sign_challenge(str(nonce), exp_i, diff_i)
    if not hmac.compare_digest(expected, str(sig or "")):
        return False
    digest = hashlib.sha256(f"{nonce}:{counter_i}".encode()).hexdigest()
    return digest.startswith("0" * diff_i)

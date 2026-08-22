import json

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse, Response

import database_social as social_db
from app.config import WIKI_VISIT_ORIGINS
from app.core.ratelimit import enforce_rate

router = APIRouter(tags=["wiki-metrics"])


def _cors_headers(request: Request) -> dict[str, str]:
    origin = (request.headers.get("origin") or "").rstrip("/")
    if origin in WIKI_VISIT_ORIGINS:
        return {
            "Access-Control-Allow-Origin": origin,
            "Access-Control-Allow-Methods": "POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type",
            "Access-Control-Max-Age": "86400",
            "Vary": "Origin",
        }
    return {}


@router.options("/api/wiki/visit")
async def wiki_visit_options(request: Request):
    headers = _cors_headers(request)
    if not headers:
        raise HTTPException(status_code=403, detail="Forbidden")
    return Response(status_code=204, headers=headers)


@router.post("/api/wiki/visit")
async def record_wiki_visit(request: Request):
    headers = _cors_headers(request)
    if request.headers.get("origin") and not headers:
        raise HTTPException(status_code=403, detail="Forbidden")
    enforce_rate(request, "wiki-visit", limit=40, window=60.0)
    raw = (await request.body()).decode("utf-8", errors="replace").strip()
    try:
        payload = json.loads(raw) if raw else {}
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid payload")
    path = str(payload.get("path") or "/").strip()[:512] or "/"
    visitor_key = str(payload.get("visitor_key") or "").strip()[:64]
    if len(visitor_key) < 8:
        raise HTTPException(status_code=400, detail="visitor_key required")
    social_db.record_wiki_visit(path, visitor_key)
    return JSONResponse({"ok": True}, headers=headers)

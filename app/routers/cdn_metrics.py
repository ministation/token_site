from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

import database_social as social_db
from app.config import CDN_METRICS_SECRET

router = APIRouter(tags=["cdn-metrics"])


class CdnEventBody(BaseModel):
    event_type: str = Field(min_length=1, max_length=64)
    fork: str = Field(min_length=1, max_length=128)
    path: str | None = Field(default=None, max_length=512)
    version: str | None = Field(default=None, max_length=256)
    platform: str | None = Field(default=None, max_length=128)
    visitor_key: str | None = Field(default=None, max_length=64)
    bytes_sent: int | None = Field(default=None, ge=0)


@router.post("/api/internal/cdn/event")
async def record_cdn_metric_event(request: Request, body: CdnEventBody):
    if not CDN_METRICS_SECRET:
        raise HTTPException(status_code=503, detail="CDN metrics disabled")
    secret = request.headers.get("x-cdn-metrics-secret")
    if secret != CDN_METRICS_SECRET:
        raise HTTPException(status_code=403, detail="Forbidden")

    if body.event_type not in {"page_visit", "server_download", "content_download"}:
        raise HTTPException(status_code=400, detail="Unknown event type")

    social_db.record_cdn_event(
        body.event_type,
        body.fork,
        path=body.path,
        version=body.version,
        platform=body.platform,
        visitor_key=body.visitor_key,
        bytes_sent=body.bytes_sent,
    )
    return {"ok": True}


@router.get("/api/cdn/stats")
async def get_public_cdn_stats():
    stats = social_db.get_cdn_stats()
    return {
        "page_visits_total": stats.get("page_visits_total", 0),
        "page_visits_today": stats.get("page_visits_today", 0),
        "page_visitors_today": stats.get("page_visitors_today", 0),
        "page_visits_7d": stats.get("page_visits_7d", 0),
        "downloads_total": stats.get("downloads_total", 0),
        "downloads_today": stats.get("downloads_today", 0),
        "downloads_7d": stats.get("downloads_7d", 0),
    }

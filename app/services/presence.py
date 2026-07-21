"""Site presence (Discord-like online / idle / offline)."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable

import database_social as social_db

# Heartbeat every ~12s from the client; keep online window generous.
ONLINE_SECONDS = 90
IDLE_SECONDS = 600


def _parse_ts(value) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        dt = value
    else:
        text = str(value).strip()
        if not text:
            return None
        try:
            dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError:
            try:
                dt = datetime.strptime(text[:19], "%Y-%m-%d %H:%M:%S")
            except ValueError:
                return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def status_from_last_seen(last_seen_at) -> str:
    dt = _parse_ts(last_seen_at)
    if not dt:
        return "offline"
    age = (datetime.now(timezone.utc) - dt).total_seconds()
    if age <= ONLINE_SECONDS:
        return "online"
    if age <= IDLE_SECONDS:
        return "idle"
    return "offline"


def heartbeat(player_id: str) -> str:
    if not player_id:
        return "offline"
    social_db.touch_presence(player_id)
    return "online"


def statuses_for(player_ids: Iterable[str]) -> dict[str, str]:
    ids = [pid for pid in player_ids if pid]
    if not ids:
        return {}
    seen = social_db.get_presence_map(ids)
    return {pid: status_from_last_seen(seen.get(pid)) for pid in ids}

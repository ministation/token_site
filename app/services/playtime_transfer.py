"""Накрутка наигранного времени на должности в игровой БД."""
from __future__ import annotations

import uuid
from datetime import timedelta

from app.db.database import get_pg_pool
from app.services.bans import translate_role, list_job_roles
from app.services.job_icons import role_id_from_tracker, tracker_from_role_id, job_icon_url
from app.services.job_unlock import (
    evaluate_role_unlock,
    get_unlock_metadata,
    enrich_and_sort_roles,
    plan_unlock_all_additions,
)


def _parse_user_uuid(value: str) -> uuid.UUID | None:
    try:
        return uuid.UUID(str(value))
    except (ValueError, TypeError):
        return None


def _interval_to_minutes(value) -> float:
    if value is None:
        return 0.0
    if hasattr(value, "total_seconds"):
        return value.total_seconds() / 60.0
    return 0.0


def _format_hours(minutes: float) -> str:
    if minutes >= 60:
        h = int(minutes // 60)
        m = int(round(minutes % 60))
        return f"{h} ч {m} м" if m else f"{h} ч"
    return f"{int(round(minutes))} м"


def normalize_job_tracker(value: str) -> str:
    raw = (value or "").strip()
    if not raw:
        raise ValueError("Укажите должность")
    if raw == "Overall":
        return "Overall"
    if raw.startswith("Job") and not raw.startswith("Job:"):
        return raw
    if raw.startswith("Job:"):
        return tracker_from_role_id(raw[4:])
    known = {r["role_id"] for r in list_job_roles()}
    if raw in known:
        return tracker_from_role_id(raw)
    candidate = tracker_from_role_id(raw)
    if candidate:
        return candidate
    raise ValueError("Некорректная должность")


def _job_row(tracker: str, minutes: float) -> dict:
    if tracker == "Overall":
        role_id = "Overall"
        label = "Общее время"
        icon = job_icon_url("Passenger")
    else:
        role_id = role_id_from_tracker(tracker)
        label = translate_role(tracker)
        icon = job_icon_url(role_id)
    return {
        "tracker": tracker,
        "role_id": role_id,
        "label": label,
        "icon": icon,
        "minutes": round(minutes, 1),
        "hours": round(minutes / 60.0, 2),
        "time_text": _format_hours(minutes),
    }


async def fetch_player_minutes_map(user_uuid: str) -> dict[str, float]:
    uid = _parse_user_uuid(user_uuid)
    if not uid:
        return {}
    pg = await get_pg_pool()
    async with pg.acquire() as conn:
        rows = await conn.fetch("""
            SELECT tracker, time_spent
            FROM play_time
            WHERE player_id = $1
              AND (tracker LIKE 'Job%' OR tracker = 'Overall')
        """, uid)
    return {row["tracker"]: _interval_to_minutes(row["time_spent"]) for row in rows}


async def _fetch_job_minutes_map(user_uuid: str) -> dict[str, float]:
    return await fetch_player_minutes_map(user_uuid)


async def get_job_playtimes(user_uuid: str) -> list[dict]:
    minutes_map = await _fetch_job_minutes_map(user_uuid)
    result = []
    for tracker, minutes in minutes_map.items():
        if minutes <= 0:
            continue
        result.append(_job_row(tracker, minutes))
    result.sort(key=lambda item: -item["minutes"])
    return result


async def get_playtime_overview(user_uuid: str) -> dict:
    minutes_map = await _fetch_job_minutes_map(user_uuid)
    roles = []
    for catalog in list_job_roles():
        tracker = catalog["id"]
        role_id = catalog["role_id"]
        current = minutes_map.get(tracker, 0.0)
        unlock_info = evaluate_role_unlock(role_id, minutes_map)
        roles.append({
            **_job_row(tracker, current),
            "deficit_minutes": unlock_info["deficit_minutes"],
            "unlocked": unlock_info["unlocked"],
            "unlock_hint": unlock_info["unlock_hint"],
            "unlock_labels": unlock_info["unlock_labels"],
        })
    roles = enrich_and_sort_roles(roles)
    sources = [
        _job_row(tracker, minutes)
        for tracker, minutes in minutes_map.items()
        if minutes > 0
    ]
    sources.sort(key=lambda item: -item["minutes"])
    return {
        "roles": roles,
        "sources": sources,
        "unlock_source": get_unlock_metadata(),
    }


def build_unlock_all_plan(minutes_map: dict[str, float], from_tracker: str | None = None) -> dict:
    _ = from_tracker
    return plan_unlock_all_additions(minutes_map)


async def bulk_add_job_playtime(
    target_user_uuid: str,
    additions: list[tuple[str, float]],
    *,
    enforce_limit: bool = True,
) -> dict:
    uid = _parse_user_uuid(target_user_uuid)
    if not uid:
        raise ValueError("Некорректный игрок")

    normalized: list[tuple[str, float]] = []
    for to_tracker, minutes in additions:
        if minutes <= 0:
            continue
        to_tracker = normalize_job_tracker(to_tracker)
        normalized.append((to_tracker, round(minutes, 1)))

    if not normalized:
        raise ValueError("Укажите хотя бы одну роль и количество минут")

    total = round(sum(minutes for _, minutes in normalized), 1)
    max_boost = 24 * 60 * 365
    if enforce_limit and total > max_boost:
        raise ValueError(
            f"Слишком большая накрутка за один раз ({total} мин, максимум {max_boost} мин)"
        )

    pg = await get_pg_pool()
    async with pg.acquire() as conn:
        async with conn.transaction():
            applied = []
            for to_tracker, minutes in normalized:
                delta = timedelta(minutes=minutes)
                updated = await conn.execute(
                    """
                    UPDATE play_time
                    SET time_spent = time_spent + $3
                    WHERE player_id = $1 AND tracker = $2
                    """,
                    uid, to_tracker, delta,
                )
                if updated.split()[-1] == "0":
                    await conn.execute(
                        "INSERT INTO play_time (player_id, tracker, time_spent) VALUES ($1, $2, $3)",
                        uid, to_tracker, delta,
                    )
                applied.append({
                    "to_tracker": to_tracker,
                    "to_label": translate_role(to_tracker),
                    "minutes": minutes,
                })

    return {
        "success": True,
        "total_minutes": total,
        "transfers": applied,
    }


async def transfer_job_playtime(
    target_user_uuid: str,
    from_tracker: str,
    to_tracker: str,
    minutes: float,
) -> dict:
    result = await bulk_add_job_playtime(
        target_user_uuid,
        [(to_tracker, minutes)],
    )
    transfer = result["transfers"][0]
    return {
        "success": True,
        "to_tracker": transfer["to_tracker"],
        "minutes": transfer["minutes"],
        "to_label": transfer["to_label"],
    }


async def bulk_transfer_job_playtime(
    target_user_uuid: str,
    from_tracker: str,
    transfers: list[tuple[str, float]],
) -> dict:
    _ = from_tracker
    return await bulk_add_job_playtime(target_user_uuid, transfers)

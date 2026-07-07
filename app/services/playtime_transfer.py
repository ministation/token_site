"""Перенос наигранного времени между должностями в игровой БД."""
from __future__ import annotations

import uuid
from datetime import timedelta

from app.db.database import get_pg_pool
from app.services.bans import translate_role, list_job_roles


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


def _normalize_job_tracker(tracker: str) -> str:
    tracker = (tracker or "").strip()
    if not tracker:
        raise ValueError("Укажите должность")
    if tracker.startswith("Job:"):
        return tracker
    if tracker in {r["id"] for r in list_job_roles()}:
        return f"Job:{tracker}"
    raise ValueError("Некорректная должность")


async def get_job_playtimes(user_uuid: str) -> list[dict]:
    uid = _parse_user_uuid(user_uuid)
    if not uid:
        return []
    pg = await get_pg_pool()
    async with pg.acquire() as conn:
        rows = await conn.fetch("""
            SELECT tracker, time_spent
            FROM play_time
            WHERE player_id = $1 AND tracker LIKE 'Job:%'
            ORDER BY time_spent DESC
        """, uid)
    result = []
    for row in rows:
        minutes = _interval_to_minutes(row["time_spent"])
        if minutes <= 0:
            continue
        tracker = row["tracker"]
        result.append({
            "tracker": tracker,
            "role_id": tracker[4:] if tracker.startswith("Job:") else tracker,
            "label": translate_role(tracker),
            "minutes": round(minutes, 1),
            "hours": round(minutes / 60.0, 2),
        })
    return result


async def transfer_job_playtime(
    target_user_uuid: str,
    from_tracker: str,
    to_tracker: str,
    minutes: float,
) -> dict:
    uid = _parse_user_uuid(target_user_uuid)
    if not uid:
        raise ValueError("Некорректный игрок")
    from_tracker = _normalize_job_tracker(from_tracker)
    to_tracker = _normalize_job_tracker(to_tracker)
    if from_tracker == to_tracker:
        raise ValueError("Выберите разные должности")
    if minutes <= 0:
        raise ValueError("Укажите положительное время")
    if minutes > 24 * 60 * 30:
        raise ValueError("Слишком большой перенос за один раз")

    delta = timedelta(minutes=minutes)
    pg = await get_pg_pool()
    async with pg.acquire() as conn:
        async with conn.transaction():
            source = await conn.fetchrow(
                "SELECT time_spent FROM play_time WHERE player_id = $1 AND tracker = $2",
                uid, from_tracker,
            )
            available = source["time_spent"] if source else timedelta(0)
            if _interval_to_minutes(available) < minutes:
                raise ValueError("Недостаточно времени на исходной должности")

            await conn.execute(
                "UPDATE play_time SET time_spent = time_spent - $3 WHERE player_id = $1 AND tracker = $2",
                uid, from_tracker, delta,
            )
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

    return {
        "success": True,
        "from_tracker": from_tracker,
        "to_tracker": to_tracker,
        "minutes": round(minutes, 1),
        "from_label": translate_role(from_tracker),
        "to_label": translate_role(to_tracker),
    }

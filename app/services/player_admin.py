"""Полное досье игрока для игровой админ-панели."""

from __future__ import annotations

import database_social as social_db
from app.db.database import get_pg_pool
from app.services.bans import _fetch_bans, _parse_player_uuid


async def _safe_fetch(conn, query: str, *args):
    try:
        return await conn.fetch(query, *args)
    except Exception:
        return []


async def get_full_player_dossier(user_uuid: str) -> dict | None:
    uid = _parse_player_uuid(user_uuid)
    if not uid:
        return None

    pg = await get_pg_pool()
    async with pg.acquire() as conn:
        row = await conn.fetchrow("""
            SELECT user_id::text AS user_uuid,
                   player_id::text AS player_id,
                   last_seen_user_name AS name,
                   first_seen_time,
                   last_seen_time,
                   last_seen_address::text AS last_ip
            FROM player
            WHERE user_id = $1
        """, uid)
        if not row:
            return None

        bans = await _fetch_bans(conn, None, "all", str(uid), None, 50, 0)

        profiles = await _safe_fetch(conn, """
            SELECT pr.slot, pr.char_name, pr.species, pr.age, pr.gender, pr.flavor_text,
                   p.selected_character_slot
            FROM preference p
            LEFT JOIN profile pr ON pr.preference_id = p.id
            WHERE p.user_id = $1
            ORDER BY pr.slot NULLS LAST
        """, uid)

        playtimes = await _safe_fetch(conn, """
            SELECT tracker, time_spent
            FROM play_time
            WHERE player_id = $1
            ORDER BY time_spent DESC
            LIMIT 30
        """, uid)

        notes = []
        for table, player_col in (
            ("admin_note", "player_user_id"),
            ("admin_notes", "player_user_id"),
            ("admin_watchlist", "player_user_id"),
            ("admin_message", "player_user_id"),
        ):
            rows = await _safe_fetch(conn, f"""
                SELECT id, message, severity, created_at, expiration_time, deleted, secret
                FROM {table}
                WHERE {player_col} = $1 AND COALESCE(deleted, false) = false
                ORDER BY created_at DESC
                LIMIT 40
            """, uid)
            if rows:
                for n in rows:
                    notes.append({
                        "id": n["id"],
                        "type": table.replace("admin_", "").replace("_", " "),
                        "message": n["message"] or "",
                        "severity": n.get("severity"),
                        "created_at": n["created_at"].isoformat() if n.get("created_at") else None,
                        "expiration_time": n["expiration_time"].isoformat() if n.get("expiration_time") else None,
                        "secret": bool(n.get("secret")),
                    })
                break

        if not notes:
            rows = await _safe_fetch(conn, """
                SELECT admin_note_id AS id, message, severity, created_at, expiration_time,
                       deleted, secret
                FROM admin_notes
                WHERE player_user_id = $1 AND COALESCE(deleted, false) = false
                ORDER BY created_at DESC
                LIMIT 40
            """, uid)
            for n in rows:
                notes.append({
                    "id": n["id"],
                    "type": "note",
                    "message": n["message"] or "",
                    "severity": n.get("severity"),
                    "created_at": n["created_at"].isoformat() if n.get("created_at") else None,
                    "expiration_time": n["expiration_time"].isoformat() if n.get("expiration_time") else None,
                    "secret": bool(n.get("secret")),
                })

    characters = []
    selected_slot = None
    for p in profiles:
        if p.get("selected_character_slot") is not None:
            selected_slot = p["selected_character_slot"]
        if p.get("char_name"):
            characters.append({
                "slot": p["slot"],
                "name": p["char_name"],
                "species": p.get("species"),
                "age": p.get("age"),
                "gender": p.get("gender"),
                "flavor_text": (p.get("flavor_text") or "")[:500],
                "is_selected": p.get("slot") == selected_slot,
            })

    pt_list = []
    for pt in playtimes:
        ts = pt["time_spent"]
        hours = round(ts.total_seconds() / 3600, 1) if hasattr(ts, "total_seconds") else 0
        pt_list.append({"tracker": pt["tracker"], "hours": hours})

    site = social_db.get_social_user_by_user_uuid(str(uid))
    if not site:
        site = social_db.get_social_user_by_player_id(str(uid))

    return {
        "user_uuid": row["user_uuid"],
        "player_id": row["player_id"],
        "name": row["name"],
        "first_seen": row["first_seen_time"].isoformat() if row["first_seen_time"] else None,
        "last_seen": row["last_seen_time"].isoformat() if row["last_seen_time"] else None,
        "last_ip": row["last_ip"],
        "characters": characters,
        "playtime": pt_list,
        "notes": notes,
        "bans": bans,
        "site_account": {
            "linked": site is not None,
            "player_id": site["player_id"] if site else None,
            "discord_username": site.get("discord_username") if site else None,
            "game_nickname": site.get("game_nickname") if site else None,
            "avatar": site.get("discord_avatar") or site.get("avatar_path") if site else None,
            "can_message": site is not None and site.get("player_id"),
        } if site else {"linked": False, "can_message": False},
    }

import uuid
from datetime import datetime, timedelta, timezone

from app.db.database import get_pg_pool

BAN_TYPE_SERVER = 0
BAN_TYPE_ROLE = 1

ROLE_TRANSLATIONS = {
    'Paramedic': 'Парамедик', 'ChiefMedicalOfficer': 'Главный врач', 'Psychologist': 'Психолог',
    'MedicalDoctor': 'Врач', 'Chemist': 'Химик', 'MedicalIntern': 'Медицинский интерн',
    'Surgeon': 'Хирург', 'Virologist': 'Вирусолог',
    'ChiefEngineer': 'Старший инженер', 'StationEngineer': 'Инженер станции',
    'TechnicalAssistant': 'Технический ассистент', 'AtmosphericTechnician': 'Атмосферный техник',
    'HeadOfSecurity': 'Глава службы безопасности', 'Pilot': 'Пилот',
    'Detective': 'Детектив', 'Brigmedic': 'Бригмедик', 'SecurityOfficer': 'Офицер безопасности',
    'SecurityCadet': 'Кадет безопасности', 'Warden': 'Смотритель', 'CBURN': 'РХБЗЗ',
    'Captain': 'Капитан', 'BlueshieldOfficer': 'ОСЩ', 'CommandMaid': 'Командная горничная',
    'CentralCommandOfficial': 'Представитель ЦентКома', 'NanotrasenRepresentative': 'Представитель НаноТрейзен',
    'DeathSquad': 'Эскадрон смерти', 'ERTLeader': 'Лидер ОБР', 'ERTEngineer': 'Инженер ОБР',
    'ERTMedical': 'Медик ОБР', 'ERTChaplain': 'Священник ОБР', 'ERTSecurity': 'Офицер безопасности ОБР',
    'ERTJanitor': 'Уборщик ОБР', 'HecuOperative': 'Оперативник ХЕКУ',
    'Quartermaster': 'Квартирмейстер', 'HeadOfPersonnel': 'Глава персонала',
    'ResearchDirector': 'Директор исследований', 'Scientist': 'Ученый',
    'ResearchAssistant': 'Лаборант', 'Roboticist': 'Робототехник',
    'Botanist': 'Ботаник', 'Bartender': 'Бармен', 'Clown': 'Клоун',
    'Chef': 'Шеф-повар', 'Janitor': 'Уборщик', 'Lawyer': 'Юрист',
    'Librarian': 'Библиотекарь', 'Visitor': 'Посетитель', 'ServiceWorker': 'Работник сервиса',
    'Zookeeper': 'Смотритель зоопарка', 'Musician': 'Музыкант', 'Chaplain': 'Священник',
    'Mime': 'Мим', 'Passenger': 'Пассажир', 'CargoTechnician': 'Карго-техник',
    'Reporter': 'Репортер', 'SalvageSpecialist': 'Спасатель',
    'Boxer': 'Боксер', 'RadioHost': 'Радиоведущий', 'Diplomat': 'Дипломат',
    'GovernmentMan': 'Правительственный агент', 'SpecialOperationsOfficer': 'Офицер спецопераций',
    'NavyOfficerUndercover': 'Офицер флота под прикрытием', 'NavyCaptain': 'Капитан флота',
    'NavyOfficer': 'Офицер флота', 'NanotrasenCareerTrainer': 'Инструктор НаноТрейзен',
    'PartyMaker': 'Организатор вечеринок', 'SecurityClown': 'Клоун безопасности',
    'Borg': 'Борг', 'StationAi': 'ИИ станции',
    'ShaftMiner': 'Шахтёр', 'Bitrunner': 'Битраннер', 'WardenHelper': 'Помощник смотрителя',
    'Assistant': 'Ассистент',
}


def translate_role(role: str) -> str:
    if role.startswith("Job:"):
        role = role[4:]
    elif role.startswith("Job") and len(role) > 3:
        role = role[3:]
    return ROLE_TRANSLATIONS.get(role, role)


def list_job_roles() -> list[dict]:
    import json
    from pathlib import Path
    from app.services.job_icons import tracker_from_role_id, job_icon_url

    role_ids = set(ROLE_TRANSLATIONS)
    unlock_path = Path(__file__).resolve().parents[2] / "data" / "mini_station_job_unlock.json"
    if unlock_path.is_file():
        try:
            data = json.loads(unlock_path.read_text(encoding="utf-8"))
            role_ids.update(data.get("jobs", {}))
            role_ids.update(data.get("role_to_department", {}))
        except (json.JSONDecodeError, OSError):
            pass

    return [
        {
            "id": tracker_from_role_id(role_id),
            "role_id": role_id,
            "label": ROLE_TRANSLATIONS.get(role_id, translate_role(role_id)),
            "icon": job_icon_url(role_id),
        }
        for role_id in sorted(role_ids, key=lambda item: ROLE_TRANSLATIONS.get(item, item))
    ]


def _parse_admin_uuid(admin_uuid: str | None) -> uuid.UUID | None:
    if not admin_uuid or str(admin_uuid).startswith("discord_"):
        return None
    try:
        return uuid.UUID(str(admin_uuid))
    except ValueError:
        return None


def _parse_player_uuid(value: str | None) -> uuid.UUID | None:
    if not value:
        return None
    try:
        return uuid.UUID(str(value))
    except ValueError:
        return None


async def resolve_player_identifier(name_or_uuid: str) -> uuid.UUID | None:
    query = (name_or_uuid or "").strip()
    if not query:
        return None
    pg = await get_pg_pool()
    async with pg.acquire() as conn:
        uid = _parse_player_uuid(query)
        if uid:
            found = await conn.fetchval("SELECT user_id FROM player WHERE user_id = $1", uid)
            return found
        row = await conn.fetchrow("""
            SELECT user_id
            FROM player
            WHERE LOWER(last_seen_user_name) = LOWER($1)
            ORDER BY last_seen_time DESC NULLS LAST
            LIMIT 1
        """, query)
        return row["user_id"] if row else None


async def search_players(query: str, limit: int = 20) -> list[dict]:
    q = (query or "").strip()
    if len(q) < 2:
        return []
    pg = await get_pg_pool()
    async with pg.acquire() as conn:
        uid = _parse_player_uuid(q)
        if uid:
            rows = await conn.fetch("""
                SELECT user_id::text AS user_uuid, last_seen_user_name AS name,
                       last_seen_time, last_seen_address::text AS last_ip
                FROM player WHERE user_id = $1
            """, uid)
        else:
            rows = await conn.fetch("""
                SELECT user_id::text AS user_uuid, last_seen_user_name AS name,
                       last_seen_time, last_seen_address::text AS last_ip
                FROM player
                WHERE last_seen_user_name ILIKE '%' || $1 || '%'
                ORDER BY last_seen_time DESC NULLS LAST
                LIMIT $2
            """, q, limit)
    return [{
        "user_uuid": r["user_uuid"],
        "name": r["name"],
        "last_seen": r["last_seen_time"].isoformat() if r["last_seen_time"] else None,
        "last_ip": r["last_ip"],
    } for r in rows]


async def get_player_profile(user_uuid: str) -> dict | None:
    uid = _parse_player_uuid(user_uuid)
    if not uid:
        return None
    pg = await get_pg_pool()
    async with pg.acquire() as conn:
        row = await conn.fetchrow("""
            SELECT user_id::text AS user_uuid, last_seen_user_name AS name,
                   first_seen_time, last_seen_time, last_seen_address::text AS last_ip
            FROM player WHERE user_id = $1
        """, uid)
        if not row:
            return None
        bans = await _fetch_bans(conn, ban_type=None, status="all", player_uuid=str(uid), limit=30, offset=0)
        return {
            "user_uuid": row["user_uuid"],
            "name": row["name"],
            "first_seen": row["first_seen_time"].isoformat() if row["first_seen_time"] else None,
            "last_seen": row["last_seen_time"].isoformat() if row["last_seen_time"] else None,
            "last_ip": row["last_ip"],
            "bans": bans,
        }


def _is_active(expiration_time, unban_time) -> bool:
    if unban_time is not None:
        return False
    if expiration_time is None:
        return True
    exp = expiration_time
    if exp.tzinfo is None:
        exp = exp.replace(tzinfo=timezone.utc)
    return exp > datetime.now(timezone.utc)


async def _fetch_bans(
    conn,
    ban_type: int | None,
    status: str,
    player_uuid: str | None,
    search: str | None,
    limit: int,
    offset: int,
) -> list[dict]:
    conditions = ["1=1"]
    params: list = []
    idx = 1

    if ban_type is not None:
        conditions.append(f"b.type = ${idx}")
        params.append(ban_type)
        idx += 1

    if status == "active":
        conditions.append("u.ban_id IS NULL")
        conditions.append("(b.expiration_time IS NULL OR b.expiration_time > NOW())")
    elif status == "expired":
        conditions.append("(u.ban_id IS NOT NULL OR (b.expiration_time IS NOT NULL AND b.expiration_time <= NOW()))")

    if player_uuid:
        conditions.append(f"EXISTS (SELECT 1 FROM ban_player bp2 WHERE bp2.ban_id = b.ban_id AND bp2.user_id::text = ${idx})")
        params.append(player_uuid)
        idx += 1

    if search:
        conditions.append(f"""(
            EXISTS (
                SELECT 1 FROM ban_player bp_s
                JOIN player p_s ON p_s.user_id = bp_s.user_id
                WHERE bp_s.ban_id = b.ban_id AND p_s.last_seen_user_name ILIKE '%' || ${idx} || '%'
            )
            OR b.reason ILIKE '%' || ${idx} || '%'
            OR CAST(b.ban_id AS text) = ${idx}
        )""")
        params.append(search.strip())
        idx += 1

    where = " AND ".join(conditions)
    params.extend([limit, offset])

    rows = await conn.fetch(f"""
        SELECT
            b.ban_id, b.type, b.ban_time, b.expiration_time, b.reason,
            b.banning_admin,
            p_admin.last_seen_user_name AS admin_name,
            u.unban_time, u.unbanning_admin,
            p_unban.last_seen_user_name AS unban_admin_name,
            COALESCE(bp_agg.players, ARRAY[]::text[]) AS player_ids,
            COALESCE(br_agg.roles, ARRAY[]::text[]) AS roles,
            COALESCE(brnd_agg.rounds, ARRAY[]::integer[]) AS rounds
        FROM ban b
        LEFT JOIN unban u ON u.ban_id = b.ban_id
        LEFT JOIN player p_admin ON b.banning_admin = p_admin.user_id
        LEFT JOIN player p_unban ON u.unbanning_admin = p_unban.user_id
        LEFT JOIN LATERAL (
            SELECT ARRAY_AGG(bp.user_id::text) AS players
            FROM ban_player bp WHERE bp.ban_id = b.ban_id
        ) bp_agg ON true
        LEFT JOIN LATERAL (
            SELECT ARRAY_AGG(br.role_id) AS roles
            FROM ban_role br WHERE br.ban_id = b.ban_id
        ) br_agg ON true
        LEFT JOIN LATERAL (
            SELECT ARRAY_AGG(brn.round_id) AS rounds
            FROM ban_round brn WHERE brn.ban_id = b.ban_id
        ) brnd_agg ON true
        WHERE {where}
        ORDER BY b.ban_time DESC
        LIMIT ${idx} OFFSET ${idx + 1}
    """, *params)

    bans = []
    for row in rows:
        player_names = []
        for pid in (row["player_ids"] or []):
            p = await conn.fetchrow(
                "SELECT last_seen_user_name FROM player WHERE user_id::text = $1", pid
            )
            player_names.append(p["last_seen_user_name"] if p else pid[:8] + "...")

        bans.append({
            "ban_id": row["ban_id"],
            "type": row["type"],
            "ban_time": row["ban_time"].isoformat() if row["ban_time"] else None,
            "expiration_time": row["expiration_time"].isoformat() if row["expiration_time"] else None,
            "reason": row["reason"] or "Не указана",
            "admin_name": row["admin_name"] or "Неизвестный",
            "player_names": player_names,
            "player_ids": row["player_ids"] or [],
            "roles": [translate_role(r) for r in (row["roles"] or [])],
            "role_ids": row["roles"] or [],
            "rounds": row["rounds"] or [],
            "is_active": _is_active(row["expiration_time"], row["unban_time"]),
            "is_unbanned": row["unban_time"] is not None,
            "unban_time": row["unban_time"].isoformat() if row["unban_time"] else None,
            "unban_admin_name": row["unban_admin_name"],
        })
    return bans


async def get_all_bans(
    limit: int = 50,
    offset: int = 0,
    ban_type: int | None = None,
    status: str = "all",
    player_uuid: str | None = None,
    search: str | None = None,
):
    pg = await get_pg_pool()
    async with pg.acquire() as conn:
        return await _fetch_bans(conn, ban_type, status, player_uuid, search, limit, offset)


async def get_player_bans(user_uuid: str | None = None, ckey: str | None = None, limit: int = 50):
    pg = await get_pg_pool()
    async with pg.acquire() as conn:
        user_ids: set[str] = set()
        if user_uuid:
            user_ids.add(user_uuid)
            rows = await conn.fetch("""
                SELECT DISTINCT user_id::text AS uid
                FROM player
                WHERE user_id::text = $1
                   OR player_id::text = $1
                   OR ($2::text IS NOT NULL AND $2 != '' AND LOWER(last_seen_user_name) = LOWER($2))
            """, user_uuid, ckey)
            for r in rows:
                user_ids.add(r["uid"])
        elif ckey:
            rows = await conn.fetch("""
                SELECT DISTINCT user_id::text AS uid
                FROM player
                WHERE LOWER(last_seen_user_name) = LOWER($1)
            """, ckey)
            for r in rows:
                user_ids.add(r["uid"])

        if not user_ids:
            return []

        all_bans = []
        for uid in user_ids:
            all_bans.extend(await _fetch_bans(conn, None, "all", uid, None, limit, 0))
        all_bans.sort(key=lambda b: b.get("ban_time") or "", reverse=True)
        seen = set()
        unique = []
        for b in all_bans:
            if b["ban_id"] in seen:
                continue
            seen.add(b["ban_id"])
            unique.append(b)
        return unique[:limit]


async def unban_ban(ban_id: int, admin_uuid: str | None) -> bool:
    """Снимает бан через INSERT в unban (как SS14.Admin и игровой сервер)."""
    pg = await get_pg_pool()
    admin_uid = _parse_admin_uuid(admin_uuid)
    async with pg.acquire() as conn:
        exists = await conn.fetchval("SELECT 1 FROM ban WHERE ban_id = $1", ban_id)
        if not exists:
            return False
        already = await conn.fetchval("SELECT 1 FROM unban WHERE ban_id = $1", ban_id)
        if already:
            return True
        await conn.execute("""
            INSERT INTO unban (ban_id, unbanning_admin, unban_time)
            VALUES ($1, $2, NOW())
        """, ban_id, admin_uid)
    return True


async def lift_ban(ban_id: int, admin_uuid: str | None = None) -> bool:
    return await unban_ban(ban_id, admin_uuid)


async def create_server_ban(
    admin_uuid: str | None,
    player_query: str,
    reason: str,
    length_minutes: int = 0,
    use_last_ip: bool = False,
) -> dict:
    reason = (reason or "").strip()
    if not reason:
        raise ValueError("Укажите причину бана")

    player_uid = await resolve_player_identifier(player_query)
    if not player_uid:
        raise ValueError("Игрок не найден")

    admin_uid = _parse_admin_uuid(admin_uuid)
    expiration = None
    if length_minutes and length_minutes > 0:
        expiration = datetime.now(timezone.utc) + timedelta(minutes=length_minutes)

    pg = await get_pg_pool()
    async with pg.acquire() as conn:
        async with conn.transaction():
            ban_id = await conn.fetchval("""
                INSERT INTO ban (
                    type, ban_time, expiration_time, reason, severity,
                    banning_admin, exempt_flags, hidden, auto_delete, playtime_at_note
                )
                VALUES (0, NOW(), $1, $2, 1, $3, 0, false, false, interval '0')
                RETURNING ban_id
            """, expiration, reason, admin_uid)

            await conn.execute(
                "INSERT INTO ban_player (user_id, ban_id) VALUES ($1, $2)",
                player_uid, ban_id,
            )

            if use_last_ip:
                ip = await conn.fetchval(
                    "SELECT last_seen_address FROM player WHERE user_id = $1", player_uid
                )
                if ip:
                    await conn.execute(
                        "INSERT INTO ban_address (address, ban_id) VALUES ($1::inet, $2)",
                        str(ip), ban_id,
                    )

    return {"ban_id": ban_id, "type": BAN_TYPE_SERVER, "player_uuid": str(player_uid)}


async def create_role_ban(
    admin_uuid: str | None,
    player_query: str,
    role_ids: list[str],
    reason: str,
    length_minutes: int = 0,
) -> dict:
    reason = (reason or "").strip()
    roles = [r.strip() for r in role_ids if r and r.strip()]
    if not reason:
        raise ValueError("Укажите причину бана")
    if not roles:
        raise ValueError("Выберите хотя бы одну должность")

    player_uid = await resolve_player_identifier(player_query)
    if not player_uid:
        raise ValueError("Игрок не найден")

    admin_uid = _parse_admin_uuid(admin_uuid)
    expiration = None
    if length_minutes and length_minutes > 0:
        expiration = datetime.now(timezone.utc) + timedelta(minutes=length_minutes)

    pg = await get_pg_pool()
    async with pg.acquire() as conn:
        async with conn.transaction():
            ban_id = await conn.fetchval("""
                INSERT INTO ban (
                    type, ban_time, expiration_time, reason, severity,
                    banning_admin, exempt_flags, hidden, auto_delete, playtime_at_note
                )
                VALUES (1, NOW(), $1, $2, 1, $3, 0, false, false, interval '0')
                RETURNING ban_id
            """, expiration, reason, admin_uid)

            await conn.execute(
                "INSERT INTO ban_player (user_id, ban_id) VALUES ($1, $2)",
                player_uid, ban_id,
            )
            for role_id in roles:
                await conn.execute(
                    "INSERT INTO ban_role (role_type, role_id, ban_id) VALUES ('Job', $1, $2)",
                    role_id, ban_id,
                )

    return {
        "ban_id": ban_id,
        "type": BAN_TYPE_ROLE,
        "player_uuid": str(player_uid),
        "role_ids": roles,
        "role_labels": [translate_role(r) for r in roles],
    }

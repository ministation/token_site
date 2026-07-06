from __future__ import annotations

import os
import re
from typing import Optional
from urllib.parse import quote
import asyncpg
from app.db.database import get_pg_pool

GHOSTS_STATIC_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "static", "ghosts")
)

SPONSOR_TIERS = {
    1: {"name": "Унати", "icon": "буст унати.png"},
    2: {"name": "Космо унати", "icon": "космический унати.png"},
    3: {"name": "Золотой унати", "icon": "золотой унати.png"},
    4: {"name": "Магический унати", "icon": "магический унати.png"},
    5: {"name": "Гига унати", "icon": "гига унати.png"},
}

TICKET_META: dict[str, dict] = {
    "traitor": {"name": "Трейтор", "icon": "fa-user-secret", "color": "#c0392b"},
    "nukie": {"name": "Ядерный оперативник", "icon": "fa-radiation", "color": "#e74c3c"},
    "nuclearoperative": {"name": "Ядерный оперативник", "icon": "fa-radiation", "color": "#e74c3c"},
    "zombie": {"name": "Зомби", "icon": "fa-biohazard", "color": "#27ae60"},
    "revolutionary": {"name": "Революционер", "icon": "fa-fist-raised", "color": "#e67e22"},
    "headrevolutionary": {"name": "Глава революции", "icon": "fa-fist-raised", "color": "#d35400"},
    "pirate": {"name": "Пират", "icon": "fa-skull-crossbones", "color": "#8e44ad"},
    "thief": {"name": "Вор", "icon": "fa-mask", "color": "#9b59b6"},
    "changeling": {"name": "Мимик", "icon": "fa-dna", "color": "#16a085"},
    "heretic": {"name": "Еретик", "icon": "fa-eye", "color": "#2c3e50"},
    "wizard": {"name": "Волшебник", "icon": "fa-hat-wizard", "color": "#3498db"},
    "dragon": {"name": "Дракон", "icon": "fa-dragon", "color": "#e74c3c"},
    "ninja": {"name": "Ниндзя", "icon": "fa-user-ninja", "color": "#34495e"},
    "paradox": {"name": "Парадокс", "icon": "fa-infinity", "color": "#1abc9c"},
    "survivor": {"name": "Выживший", "icon": "fa-person-running", "color": "#95a5a6"},
    "revenant": {"name": "Ревенант", "icon": "fa-ghost", "color": "#7f8c8d"},
    "blob": {"name": "Блоб", "icon": "fa-virus", "color": "#e91e63"},
    "cultist": {"name": "Культист", "icon": "fa-book-skull", "color": "#8b0000"},
    "bloodcultist": {"name": "Культист", "icon": "fa-book-skull", "color": "#8b0000"},
    "malfai": {"name": "Взломанный ИИ", "icon": "fa-robot", "color": "#c0392b"},
    "malfunctioningai": {"name": "Взломанный ИИ", "icon": "fa-robot", "color": "#c0392b"},
    "ratking": {"name": "Крысиный король", "icon": "fa-crown", "color": "#795548"},
    "parasite": {"name": "Паразит", "icon": "fa-bug", "color": "#4caf50"},
    "queen": {"name": "Королева", "icon": "fa-crown", "color": "#ff9800"},
    "spider": {"name": "Паук", "icon": "fa-spider", "color": "#607d8b"},
    "xeno": {"name": "Ксеноморф", "icon": "fa-alien", "color": "#2ecc71"},
    "xenomorph": {"name": "Ксеноморф", "icon": "fa-alien", "color": "#2ecc71"},
}

# Служебные записи в player_antag_token — не билеты на антагов
INTERNAL_TOKEN_IDS = frozenset({
    "balance",
    "last-donor-bonus-claim",
    "monthly-earned",
    "monthly-month",
    "monthly-year",
})

INTERNAL_TOKEN_PREFIXES = (
    "last-",
    "monthly-",
    "meta-",
    "stat-",
    "donor-",
    "bonus-",
    "claim-",
    "earned-",
)

GHOST_LABELS: dict[str, str] = {
    "MobGhostUnati": "Унати",
    "MobGhostSpaceUnati": "Космический унати",
    "MobGhostGoldUnati": "Золотой унати",
    "MobGhostMagicUnati": "Магический унати",
    "MobGhostGigaUnati": "Гига унати",
    "pink_ghost_human": "Розовый призрак",
    "pink": "Розовый призрак",
    "red_ghost_human": "Красный призрак",
    "red": "Красный призрак",
    "gold_ghost_human": "Золотой призрак",
    "gold": "Золотой призрак",
    "purple_ghost_human": "Фиолетовый призрак",
    "purple": "Фиолетовый призрак",
    "platinum_ghost_human": "Платиновый призрак",
    "platinum": "Платиновый призрак",
    "silver_ghost_human": "Серебряный призрак",
    "silver": "Серебряный призрак",
    "white_ghost_human": "Белый призрак",
    "white": "Белый призрак",
    "frog": "Лягушка",
    "kitty": "Котик",
    "parrot": "Попугай",
    "skeleton": "Скелет",
    "ian": "Иан",
    "fire": "Огненный призрак",
    "discocat": "Диско-кот",
    "blazeit": "Blaze It",
    "rainbow": "Радужный призрак",
    "rooster": "Петух",
}

GHOST_TABLE_CANDIDATES = [
    ("player_custom_ghost", "player_id", "ghost_id"),
    ("player_custom_ghost", "user_id", "ghost_id"),
    ("player_unlocked_ghost", "player_id", "ghost_prototype"),
    ("player_unlocked_ghost", "user_id", "ghost_prototype"),
    ("custom_ghost_player", "player_id", "ghost_id"),
    ("player_ghost_unlock", "player_id", "ghost_id"),
    ("player_ghost", "player_id", "ghost_id"),
]

_ghost_schema_cache: dict | None = None
_ghost_image_index: dict[str, str] | None = None


def sponsor_icon_url(filename: str) -> str:
    return f"/static/icons/{quote(filename)}"


def _build_ghost_image_index() -> dict[str, str]:
    index: dict[str, str] = {}
    if not os.path.isdir(GHOSTS_STATIC_DIR):
        return index
    for entry in os.listdir(GHOSTS_STATIC_DIR):
        dirpath = os.path.join(GHOSTS_STATIC_DIR, entry)
        if not os.path.isdir(dirpath) or not entry.endswith(".rsi"):
            continue
        folder = entry[:-4]
        img_file = None
        for fname in ("animated.png", "icon.png"):
            if os.path.isfile(os.path.join(dirpath, fname)):
                img_file = fname
                break
        if not img_file:
            continue
        url = f"/static/ghosts/{entry}/{img_file}"
        keys = {
            folder.lower(),
            folder.lower().replace("_", ""),
        }
        if "_ghost_human" in folder:
            keys.add(folder.replace("_ghost_human", "").lower())
        for key in keys:
            index[key] = url
    return index


def _ghost_lookup_keys(ghost_id: str) -> list[str]:
    raw = (ghost_id or "").strip()
    if not raw:
        return []
    snake = re.sub(r"([a-z])([A-Z])", r"\1_\2", raw).lower()
    keys = [raw.lower(), snake, snake.replace("_", "")]
    name = raw
    for prefix in ("MobGhost", "CustomGhost", "GhostHuman", "Ghost", "Mob"):
        if name.startswith(prefix):
            name = name[len(prefix):]
    if name != raw:
        stripped = re.sub(r"([a-z])([A-Z])", r"\1_\2", name).lower()
        keys.extend([stripped, stripped.replace("_", "")])
    if snake.startswith("human"):
        color = snake.replace("human", "").strip("_")
        if color:
            keys.append(color)
            keys.append(f"{color}_ghost_human")
    for part in re.split(r"[_\s]+", snake):
        if part and part not in ("ghost", "human", "mob", "custom"):
            keys.append(part)
    seen: set[str] = set()
    ordered: list[str] = []
    for key in keys:
        if key and key not in seen:
            seen.add(key)
            ordered.append(key)
    return ordered


def ghost_image_url(ghost_id: str) -> str | None:
    global _ghost_image_index
    if _ghost_image_index is None:
        _ghost_image_index = _build_ghost_image_index()
    for key in _ghost_lookup_keys(ghost_id):
        url = _ghost_image_index.get(key)
        if url:
            return url
    return None


def _ghost_entry(ghost_id: str, name: str | None = None, amount: int | None = None) -> dict:
    gid = str(ghost_id)
    entry = {
        "ghost_id": gid,
        "name": name or _format_ghost_name(gid),
        "icon": ghost_image_url(gid),
    }
    if amount is not None and amount > 1:
        entry["amount"] = amount
    return entry


def _normalize_token_key(token_id: str) -> str:
    raw = (token_id or "").strip()
    lower = raw.lower()
    if lower in TICKET_META:
        return lower
    for prefix in ("antag", "ticket", "token"):
        if lower.startswith(prefix):
            rest = lower[len(prefix):]
            if rest in TICKET_META:
                return rest
    compact = re.sub(r"[^a-z0-9]", "", lower)
    if compact in TICKET_META:
        return compact
    return lower


def _is_ghost_token(token_id: str) -> bool:
    tid = (token_id or "").lower()
    if tid == "balance":
        return False
    return (
        "ghost" in tid
        or tid.startswith("mobghost")
        or tid.startswith("customghost")
    )


def _is_internal_token(token_id: str) -> bool:
    tid = (token_id or "").strip().lower()
    if not tid or tid in INTERNAL_TOKEN_IDS:
        return True
    for prefix in INTERNAL_TOKEN_PREFIXES:
        if tid.startswith(prefix):
            return True
    # kebab-case ключи метаданных: last-donor-bonus-claim, monthly-year
    if re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)+", tid):
        return True
    return False


def _is_antag_ticket(token_id: str, amount: int) -> bool:
    """Только реальные билеты на роли, не служебные поля БД."""
    if _is_internal_token(token_id) or _is_ghost_token(token_id):
        return False
    raw = (token_id or "").strip()
    tid = raw.lower()
    # Известный антаг
    if _normalize_token_key(raw) in TICKET_META:
        return True
    # Prototype ID: Traitor, NuclearOperative, Job:Traitor
    if raw.startswith("Job:") or raw.startswith("Antag:"):
        return True
    if re.fullmatch(r"[A-Z][A-Za-z0-9]*", raw):
        return True
    # Короткий slug без дефисов: traitor, nukie
    if re.fullmatch(r"[a-z][a-z0-9]{2,}", tid):
        return True
    # Сумма как год/таймстамп — точно не билет
    if amount > 9999:
        return False
    return False


def _format_token_name(token_id: str) -> str:
    raw = (token_id or "").strip()
    for prefix in ("Antag", "Ticket", "Token", "Mob"):
        if raw.startswith(prefix):
            raw = raw[len(prefix):]
    spaced = re.sub(r"([a-z])([A-Z])", r"\1 \2", raw)
    return spaced.replace("_", " ").strip() or token_id


def _ticket_info(token_id: str) -> dict:
    key = _normalize_token_key(token_id)
    meta = TICKET_META.get(key)
    if meta:
        return {
            "token_id": token_id,
            "key": key,
            "name": meta["name"],
            "icon": meta["icon"],
            "color": meta["color"],
        }
    return {
        "token_id": token_id,
        "key": key,
        "name": _format_token_name(token_id),
        "icon": "fa-ticket",
        "color": "#5b8def",
    }


def _format_ghost_name(ghost_id: str) -> str:
    raw = (ghost_id or "").strip()
    if raw in GHOST_LABELS:
        return GHOST_LABELS[raw]
    lower = raw.lower()
    for key, label in GHOST_LABELS.items():
        if key.lower() == lower:
            return label
    name = raw
    for prefix in ("MobGhost", "CustomGhost", "Ghost", "Mob"):
        if name.startswith(prefix):
            name = name[len(prefix):]
    spaced = re.sub(r"([a-z])([A-Z])", r"\1 \2", name)
    return spaced.replace("_", " ").strip() or raw


async def _table_exists(conn, table: str) -> bool:
    row = await conn.fetchrow(
        """
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'public' AND table_name = $1
        """,
        table,
    )
    return row is not None


async def _table_columns(conn, table: str) -> set[str]:
    rows = await conn.fetch(
        """
        SELECT column_name FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = $1
        """,
        table,
    )
    return {r["column_name"].lower() for r in rows}


async def resolve_player_uuids(
    user_uuid: str | None = None,
    discord_id: str | None = None,
    ckey: str | None = None,
) -> list[str]:
    """Все user_id (UUID) игрока для запросов к player_antag_token."""
    ids: set[str] = set()
    if user_uuid and not str(user_uuid).startswith("discord_"):
        ids.add(str(user_uuid))
    try:
        pg = await get_pg_pool()
        async with pg.acquire() as conn:
            if discord_id:
                rows = await conn.fetch(
                    """
                    SELECT DISTINCT p.user_id::text AS uid
                    FROM player p
                    JOIN discord_auth da ON p.user_id = da.user_id
                    WHERE da.discord_id = $1::bigint
                    """,
                    int(discord_id),
                )
                for r in rows:
                    ids.add(r["uid"])
            if user_uuid and not str(user_uuid).startswith("discord_"):
                rows = await conn.fetch(
                    """
                    SELECT DISTINCT user_id::text AS uid
                    FROM player
                    WHERE user_id::text = $1
                       OR player_id::text = $1
                       OR ($2::text IS NOT NULL AND $2 != '' AND LOWER(last_seen_user_name) = LOWER($2))
                    """,
                    str(user_uuid),
                    ckey,
                )
                for r in rows:
                    ids.add(r["uid"])
            elif ckey:
                rows = await conn.fetch(
                    """
                    SELECT DISTINCT user_id::text AS uid
                    FROM player
                    WHERE LOWER(last_seen_user_name) = LOWER($1)
                    """,
                    ckey,
                )
                for r in rows:
                    ids.add(r["uid"])
    except (asyncpg.PostgresError, ValueError, OSError):
        pass
    return list(ids)


async def get_sponsor_level(discord_id: str) -> Optional[dict]:
    try:
        pg = await get_pg_pool()
        async with pg.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT sponsor_level FROM discord_sponsor WHERE discord_id = $1::bigint",
                int(discord_id),
            )
            if not row:
                return None
            level = int(row["sponsor_level"])
            tier = SPONSOR_TIERS.get(level, SPONSOR_TIERS[1])
            return {
                "level": level,
                "name": tier["name"],
                "icon": sponsor_icon_url(tier["icon"]),
            }
    except (asyncpg.PostgresError, ValueError, OSError):
        return None


async def get_player_tickets(user_uuids: list[str]) -> list[dict]:
    if not user_uuids:
        return []
    try:
        pg = await get_pg_pool()
        async with pg.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT token_id, COALESCE(amount, 0) as amount
                FROM player_antag_token
                WHERE player_id::text = ANY($1::text[])
                  AND token_id != 'balance'
                  AND COALESCE(amount, 0) > 0
                ORDER BY token_id
                """,
                user_uuids,
            )
            merged: dict[str, dict] = {}
            for r in rows:
                token_id = r["token_id"]
                amount = int(r["amount"])
                if not _is_antag_ticket(token_id, amount):
                    continue
                info = _ticket_info(token_id)
                key = info["key"]
                if key in merged:
                    merged[key]["amount"] += amount
                else:
                    merged[key] = {**info, "amount": amount}
            return sorted(merged.values(), key=lambda x: (-x["amount"], x["name"]))
    except (asyncpg.PostgresError, OSError):
        return []


async def _discover_ghost_schema(conn) -> dict | None:
    global _ghost_schema_cache
    if _ghost_schema_cache is not None:
        return _ghost_schema_cache or None

    for table, player_col, ghost_col in GHOST_TABLE_CANDIDATES:
        if not await _table_exists(conn, table):
            continue
        cols = await _table_columns(conn, table)
        if player_col.lower() in cols and ghost_col.lower() in cols:
            _ghost_schema_cache = {
                "table": table,
                "player_col": player_col,
                "ghost_col": ghost_col,
            }
            return _ghost_schema_cache

    rows = await conn.fetch(
        """
        SELECT table_name FROM information_schema.tables
        WHERE table_schema = 'public' AND table_name ILIKE '%ghost%'
        ORDER BY table_name
        """
    )
    for row in rows:
        table = row["table_name"]
        if table in ("ban",):
            continue
        cols = await _table_columns(conn, table)
        player_col = next((c for c in ("player_id", "user_id", "profile_id") if c in cols), None)
        ghost_col = next(
            (c for c in (
                "ghost_id", "ghost_prototype", "prototype", "ghost_type",
                "ghost_name", "custom_ghost_id", "ghost",
            ) if c in cols),
            None,
        )
        if player_col and ghost_col:
            _ghost_schema_cache = {
                "table": table,
                "player_col": player_col,
                "ghost_col": ghost_col,
            }
            return _ghost_schema_cache

    _ghost_schema_cache = {}
    return None


async def _ghosts_from_catalog(conn, schema: dict, user_uuids: list[str]) -> list[dict]:
    table = schema["table"]
    player_col = schema["player_col"]
    ghost_col = schema["ghost_col"]
    ghosts: list[dict] = []

    if await _table_exists(conn, "custom_ghost"):
        cat_cols = await _table_columns(conn, "custom_ghost")
        id_col = next((c for c in ("ghost_id", "id", "prototype", "prototype_id") if c in cat_cols), None)
        name_col = next((c for c in ("name", "display_name", "title", "ghost_name") if c in cat_cols), None)
        if id_col and name_col:
            try:
                rows = await conn.fetch(
                    f"""
                    SELECT DISTINCT pg.{ghost_col} AS ghost_id,
                           COALESCE(cg.{name_col}, pg.{ghost_col}::text) AS name
                    FROM {table} pg
                    LEFT JOIN custom_ghost cg
                        ON cg.{id_col}::text = pg.{ghost_col}::text
                    WHERE pg.{player_col}::text = ANY($1::text[])
                    ORDER BY name
                    """,
                    user_uuids,
                )
                for r in rows:
                    gid = str(r["ghost_id"])
                    ghosts.append(_ghost_entry(gid, r["name"] or _format_ghost_name(gid)))
                return ghosts
            except asyncpg.PostgresError:
                pass

    rows = await conn.fetch(
        f"""
        SELECT DISTINCT {ghost_col} AS ghost_id
        FROM {table}
        WHERE {player_col}::text = ANY($1::text[])
        ORDER BY ghost_id
        """,
        user_uuids,
    )
    for r in rows:
        gid = str(r["ghost_id"])
        ghosts.append(_ghost_entry(gid))
    return ghosts


async def _ghosts_from_tokens(conn, user_uuids: list[str]) -> list[dict]:
    rows = await conn.fetch(
        """
        SELECT token_id, COALESCE(amount, 0) as amount
        FROM player_antag_token
        WHERE player_id::text = ANY($1::text[])
          AND token_id != 'balance'
          AND COALESCE(amount, 0) > 0
          AND (
              token_id ILIKE '%ghost%'
              OR token_id ILIKE 'MobGhost%'
              OR token_id ILIKE 'CustomGhost%'
          )
        ORDER BY token_id
        """,
        user_uuids,
    )
    ghosts: list[dict] = []
    seen: set[str] = set()
    for r in rows:
        gid = str(r["token_id"])
        norm = gid.lower()
        if norm in seen:
            continue
        seen.add(norm)
        ghosts.append(_ghost_entry(gid, amount=int(r["amount"])))
    return ghosts


async def get_player_custom_ghosts(user_uuids: list[str]) -> list[dict]:
    if not user_uuids:
        return []
    try:
        pg = await get_pg_pool()
        async with pg.acquire() as conn:
            schema = await _discover_ghost_schema(conn)
            if schema:
                ghosts = await _ghosts_from_catalog(conn, schema, user_uuids)
                if ghosts:
                    return ghosts
            return await _ghosts_from_tokens(conn, user_uuids)
    except (asyncpg.PostgresError, OSError):
        return []


async def get_inventory(
    discord_id: str,
    user_uuid: Optional[str] = None,
    ckey: Optional[str] = None,
) -> dict:
    user_uuids = await resolve_player_uuids(user_uuid, discord_id, ckey)
    has_game_link = bool(user_uuids)
    sponsor = await get_sponsor_level(discord_id)
    tickets = await get_player_tickets(user_uuids) if has_game_link else []
    custom_ghosts = await get_player_custom_ghosts(user_uuids) if has_game_link else []
    return {
        "sponsor": sponsor,
        "tickets": tickets,
        "custom_ghosts": custom_ghosts,
        "has_game_link": has_game_link,
        "tiers": [
            {
                "level": lvl,
                "name": info["name"],
                "icon": sponsor_icon_url(info["icon"]),
                "active": sponsor and sponsor["level"] == lvl,
            }
            for lvl, info in sorted(SPONSOR_TIERS.items())
        ],
    }

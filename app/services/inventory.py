from typing import Optional
from urllib.parse import quote
from app.db.database import get_pg_pool

SPONSOR_TIERS = {
    1: {"name": "Унати", "icon": "буст унати.png"},
    2: {"name": "Космо унати", "icon": "космический унати.png"},
    3: {"name": "Золотой унати", "icon": "золотой унати.png"},
    4: {"name": "Магический унати", "icon": "магический унати.png"},
    5: {"name": "Гига унати", "icon": "гига унати.png"},
}

TOKEN_LABELS = {
    "traitor": "Трейтор",
    "nukie": "Ядерный оперативник",
    "zombie": "Зомби",
    "revolutionary": "Революционер",
    "pirate": "Пират",
    "thief": "Вор",
    "changeling": "Мимик",
    "heretic": "Еретик",
    "wizard": "Волшебник",
    "dragon": "Дракон",
    "ninja": "Ниндзя",
    "paradox": "Парадокс",
    "survivor": "Выживший",
}


def sponsor_icon_url(filename: str) -> str:
    return f"/static/icons/{quote(filename)}"


async def get_sponsor_level(discord_id: str) -> Optional[dict]:
    pg = await get_pg_pool()
    async with pg.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT sponsor_level FROM discord_sponsor WHERE discord_id = $1::bigint",
            int(discord_id)
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


async def get_player_tickets(user_uuid: str) -> list[dict]:
    pg = await get_pg_pool()
    async with pg.acquire() as conn:
        rows = await conn.fetch("""
            SELECT token_id, COALESCE(amount, 0) as amount
            FROM player_antag_token
            WHERE player_id::text = $1 AND token_id != 'balance' AND amount > 0
            ORDER BY token_id
        """, user_uuid)
        tickets = []
        for r in rows:
            token_id = r["token_id"]
            tickets.append({
                "token_id": token_id,
                "name": TOKEN_LABELS.get(token_id, token_id.replace("_", " ").title()),
                "amount": int(r["amount"]),
            })
        return tickets


async def get_inventory(discord_id: str, user_uuid: Optional[str]) -> dict:
    sponsor = await get_sponsor_level(discord_id)
    tickets = []
    if user_uuid and not user_uuid.startswith("discord_"):
        tickets = await get_player_tickets(user_uuid)
    return {
        "sponsor": sponsor,
        "tickets": tickets,
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

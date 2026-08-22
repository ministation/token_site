import aiohttp

import database_social as social_db
from app.config import WIKI_PUBLIC_URL
from app.services.bank import get_total_stats
from app.services.referral import get_global_referral_metrics


async def fetch_wiki_mediawiki_stats() -> dict:
    url = f"{WIKI_PUBLIC_URL}/api.php"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                url,
                params={
                    "action": "query",
                    "meta": "siteinfo",
                    "siprop": "statistics",
                    "format": "json",
                },
                timeout=aiohttp.ClientTimeout(total=4),
            ) as resp:
                if resp.status != 200:
                    return {}
                data = await resp.json()
                return (data.get("query") or {}).get("statistics") or {}
    except Exception:
        return {}


async def get_site_statistics() -> dict:
    social = social_db.get_site_stats()
    visits = social_db.get_visit_stats()
    try:
        wiki = social_db.get_wiki_stats()
    except Exception:
        wiki = {}
    wiki_mw = await fetch_wiki_mediawiki_stats()
    if wiki_mw:
        wiki = {**wiki, "mw": wiki_mw}
    cdn = social_db.get_cdn_stats()
    referral = get_global_referral_metrics()
    try:
        game_stats = await get_total_stats()
    except Exception:
        game_stats = {}
    return {
        "social": social,
        "visits": visits,
        "wiki": wiki,
        "cdn": cdn,
        "referral": referral,
        "game": game_stats,
    }


def list_admins() -> list[dict]:
    return social_db.list_site_admins()


def grant_moderator(discord_id: str, username: str, granted_by: str) -> bool:
    return social_db.add_site_moderator(discord_id, username, granted_by)


def grant_content_maker(discord_id: str, username: str, granted_by: str) -> bool:
    return social_db.add_content_maker(discord_id, username, granted_by or "admin")


def revoke_content_maker(discord_id: str) -> bool:
    return social_db.remove_content_maker(discord_id)


def grant_time_keeper(discord_id: str, username: str, granted_by: str) -> bool:
    return social_db.add_time_keeper(discord_id, username, granted_by or "admin")


def revoke_time_keeper(discord_id: str) -> bool:
    return social_db.remove_time_keeper(discord_id)


def grant_admin(discord_id: str, username: str, granted_by: str) -> bool:
    return social_db.add_site_admin(discord_id, username, granted_by)


def revoke_admin(discord_id: str) -> bool:
    return social_db.remove_site_admin(discord_id)


def find_user_for_admin(username: str) -> dict | None:
    return social_db.get_social_user_by_discord_username(username)

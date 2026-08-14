"""Assign Discord sponsor (donator) roles after paid subscription."""

from __future__ import annotations

import logging

import aiohttp

from app.config import DISCORD_BOT_TOKEN, DISCORD_GUILD_ID, SPONSOR_ROLE_IDS

logger = logging.getLogger(__name__)

DISCORD_API = "https://discord.com/api/v10"


async def assign_sponsor_role(discord_id: str | int, level: int) -> bool:
    """
    Выдаёт Discord-роль спонсора за уровень подписки.
    Снимает другие спонсорские роли из SPONSOR_ROLE_IDS, кроме целевой
    (или более высокой, если уже есть).

    Returns True if role applied / already present.
    Returns False if member is not on the guild (soft skip).
    Raises on misconfiguration or Discord API errors.
    """
    did = str(discord_id or "").strip()
    if not did.isdigit():
        raise ValueError("Некорректный Discord ID для выдачи роли спонсора")

    level = int(level)
    if level < 1 or level > 5:
        raise ValueError(f"Некорректный уровень спонсорства: {level}")

    token = (DISCORD_BOT_TOKEN or "").strip()
    guild_id = (DISCORD_GUILD_ID or "").strip()
    if not token or not guild_id:
        raise RuntimeError("DISCORD_BOT_TOKEN / DISCORD_GUILD_ID не заданы — нельзя выдать роль")

    target_role = SPONSOR_ROLE_IDS.get(level)
    if not target_role:
        raise RuntimeError(f"SPONSOR_ROLE_IDS: нет роли для уровня {level}")

    headers = {"Authorization": f"Bot {token}"}
    member_url = f"{DISCORD_API}/guilds/{guild_id}/members/{did}"
    timeout = aiohttp.ClientTimeout(total=20)

    async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
        async with session.get(member_url) as resp:
            if resp.status == 404:
                logger.info(
                    "Sponsor role skip: user %s not in guild %s",
                    did,
                    guild_id,
                )
                return False
            if resp.status >= 400:
                body = await resp.text()
                raise RuntimeError(
                    f"Не удалось получить участника Discord ({resp.status}): {body[:200]}"
                )
            member = await resp.json()

        current_roles = {str(r) for r in (member.get("roles") or [])}
        have_levels = [
            lvl for lvl, rid in SPONSOR_ROLE_IDS.items() if str(rid) in current_roles
        ]
        keep_level = max([level] + have_levels) if have_levels else level
        keep_role = str(SPONSOR_ROLE_IDS.get(keep_level) or target_role)

        for lvl, rid in SPONSOR_ROLE_IDS.items():
            rid_s = str(rid)
            if rid_s == keep_role or rid_s not in current_roles:
                continue
            url = f"{DISCORD_API}/guilds/{guild_id}/members/{did}/roles/{rid_s}"
            async with session.delete(url) as resp:
                if resp.status not in (200, 204, 404):
                    body = await resp.text()
                    raise RuntimeError(
                        f"Не удалось снять роль спонсора {rid_s} ({resp.status}): {body[:200]}"
                    )

        if keep_role not in current_roles:
            url = f"{DISCORD_API}/guilds/{guild_id}/members/{did}/roles/{keep_role}"
            async with session.put(url) as resp:
                if resp.status not in (200, 204):
                    body = await resp.text()
                    raise RuntimeError(
                        f"Не удалось выдать роль спонсора ({resp.status}): {body[:200]}"
                    )
            logger.info(
                "Assigned sponsor role %s (level %s) to %s",
                keep_role,
                keep_level,
                did,
            )
        else:
            logger.info(
                "Sponsor role %s already present for %s (level %s)",
                keep_role,
                did,
                keep_level,
            )

        return True

"""Assign Discord «Авторизован» roles on Mini / Oasis after site login."""

from __future__ import annotations

import logging
import re

import aiohttp

from app.config import (
    DISCORD_AUTH_ROLE_ID,
    DISCORD_AUTH_ROLE_ID_2,
    DISCORD_AUTH_ROLES,
    DISCORD_BOT_TOKEN,
    DISCORD_GUILD2_BOT_TOKEN,
    DISCORD_GUILD2_ID,
    DISCORD_GUILD_ID,
)

logger = logging.getLogger(__name__)

DISCORD_API = "https://discord.com/api/v10"


def _token_for_guild(guild_id: str) -> str:
    guild_id = guild_id.strip()
    if DISCORD_GUILD2_ID and guild_id == DISCORD_GUILD2_ID.strip() and DISCORD_GUILD2_BOT_TOKEN:
        return DISCORD_GUILD2_BOT_TOKEN.strip()
    return (DISCORD_BOT_TOKEN or "").strip()


def _parse_targets() -> list[tuple[str, str, str]]:
    """Return (guild_id, role_id, bot_token) targets."""
    seen: set[tuple[str, str]] = set()
    out: list[tuple[str, str, str]] = []

    def add(guild_id: str, role_id: str) -> None:
        guild_id = (guild_id or "").strip()
        role_id = (role_id or "").strip()
        if not guild_id.isdigit() or not role_id.isdigit():
            return
        key = (guild_id, role_id)
        if key in seen:
            return
        token = _token_for_guild(guild_id)
        if not token:
            return
        seen.add(key)
        out.append((guild_id, role_id, token))

    for chunk in re.split(r"[\s,;]+", (DISCORD_AUTH_ROLES or "").strip()):
        if not chunk or ":" not in chunk:
            continue
        guild_id, role_id = chunk.split(":", 1)
        add(guild_id, role_id)

    add(DISCORD_GUILD_ID or "", DISCORD_AUTH_ROLE_ID or "")
    add(DISCORD_GUILD2_ID or "", DISCORD_AUTH_ROLE_ID_2 or "")
    return out


async def assign_authorized_roles(discord_id: str) -> None:
    """Best-effort: grant configured auth roles on every target guild."""
    if not discord_id or not str(discord_id).isdigit():
        return
    targets = _parse_targets()
    if not targets:
        return

    timeout = aiohttp.ClientTimeout(total=15)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        for guild_id, role_id, token in targets:
            url = f"{DISCORD_API}/guilds/{guild_id}/members/{discord_id}/roles/{role_id}"
            try:
                async with session.put(
                    url,
                    headers={"Authorization": f"Bot {token}"},
                ) as resp:
                    if resp.status in (200, 204):
                        logger.info(
                            "Assigned auth role %s to %s on guild %s",
                            role_id,
                            discord_id,
                            guild_id,
                        )
                    elif resp.status == 404:
                        logger.info(
                            "Skip auth role on guild %s for %s: not a member",
                            guild_id,
                            discord_id,
                        )
                    else:
                        body = await resp.text()
                        logger.warning(
                            "Auth role assign failed guild=%s user=%s HTTP %s %s",
                            guild_id,
                            discord_id,
                            resp.status,
                            body[:200],
                        )
            except Exception:
                logger.exception(
                    "Auth role assign error guild=%s user=%s",
                    guild_id,
                    discord_id,
                )

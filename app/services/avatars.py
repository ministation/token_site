import os
import aiohttp
from app.config import AVATAR_DIR

DEFAULT_AVATAR = "/static/default_avatar.png"


def resolve_avatar_url(user: dict | None) -> str:
    if not user:
        return DEFAULT_AVATAR
    path = user.get("avatar_path")
    if path and (path.startswith("/static/") or path.startswith("http")):
        return path
    return DEFAULT_AVATAR


async def download_discord_avatar(discord_id: str, avatar_hash: str | None) -> str | None:
    if not avatar_hash or not discord_id:
        return None
    os.makedirs(AVATAR_DIR, exist_ok=True)
    ext = "gif" if avatar_hash.startswith("a_") else "png"
    filename = f"{discord_id}.{ext}"
    filepath = os.path.join(AVATAR_DIR, filename)
    url = f"https://cdn.discordapp.com/avatars/{discord_id}/{avatar_hash}.{ext}?size=128"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status != 200:
                    return None
                data = await resp.read()
        with open(filepath, "wb") as f:
            f.write(data)
        return f"/static/avatars/{filename}"
    except Exception:
        return None


async def sync_discord_avatar_for_user(discord_id: str, avatar_hash: str | None) -> str | None:
    import database_social as social_db
    user = social_db.get_social_user_by_discord_id(discord_id)
    if not user:
        return None
    if user.get("avatar_custom"):
        return user.get("avatar_path") or DEFAULT_AVATAR
    if not avatar_hash:
        return user.get("avatar_path") or DEFAULT_AVATAR
    if user.get("discord_avatar") == avatar_hash and user.get("avatar_path"):
        return user["avatar_path"]
    local_path = await download_discord_avatar(discord_id, avatar_hash)
    if local_path:
        social_db.update_user_avatar(discord_id, local_path, avatar_hash, custom=False)
        return local_path
    return user.get("avatar_path") or DEFAULT_AVATAR


def save_custom_avatar(player_id: str, discord_id: str, file_bytes: bytes, ext: str) -> str:
    import database_social as social_db
    os.makedirs(AVATAR_DIR, exist_ok=True)
    ext = ext.lower() if ext.lower() in (".png", ".jpg", ".jpeg", ".webp", ".gif") else ".png"
    filename = f"custom_{player_id}_{discord_id}{ext}"
    filepath = os.path.join(AVATAR_DIR, filename)
    with open(filepath, "wb") as f:
        f.write(file_bytes)
    local_path = f"/static/avatars/{filename}"
    social_db.update_user_avatar(discord_id, local_path, custom=True)
    return local_path

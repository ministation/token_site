import secrets
import string
from typing import Optional

from app.config import REFERRAL_REFEREE_COINS, REFERRAL_REFERRER_COINS
from app.services.bank import add_tokens
import database_social as social_db

_CODE_ALPHABET = string.ascii_uppercase + string.digits
_CODE_LEN = 8


def _generate_code() -> str:
    return "".join(secrets.choice(_CODE_ALPHABET) for _ in range(_CODE_LEN))


def ensure_referral_code(discord_id: str) -> str:
    user = social_db.get_social_user_by_discord_id(discord_id)
    if not user:
        raise ValueError("Пользователь не найден")
    if user.get("referral_code"):
        return user["referral_code"]
    for _ in range(20):
        code = _generate_code()
        if social_db.set_referral_code(discord_id, code):
            return code
    raise RuntimeError("Не удалось сгенерировать реферальный код")


async def _grant_coins(discord_id: str, amount: int, reason: str) -> bool:
    user = social_db.get_social_user_by_discord_id(discord_id)
    if not user:
        return False
    user_uuid = user.get("user_uuid") or user.get("player_id")
    if not user_uuid or str(user_uuid).startswith("discord_"):
        social_db.add_pending_referral_coins(discord_id, amount, reason)
        return False
    await add_tokens(str(user_uuid), amount)
    return True


async def apply_referral_code(referred_discord_id: str, code: str) -> tuple[bool, str]:
    code = (code or "").strip().upper()
    if not code:
        return False, "Введите реферальный код"

    referred = social_db.get_social_user_by_discord_id(referred_discord_id)
    if not referred:
        return False, "Сначала войдите через Discord"
    if referred.get("referred_by_code"):
        return False, "Реферальный код уже использован"
    if referred.get("referral_code") == code:
        return False, "Нельзя использовать свой код"

    referrer = social_db.get_social_user_by_referral_code(code)
    if not referrer:
        return False, "Код не найден"
    if referrer["discord_id"] == referred_discord_id:
        return False, "Нельзя использовать свой код"

    if not social_db.mark_referral_used(referred_discord_id, code, referrer["discord_id"]):
        return False, "Не удалось применить код"

    await _grant_coins(referrer["discord_id"], REFERRAL_REFERRER_COINS, "referrer")
    await _grant_coins(referred_discord_id, REFERRAL_REFEREE_COINS, "referee")
    return True, "Бонус начислен! Пригласивший получил 5 монет, вы — 3."


async def grant_pending_referral_coins(discord_id: str, user_uuid: str) -> int:
    pending = social_db.pop_pending_referral_coins(discord_id)
    granted = 0
    for item in pending:
        await add_tokens(user_uuid, int(item["amount"]))
        granted += int(item["amount"])
    return granted


def get_referral_info(discord_id: str) -> dict:
    user = social_db.get_social_user_by_discord_id(discord_id)
    if not user:
        return {}
    code = user.get("referral_code") or ensure_referral_code(discord_id)
    stats = social_db.get_referral_stats(discord_id)
    return {
        "code": code,
        "referrals_count": stats.get("count", 0),
        "referred_by": user.get("referred_by_code"),
        "needs_prompt": social_db.needs_referral_prompt(discord_id),
        "referrer_reward": REFERRAL_REFERRER_COINS,
        "referee_reward": REFERRAL_REFEREE_COINS,
    }

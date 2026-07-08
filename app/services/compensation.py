import datetime
from typing import Optional, Tuple

import database_social as social_db
from app.services.bank import add_tokens


def _parse_ends_at(value: str) -> datetime.datetime:
    text = (value or "").replace("Z", "+00:00")
    try:
        dt = datetime.datetime.fromisoformat(text)
    except ValueError:
        dt = datetime.datetime.strptime(text[:19], "%Y-%m-%d %H:%M:%S")
    if dt.tzinfo is not None:
        dt = dt.astimezone(datetime.timezone.utc).replace(tzinfo=None)
    return dt


def _serialize_giveaway(row: dict, claimed: Optional[bool] = None) -> dict:
    ends_at = _parse_ends_at(row["ends_at"])
    now = datetime.datetime.utcnow()
    remaining = max(0, int((ends_at - now).total_seconds()))
    payload = {
        "id": row["id"],
        "amount": row["amount"],
        "ends_at": ends_at.isoformat(),
        "ends_ts": int(ends_at.timestamp()),
        "remaining_seconds": remaining,
        "active": remaining > 0,
        "claims_count": social_db.count_compensation_claims(row["id"]),
        "created_by": row.get("created_by"),
        "created_at": row.get("created_at"),
    }
    if claimed is not None:
        payload["claimed"] = claimed
    return payload


def get_public_compensation(user_uuid: Optional[str] = None) -> dict:
    row = social_db.get_active_compensation_giveaway()
    if not row:
        return {"active": False}
    claimed = social_db.has_compensation_claim(row["id"], user_uuid) if user_uuid else False
    data = _serialize_giveaway(row, claimed=claimed)
    data["active"] = data["remaining_seconds"] > 0
    return data


def get_admin_compensation_status() -> dict:
    row = social_db.get_active_compensation_giveaway()
    if not row:
        return {"active": False}
    return _serialize_giveaway(row)


def start_compensation_giveaway(amount: int, duration_minutes: int, created_by: str) -> dict:
    if amount < 1:
        raise ValueError("Сумма компенсации должна быть не меньше 1")
    if amount > 500:
        raise ValueError("Сумма компенсации не может быть больше 500")
    if duration_minutes < 1:
        raise ValueError("Укажите длительность раздачи")
    if duration_minutes > 10080:
        raise ValueError("Максимальная длительность раздачи — 7 суток")
    row = social_db.create_compensation_giveaway(amount, duration_minutes, created_by)
    return _serialize_giveaway(row, claimed=False)


async def claim_compensation(user_uuid: str) -> Tuple[Optional[dict], Optional[str]]:
    row = social_db.get_active_compensation_giveaway()
    if not row:
        return None, "Раздача компенсации сейчас не активна"
    ends_at = _parse_ends_at(row["ends_at"])
    if ends_at <= datetime.datetime.utcnow():
        return None, "Время раздачи компенсации истекло"
    if social_db.has_compensation_claim(row["id"], user_uuid):
        return None, "Вы уже получили эту компенсацию"
    if not social_db.try_record_compensation_claim(row["id"], user_uuid):
        return None, "Вы уже получили эту компенсацию"
    try:
        new_balance = await add_tokens(user_uuid, row["amount"])
    except Exception:
        social_db.revoke_compensation_claim(row["id"], user_uuid)
        return None, "Не удалось начислить компенсацию"
    return {
        "amount": row["amount"],
        "new_balance": new_balance,
        "giveaway_id": row["id"],
    }, None

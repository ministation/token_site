from fastapi import APIRouter, Request, HTTPException, Query
from app.dependencies import get_current_social_user
from app.models.chat import ChatMessage
from app.services.chat import get_chat_messages, add_chat_message
from app.services.avatars import resolve_avatar_url

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.get("")
async def get_chat(after: int = Query(0, ge=0)):
    return get_chat_messages(100, after)


@router.post("")
async def post_chat(request: Request, msg: ChatMessage):
    user = await get_current_social_user(request)
    if len(msg.message) > 500:
        raise HTTPException(status_code=400, detail="Сообщение слишком длинное")
    if not msg.message.strip():
        raise HTTPException(status_code=400, detail="Пустое сообщение")

    social = user["social"]
    avatar = resolve_avatar_url(social)
    nickname = social.get("game_nickname") or social.get("discord_username") or user.get("username", "Игрок")
    msg_data = add_chat_message(user["social_id"], nickname, avatar, msg.message)
    return {"success": True, "message": msg_data}

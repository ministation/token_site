from fastapi import APIRouter, Request, HTTPException, Query, Form, File, UploadFile
from app.dependencies import get_current_social_user
from app.services.chat import get_chat_messages, add_chat_message
from app.services.avatars import resolve_avatar_url
from app.services.roles import get_staff_role
from app.services.chat_enrich import enrich_player_for_chat
from app.services.media_upload import save_upload

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.get("")
async def get_chat(after: int = Query(0, ge=0)):
    messages = get_chat_messages(100, after)
    for m in messages:
        info = enrich_player_for_chat(m["author_id"])
        m["author_avatar"] = info["avatar"]
        m["author_role"] = info["author_role"]
        m["author_badges"] = info["badges"]
        m["author_presence"] = info.get("presence") or "offline"
    return messages


@router.post("")
async def post_chat(
    request: Request,
    message: str = Form(""),
    image: UploadFile | None = File(None),
):
    user = await get_current_social_user(request)
    text = (message or "").strip()
    if len(text) > 500:
        raise HTTPException(status_code=400, detail="Сообщение слишком длинное")
    if not text and not (image and image.filename):
        raise HTTPException(status_code=400, detail="Пустое сообщение")

    image_url = None
    if image and image.filename:
        image_url = save_upload(image, user["social_id"], kind="image", prefix="chat")

    social = user["social"]
    avatar = resolve_avatar_url(social)
    nickname = social.get("game_nickname") or social.get("discord_username") or user.get("username", "Игрок")
    msg_data = add_chat_message(user["social_id"], nickname, avatar, text, image_url)
    info = enrich_player_for_chat(user["social_id"])
    msg_data["author_avatar"] = info["avatar"]
    msg_data["author_role"] = info["author_role"]
    msg_data["author_badges"] = info["badges"]
    msg_data["author_presence"] = info.get("presence") or "offline"
    return {"success": True, "message": msg_data}

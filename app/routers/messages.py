from fastapi import APIRouter, Request, HTTPException, Query, Form, File, UploadFile
from app.dependencies import get_current_social_user
from app.services.messages import send_pm, get_pm_conversation, get_pm_dialogs, mark_pm_read, get_pm_unread_total
from app.services.chat_enrich import enrich_player_for_chat
from app.services.media_upload import save_upload

router = APIRouter(prefix="/api/messages", tags=["messages"])


@router.get("/dialogs")
async def dialogs(request: Request):
    user = await get_current_social_user(request)
    items = get_pm_dialogs(user['social_id'])
    for d in items:
        info = enrich_player_for_chat(d["other_id"])
        d["avatar"] = info["avatar"]
        d["badges"] = info["badges"]
        d["author_role"] = info["author_role"]
    return items


@router.get("/unread-count")
async def unread_count(request: Request):
    user = await get_current_social_user(request)
    return {"unread": get_pm_unread_total(user['social_id'])}


@router.get("/users")
async def message_users(request: Request, q: str = Query("", min_length=0), limit: int = 100, offset: int = 0):
    user = await get_current_social_user(request)
    from app.services.users import list_platform_users
    return list_platform_users(user['social_id'], q, limit, offset)


@router.get("/conversation/{other_id}")
async def conversation(other_id: str, request: Request):
    user = await get_current_social_user(request)
    if other_id == user['social_id']:
        raise HTTPException(status_code=400, detail="Нельзя открыть диалог с самим собой")
    mark_pm_read(user['social_id'], other_id)
    messages = get_pm_conversation(user['social_id'], other_id)
    my_id = user['social_id']
    partner = enrich_player_for_chat(other_id)
    enriched = []
    for m in messages:
        row = {**m, "is_own": m.get("sender_id") == my_id}
        sender = enrich_player_for_chat(m.get("sender_id", ""))
        row["sender_avatar"] = sender["avatar"]
        row["sender_badges"] = sender["badges"]
        row["sender_role"] = sender["author_role"]
        row["sender_presence"] = sender.get("presence") or "offline"
        enriched.append(row)
    return {"partner": partner, "messages": enriched}


@router.post("/read/{other_id}")
async def mark_read(other_id: str, request: Request):
    user = await get_current_social_user(request)
    count = mark_pm_read(user['social_id'], other_id)
    return {"success": True, "marked": count}


@router.post("/send")
async def send_message(
    request: Request,
    receiver_id: str = Form(...),
    content: str = Form(""),
    image: UploadFile | None = File(None),
):
    user = await get_current_social_user(request)
    if receiver_id == user['social_id']:
        raise HTTPException(status_code=400, detail="Нельзя отправить сообщение самому себе")
    image_url = None
    if image and image.filename:
        image_url = save_upload(image, user['social_id'], kind="image", prefix="pm")
    try:
        msg_id = send_pm(user['social_id'], receiver_id, content, image_url)
        return {"success": True, "message_id": msg_id}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

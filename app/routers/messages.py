from fastapi import APIRouter, Request, HTTPException, Query
from app.dependencies import get_current_social_user
from app.services.messages import send_pm, get_pm_conversation, get_pm_dialogs, search_pm_users, mark_pm_read
from pydantic import BaseModel

router = APIRouter(prefix="/api/messages", tags=["messages"])


class SendMessageRequest(BaseModel):
    receiver_id: str
    content: str


@router.get("/dialogs")
async def dialogs(request: Request):
    user = await get_current_social_user(request)
    return get_pm_dialogs(user['social_id'])


@router.get("/users")
async def message_users(request: Request, q: str = Query("", min_length=0)):
    user = await get_current_social_user(request)
    return search_pm_users(q, user['social_id'])


@router.get("/conversation/{other_id}")
async def conversation(other_id: str, request: Request):
    user = await get_current_social_user(request)
    if other_id == user['social_id']:
        raise HTTPException(status_code=400, detail="Нельзя открыть диалог с самим собой")
    mark_pm_read(user['social_id'], other_id)
    return get_pm_conversation(user['social_id'], other_id)


@router.post("/read/{other_id}")
async def mark_read(other_id: str, request: Request):
    user = await get_current_social_user(request)
    count = mark_pm_read(user['social_id'], other_id)
    return {"success": True, "marked": count}


@router.post("/send")
async def send_message(req: SendMessageRequest, request: Request):
    user = await get_current_social_user(request)
    if req.receiver_id == user['social_id']:
        raise HTTPException(status_code=400, detail="Нельзя отправить сообщение самому себе")
    try:
        msg_id = send_pm(user['social_id'], req.receiver_id, req.content)
        return {"success": True, "message_id": msg_id}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

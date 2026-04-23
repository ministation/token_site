from fastapi import APIRouter, Request, HTTPException
from app.dependencies import get_current_user
from app.models.chat import ChatMessage
from app.services.chat import get_chat_messages, add_chat_message

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.get("")
async def get_chat():
    return get_chat_messages()


@router.post("")
async def post_chat(request: Request, msg: ChatMessage):
    user = await get_current_user(request)
    if len(msg.message) > 200:
        raise HTTPException(status_code=400, detail="Сообщение слишком длинное")
    if not msg.message.strip():
        raise HTTPException(status_code=400, detail="Пустое сообщение")
    msg_data = add_chat_message(
        username=user['username'],
        avatar=user.get('avatar'),
        message=msg.message
    )
    return {"success": True}
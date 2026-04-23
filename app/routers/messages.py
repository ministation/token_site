from fastapi import APIRouter, Request, HTTPException
from app.dependencies import get_current_player
from app.services.messages import send_pm, get_pm_conversation, get_pm_dialogs
from pydantic import BaseModel

router = APIRouter(prefix="/api/messages", tags=["messages"])

class SendMessageRequest(BaseModel):
    receiver_id: str
    content: str

@router.get("/dialogs")
async def dialogs(request: Request):
    player = await get_current_player(request)
    return get_pm_dialogs(player['player_id'])

@router.get("/conversation/{other_id}")
async def conversation(other_id: str, request: Request):
    player = await get_current_player(request)
    return get_pm_conversation(player['player_id'], other_id)

@router.post("/send")
async def send_message(req: SendMessageRequest, request: Request):
    player = await get_current_player(request)
    try:
        msg_id = send_pm(player['player_id'], req.receiver_id, req.content)
        return {"success": True, "message_id": msg_id}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
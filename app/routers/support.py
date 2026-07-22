from fastapi import APIRouter, Request, HTTPException, Form, File, UploadFile

from app.config import SUPPORT_EMAIL, SUPPORT_DISCORD_USERNAME, SUPPORT_TELEGRAM_USERNAME, BOOSTY_URL
from app.dependencies import get_current_social_user, get_optional_social_user
from app.services import support as support_svc
from app.services.media_upload import save_upload

router = APIRouter(prefix="/api/support", tags=["support"])


@router.get("/contacts")
async def support_contacts():
    return {
        "email": SUPPORT_EMAIL,
        "discord_username": SUPPORT_DISCORD_USERNAME,
        "telegram_username": SUPPORT_TELEGRAM_USERNAME,
        "boosty_url": BOOSTY_URL,
    }


@router.post("/tickets")
async def create_ticket(
    request: Request,
    contact: str = Form(...),
    subject: str = Form(...),
    body: str = Form(...),
):
    user = await get_optional_social_user(request)
    player_id = user["social_id"] if user else None
    try:
        ticket_id = support_svc.create_ticket(contact, subject, body, player_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"success": True, "ticket_id": ticket_id}


@router.get("/tickets/mine")
async def my_tickets(request: Request):
    user = await get_current_social_user(request)
    return support_svc.my_tickets(user["social_id"])


@router.get("/tickets/{ticket_id}")
async def get_my_ticket_thread(ticket_id: int, request: Request):
    user = await get_current_social_user(request)
    data = support_svc.get_ticket_thread(ticket_id)
    if not data:
        raise HTTPException(status_code=404, detail="Тикет не найден")
    ticket = data["ticket"]
    if ticket.get("player_id") != user["social_id"]:
        raise HTTPException(status_code=403, detail="Нет доступа")
    return data


@router.post("/tickets/{ticket_id}/messages")
async def post_my_ticket_message(
    ticket_id: int,
    request: Request,
    content: str = Form(""),
    image: UploadFile | None = File(None),
):
    user = await get_current_social_user(request)
    image_url = None
    if image and image.filename:
        try:
            image_url = save_upload(image, user["social_id"], kind="image", prefix="ticket")
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
    try:
        msg_id = support_svc.add_user_message(
            ticket_id,
            user["social_id"],
            content,
            image_url=image_url,
            author_name=user.get("display_name") or user.get("username"),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"success": True, "message_id": msg_id, **support_svc.get_ticket_thread(ticket_id)}

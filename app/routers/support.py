from fastapi import APIRouter, Request, HTTPException, Query, Form
from pydantic import BaseModel

from app.config import SUPPORT_EMAIL, SUPPORT_DISCORD_USERNAME, SUPPORT_TELEGRAM_USERNAME, BOOSTY_URL
from app.dependencies import get_current_social_user, get_optional_social_user
from app.services import support as support_svc

router = APIRouter(prefix="/api/support", tags=["support"])


class ReviewTicketRequest(BaseModel):
    status: str
    admin_response: str = ""


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

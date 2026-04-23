from fastapi import APIRouter, Request, HTTPException
from app.core.templates import templates   # <-- общий экземпляр
from app.services.social import get_social_user_by_player_id

router = APIRouter(tags=["pages"])


@router.get("/profile/{player_id}")
async def profile_page(request: Request, player_id: str):
    profile = get_social_user_by_player_id(player_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Профиль не найден")
    return templates.TemplateResponse("profile.html", {"request": request, "profile": profile})
from fastapi import APIRouter, Request, HTTPException

router = APIRouter(tags=["pages"])


@router.get("/profile/{player_id}")
async def profile_page(request: Request, player_id: str):
    from app.services.social import get_social_user_by_player_id
    profile = get_social_user_by_player_id(player_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Профиль не найден")
    templates = request.app.state.templates
    return templates.TemplateResponse("profile.html", {"request": request, "profile": profile})
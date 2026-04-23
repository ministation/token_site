from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse
from app.services.social import get_social_user_by_player_id

router = APIRouter(tags=["pages"])


@router.get("/profile/{player_id}")
async def profile_page(request: Request, player_id: str):
    profile = get_social_user_by_player_id(player_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Профиль не найден")

    env = request.app.state.templates_env
    template = env.get_template("profile.html")
    return HTMLResponse(template.render({"request": request, "profile": profile}))
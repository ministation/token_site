from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse
from app.services.social import get_social_user_by_player_id
import aiohttp

router = APIRouter(tags=["pages"])


@router.get("/profile/{player_id}")
async def profile_page(request: Request, player_id: str):
    profile = get_social_user_by_player_id(player_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Профиль не найден")

    env = request.app.state.templates_env
    template = env.get_template("profile.html")
    return HTMLResponse(template.render({"request": request, "profile": profile}))

@router.get("/api/server-status")
async def server_status():
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("http://85.198.118.85:1214/status", timeout=aiohttp.ClientTimeout(total=5)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return {
                        "online": True,
                        "name": data.get("name", "Мини-станция"),
                        "players": data.get("players", 0),
                        "max_players": data.get("soft_max_players", 100),
                        "map": data.get("map", "Unknown"),
                        "preset": data.get("preset", ""),
                        "round_id": data.get("round_id", 0),
                        "tags": data.get("tags", [])
                    }
    except:
        pass
    return {"online": False, "players": 0, "max_players": 100, "name": "Мини-станция", "map": "Offline"}
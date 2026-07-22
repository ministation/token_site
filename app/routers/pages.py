from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
import aiohttp
from app.services.social import get_social_user_by_player_id

router = APIRouter(tags=["pages"])


@router.get("/donate")
async def donate_page(request: Request):
    from app.seo import donate_social_meta
    env = request.app.state.templates_env
    template = env.get_template("donate_page.html")
    return HTMLResponse(template.render({"request": request, **donate_social_meta(request)}))


@router.get("/profile/{player_id}")
async def profile_page(player_id: str):
    profile = get_social_user_by_player_id(player_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Профиль не найден")
    return RedirectResponse(url=f"/#/player/{player_id}", status_code=302)


@router.get("/api/server-status")
async def server_status():
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                "http://85.198.118.85:1214/status",
                timeout=aiohttp.ClientTimeout(total=5)
            ) as resp:
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
    except Exception:
        pass
    return {
        "online": False,
        "players": 0,
        "max_players": 100,
        "name": "Мини-станция",
        "map": "Offline",
        "preset": ""
    }

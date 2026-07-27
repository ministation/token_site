import aiohttp

from app.config import (
    SS14_OAUTH_CLIENT_ID,
    SS14_OAUTH_CLIENT_SECRET,
    SS14_OAUTH_REDIRECT_URI,
    SS14_OAUTH_AUTHORITY,
)

SS14_AUTH_ENDPOINT = f"{SS14_OAUTH_AUTHORITY.rstrip('/')}/connect/authorize"
SS14_TOKEN_ENDPOINT = f"{SS14_OAUTH_AUTHORITY.rstrip('/')}/connect/token"
SS14_USERINFO_ENDPOINT = f"{SS14_OAUTH_AUTHORITY.rstrip('/')}/connect/userinfo"


def ss14_oauth_enabled() -> bool:
    return bool(SS14_OAUTH_CLIENT_ID and SS14_OAUTH_CLIENT_SECRET)


async def fetch_ss14_profile(code: str) -> dict | None:
    if not ss14_oauth_enabled():
        return None
    async with aiohttp.ClientSession() as session:
        token_data = {
            "client_id": SS14_OAUTH_CLIENT_ID,
            "client_secret": SS14_OAUTH_CLIENT_SECRET,
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": SS14_OAUTH_REDIRECT_URI,
        }
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        async with session.post(SS14_TOKEN_ENDPOINT, data=token_data, headers=headers) as resp:
            tokens = await resp.json()
            access_token = tokens.get("access_token")
            if not access_token:
                return None

        async with session.get(
            SS14_USERINFO_ENDPOINT,
            headers={"Authorization": f"Bearer {access_token}"},
        ) as resp:
            if resp.status != 200:
                return None
            return await resp.json()

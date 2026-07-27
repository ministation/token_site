import secrets
from urllib.parse import urlencode

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


def ss14_oauth_public_info() -> dict:
    return {
        "enabled": ss14_oauth_enabled(),
        "authority": SS14_OAUTH_AUTHORITY,
        "redirect_uri": SS14_OAUTH_REDIRECT_URI,
        "client_id_set": bool(SS14_OAUTH_CLIENT_ID),
        "setup_hint": (
            "В OAuth-приложении SS14 укажите callback ровно: "
            f"{SS14_OAUTH_REDIRECT_URI} (без слэша в конце, HTTPS, PKCE выключен)."
        ),
    }


def build_ss14_authorize_url(state: str, nonce: str) -> str:
    params = {
        "client_id": SS14_OAUTH_CLIENT_ID,
        "redirect_uri": SS14_OAUTH_REDIRECT_URI,
        "response_type": "code",
        "scope": "openid profile",
        "state": state,
        "nonce": nonce,
    }
    return f"{SS14_AUTH_ENDPOINT}?{urlencode(params)}"


async def fetch_ss14_profile(code: str) -> tuple[dict | None, str | None]:
    if not ss14_oauth_enabled():
        return None, "oauth_disabled"
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
            if resp.status != 200:
                err = tokens.get("error_description") or tokens.get("error") or f"http_{resp.status}"
                return None, str(err)
            access_token = tokens.get("access_token")
            if not access_token:
                return None, "no_access_token"

        async with session.get(
            SS14_USERINFO_ENDPOINT,
            headers={"Authorization": f"Bearer {access_token}"},
        ) as resp:
            if resp.status != 200:
                return None, f"userinfo_{resp.status}"
            return await resp.json(), None

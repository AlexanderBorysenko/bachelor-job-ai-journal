"""Auth endpoints — Telegram Login Widget and JWT refresh."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.auth import authenticate_telegram, decode_token, create_access_token

router = APIRouter(prefix="/api/auth", tags=["Auth"])


class TelegramAuthRequest(BaseModel):
    id: int
    first_name: str = ""
    last_name: str = ""
    username: str = ""
    photo_url: str = ""
    auth_date: int
    hash: str


class RefreshRequest(BaseModel):
    refresh_token: str


@router.post("/telegram")
async def telegram_auth(body: TelegramAuthRequest):
    """Authenticate via Telegram Login Widget."""
    try:
        result = await authenticate_telegram(body.model_dump())
        return result
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc))


@router.post("/refresh")
async def refresh_token(body: RefreshRequest):
    """Refresh JWT access token using refresh token."""
    payload = decode_token(body.refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Невалідний refresh token")

    user_id = payload["sub"]
    return {
        "access_token": create_access_token(user_id),
        "token_type": "bearer",
    }

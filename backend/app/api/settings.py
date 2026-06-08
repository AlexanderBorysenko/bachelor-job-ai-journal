"""Settings API — user preferences for bake style and future settings."""

import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional

from app.api.dependencies import get_current_user, get_current_user_id
from app.core.config import settings as app_settings
from app.models.user import User
from app.services.bake import _call_claude, DEFAULT_STYLE
from app.services.blocks import blocks_to_text

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/settings", tags=["Settings"])

PREVIEW_SAMPLE_MESSAGES = (
    "[09:00] (text): Прокинувся рано, на вулиці сонячно. Настрій гарний.\n"
    "[12:30] (voice): Зустрівся з другом на обіді, обговорювали його нову роботу. "
    "Каже що дуже задоволений, але навантаження велике.\n"
    "[18:00] (text): Увечері читав книгу, дуже затягує. Думаю завтра дочитаю."
)

PREVIEW_SAMPLE_LIST = [
    "[09:00] (text): Прокинувся рано, на вулиці сонячно. Настрій гарний.",
    "[12:30] (voice): Зустрівся з другом на обіді, обговорювали його нову роботу. "
    "Каже що дуже задоволений, але навантаження велике.",
    "[18:00] (text): Увечері читав книгу, дуже затягує. Думаю завтра дочитаю.",
]


def _get_settings_response(user: User) -> dict:
    return {
        "bake_style_prompt": user.bake_style_prompt,
        "default_style_prompt": DEFAULT_STYLE,
    }


def _normalize_style_prompt(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped if stripped else None


class UpdateSettingsRequest(BaseModel):
    bake_style_prompt: Optional[str] = None


class PreviewStyleRequest(BaseModel):
    style_prompt: Optional[str] = None


@router.get("")
async def get_settings(user: User = Depends(get_current_user)):
    return _get_settings_response(user)


@router.patch("")
async def update_settings(
    body: UpdateSettingsRequest,
    user: User = Depends(get_current_user),
):
    user.bake_style_prompt = _normalize_style_prompt(body.bake_style_prompt)
    await user.save()
    return _get_settings_response(user)


@router.post("/preview-style")
async def preview_style(
    body: PreviewStyleRequest,
    user: User = Depends(get_current_user),
):
    user_prompt = (
        "Дата: 22 квітня 2026\n\n"
        "Сирі повідомлення (хронологічно):\n\n"
        f"{PREVIEW_SAMPLE_MESSAGES}\n\n"
        "Створи щоденниковий запис за цю дату."
    )
    try:
        blocks = await _call_claude(
            user_prompt,
            style_prompt=_normalize_style_prompt(body.style_prompt),
            temperature=0.7,
            max_tokens=2048,
            model=app_settings.claude_model_preview,
            effort=app_settings.claude_effort_preview,
        )
    except Exception as exc:
        logger.error("Preview style failed: %s", exc)
        raise HTTPException(status_code=502, detail="Не вдалося згенерувати попередній перегляд")

    return {
        "preview": blocks_to_text(blocks),
        "sample_messages": PREVIEW_SAMPLE_LIST,
    }

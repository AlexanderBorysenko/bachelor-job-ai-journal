import logging

from fastapi import APIRouter, Request

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/webhook", tags=["Webhook"])


@router.post("/telegram")
async def telegram_webhook(request: Request):
    """Receive updates from Telegram Bot API."""
    from app.bot.setup import process_update

    body = await request.json()
    try:
        await process_update(body)
    except Exception:
        logger.exception("Failed to process Telegram update")
    return {"ok": True}

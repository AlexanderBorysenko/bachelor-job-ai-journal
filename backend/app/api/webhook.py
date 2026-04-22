from fastapi import APIRouter, Request

router = APIRouter(prefix="/api/webhook", tags=["Webhook"])


@router.post("/telegram")
async def telegram_webhook(request: Request):
    """Receive updates from Telegram Bot API."""
    # This will be wired to aiogram dispatcher in main.py
    from app.bot.setup import process_update

    body = await request.json()
    await process_update(body)
    return {"ok": True}

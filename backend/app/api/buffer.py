"""Buffer API — manage raw messages before baking."""

import asyncio

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from datetime import date
from bson import ObjectId

from app.models.raw_message import RawMessage, MessageStatus
from app.models.audio_job import AudioJob, AudioJobStatus
from app.services.bake import bake_messages
from app.api.dependencies import get_current_user_id
from app.core.events import event_bus

router = APIRouter(prefix="/api/buffer", tags=["Buffer"])


class UpdateMessageRequest(BaseModel):
    content: Optional[str] = None
    classified_date: Optional[date] = None


@router.get("")
async def get_buffer(
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    user_id: str = Depends(get_current_user_id),
):
    """Get all pending messages in the buffer."""
    uid = ObjectId(user_id)
    query = {"user_id": uid, "status": MessageStatus.PENDING}
    if date_from:
        query["classified_date"] = {"$gte": date_from}
    if date_to:
        query.setdefault("classified_date", {})["$lte"] = date_to

    messages = await RawMessage.find(query).sort("+created_at").to_list()

    processing_statuses = [AudioJobStatus.PENDING, AudioJobStatus.DOWNLOADING, AudioJobStatus.TRANSCRIBING]
    processing_audio = await AudioJob.find(
        {"user_id": uid, "status": {"$in": processing_statuses}}
    ).to_list()

    return {
        "messages": [msg.model_dump(mode="json") for msg in messages],
        "processing_audio": [job.model_dump(mode="json") for job in processing_audio],
        "can_bake": len(processing_audio) == 0,
    }


@router.patch("/{message_id}")
async def update_message(
    message_id: str,
    body: UpdateMessageRequest,
    user_id: str = Depends(get_current_user_id),
):
    """Edit a message in the buffer."""
    msg = await RawMessage.get(message_id)
    if not msg or str(msg.user_id) != user_id:
        raise HTTPException(status_code=404, detail="Повідомлення не знайдено")
    if msg.status == MessageStatus.BAKED:
        raise HTTPException(status_code=400, detail="Не можна редагувати вже запечене повідомлення")

    if body.content is not None:
        msg.content = body.content
    if body.classified_date is not None:
        msg.classified_date = body.classified_date

    await msg.save()
    return msg.model_dump(mode="json")


@router.delete("/{message_id}", status_code=204)
async def delete_message(
    message_id: str,
    user_id: str = Depends(get_current_user_id),
):
    """Delete a message from the buffer."""
    msg = await RawMessage.get(message_id)
    if not msg or str(msg.user_id) != user_id:
        raise HTTPException(status_code=404, detail="Повідомлення не знайдено")
    await msg.delete()
    await event_bus.publish(user_id, "buffer:update")


@router.post("/bake", status_code=202)
async def bake(user_id: str = Depends(get_current_user_id)):
    """Start baking pending messages — runs in background, notifies via SSE."""
    uid = ObjectId(user_id)

    processing_statuses = [AudioJobStatus.DOWNLOADING, AudioJobStatus.TRANSCRIBING]
    processing_count = await AudioJob.find(
        {"user_id": uid, "status": {"$in": processing_statuses}}
    ).count()

    if processing_count > 0:
        raise HTTPException(
            status_code=409,
            detail=f"Є {processing_count} повідомлень в процесі транскрибації. Зачекайте завершення.",
        )

    pending = await RawMessage.find(
        {"user_id": uid, "status": MessageStatus.PENDING}
    ).sort("+created_at").to_list()

    if not pending:
        raise HTTPException(status_code=422, detail="Буфер порожній — нічого запікати")

    asyncio.create_task(_run_bake(user_id, uid, pending))
    return {"status": "started", "message_count": len(pending)}


async def _run_bake(user_id: str, uid: ObjectId, pending: list):
    """Background bake task — publishes result via SSE."""
    try:
        entries = await bake_messages(user_id=uid, messages=pending)
        await event_bus.publish(user_id, "bake:complete", {
            "entries_created": len(entries),
            "entries": [
                {"id": str(e.id), "date": e.date.isoformat(), "preview": e.content[:200]}
                for e in entries
            ],
        })
    except Exception as exc:
        await event_bus.publish(user_id, "bake:error", {"detail": str(exc)[:300]})

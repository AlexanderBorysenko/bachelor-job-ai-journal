"""Entries API — diary entries with date navigation."""

from datetime import date
from typing import Optional

from bson import ObjectId
from fastapi import APIRouter, HTTPException, Depends

from app.models.entry import Entry
from app.models.raw_message import RawMessage
from app.models.highlight import Highlight
from app.api.dependencies import get_current_user_id

router = APIRouter(prefix="/api/entries", tags=["Entries"])


@router.get("")
async def list_entries(
    page: int = 1,
    per_page: int = 10,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    user_id: str = Depends(get_current_user_id),
):
    """List diary entries with pagination, sorted by date (newest first)."""
    uid = ObjectId(user_id)
    query = {"user_id": uid}
    if date_from:
        query["date"] = {"$gte": date_from}
    if date_to:
        query.setdefault("date", {})["$lte"] = date_to

    total = await Entry.find(query).count()
    entries = (
        await Entry.find(query)
        .sort("-date")
        .skip((page - 1) * per_page)
        .limit(per_page)
        .to_list()
    )

    all_entries = await Entry.find({"user_id": uid}).sort("-date").to_list()
    available_dates = [e.date.isoformat() for e in all_entries]

    return {
        "items": [_entry_preview(e) for e in entries],
        "total": total,
        "page": page,
        "per_page": per_page,
        "available_dates": available_dates,
    }


@router.get("/by-date/{entry_date}")
async def get_entry_by_date(
    entry_date: date,
    user_id: str = Depends(get_current_user_id),
):
    """Get entry by date with prev/next navigation."""
    uid = ObjectId(user_id)
    entry = await Entry.find_one({"user_id": uid, "date": entry_date})
    if not entry:
        raise HTTPException(status_code=404, detail="Запис за цю дату не знайдено")

    prev_entry = await Entry.find(
        {"user_id": uid, "date": {"$lt": entry_date}}
    ).sort("-date").first_or_none()
    next_entry = await Entry.find(
        {"user_id": uid, "date": {"$gt": entry_date}}
    ).sort("+date").first_or_none()

    highlights = await Highlight.find({"source_entries": entry.id}).to_list()

    return {
        "entry": _entry_full(entry, highlights),
        "prev_date": prev_entry.date.isoformat() if prev_entry else None,
        "next_date": next_entry.date.isoformat() if next_entry else None,
    }


@router.get("/{entry_id}")
async def get_entry(
    entry_id: str,
    user_id: str = Depends(get_current_user_id),
):
    """Get a specific entry by ID."""
    entry = await Entry.get(entry_id)
    if not entry or str(entry.user_id) != user_id:
        raise HTTPException(status_code=404, detail="Запис не знайдено")

    highlights = await Highlight.find({"source_entries": entry.id}).to_list()
    return _entry_full(entry, highlights)


@router.get("/{entry_id}/raw")
async def get_entry_raw_messages(
    entry_id: str,
    user_id: str = Depends(get_current_user_id),
):
    """Get the raw messages that were baked into this entry."""
    entry = await Entry.get(entry_id)
    if not entry or str(entry.user_id) != user_id:
        raise HTTPException(status_code=404, detail="Запис не знайдено")

    messages = await RawMessage.find(
        {"_id": {"$in": entry.source_messages}}
    ).sort("+created_at").to_list()

    return [msg.model_dump(mode="json") for msg in messages]


def _entry_preview(entry: Entry) -> dict:
    return {
        "id": str(entry.id),
        "date": entry.date.isoformat(),
        "content_preview": entry.content[:200] + "..." if len(entry.content) > 200 else entry.content,
        "version": entry.version,
        "created_at": entry.created_at.isoformat() if entry.created_at else None,
        "updated_at": entry.updated_at.isoformat() if entry.updated_at else None,
    }


def _entry_full(entry: Entry, highlights: list[Highlight]) -> dict:
    return {
        "id": str(entry.id),
        "date": entry.date.isoformat(),
        "content": entry.content,
        "source_messages_count": len(entry.source_messages),
        "highlights": [
            {"id": str(h.id), "title": h.title, "category": h.category}
            for h in highlights
        ],
        "version": entry.version,
        "created_at": entry.created_at.isoformat() if entry.created_at else None,
        "updated_at": entry.updated_at.isoformat() if entry.updated_at else None,
    }

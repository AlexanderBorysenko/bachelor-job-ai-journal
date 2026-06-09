"""Story points API — user-authored key story points attached to entries (pages)."""

from datetime import datetime

from bson import ObjectId
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from app.models.story_point import StoryPoint
from app.models.entry import Entry
from app.models.user import User
from app.api.dependencies import get_current_user_id
from app.core.i18n import t, DEFAULT_LANG

router = APIRouter(prefix="/api/storypoints", tags=["StoryPoints"])

MAX_TITLE_LEN = 200


def _serialize(p: StoryPoint) -> dict:
    return {
        "id": str(p.id),
        "entry_id": str(p.entry_id),
        "date": p.date.isoformat(),
        "title": p.title,
        "order": p.order,
        "source": p.source,
    }


async def _lang(user_id: str) -> str:
    user = await User.get(user_id)
    return user.language if user else DEFAULT_LANG


async def _owned_entry(entry_id: str, user_id: str) -> Entry:
    entry = await Entry.get(entry_id)
    if not entry or str(entry.user_id) != user_id:
        raise HTTPException(status_code=404, detail=t("entry_not_found", await _lang(user_id)))
    return entry


async def _owned_point(point_id: str, user_id: str) -> StoryPoint:
    point = await StoryPoint.get(point_id)
    if not point or str(point.user_id) != user_id:
        raise HTTPException(status_code=404, detail=t("story_point_not_found", await _lang(user_id)))
    return point


async def _clean_title(title: str, user_id: str) -> str:
    cleaned = (title or "").strip()
    if not cleaned:
        raise HTTPException(status_code=422, detail=t("story_point_title_required", await _lang(user_id)))
    return cleaned[:MAX_TITLE_LEN]


class CreateStoryPointRequest(BaseModel):
    entry_id: str
    title: str


class UpdateStoryPointRequest(BaseModel):
    title: str


class ReorderRequest(BaseModel):
    entry_id: str
    ordered_ids: list[str]


@router.get("/timeline")
async def get_timeline(user_id: str = Depends(get_current_user_id)):
    """Dates that have story points, newest first; points by order asc."""
    uid = ObjectId(user_id)
    points = await StoryPoint.find({"user_id": uid}).sort([("date", -1), ("order", 1)]).to_list()
    groups: list[dict] = []
    index: dict[str, dict] = {}
    for p in points:
        key = p.date.isoformat()
        if key not in index:
            grp = {"date": key, "entry_id": str(p.entry_id), "points": []}
            index[key] = grp
            groups.append(grp)
        index[key]["points"].append({"id": str(p.id), "title": p.title, "order": p.order})
    return {"groups": groups}


@router.get("")
async def list_for_entry(entry_id: str, user_id: str = Depends(get_current_user_id)):
    """List story points for one entry (page), ordered."""
    await _owned_entry(entry_id, user_id)
    points = (
        await StoryPoint.find(
            {"user_id": ObjectId(user_id), "entry_id": ObjectId(entry_id)}
        )
        .sort("+order")
        .to_list()
    )
    return {"items": [_serialize(p) for p in points]}


@router.post("", status_code=201)
async def create_story_point(
    body: CreateStoryPointRequest,
    user_id: str = Depends(get_current_user_id),
):
    """Create a story point on an entry, appended to the end."""
    entry = await _owned_entry(body.entry_id, user_id)
    title = await _clean_title(body.title, user_id)
    last = await StoryPoint.find(
        {"user_id": ObjectId(user_id), "entry_id": entry.id}
    ).sort("-order").first_or_none()
    next_order = (last.order + 1) if last else 0
    point = StoryPoint(
        user_id=ObjectId(user_id),
        entry_id=entry.id,
        date=entry.date,
        title=title,
        order=next_order,
        source="manual",
    )
    await point.insert()
    return _serialize(point)


@router.patch("/{point_id}")
async def rename_story_point(
    point_id: str,
    body: UpdateStoryPointRequest,
    user_id: str = Depends(get_current_user_id),
):
    """Rename a story point."""
    point = await _owned_point(point_id, user_id)
    point.title = await _clean_title(body.title, user_id)
    point.updated_at = datetime.utcnow()
    await point.save()
    return _serialize(point)


@router.put("/reorder")
async def reorder_story_points(
    body: ReorderRequest,
    user_id: str = Depends(get_current_user_id),
):
    """Persist the order of an entry's story points. ordered_ids must be exactly the entry's points."""
    entry = await _owned_entry(body.entry_id, user_id)
    points = await StoryPoint.find(
        {"user_id": ObjectId(user_id), "entry_id": entry.id}
    ).to_list()
    by_id = {str(p.id): p for p in points}
    if len(body.ordered_ids) != len(by_id) or set(body.ordered_ids) != set(by_id.keys()):
        raise HTTPException(status_code=422, detail=t("story_point_reorder_mismatch", await _lang(user_id)))
    for i, pid in enumerate(body.ordered_ids):
        p = by_id[pid]
        p.order = i
        p.updated_at = datetime.utcnow()
        await p.save()
    ordered = [by_id[pid] for pid in body.ordered_ids]
    return {"items": [_serialize(p) for p in ordered]}


@router.delete("/{point_id}", status_code=204)
async def delete_story_point(
    point_id: str,
    user_id: str = Depends(get_current_user_id),
):
    """Delete a story point."""
    point = await _owned_point(point_id, user_id)
    await point.delete()

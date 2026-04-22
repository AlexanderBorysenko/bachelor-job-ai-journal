"""Highlights API — ideas, stories, moods, insights extracted from entries."""

from typing import Optional

from bson import ObjectId
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from app.models.highlight import Highlight
from app.models.user import User, CustomCategory
from app.api.dependencies import get_current_user_id, get_current_user

router = APIRouter(prefix="/api/highlights", tags=["Highlights"])


SYSTEM_CATEGORIES = [
    {"name": "idea", "description": "Креативні думки, плани, задуми", "icon": "💡", "is_system": True},
    {"name": "story", "description": "Події, подорожі, зустрічі, визначні моменти", "icon": "📖", "is_system": True},
    {"name": "mood", "description": "Емоції, настрій, рефлексія", "icon": "🧠", "is_system": True},
    {"name": "insight", "description": "Висновки, усвідомлення, «аха-моменти»", "icon": "⚡", "is_system": True},
]


class CreateCategoryRequest(BaseModel):
    name: str
    description: str
    icon: Optional[str] = None


@router.get("")
async def list_highlights(
    category: Optional[str] = None,
    page: int = 1,
    per_page: int = 20,
    user_id: str = Depends(get_current_user_id),
):
    """List highlights with optional category filter."""
    uid = ObjectId(user_id)
    query = {"user_id": uid}
    if category:
        query["category"] = category

    total = await Highlight.find(query).count()
    highlights = (
        await Highlight.find(query)
        .sort("-created_at")
        .skip((page - 1) * per_page)
        .limit(per_page)
        .to_list()
    )

    return {
        "items": [h.model_dump(mode="json") for h in highlights],
        "total": total,
        "page": page,
        "per_page": per_page,
    }


@router.get("/categories")
async def list_categories(user: User = Depends(get_current_user)):
    """List system + user-defined categories."""
    categories = list(SYSTEM_CATEGORIES)
    for cat in (user.custom_categories or []):
        categories.append({
            "name": cat.name,
            "description": cat.description,
            "icon": cat.icon or "🏷️",
            "is_system": False,
        })
    return categories


@router.post("/categories", status_code=201)
async def create_category(
    body: CreateCategoryRequest,
    user: User = Depends(get_current_user),
):
    """Create a custom highlight category."""
    # Check for duplicate
    existing_names = [c.name for c in (user.custom_categories or [])]
    system_names = [c["name"] for c in SYSTEM_CATEGORIES]
    if body.name in existing_names or body.name in system_names:
        raise HTTPException(status_code=400, detail="Категорія з такою назвою вже існує")

    new_cat = CustomCategory(
        name=body.name,
        description=body.description,
        icon=body.icon,
    )
    if not user.custom_categories:
        user.custom_categories = []
    user.custom_categories.append(new_cat)
    await user.save()

    return {
        "name": new_cat.name,
        "description": new_cat.description,
        "icon": new_cat.icon,
        "is_system": False,
    }


@router.get("/{highlight_id}")
async def get_highlight(
    highlight_id: str,
    user_id: str = Depends(get_current_user_id),
):
    """Get a specific highlight."""
    highlight = await Highlight.get(highlight_id)
    if not highlight or str(highlight.user_id) != user_id:
        raise HTTPException(status_code=404, detail="Хайлайт не знайдено")
    return highlight.model_dump(mode="json")

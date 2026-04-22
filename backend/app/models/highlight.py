from datetime import date, datetime
from enum import Enum
from typing import Optional

from beanie import Document, PydanticObjectId
from pydantic import BaseModel, Field


class HighlightCategory(str, Enum):
    IDEA = "idea"
    STORY = "story"
    MOOD = "mood"
    INSIGHT = "insight"
    CUSTOM = "custom"


class DateRange(BaseModel):
    from_date: date = Field(alias="from")
    to_date: date = Field(alias="to")

    model_config = {"populate_by_name": True}


class Highlight(Document):
    """An auto-extracted highlight from diary entries."""

    user_id: PydanticObjectId
    title: str
    category: str  # HighlightCategory value or custom category name
    content: str
    source_entries: list[PydanticObjectId] = Field(default_factory=list)
    date_range: Optional[DateRange] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "highlights"

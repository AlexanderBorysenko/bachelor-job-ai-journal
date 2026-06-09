from datetime import date as date_, datetime

from beanie import Document, PydanticObjectId
from pydantic import Field


class StoryPoint(Document):
    """A user-authored key story point attached to a diary entry (page)."""

    user_id: PydanticObjectId
    entry_id: PydanticObjectId          # the page it belongs to
    date: date_                         # denormalized from the entry → group/sort timeline, no join
    title: str
    order: int = 0                      # position within the date
    source: str = "manual"             # "manual" | "ai" — future AI-generation origin flag
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "story_points"
        indexes = [
            [("user_id", 1), ("date", -1), ("order", 1)],
            [("entry_id", 1)],
        ]

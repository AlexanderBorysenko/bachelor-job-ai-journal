from datetime import date, datetime

from beanie import Document, PydanticObjectId
from pydantic import Field


class Entry(Document):
    """A diary entry for a single date. One date = one entry per user."""

    user_id: PydanticObjectId
    date: date
    content: str  # Markdown literary text
    source_messages: list[PydanticObjectId] = Field(default_factory=list)
    highlights_checked: bool = False
    version: int = 1
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "entries"
        indexes = [
            [("user_id", 1), ("date", -1)],  # compound unique per user+date
        ]

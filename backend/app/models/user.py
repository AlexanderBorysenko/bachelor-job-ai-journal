from datetime import datetime
from typing import Optional

from beanie import Document, Indexed
from pydantic import BaseModel, Field


class CustomCategory(BaseModel):
    """User-defined highlight category."""

    name: str
    description: str
    icon: Optional[str] = None


class User(Document):
    """Registered user (linked to Telegram account)."""

    telegram_id: Indexed(int, unique=True)  # type: ignore[valid-type]
    username: Optional[str] = None
    display_name: str
    custom_categories: list[CustomCategory] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "users"

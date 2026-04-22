from datetime import date, datetime
from enum import Enum
from typing import Optional

from beanie import Document, PydanticObjectId
from pydantic import Field


class SourceType(str, Enum):
    TEXT = "text"
    VOICE = "voice"


class MessageStatus(str, Enum):
    PENDING = "pending"
    BAKED = "baked"


class RawMessage(Document):
    """A single raw message in the buffer, waiting to be baked into an entry."""

    user_id: PydanticObjectId
    source_type: SourceType
    content: str
    telegram_message_id: int
    audio_duration: Optional[float] = None
    classified_date: date
    status: MessageStatus = MessageStatus.PENDING
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "raw_messages"

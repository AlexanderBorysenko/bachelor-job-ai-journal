from datetime import datetime
from enum import Enum
from typing import Optional

from beanie import Document, PydanticObjectId
from pydantic import Field


class AudioJobStatus(str, Enum):
    PENDING = "pending"
    DOWNLOADING = "downloading"
    TRANSCRIBING = "transcribing"
    COMPLETED = "completed"
    ERROR = "error"


class AudioJob(Document):
    """Tracks audio message processing pipeline."""

    user_id: PydanticObjectId
    telegram_message_id: int
    file_id: str
    file_path: Optional[str] = None
    duration: float
    status: AudioJobStatus = AudioJobStatus.PENDING
    transcription: Optional[str] = None
    error_message: Optional[str] = None
    attempts: int = 0
    raw_message_id: Optional[PydanticObjectId] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "audio_jobs"

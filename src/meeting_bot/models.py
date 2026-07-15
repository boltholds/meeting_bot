from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from urllib.parse import urlparse
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class MeetingProvider(StrEnum):
    GOOGLE_MEET = "google_meet"
    ZOOM = "zoom"


class MeetingStatus(StrEnum):
    QUEUED = "queued"
    JOINING = "joining"
    WAITING_ROOM = "waiting_room"
    RECORDING = "recording"
    PROCESSING = "processing"
    COMPLETED = "completed"
    STOPPED = "stopped"
    FAILED = "failed"


def provider_from_url(url: str) -> MeetingProvider:
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.username or parsed.password:
        raise ValueError("Meeting URL must be a plain HTTPS URL.")

    host = (parsed.hostname or "").lower().rstrip(".")
    if parsed.port not in {None, 443}:
        raise ValueError("Meeting URL must use the standard HTTPS port.")
    if host == "meet.google.com":
        return MeetingProvider.GOOGLE_MEET
    if host == "zoom.us" or host.endswith(".zoom.us"):
        return MeetingProvider.ZOOM
    raise ValueError("Only meet.google.com and *.zoom.us URLs are supported.")


class CreateMeetingRequest(BaseModel):
    url: str
    title: str | None = Field(default=None, max_length=200)
    bot_name: str | None = Field(default=None, min_length=1, max_length=100)
    language: str | None = Field(default=None, min_length=2, max_length=16)
    analyze: bool | None = None
    min_speakers: int | None = Field(default=None, ge=1, le=50)
    max_speakers: int | None = Field(default=None, ge=1, le=50)

    @field_validator("url")
    @classmethod
    def validate_url(cls, value: str) -> str:
        provider_from_url(value)
        return value

    def validate_speaker_bounds(self) -> None:
        if (
            self.min_speakers is not None
            and self.max_speakers is not None
            and self.min_speakers > self.max_speakers
        ):
            raise ValueError("min_speakers must not exceed max_speakers.")


class MeetingSession(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    url: str
    provider: MeetingProvider
    status: MeetingStatus = MeetingStatus.QUEUED
    title: str | None = None
    bot_name: str
    language: str
    analyze: bool
    min_speakers: int | None = None
    max_speakers: int | None = None
    created_at: datetime = Field(default_factory=utc_now)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error: str | None = None
    recording_path: str | None = None
    transcription_job_id: str | None = None

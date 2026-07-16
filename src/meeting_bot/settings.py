from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    api_key: str = ""
    data_dir: Path = Path("data")
    bot_name: str = "Super Transcriber Bot - идёт запись"
    recording_notice: str = (
        "Бот записывает аудио встречи для расшифровки. "
        "Продолжая участие, вы соглашаетесь с записью."
    )

    super_transcriber_url: str = "http://localhost:8000"
    super_transcriber_api_key: str = ""
    google_storage_state: str = ""
    transcription_language: str = "ru"
    transcription_analyze: bool = True
    transcription_min_speakers: int | None = Field(default=1, ge=1, le=50)
    transcription_max_speakers: int | None = Field(default=10, ge=1, le=50)

    pulse_sink: str = "meeting_output"
    ffmpeg_segment_seconds: int = Field(default=300, ge=30, le=3600)
    join_timeout_seconds: int = Field(default=300, ge=10, le=3600)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


def get_settings() -> Settings:
    return Settings()

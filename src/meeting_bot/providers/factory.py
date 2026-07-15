from __future__ import annotations

from typing import Any

from meeting_bot.models import MeetingProvider
from meeting_bot.providers.base import MeetingPageAdapter
from meeting_bot.providers.google_meet import GoogleMeetAdapter
from meeting_bot.providers.zoom import ZoomAdapter


def create_provider_adapter(
    provider: MeetingProvider, page: Any, *, bot_name: str
) -> MeetingPageAdapter:
    if provider == MeetingProvider.GOOGLE_MEET:
        return GoogleMeetAdapter(page, bot_name=bot_name)
    if provider == MeetingProvider.ZOOM:
        return ZoomAdapter(page, bot_name=bot_name)
    raise ValueError(f"Unsupported meeting provider: {provider}")

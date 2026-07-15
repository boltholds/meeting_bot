from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from meeting_bot.providers.google_meet import GoogleMeetAdapter, _with_ui_language


def test_google_meet_url_forces_english_and_preserves_query() -> None:
    result = _with_ui_language("https://meet.google.com/abc-defg-hij?authuser=1&hl=nl")

    assert result == ("https://meet.google.com/abc-defg-hij?authuser=1&hl=en")


@pytest.mark.asyncio
async def test_google_meet_chat_notice_waits_for_controls() -> None:
    page = SimpleNamespace(
        keyboard=SimpleNamespace(press=AsyncMock()),
        wait_for_timeout=AsyncMock(),
    )
    adapter = GoogleMeetAdapter(page, bot_name="Recording bot")
    adapter._retry_click = AsyncMock(return_value=True)
    adapter._retry_fill = AsyncMock(return_value=True)

    sent = await adapter.send_chat_notice("Recording notice")

    assert sent is True
    page.keyboard.press.assert_awaited_once_with("Enter")
    adapter._retry_fill.assert_awaited_once()


@pytest.mark.asyncio
async def test_google_meet_chat_notice_reports_missing_button() -> None:
    adapter = GoogleMeetAdapter(SimpleNamespace(), bot_name="Recording bot")
    adapter._retry_click = AsyncMock(return_value=False)
    adapter._page_summary = AsyncMock(return_value="visible_text='Chat disabled'")

    with pytest.raises(RuntimeError, match="chat button was not found"):
        await adapter.send_chat_notice("Recording notice")

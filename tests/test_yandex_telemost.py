from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from meeting_bot.providers.yandex_telemost import YandexTelemostAdapter


@pytest.mark.asyncio
async def test_yandex_telemost_guest_join_uses_browser_prejoin() -> None:
    page = SimpleNamespace(
        goto=AsyncMock(),
        wait_for_timeout=AsyncMock(),
    )
    adapter = YandexTelemostAdapter(page, bot_name="Recording bot")
    adapter._visible_failure = AsyncMock(return_value=None)
    adapter._fill_first = AsyncMock(return_value=True)
    adapter._disable_media = AsyncMock()
    adapter._retry_click = AsyncMock(return_value=True)
    adapter._in_call_controls_visible = AsyncMock(return_value=True)
    adapter._dismiss_tips = AsyncMock()

    await adapter.join(
        "https://telemost.yandex.ru/j/12345678901234",
        timeout_seconds=30,
    )

    page.goto.assert_awaited_once_with(
        "https://telemost.yandex.ru/j/12345678901234",
        wait_until="domcontentloaded",
    )
    adapter._fill_first.assert_awaited_once()
    adapter._disable_media.assert_awaited_once()
    adapter._retry_click.assert_awaited_once()
    assert adapter._dismiss_tips.await_count == 2


@pytest.mark.asyncio
async def test_yandex_telemost_dismisses_both_media_permission_tips() -> None:
    page = SimpleNamespace(wait_for_timeout=AsyncMock())
    adapter = YandexTelemostAdapter(page, bot_name="Recording bot")
    adapter._click_first = AsyncMock(side_effect=[True, True, False])

    await adapter._dismiss_tips()

    assert adapter._click_first.await_count == 3
    assert page.wait_for_timeout.await_count == 2


@pytest.mark.asyncio
async def test_yandex_telemost_chat_notice_waits_for_controls() -> None:
    page = SimpleNamespace(
        keyboard=SimpleNamespace(press=AsyncMock()),
        wait_for_timeout=AsyncMock(),
    )
    adapter = YandexTelemostAdapter(page, bot_name="Recording bot")
    adapter._retry_click = AsyncMock(return_value=True)
    adapter._retry_fill = AsyncMock(return_value=True)

    sent = await adapter.send_chat_notice("Recording notice")

    assert sent is True
    page.keyboard.press.assert_awaited_once_with("Enter")
    adapter._retry_fill.assert_awaited_once()


@pytest.mark.asyncio
async def test_yandex_telemost_chat_notice_reports_missing_button() -> None:
    adapter = YandexTelemostAdapter(SimpleNamespace(), bot_name="Recording bot")
    adapter._retry_click = AsyncMock(return_value=False)
    adapter._page_summary = AsyncMock(return_value="visible_text='Chat unavailable'")

    with pytest.raises(RuntimeError, match="chat button was not found"):
        await adapter.send_chat_notice("Recording notice")

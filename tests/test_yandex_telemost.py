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
    adapter._retry_join = AsyncMock(return_value=True)
    adapter._in_call_controls_visible = AsyncMock(return_value=False)
    adapter._prejoin_visible = AsyncMock(return_value=False)
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
    adapter._retry_join.assert_awaited_once()
    adapter._dismiss_tips.assert_awaited_once()


@pytest.mark.asyncio
async def test_yandex_telemost_stays_active_without_known_toolbar_label() -> None:
    page = SimpleNamespace(is_closed=lambda: False)
    adapter = YandexTelemostAdapter(page, bot_name="Recording bot")
    adapter._visible_failure = AsyncMock(return_value=None)
    adapter._in_call_controls_visible = AsyncMock(return_value=False)
    adapter._prejoin_visible = AsyncMock(return_value=False)

    assert await adapter.is_meeting_active() is True


@pytest.mark.asyncio
async def test_yandex_telemost_stops_when_end_screen_appears() -> None:
    page = SimpleNamespace(is_closed=lambda: False)
    adapter = YandexTelemostAdapter(page, bot_name="Recording bot")
    adapter._visible_failure = AsyncMock(return_value="Звонок завершён")

    assert await adapter.is_meeting_active() is False


@pytest.mark.asyncio
async def test_yandex_telemost_dismisses_both_media_permission_tips() -> None:
    page = SimpleNamespace(wait_for_timeout=AsyncMock())
    adapter = YandexTelemostAdapter(page, bot_name="Recording bot")
    adapter._click_visible_tip = AsyncMock(side_effect=[True, True, False])

    await adapter._dismiss_tips()

    assert adapter._click_visible_tip.await_count == 3
    assert page.wait_for_timeout.await_count == 2


@pytest.mark.asyncio
async def test_yandex_telemost_retries_join_after_late_permission_tip() -> None:
    adapter = YandexTelemostAdapter(SimpleNamespace(), bot_name="Recording bot")
    adapter._dismiss_tips = AsyncMock()
    adapter._click_first = AsyncMock(side_effect=[False, True])

    clicked = await adapter._retry_join(
        ['button[data-testid="enter-conference-button"]'],
        timeout_seconds=2,
    )

    assert clicked is True
    assert adapter._dismiss_tips.await_count == 2
    assert adapter._click_first.await_count == 2


@pytest.mark.asyncio
async def test_yandex_telemost_chat_notice_waits_for_controls() -> None:
    page = SimpleNamespace(
        keyboard=SimpleNamespace(press=AsyncMock()),
        wait_for_timeout=AsyncMock(),
    )
    adapter = YandexTelemostAdapter(page, bot_name="Recording bot")
    adapter._open_chat_and_fill = AsyncMock(return_value=True)

    sent = await adapter.send_chat_notice("Recording notice")

    assert sent is True
    page.keyboard.press.assert_awaited_once_with("Enter")
    adapter._open_chat_and_fill.assert_awaited_once()


@pytest.mark.asyncio
async def test_yandex_telemost_chat_notice_reports_missing_field() -> None:
    adapter = YandexTelemostAdapter(SimpleNamespace(), bot_name="Recording bot")
    adapter._open_chat_and_fill = AsyncMock(return_value=False)
    adapter._page_summary = AsyncMock(return_value="visible_text='Chat unavailable'")

    with pytest.raises(RuntimeError, match="chat message field was not found"):
        await adapter.send_chat_notice("Recording notice")


@pytest.mark.asyncio
async def test_yandex_telemost_waits_for_editor_after_opening_chat() -> None:
    adapter = YandexTelemostAdapter(SimpleNamespace(), bot_name="Recording bot")
    adapter._fill_first = AsyncMock(side_effect=[False, False, True])
    adapter._fill_messenger_frame = AsyncMock(return_value=False)
    adapter._click_first = AsyncMock(return_value=True)

    filled = await adapter._open_chat_and_fill(
        ['button:has-text("Чат")'],
        ['[contenteditable="true"]'],
        "Recording notice",
        timeout_seconds=2,
    )

    assert filled is True
    adapter._click_first.assert_awaited_once()


@pytest.mark.asyncio
async def test_yandex_telemost_fills_messenger_iframe() -> None:
    field = SimpleNamespace(
        is_visible=AsyncMock(return_value=True),
        fill=AsyncMock(),
    )
    frame = SimpleNamespace(
        parent_frame=object(),
        url="https://yandex.ru/chat/iframe/meeting",
        locator=lambda _selector: SimpleNamespace(first=field),
    )
    page = SimpleNamespace(frames=[frame])
    adapter = YandexTelemostAdapter(page, bot_name="Recording bot")

    filled = await adapter._fill_messenger_frame([], "Recording notice")

    assert filled is True
    field.fill.assert_awaited_once_with("Recording notice")

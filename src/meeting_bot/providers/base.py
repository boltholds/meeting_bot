from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class MeetingPageAdapter(ABC):
    def __init__(self, page: Any, *, bot_name: str) -> None:
        self.page = page
        self.bot_name = bot_name

    @abstractmethod
    async def join(self, url: str, timeout_seconds: int) -> None:
        raise NotImplementedError

    @abstractmethod
    async def send_chat_notice(self, message: str) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def is_meeting_active(self) -> bool:
        raise NotImplementedError

    async def _click_first(self, selectors: list[str]) -> bool:
        for selector in selectors:
            locator = self.page.locator(selector).first
            try:
                if await locator.is_visible(timeout=800):
                    await locator.click()
                    return True
            except Exception:
                continue
        return False

    async def _fill_first(self, selectors: list[str], value: str) -> bool:
        for selector in selectors:
            locator = self.page.locator(selector).first
            try:
                if await locator.is_visible(timeout=800):
                    await locator.fill(value)
                    return True
            except Exception:
                continue
        return False

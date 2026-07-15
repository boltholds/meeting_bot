from __future__ import annotations

import asyncio

from meeting_bot.providers.base import MeetingPageAdapter


class ZoomAdapter(MeetingPageAdapter):
    async def join(self, url: str, timeout_seconds: int) -> None:
        await self.page.goto(url, wait_until="domcontentloaded")

        await self._click_first(
            [
                'a:has-text("Join from Your Browser")',
                'a:has-text("Join from your browser")',
                'a:has-text("Войти из браузера")',
            ]
        )
        await self._fill_first(
            [
                "input#inputname",
                'input[placeholder*="name"]',
                'input[placeholder*="имя"]',
            ],
            self.bot_name,
        )
        clicked = await self._click_first(
            [
                'button:has-text("Join")',
                'button:has-text("Войти")',
            ]
        )
        if not clicked:
            raise RuntimeError(
                "Zoom browser join is unavailable or the join button was not found."
            )

        deadline = asyncio.get_running_loop().time() + timeout_seconds
        while asyncio.get_running_loop().time() < deadline:
            if await self._in_call_controls_visible():
                await self._click_first(
                    [
                        'button:has-text("Join Audio by Computer")',
                        'button:has-text("Join with Computer Audio")',
                        'button:has-text("Войти с использованием звука компьютера")',
                    ]
                )
                return
            await asyncio.sleep(2)
        raise TimeoutError("Timed out waiting for Zoom admission.")

    async def send_chat_notice(self, message: str) -> bool:
        opened = await self._click_first(
            [
                'button[aria-label*="chat"]',
                'button:has-text("Chat")',
                'button:has-text("Чат")',
            ]
        )
        if not opened:
            return False
        filled = await self._fill_first(
            [
                'textarea[placeholder*="message"]',
                'textarea[placeholder*="сообщение"]',
            ],
            message,
        )
        if not filled:
            return False
        await self.page.keyboard.press("Enter")
        return True

    async def is_meeting_active(self) -> bool:
        if self.page.is_closed():
            return False
        return await self._in_call_controls_visible()

    async def _in_call_controls_visible(self) -> bool:
        controls = self.page.locator(
            'button[aria-label*="leave"], '
            'button:has-text("Leave"), '
            'button:has-text("Выйти")'
        ).first
        try:
            return await controls.is_visible(timeout=700)
        except Exception:
            return False

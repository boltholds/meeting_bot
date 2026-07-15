from __future__ import annotations

import asyncio

from meeting_bot.providers.base import MeetingPageAdapter


class GoogleMeetAdapter(MeetingPageAdapter):
    async def join(self, url: str, timeout_seconds: int) -> None:
        await self.page.goto(url, wait_until="domcontentloaded")

        await self._disable_media()
        await self._fill_first(
            [
                'input[placeholder="Your name"]',
                'input[placeholder="Ваше имя"]',
                'input[aria-label="Your name"]',
                'input[aria-label="Ваше имя"]',
            ],
            self.bot_name,
        )

        clicked = await self._click_first(
            [
                'button:has-text("Ask to join")',
                'button:has-text("Join now")',
                'button:has-text("Попросить присоединиться")',
                'button:has-text("Присоединиться")',
            ]
        )
        if not clicked:
            raise RuntimeError("Google Meet join button was not found.")

        deadline = asyncio.get_running_loop().time() + timeout_seconds
        while asyncio.get_running_loop().time() < deadline:
            if await self._in_call_controls_visible():
                return
            denied = self.page.locator(
                "text=/You can't join|не разрешили присоединиться/i"
            ).first
            try:
                if await denied.is_visible(timeout=500):
                    raise RuntimeError("Google Meet admission was denied.")
            except RuntimeError:
                raise
            except Exception:
                pass
            await asyncio.sleep(2)
        raise TimeoutError("Timed out waiting for Google Meet admission.")

    async def send_chat_notice(self, message: str) -> bool:
        opened = await self._click_first(
            [
                'button[aria-label*="Chat"]',
                'button[aria-label*="чат"]',
                'button[aria-label*="messages"]',
            ]
        )
        if not opened:
            return False
        filled = await self._fill_first(
            [
                'textarea[aria-label*="message"]',
                'textarea[aria-label*="сообщение"]',
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

    async def _disable_media(self) -> None:
        await self._click_first(
            [
                'button[aria-label*="Turn off microphone"]',
                'button[aria-label*="Выключить микрофон"]',
            ]
        )
        await self._click_first(
            [
                'button[aria-label*="Turn off camera"]',
                'button[aria-label*="Выключить камеру"]',
            ]
        )

    async def _in_call_controls_visible(self) -> bool:
        controls = self.page.locator(
            'button[aria-label*="Leave call"], button[aria-label*="Выйти из встречи"]'
        ).first
        try:
            return await controls.is_visible(timeout=700)
        except Exception:
            return False

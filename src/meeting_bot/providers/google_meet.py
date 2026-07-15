from __future__ import annotations

import asyncio
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from meeting_bot.providers.base import MeetingPageAdapter


class GoogleMeetAdapter(MeetingPageAdapter):
    async def join(self, url: str, timeout_seconds: int) -> None:
        await self.page.goto(_with_ui_language(url), wait_until="domcontentloaded")
        await self.page.wait_for_timeout(1500)

        # A fresh browser in the EU can be redirected to Google's cookie
        # consent page before Meet is rendered. Rejecting optional cookies is
        # enough to continue and avoids persisting tracking consent.
        consent_closed = await self._click_first(
            [
                'button:has-text("Reject all")',
                'button:has-text("Отклонить все")',
                'button:has-text("Alles afwijzen")',
            ]
        )
        if consent_closed:
            await self.page.wait_for_timeout(1500)

        await self._disable_media()

        name_selectors = [
            'input[placeholder="Your name"]',
            'input[placeholder="Ваше имя"]',
            'input[placeholder="Je naam"]',
            'input[aria-label="Your name"]',
            'input[aria-label="Ваше имя"]',
            'input[aria-label="Je naam"]',
        ]
        join_selectors = [
            'button:has-text("Ask to join")',
            'button:has-text("Join now")',
            'button:has-text("Попросить присоединиться")',
            'button:has-text("Присоединиться")',
            'button:has-text("Vragen om deel te nemen")',
            'button:has-text("Nu deelnemen")',
            '[role="button"]:has-text("Ask to join")',
            '[role="button"]:has-text("Join now")',
        ]

        clicked = False
        render_deadline = asyncio.get_running_loop().time() + min(timeout_seconds, 15)
        while asyncio.get_running_loop().time() < render_deadline:
            await self._dismiss_media_prompt()
            await self._fill_first(name_selectors, self.bot_name)
            clicked = await self._click_first(join_selectors)
            if clicked:
                break
            await asyncio.sleep(1)

        if not clicked:
            summary = await self._page_summary()
            raise RuntimeError(f"Google Meet join button was not found. {summary}")

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

    async def _dismiss_media_prompt(self) -> None:
        await self._click_first(
            [
                'button:has-text("Continue without microphone and camera")',
                'button:has-text("Continue without camera and microphone")',
                'button:has-text("Continue without mic and camera")',
                'button:has-text("Продолжить без микрофона и камеры")',
                'button:has-text("Doorgaan zonder microfoon en camera")',
            ]
        )

    async def _page_summary(self) -> str:
        title = ""
        body = ""
        try:
            title = await self.page.title()
        except Exception:
            pass
        try:
            body = await self.page.locator("body").inner_text(timeout=1000)
        except Exception:
            pass
        visible_text = " ".join(body.split())[:1000]
        return f"url={self.page.url!r}, title={title!r}, visible_text={visible_text!r}"

    async def _in_call_controls_visible(self) -> bool:
        controls = self.page.locator(
            'button[aria-label*="Leave call"], button[aria-label*="Выйти из встречи"]'
        ).first
        try:
            return await controls.is_visible(timeout=700)
        except Exception:
            return False


def _with_ui_language(url: str) -> str:
    parts = urlsplit(url)
    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    query["hl"] = "en"
    return urlunsplit(
        (parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment)
    )

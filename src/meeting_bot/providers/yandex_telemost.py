from __future__ import annotations

import asyncio

from meeting_bot.providers.base import MeetingPageAdapter


class YandexTelemostAdapter(MeetingPageAdapter):
    """Guest browser adapter for links such as telemost.yandex.ru/j/<id>."""

    async def join(self, url: str, timeout_seconds: int) -> None:
        await self.page.goto(url, wait_until="domcontentloaded")
        await self.page.wait_for_timeout(1000)

        # A direct meeting link first offers the native application. Continue
        # in Chromium, then wait for the guest-name field. Returning visitors
        # can be sent directly to the pre-join screen, so both states are
        # handled in the same loop.
        name_selectors = [
            'input[data-testid="orb-textinput-input"]',
            'input[aria-label*="имя" i]',
            'input[aria-label*="name" i]',
        ]
        browser_selectors = [
            'button:has-text("Продолжить в браузере")',
            'button:has-text("Continue in browser")',
        ]

        name_filled = False
        render_deadline = asyncio.get_running_loop().time() + min(timeout_seconds, 20)
        while asyncio.get_running_loop().time() < render_deadline:
            failure = await self._visible_failure()
            if failure:
                raise RuntimeError(f"Yandex Telemost is unavailable: {failure}")

            name_filled = await self._fill_first(name_selectors, self.bot_name)
            if name_filled:
                break

            if await self._click_first(browser_selectors):
                await self.page.wait_for_timeout(500)
            else:
                await asyncio.sleep(0.5)

        if not name_filled:
            summary = await self._page_summary()
            raise RuntimeError(
                f"Yandex Telemost guest name field was not found. {summary}"
            )

        await self._disable_media()
        clicked = await self._retry_join(
            [
                'button[data-testid="enter-conference-button"]',
                'button:has-text("Подключиться")',
                'button:has-text("Join")',
            ],
            timeout_seconds=10,
        )
        if not clicked:
            summary = await self._page_summary()
            raise RuntimeError(f"Yandex Telemost join button was not found. {summary}")

        deadline = asyncio.get_running_loop().time() + timeout_seconds
        while asyncio.get_running_loop().time() < deadline:
            if await self._in_call_controls_visible():
                await self._dismiss_tips()
                return
            failure = await self._visible_failure()
            if failure:
                raise RuntimeError(f"Yandex Telemost admission failed: {failure}")
            # Telemost changes its in-call toolbar labels frequently. The
            # stable transition is removal of the pre-join button after the
            # accepted click. This also covers guest calls that have no lobby.
            if not await self._prejoin_visible():
                await self._dismiss_tips()
                return
            await asyncio.sleep(1)

        raise TimeoutError("Timed out waiting for Yandex Telemost admission.")

    async def send_chat_notice(self, message: str) -> bool:
        chat_selectors = [
            '[data-testid="chat-alt-button"]',
            '[role="button"]:has-text("Чат")',
            '[role="button"]:has-text("Chat")',
            'button[aria-label="Открыть чат"]',
            'button[aria-label="Open chat"]',
            'text="Чат"',
            'text="Chat"',
        ]
        field_selectors = [
            'textarea[data-testid*="message" i]',
            'textarea[placeholder*="сообщение" i]',
            'textarea[placeholder*="message" i]',
            '[contenteditable="true"][data-testid*="message" i]',
            '[contenteditable="true"][aria-label*="сообщение" i]',
            '[contenteditable="true"][aria-label*="message" i]',
            '[contenteditable="true"][role="textbox"]',
        ]
        filled = await self._open_chat_and_fill(
            chat_selectors, field_selectors, message, timeout_seconds=20
        )
        if not filled:
            summary = await self._page_summary()
            raise RuntimeError(
                f"Yandex Telemost chat message field was not found. {summary}"
            )

        await self.page.keyboard.press("Enter")
        await self.page.wait_for_timeout(500)
        return True

    async def _open_chat_and_fill(
        self,
        chat_selectors: list[str],
        field_selectors: list[str],
        message: str,
        *,
        timeout_seconds: int,
    ) -> bool:
        deadline = asyncio.get_running_loop().time() + timeout_seconds
        while asyncio.get_running_loop().time() < deadline:
            if await self._fill_first(field_selectors, message):
                return True
            if await self._fill_messenger_frame(field_selectors, message):
                return True

            if not await self._click_visible_chat(chat_selectors):
                await asyncio.sleep(0.5)
                continue

            # Telemost mounts the Messenger editor only after the visible Chat
            # button is pressed. Do not click again while the panel is opening:
            # another click would toggle it closed.
            field_deadline = min(deadline, asyncio.get_running_loop().time() + 4)
            while asyncio.get_running_loop().time() < field_deadline:
                if await self._fill_first(field_selectors, message):
                    return True
                if await self._fill_messenger_frame(field_selectors, message):
                    return True
                await asyncio.sleep(0.5)
        return False

    async def _click_visible_chat(self, selectors: list[str]) -> bool:
        # Telemost renders several responsive toolbar variants at once. The
        # first matching node can be hidden, and the visible "Чат" control is
        # not consistently a <button>, so inspect every matching node.
        for selector in selectors:
            locator = self.page.locator(selector)
            try:
                count = min(await locator.count(), 12)
            except Exception:
                continue
            for index in range(count):
                candidate = locator.nth(index)
                try:
                    if await candidate.is_visible(timeout=300):
                        await candidate.click()
                        return True
                except Exception:
                    continue
        return False

    async def is_meeting_active(self) -> bool:
        if self.page.is_closed():
            return False
        if await self._visible_failure():
            return False
        if await self._in_call_controls_visible():
            return True
        return not await self._prejoin_visible()

    async def _disable_media(self) -> None:
        # With browser permissions denied these buttons normally say "turn on"
        # and need no action. Only click controls that explicitly mean "turn
        # off" so the bot can never enter with a live microphone or camera.
        await self._click_first(
            [
                'button[data-testid="turn-off-mic-button"]',
                'button[aria-label*="Выключить микрофон" i]',
                'button[aria-label*="Turn off microphone" i]',
            ]
        )
        await self._click_first(
            [
                'button[data-testid="turn-off-camera-button"]',
                'button[aria-label*="Выключить камеру" i]',
                'button[aria-label*="Turn off camera" i]',
            ]
        )

    async def _dismiss_tips(self) -> None:
        selectors = [
            '[role="dialog"] button:has-text("Понятно")',
            '[role="dialog"] button:has-text("Got it")',
        ]
        for _ in range(4):
            if not await self._click_visible_tip(selectors):
                return
            await self.page.wait_for_timeout(150)

    async def _click_visible_tip(self, selectors: list[str]) -> bool:
        for selector in selectors:
            locator = self.page.locator(selector)
            try:
                count = min(await locator.count(), 8)
            except Exception:
                continue
            for index in range(count):
                candidate = locator.nth(index)
                try:
                    if await candidate.is_visible(timeout=300):
                        await candidate.click()
                        return True
                except Exception:
                    continue
        return False

    async def _in_call_controls_visible(self) -> bool:
        selectors = [
            'button[data-testid*="leave" i]',
            'button[data-testid*="exit" i]',
            'button[aria-label*="покинуть" i]',
            'button[aria-label*="выйти" i]',
            'button[aria-label*="leave" i]',
        ]
        for selector in selectors:
            locator = self.page.locator(selector).first
            try:
                if await locator.is_visible(timeout=500):
                    return True
            except Exception:
                continue
        return False

    async def _prejoin_visible(self) -> bool:
        locator = self.page.locator(
            'button[data-testid="enter-conference-button"]'
        ).first
        try:
            return await locator.is_visible(timeout=500)
        except Exception:
            return False

    async def _visible_failure(self) -> str | None:
        locator = self.page.locator(
            "text=/видеовстреча не найдена|встреча завершена|"
            "звонок завершен|звонок завершён|вы покинули встречу|"
            "встреча закончилась|ссылка недействительна|"
            "доступ запрещен|доступ запрещён|meeting not found|"
            "meeting has ended|call ended|you left|invalid link|access denied/i"
        ).first
        try:
            if await locator.is_visible(timeout=300):
                return " ".join((await locator.inner_text()).split())[:500]
        except Exception:
            pass
        return None

    async def _retry_click(self, selectors: list[str], *, timeout_seconds: int) -> bool:
        deadline = asyncio.get_running_loop().time() + timeout_seconds
        while asyncio.get_running_loop().time() < deadline:
            if await self._click_first(selectors):
                return True
            await asyncio.sleep(0.5)
        return False

    async def _retry_join(self, selectors: list[str], *, timeout_seconds: int) -> bool:
        # Permission-error dialogs are mounted asynchronously and can appear
        # after the join button itself. Dismiss them on every attempt so an
        # overlay cannot intercept the click.
        deadline = asyncio.get_running_loop().time() + timeout_seconds
        while asyncio.get_running_loop().time() < deadline:
            await self._dismiss_tips()
            if await self._click_first(selectors):
                return True
            await asyncio.sleep(0.5)
        return False

    async def _retry_fill(
        self,
        selectors: list[str],
        value: str,
        *,
        timeout_seconds: int,
    ) -> bool:
        deadline = asyncio.get_running_loop().time() + timeout_seconds
        while asyncio.get_running_loop().time() < deadline:
            if await self._fill_first(selectors, value):
                return True
            if await self._fill_messenger_frame(selectors, value):
                return True
            await asyncio.sleep(0.5)
        return False

    async def _fill_messenger_frame(self, selectors: list[str], value: str) -> bool:
        # Telemost embeds meeting chat as a cross-origin Yandex Messenger
        # iframe. Playwright can access it through Frame locators, but normal
        # page.locator calls do not cross the frame boundary.
        frame_selectors = [
            *selectors,
            "textarea",
            '[contenteditable="true"]',
            'input[type="text"]',
        ]
        for frame in self.page.frames:
            if frame.parent_frame is None:
                continue

            frame_url = (frame.url or "").lower()
            is_messenger = "messenger" in frame_url or "/chat" in frame_url
            if not is_messenger:
                try:
                    frame_element = await frame.frame_element()
                    marker = await frame_element.get_attribute("data-messenger-iframe")
                    is_messenger = marker is not None
                except Exception:
                    pass
            if not is_messenger:
                continue

            for selector in frame_selectors:
                locator = frame.locator(selector).first
                try:
                    if await locator.is_visible(timeout=500):
                        await locator.fill(value)
                        return True
                except Exception:
                    continue
        return False

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

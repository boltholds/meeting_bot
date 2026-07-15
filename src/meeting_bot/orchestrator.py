from __future__ import annotations

import asyncio
import logging
from contextlib import suppress

from meeting_bot.audio import AudioRecorder
from meeting_bot.models import MeetingSession, MeetingStatus
from meeting_bot.providers.factory import create_provider_adapter
from meeting_bot.settings import Settings
from meeting_bot.store import InMemoryMeetingStore
from meeting_bot.transcription import SuperTranscriberClient

logger = logging.getLogger(__name__)


class MeetingOrchestrator:
    def __init__(
        self,
        *,
        settings: Settings,
        store: InMemoryMeetingStore,
        transcription_client: SuperTranscriberClient | None = None,
    ) -> None:
        self.settings = settings
        self.store = store
        self.transcription_client = transcription_client or SuperTranscriberClient(
            base_url=settings.super_transcriber_url,
            api_key=settings.super_transcriber_api_key,
        )
        self._tasks: dict[str, asyncio.Task[None]] = {}
        self._stop_events: dict[str, asyncio.Event] = {}
        # Chromium sessions in one container share a PulseAudio sink. Keeping one
        # active session prevents audio from different meetings being mixed.
        self._capacity = asyncio.Semaphore(1)

    def start(self, session: MeetingSession) -> None:
        if session.id in self._tasks:
            raise RuntimeError("Meeting bot is already running.")
        stop_event = asyncio.Event()
        self._stop_events[session.id] = stop_event
        task = asyncio.create_task(self._run(session.id, stop_event))
        task.add_done_callback(lambda _: self._cleanup(session.id))
        self._tasks[session.id] = task

    def stop(self, meeting_id: str) -> None:
        event = self._stop_events.get(meeting_id)
        if event is None:
            raise RuntimeError("Meeting bot is not running.")
        event.set()

    def _cleanup(self, meeting_id: str) -> None:
        self._tasks.pop(meeting_id, None)
        self._stop_events.pop(meeting_id, None)

    async def _run(self, meeting_id: str, stop_event: asyncio.Event) -> None:
        async with self._capacity:
            if stop_event.is_set():
                self.store.update_status(meeting_id, MeetingStatus.STOPPED)
                return
            await self._run_with_capacity(meeting_id, stop_event)

    async def _run_with_capacity(
        self, meeting_id: str, stop_event: asyncio.Event
    ) -> None:
        session = self.store.get(meeting_id)
        session_dir = self.settings.data_dir / "meetings" / meeting_id
        recorder = AudioRecorder(
            pulse_sink=self.settings.pulse_sink,
            segment_seconds=self.settings.ffmpeg_segment_seconds,
        )

        try:
            self.store.update_status(meeting_id, MeetingStatus.JOINING)
            from playwright.async_api import async_playwright

            async with async_playwright() as playwright:
                browser = None
                context = None
                try:
                    browser = await playwright.chromium.launch(
                        headless=False,
                        args=[
                            "--autoplay-policy=no-user-gesture-required",
                            "--disable-dev-shm-usage",
                            "--no-sandbox",
                        ],
                    )
                    context = await browser.new_context(
                        permissions=[],
                        viewport={"width": 1280, "height": 720},
                    )
                    page = await context.new_page()
                    adapter = create_provider_adapter(
                        session.provider, page, bot_name=session.bot_name
                    )
                    await adapter.join(session.url, self.settings.join_timeout_seconds)

                    # Notify before recording. A failed chat notice is fatal so the
                    # service never silently records a meeting.
                    notice_sent = await adapter.send_chat_notice(
                        self.settings.recording_notice
                    )
                    if not notice_sent:
                        raise RuntimeError(
                            "Could not post the recording notice in chat."
                        )

                    await recorder.start(session_dir)
                    self.store.update_status(meeting_id, MeetingStatus.RECORDING)

                    while not stop_event.is_set() and await adapter.is_meeting_active():
                        await asyncio.sleep(3)

                    recording = await recorder.stop()
                finally:
                    if context is not None:
                        with suppress(Exception):
                            await context.close()
                    if browser is not None:
                        with suppress(Exception):
                            await browser.close()

            self.store.update_status(
                meeting_id,
                MeetingStatus.PROCESSING,
                recording_path=str(recording),
            )
            job_id = await self.transcription_client.submit(
                recording,
                language=session.language,
                analyze=session.analyze,
                min_speakers=session.min_speakers,
                max_speakers=session.max_speakers,
            )
            self.store.update_status(
                meeting_id,
                MeetingStatus.COMPLETED,
                transcription_job_id=job_id,
            )
        except Exception as exc:
            logger.exception("Meeting bot %s failed", meeting_id)
            await recorder.abort()
            self.store.update_status(
                meeting_id,
                MeetingStatus.FAILED,
                error=f"{type(exc).__name__}: {exc}",
            )

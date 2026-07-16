from __future__ import annotations

from pathlib import Path
from secrets import compare_digest

from fastapi import Depends, FastAPI, Header, HTTPException, status
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from meeting_bot.models import (
    CreateMeetingRequest,
    MeetingSession,
    MeetingStatus,
    provider_from_url,
)
from meeting_bot.orchestrator import MeetingOrchestrator
from meeting_bot.settings import Settings, get_settings
from meeting_bot.store import InMemoryMeetingStore, MeetingNotFoundError


def create_app(
    *,
    settings: Settings | None = None,
    store: InMemoryMeetingStore | None = None,
    orchestrator: MeetingOrchestrator | None = None,
) -> FastAPI:
    config = settings or get_settings()
    meeting_store = store or InMemoryMeetingStore()
    meeting_orchestrator = orchestrator or MeetingOrchestrator(
        settings=config, store=meeting_store
    )
    app = FastAPI(title="Meeting Bot API", version="0.1.0")
    static_dir = Path(__file__).with_name("static")
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

    def require_api_key(x_api_key: str | None = Header(default=None)) -> None:
        valid = bool(x_api_key) and compare_digest(x_api_key or "", config.api_key)
        if config.api_key and not valid:
            raise HTTPException(status_code=401, detail="Invalid API key.")

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/", include_in_schema=False)
    def dashboard() -> FileResponse:
        return FileResponse(static_dir / "index.html")

    @app.get(
        "/v1/meetings",
        response_model=list[MeetingSession],
        dependencies=[Depends(require_api_key)],
    )
    def list_meetings() -> list[MeetingSession]:
        return meeting_store.list()

    @app.post(
        "/v1/meetings",
        response_model=MeetingSession,
        status_code=status.HTTP_202_ACCEPTED,
        dependencies=[Depends(require_api_key)],
    )
    async def create_meeting(request: CreateMeetingRequest) -> MeetingSession:
        try:
            request.validate_speaker_bounds()
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

        min_speakers = (
            request.min_speakers
            if request.min_speakers is not None
            else config.transcription_min_speakers
        )
        max_speakers = (
            request.max_speakers
            if request.max_speakers is not None
            else config.transcription_max_speakers
        )
        if (
            min_speakers is not None
            and max_speakers is not None
            and min_speakers > max_speakers
        ):
            raise HTTPException(
                status_code=422,
                detail="min_speakers must not exceed max_speakers.",
            )

        session = MeetingSession(
            url=request.url,
            provider=provider_from_url(request.url),
            title=request.title,
            bot_name=request.bot_name or config.bot_name,
            language=request.language or config.transcription_language,
            analyze=(
                request.analyze
                if request.analyze is not None
                else config.transcription_analyze
            ),
            min_speakers=min_speakers,
            max_speakers=max_speakers,
        )
        meeting_store.create(session)
        meeting_orchestrator.start(session)
        return meeting_store.get(session.id)

    @app.get(
        "/v1/meetings/{meeting_id}",
        response_model=MeetingSession,
        dependencies=[Depends(require_api_key)],
    )
    def get_meeting(meeting_id: str) -> MeetingSession:
        try:
            return meeting_store.get(meeting_id)
        except MeetingNotFoundError as exc:
            raise HTTPException(status_code=404, detail="Meeting not found.") from exc

    @app.post(
        "/v1/meetings/{meeting_id}/stop",
        response_model=MeetingSession,
        dependencies=[Depends(require_api_key)],
    )
    def stop_meeting(meeting_id: str) -> MeetingSession:
        try:
            session = meeting_store.get(meeting_id)
        except MeetingNotFoundError as exc:
            raise HTTPException(status_code=404, detail="Meeting not found.") from exc
        if session.status not in {
            MeetingStatus.QUEUED,
            MeetingStatus.JOINING,
            MeetingStatus.WAITING_ROOM,
            MeetingStatus.RECORDING,
        }:
            raise HTTPException(
                status_code=409, detail="Meeting bot cannot be stopped now."
            )
        try:
            meeting_orchestrator.stop(meeting_id)
        except RuntimeError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        return meeting_store.get(meeting_id)

    return app


app = create_app()

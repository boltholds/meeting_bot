from __future__ import annotations

from threading import RLock

from meeting_bot.models import MeetingSession, MeetingStatus, utc_now


class MeetingNotFoundError(KeyError):
    pass


class InMemoryMeetingStore:
    def __init__(self) -> None:
        self._meetings: dict[str, MeetingSession] = {}
        self._lock = RLock()

    def create(self, session: MeetingSession) -> MeetingSession:
        with self._lock:
            self._meetings[session.id] = session
        return session.model_copy(deep=True)

    def get(self, meeting_id: str) -> MeetingSession:
        with self._lock:
            session = self._require(meeting_id)
            return session.model_copy(deep=True)

    def list(self) -> list[MeetingSession]:
        with self._lock:
            sessions = sorted(
                self._meetings.values(),
                key=lambda session: session.created_at,
                reverse=True,
            )
            return [session.model_copy(deep=True) for session in sessions]

    def update_status(
        self,
        meeting_id: str,
        status: MeetingStatus,
        *,
        error: str | None = None,
        recording_path: str | None = None,
        transcription_job_id: str | None = None,
    ) -> MeetingSession:
        with self._lock:
            session = self._require(meeting_id)
            session.status = status
            session.error = error
            if status == MeetingStatus.RECORDING and session.started_at is None:
                session.started_at = utc_now()
            if status in {
                MeetingStatus.COMPLETED,
                MeetingStatus.STOPPED,
                MeetingStatus.FAILED,
            }:
                session.completed_at = utc_now()
            if recording_path is not None:
                session.recording_path = recording_path
            if transcription_job_id is not None:
                session.transcription_job_id = transcription_job_id
            return session.model_copy(deep=True)

    def _require(self, meeting_id: str) -> MeetingSession:
        session = self._meetings.get(meeting_id)
        if session is None:
            raise MeetingNotFoundError(meeting_id)
        return session

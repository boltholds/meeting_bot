from datetime import timedelta

from meeting_bot.models import MeetingProvider, MeetingSession, MeetingStatus
from meeting_bot.store import InMemoryMeetingStore


def test_meeting_lifecycle() -> None:
    store = InMemoryMeetingStore()
    meeting = store.create(
        MeetingSession(
            url="https://meet.google.com/abc-defg-hij",
            provider=MeetingProvider.GOOGLE_MEET,
            bot_name="Recorder",
            language="ru",
            analyze=True,
        )
    )

    assert meeting.status == MeetingStatus.QUEUED
    assert (
        store.update_status(meeting.id, MeetingStatus.JOINING).status
        == MeetingStatus.JOINING
    )
    recording = store.update_status(meeting.id, MeetingStatus.RECORDING)
    assert recording.started_at is not None
    completed = store.update_status(
        meeting.id,
        MeetingStatus.COMPLETED,
        recording_path="/data/meeting.flac",
        transcription_job_id="job-1",
    )
    assert completed.completed_at is not None
    assert completed.transcription_job_id == "job-1"


def test_list_meetings_returns_newest_first() -> None:
    store = InMemoryMeetingStore()
    first = MeetingSession(
        url="https://meet.google.com/abc-defg-hij",
        provider=MeetingProvider.GOOGLE_MEET,
        bot_name="Recorder",
        language="ru",
        analyze=True,
    )
    second = first.model_copy(update={"id": "newer"}, deep=True)
    second.created_at = first.created_at + timedelta(microseconds=1)
    store.create(first)
    store.create(second)

    assert [meeting.id for meeting in store.list()] == ["newer", first.id]

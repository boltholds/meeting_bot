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

from fastapi.testclient import TestClient

from meeting_bot.app import create_app
from meeting_bot.settings import Settings
from meeting_bot.store import InMemoryMeetingStore


class FakeOrchestrator:
    def __init__(self) -> None:
        self.started = []
        self.stopped = []

    def start(self, session) -> None:
        self.started.append(session)

    def stop(self, meeting_id: str) -> None:
        self.stopped.append(meeting_id)


def test_create_meeting_requires_key_and_starts_bot(tmp_path) -> None:
    store = InMemoryMeetingStore()
    orchestrator = FakeOrchestrator()
    app = create_app(
        settings=Settings(api_key="secret", data_dir=tmp_path),
        store=store,
        orchestrator=orchestrator,
    )
    client = TestClient(app)

    unauthorized = client.post(
        "/v1/meetings",
        json={"url": "https://meet.google.com/abc-defg-hij"},
    )
    assert unauthorized.status_code == 401

    response = client.post(
        "/v1/meetings",
        headers={"X-API-Key": "secret"},
        json={"url": "https://meet.google.com/abc-defg-hij"},
    )
    assert response.status_code == 202
    assert response.json()["provider"] == "google_meet"
    assert len(orchestrator.started) == 1


def test_create_meeting_rejects_inverted_speaker_bounds(tmp_path) -> None:
    app = create_app(
        settings=Settings(data_dir=tmp_path),
        store=InMemoryMeetingStore(),
        orchestrator=FakeOrchestrator(),
    )
    response = TestClient(app).post(
        "/v1/meetings",
        json={
            "url": "https://meet.google.com/abc-defg-hij",
            "min_speakers": 5,
            "max_speakers": 2,
        },
    )
    assert response.status_code == 422


def test_create_meeting_validates_effective_default_bounds(tmp_path) -> None:
    app = create_app(
        settings=Settings(
            data_dir=tmp_path,
            transcription_min_speakers=1,
            transcription_max_speakers=10,
        ),
        store=InMemoryMeetingStore(),
        orchestrator=FakeOrchestrator(),
    )
    response = TestClient(app).post(
        "/v1/meetings",
        json={
            "url": "https://meet.google.com/abc-defg-hij",
            "min_speakers": 20,
        },
    )
    assert response.status_code == 422

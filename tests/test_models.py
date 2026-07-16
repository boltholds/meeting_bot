import pytest
from pydantic import ValidationError

from meeting_bot.models import (
    CreateMeetingRequest,
    MeetingProvider,
    provider_from_url,
)


@pytest.mark.parametrize(
    ("url", "provider"),
    [
        ("https://meet.google.com/abc-defg-hij", MeetingProvider.GOOGLE_MEET),
        ("https://us05web.zoom.us/j/123", MeetingProvider.ZOOM),
        (
            "https://telemost.yandex.ru/j/12345678901234",
            MeetingProvider.YANDEX_TELEMOST,
        ),
        (
            "https://telemost.yandex.com/j/12345678901234?lang=en",
            MeetingProvider.YANDEX_TELEMOST,
        ),
    ],
)
def test_provider_from_url(url: str, provider: MeetingProvider) -> None:
    assert provider_from_url(url) == provider


@pytest.mark.parametrize(
    "url",
    [
        "http://meet.google.com/abc-defg-hij",
        "https://meet.google.com.evil.example/abc",
        "https://user:password@meet.google.com/abc",
        "https://meet.google.com:8443/abc",
        "https://telemost.yandex.ru/",
        "https://telemost.yandex.ru/j/not-a-number",
        "https://telemost.yandex.ru.evil.example/j/12345678901234",
        "https://example.com/meeting",
    ],
)
def test_rejects_unsafe_or_unsupported_url(url: str) -> None:
    with pytest.raises((ValueError, ValidationError)):
        CreateMeetingRequest(url=url)


def test_rejects_inverted_speaker_bounds() -> None:
    request = CreateMeetingRequest(
        url="https://meet.google.com/abc-defg-hij",
        min_speakers=5,
        max_speakers=2,
    )
    with pytest.raises(ValueError, match="must not exceed"):
        request.validate_speaker_bounds()

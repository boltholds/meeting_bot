from meeting_bot.providers.google_meet import _with_ui_language


def test_google_meet_url_forces_english_and_preserves_query() -> None:
    result = _with_ui_language("https://meet.google.com/abc-defg-hij?authuser=1&hl=nl")

    assert result == ("https://meet.google.com/abc-defg-hij?authuser=1&hl=en")

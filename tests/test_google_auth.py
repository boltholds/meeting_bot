from meeting_bot.google_auth import build_parser


def test_google_auth_cli_defaults() -> None:
    args = build_parser().parse_args([])

    assert str(args.output).replace("\\", "/") == "auth/google.json"
    assert str(args.profile_dir).replace("\\", "/") == ("auth/google-chrome-profile")
    assert args.browser == "chrome"
    assert args.port == 9222


def test_google_auth_cli_accepts_channel_as_compatibility_alias() -> None:
    args = build_parser().parse_args(["--channel", "msedge"])

    assert args.browser == "msedge"

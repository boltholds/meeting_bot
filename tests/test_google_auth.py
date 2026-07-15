from meeting_bot.google_auth import build_parser


def test_google_auth_cli_defaults() -> None:
    args = build_parser().parse_args([])

    assert str(args.output).replace("\\", "/") == "auth/google.json"
    assert args.channel == "chrome"

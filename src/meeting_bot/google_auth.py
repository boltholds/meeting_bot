from __future__ import annotations

import argparse
from pathlib import Path

from playwright.sync_api import sync_playwright


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Create a Playwright auth state for a Google Meet bot account."
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("auth/google.json"),
        help="Where to save the auth state (default: auth/google.json).",
    )
    parser.add_argument(
        "--channel",
        choices=("chrome", "msedge", "chromium"),
        default="chrome",
        help="Local browser channel used for the interactive login.",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    output: Path = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as playwright:
        launch_options: dict[str, object] = {"headless": False}
        if args.channel != "chromium":
            launch_options["channel"] = args.channel

        browser = playwright.chromium.launch(**launch_options)
        context = browser.new_context(locale="en-US")
        page = context.new_page()
        page.goto("https://accounts.google.com/", wait_until="domcontentloaded")

        print(
            "Sign in to the dedicated Google bot account in the opened browser.\n"
            "Complete any two-factor authentication, then press Enter here."
        )
        input()

        page.goto("https://meet.google.com/?hl=en", wait_until="domcontentloaded")
        cookies = context.cookies("https://google.com")
        authenticated = any(
            cookie["name"] in {"SID", "SAPISID", "__Secure-1PSID", "__Secure-3PSID"}
            for cookie in cookies
        )
        if not authenticated:
            browser.close()
            raise RuntimeError(
                "Google login cookies were not found. Complete sign-in before "
                "pressing Enter."
            )

        context.storage_state(path=str(output))
        browser.close()

    print(f"Google auth state saved to {output}")


if __name__ == "__main__":
    main()

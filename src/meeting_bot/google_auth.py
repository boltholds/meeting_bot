from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import time
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

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
        "--browser",
        "--channel",
        dest="browser",
        choices=("chrome", "msedge"),
        default="chrome",
        help="Installed browser used for the interactive login.",
    )
    parser.add_argument(
        "--profile-dir",
        type=Path,
        default=Path("auth/google-chrome-profile"),
        help="Dedicated browser profile used only by the bot account.",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=9222,
        help="Loopback Chrome DevTools port (default: 9222).",
    )
    return parser


def find_browser_executable(browser: str) -> Path:
    executable_names = {
        "chrome": ("chrome", "google-chrome", "google-chrome-stable"),
        "msedge": ("msedge", "microsoft-edge", "microsoft-edge-stable"),
    }[browser]
    for name in executable_names:
        resolved = shutil.which(name)
        if resolved:
            return Path(resolved)

    candidates: list[Path] = []
    if os.name == "nt":
        roots = [
            os.environ.get("PROGRAMFILES"),
            os.environ.get("PROGRAMFILES(X86)"),
            os.environ.get("LOCALAPPDATA"),
        ]
        relative = (
            Path("Google/Chrome/Application/chrome.exe")
            if browser == "chrome"
            else Path("Microsoft/Edge/Application/msedge.exe")
        )
        candidates.extend(Path(root) / relative for root in roots if root)
    elif browser == "chrome":
        candidates.extend(
            [
                Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
                Path("/usr/bin/google-chrome"),
            ]
        )
    else:
        candidates.extend(
            [
                Path("/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge"),
                Path("/usr/bin/microsoft-edge"),
            ]
        )

    for candidate in candidates:
        if candidate.is_file():
            return candidate
    raise FileNotFoundError(
        f"Installed {browser} executable was not found. Try --browser msedge."
    )


def wait_for_cdp(port: int, timeout_seconds: float = 20) -> None:
    endpoint = f"http://127.0.0.1:{port}/json/version"
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        try:
            with urlopen(endpoint, timeout=0.5):
                return
        except (OSError, URLError):
            time.sleep(0.2)
    raise TimeoutError(f"Browser debugging endpoint did not start on 127.0.0.1:{port}.")


def main() -> None:
    args = build_parser().parse_args()
    output: Path = args.output.resolve()
    profile_dir: Path = args.profile_dir.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    profile_dir.mkdir(parents=True, exist_ok=True)
    executable = find_browser_executable(args.browser)

    subprocess.Popen(
        [
            str(executable),
            f"--remote-debugging-port={args.port}",
            "--remote-debugging-address=127.0.0.1",
            f"--user-data-dir={profile_dir}",
            "--no-first-run",
            "--no-default-browser-check",
            "https://accounts.google.com/",
        ]
    )
    wait_for_cdp(args.port)

    print(
        "A regular browser was opened with a dedicated bot profile.\n"
        "Sign in to the Google bot account and complete two-factor "
        "authentication.\n"
        "Do not close the browser; press Enter here after sign-in is complete."
    )
    input()

    with sync_playwright() as playwright:
        browser = playwright.chromium.connect_over_cdp(f"http://127.0.0.1:{args.port}")
        if not browser.contexts:
            browser.close()
            raise RuntimeError("The browser profile context was not found.")
        context = browser.contexts[0]
        cookies = context.cookies()
        authenticated = any(
            cookie["name"] in {"SID", "SAPISID", "__Secure-1PSID", "__Secure-3PSID"}
            and cookie["domain"].endswith("google.com")
            for cookie in cookies
        )
        if not authenticated:
            browser.close()
            raise RuntimeError(
                "Google login cookies were not found. Complete sign-in before "
                "pressing Enter."
            )

        context.storage_state(path=str(output), indexed_db=True)
        browser.close()

    print(f"Google auth state saved to {output}")


if __name__ == "__main__":
    main()

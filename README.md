# Meeting Bot

Visible audio recording bot for Google Meet, Zoom and Yandex Telemost. The bot
joins through a real Chromium session, posts a recording notice in chat,
captures the browser's PulseAudio output, produces a crash-tolerant FLAC
recording and submits it to Super Transcriber.

## Current scope

- Google Meet guest join through Playwright;
- Zoom guest join when **Join from browser** is enabled by the host;
- Yandex Telemost guest join for `telemost.yandex.ru/j/<meeting-number>` links;
- camera and microphone are not granted to Chromium;
- one active browser session per container, preventing cross-meeting audio mix;
- five-minute WAV chunks merged into 16 kHz mono FLAC;
- upload to the asynchronous Super Transcriber API;
- API-key authentication for team use.

The provider selectors are intentionally isolated in `meeting_bot/providers`.
They need integration tests against your own Meet and Zoom tenant because both
platforms change their UI and can show account-specific consent screens.

## Run

1. Copy `.env.example` to `.env` and set both API keys.
2. Make sure `SUPER_TRANSCRIBER_URL` is reachable from the container.
3. Start the bot:

```bash
docker compose up --build
```

Open `http://localhost:8080` for the web console. Paste a Google Meet, Zoom or
Yandex Telemost invitation URL, enter the API key from `.env`, and use the live
session list to monitor or stop the bot. The key is kept in browser
`sessionStorage` and is cleared when the browser session ends.

When a Google Meet URL is detected, the console shows the bot account status
and an **Authorize** helper with the exact host commands. Zoom and Yandex
Telemost are marked as guest providers and do not require an account.

### Google bot account

Google Meet can reject anonymous third-party bots before they can ask to join.
For reliable access, use a dedicated Google account for the bot and invite that
account to the Calendar event.

Create its Playwright auth state once on the host machine:

```bash
uv sync
uv run meeting-bot-auth-google --output auth/google.json --channel chrome
```

Complete the interactive Google login in the opened browser. Then set this in
`.env` and recreate the container:

The command starts a regular installed Chrome with a separate profile and only
attaches through the local DevTools port after you confirm that login is done.
This avoids Google's rejection of sign-in from a Playwright-launched browser.

```env
GOOGLE_STORAGE_STATE=/auth/google.json
```

```bash
docker compose up --build --force-recreate
```

The `auth` directory is excluded from Git and the Docker build context. Treat
`auth/google.json` as a password: never commit or share it.

Create a bot:

```bash
curl -X POST http://localhost:8080/v1/meetings \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_KEY" \
  -d '{
    "url": "https://meet.google.com/abc-defg-hij",
    "title": "Командный созвон",
    "language": "ru",
    "min_speakers": 2,
    "max_speakers": 6
  }'
```

Poll `GET /v1/meetings/{id}`. Stop an active recording with
`POST /v1/meetings/{id}/stop`.

For Yandex Telemost, use the same endpoint with a Telemost invitation URL:

```bash
curl -X POST http://localhost:8080/v1/meetings \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_KEY" \
  -d '{
    "url": "https://telemost.yandex.ru/j/12345678901234",
    "title": "Командный созвон в Телемосте",
    "language": "ru"
  }'
```

Telemost does not require a Yandex account for invited guests. The adapter
chooses **Continue in browser**, enters the visible bot name and keeps the
microphone and camera disabled. As with the other browser adapters, selectors
should be integration-tested against a real team meeting after UI updates.

## Consent behavior

The recording starts only after admission and a successful chat notice. If chat
is disabled or the notice cannot be sent, the session fails without recording.
The bot name also includes an explicit recording marker. Keep the default
behavior when the service is used outside controlled team meetings.

## Path toward SaaS

The API contract already carries provider, lifecycle, transcription job ID and
speaker limits. Replace these MVP components independently:

- `InMemoryMeetingStore` -> PostgreSQL;
- in-process `asyncio.Task` -> durable queue and one-container-per-meeting scheduler;
- local `/data` -> S3-compatible storage;
- one API key -> users, workspaces and per-tenant quotas;
- browser Zoom adapter -> Zoom Meeting SDK;
- browser Google adapter -> Meet Media API when generally available.

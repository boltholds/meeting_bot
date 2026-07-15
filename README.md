# Meeting Bot

Visible audio recording bot for Google Meet and Zoom. The bot joins through a
real Chromium session, posts a recording notice in chat, captures the browser's
PulseAudio output, produces a crash-tolerant FLAC recording and submits it to
Super Transcriber.

## Current scope

- Google Meet guest join through Playwright;
- Zoom guest join when **Join from browser** is enabled by the host;
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

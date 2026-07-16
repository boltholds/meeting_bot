# Product backlog

## Parse meeting chats

**Status:** planned

Collect chat messages from Google Meet, Zoom and Yandex Telemost while the bot
is present, then include them in meeting artifacts alongside the audio
transcript.

MVP scope:

- capture message text, sender display name and platform timestamp;
- preserve message ordering and provider metadata;
- store chat as JSON and readable Markdown artifacts;
- align messages with the recording timeline where possible;
- pass chat context to the final summary and action-item analysis;
- show chat collection status and artifact links in the web console;
- handle unavailable or disabled chat without interrupting audio recording;
- document participant notice, retention and deletion requirements.

Implementation notes:

- keep provider-specific DOM selectors inside the existing adapters;
- deduplicate messages observed during periodic polling;
- never collect chat history from before the bot joined unless explicitly
  supported and disclosed;
- add fixtures and integration tests for each provider before enabling it by
  default.

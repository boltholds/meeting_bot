from __future__ import annotations

from pathlib import Path

import httpx


class SuperTranscriberClient:
    def __init__(
        self, *, base_url: str, api_key: str, timeout_seconds: int = 120
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = httpx.Timeout(timeout_seconds, connect=15)

    async def submit(
        self,
        audio_path: Path,
        *,
        language: str,
        analyze: bool,
        min_speakers: int | None,
        max_speakers: int | None,
    ) -> str:
        headers = {"X-API-Key": self.api_key} if self.api_key else {}
        form = {
            "language": language,
            "analyze": str(analyze).lower(),
        }
        if min_speakers is not None:
            form["min_speakers"] = str(min_speakers)
        if max_speakers is not None:
            form["max_speakers"] = str(max_speakers)

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            with audio_path.open("rb") as audio:
                response = await client.post(
                    f"{self.base_url}/v1/transcriptions",
                    headers=headers,
                    data=form,
                    files={"audio": (audio_path.name, audio, "audio/flac")},
                )
        response.raise_for_status()
        payload = response.json()
        job_id = payload.get("id")
        if not isinstance(job_id, str) or not job_id:
            raise RuntimeError("Super Transcriber returned no job id.")
        return job_id

from __future__ import annotations

import asyncio
import signal
from pathlib import Path


def build_ffmpeg_command(
    *, pulse_sink: str, output_pattern: Path, segment_seconds: int
) -> list[str]:
    return [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "warning",
        "-f",
        "pulse",
        "-i",
        f"{pulse_sink}.monitor",
        "-ac",
        "1",
        "-ar",
        "16000",
        "-c:a",
        "pcm_s16le",
        "-f",
        "segment",
        "-segment_time",
        str(segment_seconds),
        "-reset_timestamps",
        "1",
        str(output_pattern),
    ]


class AudioRecorder:
    def __init__(self, *, pulse_sink: str, segment_seconds: int) -> None:
        self.pulse_sink = pulse_sink
        self.segment_seconds = segment_seconds
        self._process: asyncio.subprocess.Process | None = None
        self._session_dir: Path | None = None
        self._stderr_file = None

    async def start(self, session_dir: Path) -> None:
        if self._process is not None:
            raise RuntimeError("Audio recorder is already running.")
        session_dir.mkdir(parents=True, exist_ok=True)
        self._session_dir = session_dir
        self._stderr_file = (session_dir / "ffmpeg.log").open("ab")
        command = build_ffmpeg_command(
            pulse_sink=self.pulse_sink,
            output_pattern=session_dir / "chunk-%05d.wav",
            segment_seconds=self.segment_seconds,
        )
        self._process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=self._stderr_file,
        )

    async def stop(self) -> Path:
        if self._process is None or self._session_dir is None:
            raise RuntimeError("Audio recorder is not running.")

        process = self._process
        process.send_signal(signal.SIGINT)
        try:
            await asyncio.wait_for(process.wait(), timeout=15)
        except TimeoutError:
            process.kill()
            await process.wait()
        finally:
            self._process = None
            if self._stderr_file is not None:
                self._stderr_file.close()
                self._stderr_file = None

        chunks = sorted(self._session_dir.glob("chunk-*.wav"))
        if not chunks:
            raise RuntimeError("FFmpeg did not produce audio chunks.")

        concat_file = self._session_dir / "concat.txt"
        concat_file.write_text(
            "\n".join(f"file '{path.name}'" for path in chunks),
            encoding="utf-8",
        )
        output = self._session_dir / "meeting.flac"
        merge = await asyncio.create_subprocess_exec(
            "ffmpeg",
            "-y",
            "-hide_banner",
            "-loglevel",
            "warning",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(concat_file),
            "-ac",
            "1",
            "-ar",
            "16000",
            "-c:a",
            "flac",
            str(output),
            cwd=self._session_dir,
        )
        if await merge.wait() != 0 or not output.is_file():
            raise RuntimeError("Could not merge recorded audio chunks.")
        return output

    async def abort(self) -> None:
        if self._process is None:
            return
        self._process.kill()
        await self._process.wait()
        self._process = None
        if self._stderr_file is not None:
            self._stderr_file.close()
            self._stderr_file = None

from pathlib import Path

from meeting_bot.audio import build_ffmpeg_command


def test_ffmpeg_records_pulse_monitor_to_segmented_mono_audio() -> None:
    command = build_ffmpeg_command(
        pulse_sink="meeting_output",
        output_pattern=Path("/data/chunk-%05d.wav"),
        segment_seconds=300,
    )

    assert "meeting_output.monitor" in command
    assert command[command.index("-ac") + 1] == "1"
    assert command[command.index("-ar") + 1] == "16000"
    assert command[command.index("-segment_time") + 1] == "300"

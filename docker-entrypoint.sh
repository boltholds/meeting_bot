#!/bin/sh
set -eu

mkdir -p "${XDG_RUNTIME_DIR:-/tmp/runtime-appuser}"
pulseaudio --start --exit-idle-time=-1 --log-target=stderr

if ! pactl list short sinks | grep -q "${PULSE_SINK:-meeting_output}"; then
  pactl load-module module-null-sink \
    sink_name="${PULSE_SINK:-meeting_output}" \
    sink_properties=device.description=MeetingOutput >/dev/null
fi
pactl set-default-sink "${PULSE_SINK:-meeting_output}"

Xvfb :99 -screen 0 1280x720x24 -nolisten tcp &
sleep 1

exec "$@"

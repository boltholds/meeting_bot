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
xvfb_pid=$!

attempt=0
while [ ! -S /tmp/.X11-unix/X99 ]; do
  if ! kill -0 "$xvfb_pid" 2>/dev/null; then
    echo "Xvfb failed to start on display ${DISPLAY}" >&2
    wait "$xvfb_pid" || true
    exit 1
  fi
  attempt=$((attempt + 1))
  if [ "$attempt" -ge 50 ]; then
    echo "Timed out waiting for Xvfb on display ${DISPLAY}" >&2
    exit 1
  fi
  sleep 0.1
done

exec "$@"

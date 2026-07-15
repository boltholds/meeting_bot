FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DISPLAY=:99 \
    XDG_RUNTIME_DIR=/tmp/runtime-appuser \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ffmpeg \
        pulseaudio \
        pulseaudio-utils \
        xvfb \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md /app/
COPY src /app/src
RUN pip install --no-cache-dir . \
    && mkdir -p /ms-playwright \
    && playwright install --with-deps chromium \
    && useradd --create-home --uid 10001 appuser \
    && mkdir -p /data /tmp/runtime-appuser \
    && chmod 700 /tmp/runtime-appuser \
    && chmod -R a+rX /ms-playwright \
    && chown -R appuser:appuser /app /data /tmp/runtime-appuser

COPY docker-entrypoint.sh /usr/local/bin/meeting-bot-entrypoint
RUN chmod +x /usr/local/bin/meeting-bot-entrypoint

USER appuser
EXPOSE 8080

ENTRYPOINT ["meeting-bot-entrypoint"]
CMD ["uvicorn", "meeting_bot.app:app", "--host", "0.0.0.0", "--port", "8080"]

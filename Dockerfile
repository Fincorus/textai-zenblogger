## Multi-stage Dockerfile with Playwright (Chromium)
## RU: В контейнере ставим Playwright + Chromium, затем запускаем бота.
## EN: Install Playwright + Chromium and run the bot.

FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

FROM base AS builder
RUN pip install --upgrade pip
COPY requirements.txt /app/requirements.txt
RUN pip wheel --wheel-dir /wheels -r /app/requirements.txt

FROM base AS runtime
COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir /wheels/* \
    && playwright install --with-deps chromium

COPY . /app

EXPOSE 8080

CMD ["python", "-m", "bot.main"]


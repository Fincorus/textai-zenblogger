# textai-zenblogger

RU/EN: Telegram-бот (aiogram 3.x), который **генерирует SEO‑статьи на русском** через LLM (по умолчанию xAI Grok) и публикует их в **Telegram‑канал** и/или **Яндекс.Дзен** (через Playwright + cookies).

## Возможности / Features

- **Telegram Bot (aiogram 3.x)**:
  - **Только приватный чат с админом** (проверка `ADMIN_TELEGRAM_ID`).
  - `/generate <тема>` или интерактивный выбор темы.
  - Генерация статьи (HTML для Telegram/Дзен), preview + кнопки:
    - «Опубликовать в TG‑канал»
    - «Опубликовать в Дзен»
    - «Оба»
    - «Отмена»
- **LLM интеграция (configurable)**:
  - По умолчанию: **xAI Grok** через `litellm` (например, `grok-4` или `grok-4.1-fast`).
  - Fallback цепочка: OpenAI / Google Gemini / Groq / HuggingFace (заполняется в `.env`).
- **Публикация в Дзен**:
  - У Дзен нет публичного API → **Playwright headless + cookies**.
  - Скриншоты ошибок сохраняются в `artifacts/`.
- **Планировщик**:
  - APScheduler: по cron может автоматически генерировать и публиковать статьи.
- **Docker**:
  - Multi-stage, Playwright + Chromium внутри контейнера.

## Структура проекта / Project structure

```
textai-zenblogger/
├── bot/
│   ├── __init__.py
│   ├── main.py
│   ├── handlers.py
│   ├── llm.py
│   ├── tg_publisher.py
│   └── dzen_publisher.py
├── utils/
│   ├── __init__.py
│   ├── article_generator.py
│   ├── image.py
│   └── scheduler.py
├── config/
│   ├── __init__.py
│   ├── settings.py
│   └── prompts.py
├── .env.example
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── README.md
└── .gitignore
```

## Быстрый старт (локально) / Quick start (local)

### 1) Установка / Install

```bash
cd textai-zenblogger
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
# source .venv/bin/activate

pip install -r requirements.txt
playwright install chromium
```

### 2) Настройка .env / Configure .env

Скопируйте `.env.example` → `.env` и заполните:

- `BOT_TOKEN` — токен бота из BotFather.
- `ADMIN_TELEGRAM_ID` — ваш Telegram user id.
- `TG_CHANNEL_ID` — `@channel` или `-100...` id канала.
- `LLM_PROVIDER`, `LLM_MODEL` и ключи API.

### 3) Запуск / Run

```bash
python -m bot.main
```

В Telegram напишите боту в личку:

- `/generate Как выбрать ноутбук для работы в 2026`
- или `/generate` → выбрать тему кнопкой

## Grok (xAI) API ключ и кредиты (2026) / Grok API key & credits (2026)

RU:
- Зайдите в аккаунт xAI и создайте **API key**.
- В 2026 году xAI периодически предлагает **$25 стартовых кредитов** и **до $150/мес** при включённом data sharing (условия могут меняться).
- Запишите ключ в `.env` как `XAI_API_KEY=...` и выставьте:
  - `LLM_PROVIDER=xai`
  - `LLM_MODEL=grok-4` или `grok-4.1-fast`

EN:
- Create an xAI API key in your xAI account.
- In 2026, xAI may provide **$25 starter credits** and **up to $150/month** via data sharing (terms can change).
- Put it into `.env` as `XAI_API_KEY=...`, set `LLM_PROVIDER=xai`.

## Экспорт cookies для Дзен / Export Dzen cookies

RU (общий подход):
1) Откройте `dzen.ru` в браузере и залогиньтесь.
2) Экспортируйте cookies в JSON.
   - Вариант A: расширение **Get cookies.txt** / cookies exporter
   - Вариант B: DevTools → Application/Storage → Cookies → export
3) Сохраните файл как `cookies_dzen.json` в корне проекта.
4) В `.env` укажите `DZEN_COOKIES_PATH=cookies_dzen.json`.

EN:
1) Login to `dzen.ru` in your browser.
2) Export cookies to JSON (extension or DevTools).
3) Save as `cookies_dzen.json` in project root and set `DZEN_COOKIES_PATH`.

Примечание / Note:
- UI Дзен меняется. Если публикация не сработала, смотрите скриншоты в `artifacts/` и при необходимости поправьте селекторы в `bot/dzen_publisher.py`.

## Webhook режим / Webhook mode

RU:
- Поставьте `BOT_MODE=webhook`
- Укажите публичный домен `WEBHOOK_BASE_URL=https://...`
- Порт внутри контейнера/сервера: `WEBHOOK_PORT` (по умолчанию 8080)

EN:
- Set `BOT_MODE=webhook` and provide `WEBHOOK_BASE_URL`.

## Планировщик / Scheduler

RU:
- Включите `SCHEDULER_ENABLED=true`
- Укажите cron: `SCHEDULER_CRON=0 10 * * *` (каждый день в 10:00)
- Выберите цель: `SCHEDULER_PUBLISH_TARGET=tg|dzen|both`

EN:
- Enable `SCHEDULER_ENABLED=true`, set `SCHEDULER_CRON`, choose publish target.

## Docker

### Build & run

```bash
cd textai-zenblogger
cp .env.example .env
docker build -t textai-zenblogger .
docker run --rm --env-file .env -p 8080:8080 textai-zenblogger
```

### docker-compose

```bash
docker compose up --build
```

## Деплой на бесплатные серверы / Free-tier deployments

RU:
- **Railway.app (рекомендовано)**: удобно для webhooks, есть cron/планировщик на free tier (условия меняются).
  - Запуск: `python -m bot.main`
  - Для webhook: выставьте `WEBHOOK_BASE_URL` на домен Railway.
- **Render.com**: web service + env vars.
- **PythonAnywhere**: проще для polling (webhook сложнее из-за входящих запросов).
- **Google Cloud e2-micro (always‑free)**: запуск как systemd service или Docker.

EN:
- Railway/Render: set env vars, run `python -m bot.main`.
- PythonAnywhere: easiest with polling.
- GCP e2-micro: run as a service (systemd) or Docker.

## Troubleshooting

- **Bot молчит**: проверьте `ADMIN_TELEGRAM_ID` (должен совпадать с вашим user id).
- **Не публикует в канал**: добавьте бота администратором канала и разрешите постинг.
- **Дзен падает**: обновите cookies, отключите headless (`DZEN_HEADLESS=false`) и посмотрите `artifacts/dzen_error.png`.


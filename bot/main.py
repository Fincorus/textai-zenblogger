"""
RU: Точка входа бота. Поддерживает polling и webhook.
EN: Bot entrypoint. Supports polling and webhook.
"""

from __future__ import annotations

import asyncio
import os
import socket
import signal
from contextlib import suppress

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramNetworkError
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import ThreadedResolver, web
from loguru import logger

from bot.handlers import router
from config.settings import load_settings
from utils.scheduler import build_scheduler


def _configure_logging(level: str) -> None:
    logger.remove()
    logger.add(lambda msg: print(msg, end=""), level=level)


async def _run_polling(dp: Dispatcher, bot: Bot) -> None:
    # RU: Сетевые/ DNS проблемы часто временные. Делаем бесконечный retry с паузой.
    # EN: Network/DNS issues are often transient. Keep retrying with delay.
    while True:
        try:
            await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
            return
        except (TelegramNetworkError, OSError) as e:
            logger.warning("Polling network error: {}. Retry in 10s...", e)
            await asyncio.sleep(10)


async def _run_webhook(dp: Dispatcher, bot: Bot, settings) -> None:
    if not settings.WEBHOOK_BASE_URL:
        raise RuntimeError("WEBHOOK_BASE_URL is required for webhook mode")

    webhook_url = settings.WEBHOOK_BASE_URL.rstrip("/") + settings.WEBHOOK_PATH

    await bot.set_webhook(
        url=webhook_url,
        secret_token=settings.WEBHOOK_SECRET_TOKEN.get_secret_value()
        if settings.WEBHOOK_SECRET_TOKEN
        else None,
        drop_pending_updates=True,
    )

    app = web.Application()
    SimpleRequestHandler(dispatcher=dp, bot=bot, secret_token=settings.WEBHOOK_SECRET_TOKEN.get_secret_value()
                         if settings.WEBHOOK_SECRET_TOKEN else None).register(
        app, path=settings.WEBHOOK_PATH
    )
    setup_application(app, dp, bot=bot)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host=settings.WEBHOOK_HOST, port=settings.WEBHOOK_PORT)
    await site.start()
    logger.info("Webhook server started on {}:{}", settings.WEBHOOK_HOST, settings.WEBHOOK_PORT)

    # Keep running
    stop_event = asyncio.Event()

    def _stop(*_args):
        stop_event.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        with suppress(NotImplementedError):
            loop.add_signal_handler(sig, _stop)

    await stop_event.wait()
    await runner.cleanup()


async def main() -> None:
    settings = load_settings()
    _configure_logging(settings.LOG_LEVEL)

    # Ensure provider keys are available to litellm (best-effort).
    if settings.XAI_API_KEY:
        os.environ["XAI_API_KEY"] = settings.XAI_API_KEY.get_secret_value()
    if settings.OPENAI_API_KEY:
        os.environ["OPENAI_API_KEY"] = settings.OPENAI_API_KEY.get_secret_value()
    if settings.GEMINI_API_KEY:
        os.environ["GEMINI_API_KEY"] = settings.GEMINI_API_KEY.get_secret_value()
    if settings.GROQ_API_KEY:
        os.environ["GROQ_API_KEY"] = settings.GROQ_API_KEY.get_secret_value()
    if settings.HUGGINGFACE_API_KEY:
        os.environ["HUGGINGFACE_API_KEY"] = settings.HUGGINGFACE_API_KEY.get_secret_value()

    session = AiohttpSession(timeout=60)
    # RU: Настраиваем TCPConnector, который aiogram создаёт внутри AiohttpSession.
    # EN: Configure TCPConnector init kwargs used internally by AiohttpSession.
    #
    # Notes:
    # - ThreadedResolver avoids aiodns on some Windows setups.
    # - family=AF_INET forces IPv4 (often fixes IPv6 routing/DNS edge cases).
    session._connector_init.update(  # type: ignore[attr-defined]
        {
            "resolver": ThreadedResolver(),
            "ttl_dns_cache": 300,
            "family": socket.AF_INET,
        }
    )

    bot = Bot(
        token=settings.BOT_TOKEN.get_secret_value(),
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
        session=session,
    )
    dp = Dispatcher()

    # Inject settings into handlers via dependency (dp["settings"])
    dp["settings"] = settings
    dp.include_router(router)

    scheduler = build_scheduler(settings, bot)
    if scheduler:
        scheduler.start()

    try:
        if settings.BOT_MODE == "webhook":
            await _run_webhook(dp, bot, settings)
        else:
            await _run_polling(dp, bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())


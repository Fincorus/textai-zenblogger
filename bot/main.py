"""
RU: Точка входа AI ZenBlogger бота.
EN: Main entrypoint for AI ZenBlogger bot.
"""

from __future__ import annotations

import asyncio
import os
import signal
import sys
from contextlib import asynccontextmanager

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramNetworkError, TelegramBadRequest
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web
from loguru import logger

from bot.handlers import router
from config.settings import Settings, load_settings


@asynccontextmanager
async def lifespan(dispatcher: Dispatcher, bot: Bot):
    """Lifespan для graceful shutdown и очистки webhook при необходимости."""
    yield
    await dispatcher.storage.close()
    logger.info("Бот остановлен")


async def delete_webhook_if_needed(bot: Bot) -> None:
    """Автоматически удаляет webhook, если запускаемся в polling-режиме."""
    try:
        webhook_info = await bot.get_webhook_info()
        if webhook_info.url:
            logger.warning("Обнаружен активный webhook. Удаляем его для перехода в polling...")
            await bot.delete_webhook(drop_pending_updates=True)
            logger.success("Webhook успешно удалён")
    except Exception as e:
        logger.error(f"Ошибка при проверке/удалении webhook: {e}")


async def _run_polling(dp: Dispatcher, bot: Bot) -> None:
    """Запуск бота в режиме polling."""
    logger.info("Запуск бота в режиме POLLING...")
    await delete_webhook_if_needed(bot)  # ← Авто-очистка конфликта

    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    except Exception as e:
        logger.exception(f"Ошибка в polling: {e}")
        raise


async def _run_webhook(dp: Dispatcher, bot: Bot, settings: Settings) -> None:
    """Запуск бота в режиме webhook."""
    if not settings.WEBHOOK_BASE_URL:
        logger.warning("WEBHOOK_BASE_URL не задан → переключаемся на polling")
        await _run_polling(dp, bot)
        return

    logger.info(f"Запуск бота в режиме WEBHOOK на {settings.WEBHOOK_BASE_URL}{settings.WEBHOOK_PATH}")

    try:
        secret_token = None
        if settings.WEBHOOK_SECRET_TOKEN: # если это SecretStr, достаём обычную строку
            try:
        secret_token = settings.WEBHOOK_SECRET_TOKEN.get_secret_value()
            except AttributeError:
        secret_token = settings.WEBHOOK_SECRET_TOKEN
        
        await bot.set_webhook(
            url=f"{settings.WEBHOOK_BASE_URL}{settings.WEBHOOK_PATH}",
            secret_token=settings.WEBHOOK_SECRET_TOKEN,
            drop_pending_updates=True,
        )
        logger.success("Webhook успешно установлен")
    except Exception as e:
        logger.error(f"Не удалось установить webhook: {e}. Переключаемся на polling...")
        await _run_polling(dp, bot)
        return

    # Запуск aiohttp сервера
    app = web.Application()
    SimpleRequestHandler(dispatcher=dp, bot=bot).register(app, path=settings.WEBHOOK_PATH)
    setup_application(app, dp, bot=bot)

async def health(request):
    return web.Response(text="OK")

    app.router.add_get("/", health)  # эндпоинт для Render

    runner = web.AppRunner(app)
    await runner.setup()

    port = int(os.getenv("PORT", settings.WEBHOOK_PORT or 8080))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

    logger.info(f"Webhook сервер запущен на 0.0.0.0:{port}")

    # Держим сервер запущенным
    try:
        await asyncio.Event().wait()
    finally:
        await runner.cleanup()


async def main() -> None:
    """Главная функция запуска."""
    logger.info("🚀 Запуск AI ZenBlogger...")

    settings = load_settings()

    # Настройка бота
    session = AiohttpSession(timeout=60)
    bot = Bot(
        token=settings.BOT_TOKEN.get_secret_value(),
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
        session=session,
    )

    dp = Dispatcher()
    dp.include_router(router)

    # Graceful shutdown
    for sig in (signal.SIGINT, signal.SIGTERM):
        asyncio.get_running_loop().add_signal_handler(
            sig, lambda: asyncio.create_task(dp.stop_polling())
        )

    try:
        if settings.BOT_MODE == "webhook":
            await _run_webhook(dp, bot, settings)
        else:
            await _run_polling(dp, bot)
    except Exception as e:
        logger.exception(f"Критическая ошибка запуска: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

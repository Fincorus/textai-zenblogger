"""
RU: Планировщик автопубликаций (APScheduler + asyncio).
EN: Auto-publishing scheduler (APScheduler + asyncio).
"""

from __future__ import annotations

import random
from typing import Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from loguru import logger

from aiogram import Bot

from bot.dzen_publisher import publish_to_dzen
from bot.tg_publisher import publish_to_channel
from config.settings import Settings
from utils.article_generator import generate_article


def _topics(settings: Settings) -> list[str]:
    return [t.strip() for t in (settings.DEFAULT_TOPICS or "").split(",") if t.strip()]


def _cron_trigger(expr: str) -> CronTrigger:
    """
    RU: 5-польный cron "min hour dom mon dow".
    EN: 5-field cron "min hour dom mon dow".
    """

    parts = [p.strip() for p in (expr or "").split() if p.strip()]
    if len(parts) != 5:
        raise ValueError("SCHEDULER_CRON must have 5 fields: min hour dom mon dow")
    minute, hour, day, month, day_of_week = parts
    return CronTrigger(minute=minute, hour=hour, day=day, month=month, day_of_week=day_of_week)


def build_scheduler(settings: Settings, bot: Bot) -> Optional[AsyncIOScheduler]:
    if not settings.SCHEDULER_ENABLED:
        return None

    scheduler = AsyncIOScheduler()

    async def job():
        topic_list = _topics(settings) or ["Технологии"]
        topic = random.choice(topic_list)
        logger.info("Scheduler: generating topic: {}", topic)
        article = await generate_article(settings, topic)

        if settings.SCHEDULER_PUBLISH_TARGET in {"tg", "both"}:
            await publish_to_channel(bot=bot, settings=settings, article=article)
        if settings.SCHEDULER_PUBLISH_TARGET in {"dzen", "both"}:
            await publish_to_dzen(settings=settings, article=article)

        logger.info("Scheduler: done")

    trigger = _cron_trigger(settings.SCHEDULER_CRON)
    scheduler.add_job(job, trigger=trigger, id="auto_generate_publish", max_instances=1, replace_existing=True)
    logger.info("Scheduler enabled with cron: {}", settings.SCHEDULER_CRON)
    return scheduler


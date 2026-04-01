"""
RU: Генерация/подбор обложки.
EN: Cover generation / selection.
"""

from __future__ import annotations

import urllib.parse

from loguru import logger

from config.settings import Settings


def cover_url_for_topic(settings: Settings, topic: str) -> str:
    """
    RU: Возвращает URL обложки. По умолчанию — Unsplash Source (без ключа).
    EN: Returns a cover image URL. Default: Unsplash Source endpoint (no key).

    Note:
    - Telegram Bot API может принимать URL как фото.
    - Для Дзен Playwright сможет загрузить картинку по URL (через fetch->file или прямую вставку, зависит от UI).
    """

    query = urllib.parse.quote_plus(topic.strip() or "technology")

    if settings.IMAGE_MODE == "unsplash":
        url = settings.UNSPLASH_SOURCE_URL.format(query=query)
        logger.info("Cover url (unsplash): {}", url)
        return url

    # RU: LLM-генерация изображений сильно зависит от провайдера/доступности.
    # EN: LLM image gen is provider-dependent; keep a safe fallback.
    url = settings.UNSPLASH_SOURCE_URL.format(query=query)
    logger.warning("IMAGE_MODE=llm not implemented yet, fallback to unsplash: {}", url)
    return url


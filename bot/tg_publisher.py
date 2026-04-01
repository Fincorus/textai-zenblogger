"""
RU: Публикация статьи в Telegram-канал.
EN: Publish an article to a Telegram channel.
"""

from __future__ import annotations

from aiogram import Bot
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest
from loguru import logger

from utils.article_generator import GeneratedArticle
from utils.image import cover_url_for_topic
from config.settings import Settings


async def publish_to_channel(
    *,
    bot: Bot,
    settings: Settings,
    article: GeneratedArticle,
) -> None:
    """
    RU: Публикует обложку + текст в канал. Если HTML слишком длинный для подписи,
    отправляем фото отдельно, затем текст сообщением.
    EN: Posts cover + text to channel. If caption too long, send separately.
    """

    cover_url = cover_url_for_topic(settings, article.topic)
    channel = settings.TG_CHANNEL_ID

    # Telegram caption limit is ~1024 chars; message limit is 4096.
    caption = f"<b>{article.title}</b>"

    try:
        await bot.send_photo(
            chat_id=channel,
            photo=cover_url,
            caption=caption[:1024],
            parse_mode=ParseMode.HTML,
        )
    except TelegramBadRequest as e:
        logger.warning("send_photo failed (fallback to text only): {}", e)
        await bot.send_message(chat_id=channel, text=caption, parse_mode=ParseMode.HTML)

    # Split article html to Telegram message chunks (4096)
    text = article.html.strip()
    if not text:
        return

    chunks: list[str] = []
    while text:
        chunks.append(text[:4096])
        text = text[4096:]

    for ch in chunks:
        await bot.send_message(chat_id=channel, text=ch, parse_mode=ParseMode.HTML)


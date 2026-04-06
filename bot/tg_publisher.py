from aiogram.enums import ParseMode
from loguru import logger
import re

from config.settings import Settings
from utils.article_generator import GeneratedArticle


async def publish_to_channel(*, bot, settings: Settings, article: GeneratedArticle) -> None:
    """
    RU: Публикация статьи в TG-канал.
    EN: Publish article to TG channel.
    """
    channel = settings.TG_CHANNEL_ID
    if not channel:
        logger.warning("TG_CHANNEL_ID is not set, skipping TG publish")
        return

    # формируем контент: заголовок + тело
    ch = (article.html or "").strip()

    # сначала заменим h1/ h2 на простые заголовки
    ch = re.sub(r"<h1[^>]*>(.*?)</h1>", r"\1\n", ch, flags=re.IGNORECASE | re.DOTALL)
    ch = re.sub(r"<h2[^>]*>(.*?)</h2>", r"\1\n", ch, flags=re.IGNORECASE | re.DOTALL)

    # заменим <br> на переносы строки
    ch = ch.replace("<br>", "\n").replace("<br/>", "\n").replace("<br />", "\n")

    # вырежем все остальные HTML-теги
    ch = re.sub(r"<[^>]+>", "", ch)

    # можно ограничить длину, если текст очень большой
    if len(ch) > 3500:
        ch = ch[:3500].rstrip() + "…\n\n(текст обрезан для Telegram)"

    try:
        await bot.send_message(
            chat_id=channel,
            text=ch,
            parse_mode=None,  # важно: без HTML
            disable_web_page_preview=False,
        )
        logger.info("Article published to TG channel {}", channel)
    except Exception as e:
        logger.exception("Failed to send article to TG channel: {}", e)
        raise

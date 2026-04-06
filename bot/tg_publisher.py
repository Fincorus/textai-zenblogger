"""
RU: Публикация статей в Telegram-канал.
EN: Publishing articles to Telegram channel.
"""

from __future__ import annotations

import re

from aiogram.enums import ParseMode
from loguru import logger

from config.settings import Settings
from utils.article_generator import GeneratedArticle


def _strip_plan_and_format(text: str) -> str:
    """
    RU: Убираем план (до первой строки с 'H1:' / 'H2:' / 'H3:')
    и красиво форматируем заголовки, удаляя HTML.
    EN: Remove outline (plan) and format headings nicely, stripping HTML.
    """
    lines = text.splitlines()

    # 1) Убираем план до первой строки с H1/H2/H3
    content_started = False
    content_lines: list[str] = []
    for line in lines:
        if re.search(r"^\s*H[123]:", line):
            content_started = True
        if content_started:
            content_lines.append(line)

    if not content_lines:
        content_lines = lines  # fallback, если не нашли H1/H2/H3

    text = "\n".join(content_lines)

    # 2) Форматируем заголовки H1/H2/H3
    def _fmt_heading(match: re.Match) -> str:
        level = match.group(1)
        title = match.group(2).strip()
        underline = "=" * len(title) if level == "1" else "-" * len(title)
        return f"\n{title}\n{underline}\n"

    text = re.sub(r"^\s*H([123]):\s*(.+)$", _fmt_heading, text, flags=re.MULTILINE)

    # 3) <br> -> переносы строк
    text = (
        text.replace("<br>", "\n")
        .replace("<br/>", "\n")
        .replace("<br />", "\n")
    )

    # 4) Убираем все остальные HTML‑теги
    text = re.sub(r"<[^>]+>", "", text)

    # 5) Сжимаем лишние пустые строки
    text = re.sub(r"\n{3,}", "\n\n", text).strip()

    return text


async def publish_to_channel(*, bot, settings: Settings, article: GeneratedArticle) -> None:
    """
    RU: Публикация статьи в TG-канал (без плана, с красиво оформленными заголовками).
    EN: Publish article to TG channel.
    """
    channel = settings.TG_CHANNEL_ID
    if not channel:
        logger.warning("TG_CHANNEL_ID is not set, skipping TG publish")
        return

    raw = (article.html or "").strip()
    text = _strip_plan_and_format(raw)

    # целимся в ~3000 символов
    MAX_LEN = 3000
    if len(text) > MAX_LEN:
        text = text[:MAX_LEN].rstrip()

    try:
        await bot.send_message(
            chat_id=channel,
            text=text,
            parse_mode=None,  # чистый текст, без HTML
            disable_web_page_preview=False,
        )
        logger.info("Article published to TG channel {}", channel)
    except Exception as e:
        logger.exception("Failed to send article to TG channel: {}", e)
        raise

"""
RU: Публикация статей в Telegram-канал.
EN: Publishing articles to Telegram channel.
"""

from __future__ import annotations

import re

from loguru import logger

from config.settings import Settings
from utils.article_generator import GeneratedArticle


def _strip_plan_and_format(text: str) -> str:
    """
    RU: Убираем план (всё до первой строки '## Статья')
    и красиво форматируем заголовки H1/H2/H3, удаляя HTML.
    EN: Remove outline (plan) and format headings, stripping HTML.
    """
    lines = text.splitlines()

    # 1) Убираем план до строки "## Статья"
    content_started = False
    content_lines: list[str] = []
    for line in lines:
        if not content_started and line.strip().lower().startswith("## статья"):
            content_started = True
            continue  # сам заголовок "## Статья" пропускаем
        if content_started:
            content_lines.append(line)

    if not content_lines:
        content_lines = lines

    text = "\n".join(content_lines)

    # 2) Форматируем markdown‑заголовки "## ..." / "### ..."
    def _fmt_md_heading(match: re.Match) -> str:
        hashes = match.group(1)
        title = match.group(2).strip()
        level = len(hashes)
        underline = "=" * len(title) if level == 1 else "-" * len(title)
        return f"\n{title}\n{underline}\n"

    text = re.sub(r"^\s*(#{1,3})\s+(.+)$", _fmt_md_heading, text, flags=re.MULTILINE)

    # 3) <br> -> переносы строк
    text = (
        text.replace("<br>", "\n")
        .replace("<br/>", "\n")
        .replace("<br />", "\n")
    )

    # 4) Убираем все HTML‑теги
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
        cut = text[:MAX_LEN]
        last_dot = cut.rfind(".")
        if last_dot > 200:
            cut = cut[: last_dot + 1]
        text = cut.rstrip()

    try:
        await bot.send_message(
            chat_id=channel,
            text=text,
            parse_mode=None,
            disable_web_page_preview=False,
        )
        logger.info("Article published to TG channel {}", channel)
    except Exception as e:
        logger.exception("Failed to send article to TG channel: {}", e)
        raise
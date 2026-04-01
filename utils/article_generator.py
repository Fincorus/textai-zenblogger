"""
RU: Генерация статьи через LLM, возвращает заголовок и HTML-текст.
EN: Generate an article via LLM, returning title and HTML body.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from loguru import logger

from bot.llm import generate_text
from config.prompts import (
    ARTICLE_USER_PROMPT_TEMPLATE,
    BLOGGER_SYSTEM_PROMPT,
    default_audience,
    default_tone,
)
from config.settings import Settings


@dataclass(frozen=True)
class GeneratedArticle:
    topic: str
    title: str
    html: str


def _extract_title(text: str, topic: str) -> str:
    """
    RU: Пытаемся достать заголовок из первых строк; fallback — по теме.
    EN: Extract a title from first lines; fallback to topic.
    """

    lines = [l.strip() for l in text.splitlines() if l.strip()]
    if not lines:
        return topic.strip()[:120]

    first = lines[0]
    # Common patterns: "Заголовок: ..." or "# ..."
    m = re.match(r"^(?:Заголовок|Title)\s*:\s*(.+)$", first, flags=re.I)
    if m:
        return m.group(1).strip()[:140]
    if first.startswith("#"):
        return first.lstrip("#").strip()[:140]
    return first[:140]


def _ensure_html(text: str) -> str:
    """
    RU: Для Telegram/Дзен удобнее HTML. Если модель вернула plain text,
    минимально преобразуем: пустые строки -> <br><br>, списки -> <ul>.
    EN: Convert to minimal HTML if needed.
    """

    if "<" in text and ">" in text:
        return text

    # Minimal formatting: paragraphs and simple lists
    html_lines: list[str] = []
    in_ul = False
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            if in_ul:
                html_lines.append("</ul>")
                in_ul = False
            html_lines.append("<br>")
            continue
        if re.match(r"^[-•]\s+", line):
            if not in_ul:
                html_lines.append("<ul>")
                in_ul = True
            item = re.sub(r"^[-•]\s+", "", line).strip()
            html_lines.append(f"<li>{item}</li>")
            continue
        if in_ul:
            html_lines.append("</ul>")
            in_ul = False
        # headings heuristic
        if len(line) <= 90 and line.endswith(":"):
            html_lines.append(f"<b>{line[:-1]}</b><br>")
        else:
            html_lines.append(f"{line}<br>")
    if in_ul:
        html_lines.append("</ul>")
    return "\n".join(html_lines).replace("<br>\n<br>", "<br><br>")


async def generate_article(settings: Settings, topic: str) -> GeneratedArticle:
    """
    RU: Генерирует SEO-статью по теме и возвращает (title, html).
    EN: Generates a SEO article and returns (title, html).
    """

    topic = topic.strip()
    if not topic:
        raise ValueError("Topic is empty")

    user_prompt = ARTICLE_USER_PROMPT_TEMPLATE.format(
        topic=topic,
        audience=default_audience(),
        tone=default_tone(),
        keywords="",
    )

    messages = [
        {"role": "system", "content": BLOGGER_SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]

    logger.info("Generating article for topic: {}", topic)
    text = await generate_text(settings=settings, messages=messages, temperature=0.7)

    title = _extract_title(text, topic)
    html = _ensure_html(text)

    return GeneratedArticle(topic=topic, title=title, html=html)


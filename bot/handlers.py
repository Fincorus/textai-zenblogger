"""
RU: Handlers для aiogram 3.x (админ-онли).
EN: aiogram 3.x handlers (admin-only).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from aiogram import Bot, F, Router
from aiogram.filters import Command, CommandObject
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from loguru import logger

from bot.dzen_publisher import publish_to_dzen
from bot.tg_publisher import publish_to_channel, _strip_plan_and_format
from config.settings import load_settings
from utils.article_generator import GeneratedArticle, generate_article

router = Router(name="handlers")

# Глобальные настройки, загружаем один раз
settings = load_settings()


def _admin_only(user_id: Optional[int]) -> bool:
    return user_id is not None and int(user_id) == int(settings.ADMIN_TELEGRAM_ID)


def _topics() -> list[str]:
    return [t.strip() for t in (settings.DEFAULT_TOPICS or "").split(",") if t.strip()]


def _topic_keyboard() -> InlineKeyboardMarkup:
    buttons: list[list[InlineKeyboardButton]] = []
    for t in _topics()[:12]:
        buttons.append([InlineKeyboardButton(text=t, callback_data=f"topic:{t}")])
    buttons.append([InlineKeyboardButton(text="Отмена", callback_data="action:cancel")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def _actions_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Опубликовать в TG-канал",
                    callback_data="action:tg",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="Опубликовать в Дзен",
                    callback_data="action:dzen",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="Оба",
                    callback_data="action:both",
                ),
                InlineKeyboardButton(
                    text="Отмена",
                    callback_data="action:cancel",
                ),
            ],
        ]
    )


@dataclass
class DraftStore:
    """
    RU: Простейшее хранилище черновика в памяти процесса (для одного админа достаточно).
    EN: Simple in-memory draft store (good enough for single admin).
    """

    article: Optional[GeneratedArticle] = None


draft_store = DraftStore()


@router.message(Command("start"))
async def cmd_start(message: Message) -> None:
    if not _admin_only(message.from_user.id if message.from_user else None):
        return

    await message.answer(
        "Привет! Я умею генерировать статьи и публиковать их в TG/Дзен.\n\n"
        "Команды:\n"
        "- /generate [тема]\n"
        "- /generate (покажу список тем)\n",
        parse_mode=None,
    )


@router.message(Command("generate"))
async def cmd_generate(message: Message, command: CommandObject) -> None:
    if not _admin_only(message.from_user.id if message.from_user else None):
        return

    topic = (command.args or "").strip() if command else ""
    if not topic:
        await message.answer("Выберите тему:", reply_markup=_topic_keyboard())
        return

    await _generate_and_preview(message, topic)


@router.callback_query(F.data.startswith("topic:"))
async def on_topic_pick(query: CallbackQuery) -> None:
    if not _admin_only(query.from_user.id if query.from_user else None):
        await query.answer("Недоступно", show_alert=True)
        return

    topic = (query.data or "").split("topic:", 1)[1].strip()
    await query.answer()
    if not topic:
        return

    if query.message:
        await query.message.edit_text(
            f"Ок, генерирую статью про: {topic}…",
            parse_mode=None,
        )
        await _generate_and_preview(query.message, topic)


async def _generate_and_preview(message: Message, topic: str) -> None:
    await message.answer(
        f"Генерирую статью по теме: {topic}…",
        parse_mode=None,
    )
    article = await generate_article(settings, topic)
    draft_store.article = article

    raw = article.html or ""
    preview = _strip_plan_and_format(raw)

    if len(preview) > 1200:
        preview = preview[:1200].rstrip() + "\n\n(preview обрезан)"

    await message.answer(
        f"Preview\n\n{article.title}\n\n{preview}",
        parse_mode=None,
        reply_markup=_actions_keyboard(),
        disable_web_page_preview=True,
    )


@router.callback_query(F.data.startswith("action:"))
async def on_action(query: CallbackQuery, bot: Bot) -> None:
    if not _admin_only(query.from_user.id if query.from_user else None):
        await query.answer("Недоступно", show_alert=True)
        return

    action = (query.data or "").split("action:", 1)[1]
    await query.answer()

    if action == "cancel":
        draft_store.article = None
        if query.message:
            await query.message.edit_reply_markup(reply_markup=None)
            await query.message.answer("Ок, отменено.")
        return

    article = draft_store.article
    if not article:
        if query.message:
            await query.message.answer("Черновик не найден. Сначала /generate.")
        return

    if query.message:
        await query.message.answer("Публикую…")

    if action in {"tg", "both"}:
        await publish_to_channel(bot=bot, settings=settings, article=article)

    if action in {"dzen", "both"}:
        res = await publish_to_dzen(settings=settings, article=article)
        if query.message:
            if res.success:
                await query.message.answer(f"Дзен: опубликовано. URL (если доступно): {res.url}")
            else:
                await query.message.answer(
                    "Дзен: ошибка публикации. "
                    + (f"Скриншот: {res.screenshot_path}" if res.screenshot_path else "")
                )

    if query.message:
        await query.message.answer("Готово.")

    logger.info("Action completed: {}", action)

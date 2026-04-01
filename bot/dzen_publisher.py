"""
RU: Публикация статьи в Яндекс.Дзен через Playwright (официального API нет).
EN: Publish to Yandex Dzen via Playwright (no public API).

Важно / Important:
- UI Дзен может меняться. Селекторы и шаги в этом модуле сделаны максимально
  "бережно", но при необходимости их нужно подправить под текущую верстку.
- Авторизация: cookies-based (файл cookies_dzen.json).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from loguru import logger
from playwright.async_api import async_playwright, Page

from config.settings import Settings
from utils.article_generator import GeneratedArticle
from utils.image import cover_url_for_topic


class DzenPublishError(RuntimeError):
    pass


@dataclass(frozen=True)
class DzenPublishResult:
    success: bool
    url: Optional[str] = None
    screenshot_path: Optional[str] = None


async def _load_cookies(path: str) -> list[dict]:
    p = Path(path)
    if not p.exists():
        raise DzenPublishError(
            f"Cookies file not found: {path}. Export cookies to cookies_dzen.json"
        )
    data = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise DzenPublishError("cookies_dzen.json must contain a JSON array of cookies")
    return data


async def _safe_screenshot(page: Page, name: str) -> str:
    out = Path("artifacts")
    out.mkdir(exist_ok=True)
    path = out / name
    await page.screenshot(path=str(path), full_page=True)
    return str(path)


async def publish_to_dzen(*, settings: Settings, article: GeneratedArticle) -> DzenPublishResult:
    """
    RU: Пытается создать и опубликовать статью в Дзен.
    EN: Attempts to create and publish an article on Dzen.
    """

    cookies = await _load_cookies(settings.DZEN_COOKIES_PATH)
    cover_url = cover_url_for_topic(settings, article.topic)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=settings.DZEN_HEADLESS)
        context = await browser.new_context()
        await context.add_cookies(cookies)
        page = await context.new_page()

        try:
            # RU: Стартовая страница редактора (может меняться).
            # EN: Editor entry point (may change over time).
            await page.goto("https://dzen.ru/", wait_until="domcontentloaded")

            # Many accounts have "studio" / editor path.
            await page.goto("https://dzen.ru/profile/editor", wait_until="domcontentloaded")

            # Create new article (best-effort selectors).
            # RU: иногда кнопка называется "Создать" / "Новая публикация".
            await page.wait_for_timeout(1500)
            for sel in [
                "text=Создать",
                "text=Новая публикация",
                "text=Статья",
                "[data-test-id='create']",
            ]:
                try:
                    await page.locator(sel).first.click(timeout=1500)
                    break
                except Exception:
                    continue

            # Title input
            # RU: обычно это contenteditable или input.
            for sel in [
                "[contenteditable='true'][data-placeholder*='Заголовок']",
                "textarea[placeholder*='Заголовок']",
                "input[placeholder*='Заголовок']",
            ]:
                loc = page.locator(sel).first
                if await loc.count():
                    await loc.click()
                    await loc.fill(article.title)
                    break

            # Body editor
            body_filled = False
            for sel in [
                "[contenteditable='true'][data-placeholder*='Текст']",
                "[contenteditable='true']",
                "div[role='textbox']",
            ]:
                loc = page.locator(sel).nth(0)
                try:
                    if await loc.count():
                        await loc.click()
                        # RU: Вставляем как HTML: используем evaluate + execCommand('insertHTML').
                        # EN: Insert as HTML via execCommand for rich editor.
                        await page.evaluate(
                            """(html) => {
                              const el = document.activeElement;
                              if (!el) return;
                              document.execCommand('insertHTML', false, html);
                            }""",
                            article.html,
                        )
                        body_filled = True
                        break
                except Exception:
                    continue
            if not body_filled:
                raise DzenPublishError("Could not find Dzen body editor")

            # Cover upload: UI varies. We try to open cover dialog and set URL if possible.
            # RU: Часто обложка загружается через input[type=file]; из URL нужен download.
            # EN: Usually requires file upload; from URL you'd download first.
            logger.info("Cover URL prepared: {}", cover_url)

            # Tags / rubric are highly UI-dependent; we keep best-effort.
            # Publish button
            published = False
            for sel in ["text=Опубликовать", "[data-test-id='publish']"]:
                try:
                    await page.locator(sel).first.click(timeout=2000)
                    published = True
                    break
                except Exception:
                    continue

            if not published:
                raise DzenPublishError("Could not click Publish button (selectors outdated?)")

            await page.wait_for_timeout(2000)
            shot = await _safe_screenshot(page, "dzen_after_publish.png")

            # Try to capture resulting URL
            url = page.url
            await context.close()
            await browser.close()
            return DzenPublishResult(success=True, url=url, screenshot_path=shot)

        except Exception as e:
            logger.exception("Dzen publish failed: {}", e)
            try:
                shot = await _safe_screenshot(page, "dzen_error.png")
            except Exception:
                shot = None
            await context.close()
            await browser.close()
            return DzenPublishResult(success=False, url=None, screenshot_path=shot)


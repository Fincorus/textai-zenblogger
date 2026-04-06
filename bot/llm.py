"""
RU: Единая точка доступа к LLM через litellm с fallback.
EN: Single LLM gateway via litellm with fallbacks.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, Optional

from loguru import logger
from tenacity import AsyncRetrying, retry_if_exception_type, stop_after_attempt, wait_exponential

try:
    # litellm is optional at import time for docs/tests.
    import litellm
except Exception:  # pragma: no cover
    litellm = None  # type: ignore

from config.settings import Settings


@dataclass(frozen=True)
class ProviderModel:
    provider: str
    model: str


class LLMError(RuntimeError):
    pass


def _provider_env(settings: Settings) -> dict[str, str]:
    """
    RU: litellm читает ключи из env; мы прокидываем в process env через kwargs.
    EN: litellm reads keys from env; we pass them via kwargs/env.
    """

    env: dict[str, str] = {}
    if settings.XAI_API_KEY:
        env["XAI_API_KEY"] = settings.XAI_API_KEY.get_secret_value()
    if settings.OPENAI_API_KEY:
        env["OPENAI_API_KEY"] = settings.OPENAI_API_KEY.get_secret_value()
    if settings.GEMINI_API_KEY:
        env["GEMINI_API_KEY"] = settings.GEMINI_API_KEY.get_secret_value()
    if settings.GROQ_API_KEY:
        env["GROQ_API_KEY"] = settings.GROQ_API_KEY.get_secret_value()
    if settings.HUGGINGFACE_API_KEY:
        env["HUGGINGFACE_API_KEY"] = settings.HUGGINGFACE_API_KEY.get_secret_value()
    return env


def _parse_fallbacks(s: str) -> list[ProviderModel]:
    out: list[ProviderModel] = []
    for item in [x.strip() for x in (s or "").split(",") if x.strip()]:
        if ":" not in item:
            continue
        provider, model = item.split(":", 1)
        out.append(ProviderModel(provider=provider.strip(), model=model.strip()))
    return out


def _litellm_model_name(provider: str, model: str) -> str:
    """
    RU: litellm использует префиксы провайдеров (например, xai/grok-4).
    EN: litellm uses provider prefixes (e.g., xai/grok-4).
    """

    provider = provider.lower()
    if provider in {"xai", "openai", "gemini", "groq"}:
        return f"{provider}/{model}"
    if provider in {"huggingface", "hf"}:
        return f"huggingface/{model}"
    return model


async def generate_text(
    *,
    settings: Settings,
    messages: list[dict[str, Any]],
    temperature: float = 0.7,
    max_tokens: Optional[int] = None,
) -> str:
    """
    RU: Генерация текста с fallback по провайдерам/моделям.
    EN: Text generation with provider/model fallbacks.
    """

    if litellm is None:
        raise LLMError("litellm is not installed. Install requirements.txt dependencies.")

    candidates: list[ProviderModel] = [
        ProviderModel(provider=settings.LLM_PROVIDER, model=settings.LLM_MODEL),
        *_parse_fallbacks(settings.LLM_FALLBACKS),
    ]

    last_err: Optional[BaseException] = None

    for cand in candidates:
        model_name = _litellm_model_name(cand.provider, cand.model)
        logger.info("LLM request -> {}", model_name)

        try:
            async for attempt in AsyncRetrying(
                stop=stop_after_attempt(3),
                wait=wait_exponential(multiplier=1, min=1, max=10),
                retry=retry_if_exception_type((TimeoutError, asyncio.TimeoutError, OSError)),
                reraise=True,
            ):
                with attempt:
                    resp = await litellm.acompletion(
                        model=model_name,
                        messages=messages,
                        temperature=temperature,
                        max_tokens=max_tokens,
                        timeout=settings.LLM_TIMEOUT_S,
                        extra_headers={},
                    )
                    content = (resp["choices"][0]["message"].get("content") or "").strip()
                    if not content:
                        raise LLMError(f"Empty content from {model_name}")
                    return content
        except Exception as e:
            last_err = e
            logger.warning("LLM failed for {}: {}", model_name, e)
            continue

    raise LLMError(f"All LLM providers failed. Last error: {last_err}")

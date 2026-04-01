"""
RU: Настройки проекта через переменные окружения (.env).
EN: Project settings via environment variables (.env).
"""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    RU: Все настройки читаются из окружения и/или .env.
    EN: All settings are loaded from environment and/or .env.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- Telegram ---
    BOT_TOKEN: SecretStr = Field(..., description="Telegram bot token")
    ADMIN_TELEGRAM_ID: int = Field(..., description="Only this user can use the bot")
    TG_CHANNEL_ID: str = Field(
        ..., description="Target channel id or @username. Example: @my_channel or -100123..."
    )

    # Polling / Webhook
    BOT_MODE: Literal["polling", "webhook"] = Field(
        "polling", description="Run mode: polling or webhook"
    )
    WEBHOOK_BASE_URL: Optional[str] = Field(
        None, description="Public base URL for webhook, e.g. https://example.com"
    )
    WEBHOOK_PATH: str = Field("/telegram/webhook", description="Webhook path")
    WEBHOOK_SECRET_TOKEN: Optional[SecretStr] = Field(
        None, description="Optional secret token for webhook"
    )
    WEBHOOK_HOST: str = Field("0.0.0.0", description="Webhook server host")
    WEBHOOK_PORT: int = Field(8080, description="Webhook server port")

    # --- LLM (via litellm) ---
    LLM_PROVIDER: Literal["xai", "openai", "gemini", "groq", "huggingface"] = Field(
        "xai", description="Default provider for generation"
    )
    LLM_MODEL: str = Field("grok-4.1-fast", description="Default text model")
    LLM_FALLBACKS: str = Field(
        "openai:gpt-4o-mini,gemini:gemini-2.0-flash,groq:llama-3.1-70b-versatile",
        description="Comma-separated fallbacks: provider:model",
    )
    LLM_TIMEOUT_S: int = Field(120, description="LLM request timeout seconds")

    # Keys (keep optional; provider selection defines what you need)
    XAI_API_KEY: Optional[SecretStr] = None
    OPENAI_API_KEY: Optional[SecretStr] = None
    GEMINI_API_KEY: Optional[SecretStr] = None
    GROQ_API_KEY: Optional[SecretStr] = None
    HUGGINGFACE_API_KEY: Optional[SecretStr] = None

    # --- Article generation ---
    ARTICLE_MIN_WORDS: int = Field(1500, description="Minimum words")
    ARTICLE_MAX_WORDS: int = Field(3000, description="Maximum words")
    DEFAULT_TOPICS: str = Field(
        "Искусственный интеллект,Продуктивность,Маркетинг,Здоровье,Финансы,Саморазвитие",
        description="Comma-separated topics used for interactive selection and scheduler",
    )

    # --- Images / Cover ---
    IMAGE_MODE: Literal["unsplash", "llm"] = Field(
        "unsplash", description="Cover image mode"
    )
    UNSPLASH_SOURCE_URL: str = Field(
        "https://source.unsplash.com/featured/1280x720/?{query}",
        description="No-key Unsplash Source endpoint template",
    )
    LLM_IMAGE_MODEL: str = Field("grok-2-image", description="If IMAGE_MODE=llm")

    # --- Dzen / Playwright ---
    DZEN_COOKIES_PATH: str = Field(
        "cookies_dzen.json", description="Cookies exported from browser"
    )
    DZEN_HEADLESS: bool = Field(True, description="Run Playwright headless")
    DZEN_RUBRIC: Optional[str] = Field(
        None, description="Optional rubric/category name to select"
    )
    DZEN_TAGS: str = Field("AI,технологии,обучение", description="Comma-separated tags")

    # --- Scheduler ---
    SCHEDULER_ENABLED: bool = Field(False, description="Enable auto posting")
    SCHEDULER_CRON: str = Field(
        "0 10 * * *", description="Cron expression in 5-field format (min hour dom mon dow)"
    )
    SCHEDULER_PUBLISH_TARGET: Literal["tg", "dzen", "both"] = Field(
        "tg", description="Where scheduler publishes"
    )

    # --- Logging ---
    LOG_LEVEL: str = Field("INFO", description="Loguru level")


def load_settings() -> Settings:
    return Settings()


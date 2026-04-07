from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator
from typing import List


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Gmail / OAuth
    GMAIL_CREDENTIALS_FILE: str = Field(default="credentials.json")
    GMAIL_TOKEN_FILE: str = Field(default="token.json")
    GMAIL_USER_ID: str = Field(default="me")

    # LLM
    LLM_API_BASE: str = Field(default="https://api.openai.com/v1")
    LLM_API_KEY: str = Field(default="")
    LLM_MODEL: str = Field(default="gpt-4.1-mini")
    ENABLE_LLM: bool = Field(default=True)
    LLM_REDACT: bool = Field(default=True)

    # Cleanup behavior
    CLEANUP_MODE: str = Field(default="archive")  # archive|delete|spam
    ENABLE_UNSUBSCRIBE: bool = Field(default=True)
    DRY_RUN: bool = Field(default=True)
    SAFE_MODE: bool = Field(default=True)

    JUNK_CONFIDENCE_THRESHOLD: float = Field(default=0.8)
    IMPORTANT_CONFIDENCE_THRESHOLD: float = Field(default=0.75)
    JUNK_REPEAT_THRESHOLD: int = Field(default=5)
    REQUIRE_RULE_FOR_JUNK: bool = Field(default=True)

    # Scheduling
    SCAN_WINDOW_MINUTES: int = Field(default=60)
    SCAN_INTERVAL_MINUTES: int = Field(default=10)
    MAX_RESULTS_PER_SCAN: int = Field(default=100)

    # Notifications
    NOTIFY_TELEGRAM: bool = Field(default=False)
    TELEGRAM_BOT_TOKEN: str = Field(default="")
    TELEGRAM_CHAT_ID: str = Field(default="")
    NOTIFY_EMAIL_SUMMARY: bool = Field(default=False)
    NOTIFY_WEBHOOK: bool = Field(default=False)
    WEBHOOK_URL: str = Field(default="")

    # API
    USERS_FILE: str = Field(default="configs/users.json")

    # Unsubscribe safety
    UNSUBSCRIBE_ALLOWLIST: List[str] = Field(default_factory=list)
    BLOCK_PRIVATE_IPS: bool = Field(default=True)

    # Accounts
    ACCOUNTS_FILE: str = Field(default="configs/accounts.json")

    # Access control
    ALLOWED_SENDERS: List[str] = Field(default_factory=list)
    BLOCKED_SENDERS: List[str] = Field(default_factory=list)
    PROTECTED_DOMAINS: List[str] = Field(default_factory=list)

    # Paths
    DATABASE_PATH: str = Field(default="data/email_assistant.db")
    LOG_PATH: str = Field(default="logs/app.log")

    @field_validator("ALLOWED_SENDERS", "BLOCKED_SENDERS", "PROTECTED_DOMAINS", mode="before")
    @classmethod
    def _parse_csv(cls, v):
        if isinstance(v, str):
            return [item.strip() for item in v.split(",") if item.strip()]
        return v


settings = Settings()

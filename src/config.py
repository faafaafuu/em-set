from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Settings:
    # LLM (Ollama)
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "qwen2.5:7b"
    ENABLE_LLM: bool = True
    LLM_REDACT: bool = True

    # Cleanup behavior
    CLEANUP_MODE: str = "archive"  # archive|delete|spam
    ENABLE_UNSUBSCRIBE: bool = True
    DRY_RUN: bool = True
    SAFE_MODE: bool = True

    JUNK_CONFIDENCE_THRESHOLD: float = 0.8
    IMPORTANT_CONFIDENCE_THRESHOLD: float = 0.75
    JUNK_REPEAT_THRESHOLD: int = 5
    REQUIRE_RULE_FOR_JUNK: bool = True

    # Scheduling (for future use)
    SCAN_WINDOW_MINUTES: int = 60
    MAX_RESULTS_PER_SCAN: int = 100

    # Notifications
    NOTIFY_TELEGRAM: bool = False
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_CHAT_ID: str = ""
    NOTIFY_EMAIL_SUMMARY: bool = False
    NOTIFY_WEBHOOK: bool = False
    WEBHOOK_URL: str = ""

    # Access control
    ALLOWED_SENDERS: list[str] = None
    BLOCKED_SENDERS: list[str] = None
    PROTECTED_DOMAINS: list[str] = None

    # Unsubscribe safety
    UNSUBSCRIBE_ALLOWLIST: list[str] = None
    BLOCK_PRIVATE_IPS: bool = True

    # Paths
    DATABASE_PATH: str = "data/email_assistant.db"
    LOG_PATH: str = "logs/app.log"


settings = Settings()

# Normalize None lists to empty lists
settings.ALLOWED_SENDERS = settings.ALLOWED_SENDERS or []
settings.BLOCKED_SENDERS = settings.BLOCKED_SENDERS or []
settings.PROTECTED_DOMAINS = settings.PROTECTED_DOMAINS or []
settings.UNSUBSCRIBE_ALLOWLIST = settings.UNSUBSCRIBE_ALLOWLIST or []

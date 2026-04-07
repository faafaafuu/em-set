from __future__ import annotations

import logging
import httpx

from .config import settings
from .gmail_client import GmailClient
from .models import EmailMessage, ClassificationResult

logger = logging.getLogger(__name__)


def notify_important(gmail: GmailClient, email: EmailMessage, classification: ClassificationResult) -> None:
    message = (
        f"Important email\n"
        f"From: {email.from_email}\n"
        f"Subject: {email.subject}\n"
        f"Reason: {classification.reason}\n"
    )

    if settings.NOTIFY_TELEGRAM and settings.TELEGRAM_BOT_TOKEN and settings.TELEGRAM_CHAT_ID:
        _send_telegram(message)

    if settings.NOTIFY_EMAIL_SUMMARY:
        try:
            gmail.send_mail(settings.GMAIL_USER_ID, "Important email notification", message)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Email notify failed: %s", exc)

    if settings.NOTIFY_WEBHOOK and settings.WEBHOOK_URL:
        _send_webhook(message)


def send_summary(gmail: GmailClient, stats: dict) -> None:
    text = (
        "Daily summary\n"
        f"scanned: {stats.get('scanned', 0)}\n"
        f"important: {stats.get('important', 0)}\n"
        f"useful: {stats.get('useful', 0)}\n"
        f"junk: {stats.get('junk', 0)}\n"
        f"manual_review: {stats.get('manual_review', 0)}\n"
        f"archived: {stats.get('archived', 0)}\n"
        f"deleted: {stats.get('deleted', 0)}\n"
        f"unsubscribe: {stats.get('unsubscribe', 0)}\n"
    )

    if settings.NOTIFY_TELEGRAM and settings.TELEGRAM_BOT_TOKEN and settings.TELEGRAM_CHAT_ID:
        _send_telegram(text)

    if settings.NOTIFY_EMAIL_SUMMARY:
        try:
            gmail.send_mail(settings.GMAIL_USER_ID, "Daily email summary", text)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Email summary failed: %s", exc)

    if settings.NOTIFY_WEBHOOK and settings.WEBHOOK_URL:
        _send_webhook(text)


def _send_telegram(text: str) -> None:
    url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": settings.TELEGRAM_CHAT_ID, "text": text}
    try:
        with httpx.Client(timeout=10) as client:
            client.post(url, json=payload)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Telegram notify failed: %s", exc)


def _send_webhook(text: str) -> None:
    try:
        with httpx.Client(timeout=10) as client:
            client.post(settings.WEBHOOK_URL, json={"message": text})
    except Exception as exc:  # noqa: BLE001
        logger.warning("Webhook notify failed: %s", exc)

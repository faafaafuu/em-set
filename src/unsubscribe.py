from __future__ import annotations

import logging
import re
import socket
from typing import Optional
from urllib.parse import urlparse
import ipaddress

import httpx

from .config import settings
from .models import EmailMessage, UnsubscribeResult
from .rules_engine import safe_delete_allowed
from .gmail_client import GmailClient

logger = logging.getLogger(__name__)


def _is_protected_sender(email: EmailMessage) -> bool:
    domain = email.from_email.split("@")[-1].lower() if "@" in email.from_email else ""
    protected = [d.lower() for d in settings.PROTECTED_DOMAINS]
    return domain in protected


def attempt_unsubscribe(gmail: GmailClient, email: EmailMessage) -> UnsubscribeResult:
    if not settings.ENABLE_UNSUBSCRIBE:
        return UnsubscribeResult(attempted=False, success=False, detail="Unsubscribe disabled")

    if _is_protected_sender(email):
        return UnsubscribeResult(attempted=False, success=False, detail="Protected domain")

    header = email.headers.get("List-Unsubscribe", "")
    candidates = []
    if header:
        candidates.extend(re.findall(r"<([^>]+)>", header))

    if not candidates:
        return UnsubscribeResult(attempted=False, success=False, detail="No unsubscribe header")

    if settings.SAFE_MODE:
        return UnsubscribeResult(attempted=True, success=False, detail="Safe mode - logged only")

    for link in candidates:
        if link.startswith("mailto:"):
            address = link.replace("mailto:", "").split("?")[0]
            try:
                gmail.send_mail(address, "Unsubscribe", "Please unsubscribe me")
                return UnsubscribeResult(attempted=True, success=True, method="mailto")
            except Exception as exc:  # noqa: BLE001
                logger.warning("Unsubscribe mailto failed: %s", exc)
        elif link.startswith("http"):
            if not _is_safe_url(link):
                logger.warning("Blocked unsafe unsubscribe URL: %s", link)
                continue
            try:
                with httpx.Client(timeout=15, follow_redirects=False) as client:
                    resp = client.get(link)
                    if resp.status_code < 400:
                        return UnsubscribeResult(attempted=True, success=True, method="url")
            except Exception as exc:  # noqa: BLE001
                logger.warning("Unsubscribe url failed: %s", exc)

    return UnsubscribeResult(attempted=True, success=False, detail="All unsubscribe methods failed")


def _is_safe_url(url: str) -> bool:
    try:
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"}:
            return False
        host = parsed.hostname or ""

        allowlist = [d.lower() for d in settings.UNSUBSCRIBE_ALLOWLIST]
        if allowlist and not any(host.endswith(d) for d in allowlist):
            return False

        if settings.BLOCK_PRIVATE_IPS:
            ips = _resolve_host_ips(host)
            for ip in ips:
                if _is_private_ip(ip):
                    return False
        return True
    except Exception:  # noqa: BLE001
        return False


def _resolve_host_ips(host: str) -> list[str]:
    try:
        return [info[4][0] for info in socket.getaddrinfo(host, None)]
    except Exception:  # noqa: BLE001
        return []


def _is_private_ip(ip_str: str) -> bool:
    try:
        ip = ipaddress.ip_address(ip_str)
        return ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved
    except Exception:  # noqa: BLE001
        return True

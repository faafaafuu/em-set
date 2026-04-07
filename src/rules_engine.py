from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

from .models import EmailMessage, ClassificationResult
from .config import settings


@dataclass
class RuleResult:
    label: str
    confidence: float
    reason: str
    rule_id: str


IMPORTANT_KEYWORDS = [
    "security", "login", "password", "reset", "verification", "verify", "2fa",
    "invoice", "receipt", "payment", "charge", "billing", "booking", "ticket",
    "shipment", "delivery", "account", "urgent", "action required", "deadline",
]

JUNK_KEYWORDS = [
    "sale", "discount", "offer", "weekly digest", "recommended for you", "we miss you",
    "last chance", "special offer", "newsletter", "promo", "promotions", "deal",
]

USEFUL_KEYWORDS = [
    "subscription", "trial", "plan", "renewal", "policy update", "terms update",
]


SAFE_DELETE_BLOCKERS = [
    "urgent", "action required", "verify", "invoice", "payment", "login",
    "security", "booking", "receipt", "reset password",
]


def _contains_any(text: str, keywords: list[str]) -> bool:
    t = text.lower()
    return any(k in t for k in keywords)


def _matches_people_sender(from_email: str) -> bool:
    # crude heuristic: if sender is a free email provider, more likely a person
    free_domains = ["gmail.com", "yahoo.com", "outlook.com", "icloud.com", "hotmail.com"]
    domain = from_email.split("@")[-1].lower() if "@" in from_email else ""
    return domain in free_domains


def apply_rules(email: EmailMessage) -> Optional[ClassificationResult]:
    text_blob = f"{email.from_email} {email.subject} {email.snippet} {email.body}".lower()

    if settings.ALLOWED_SENDERS and email.from_email.lower() in [s.lower() for s in settings.ALLOWED_SENDERS]:
        if _sender_auth_pass(email):
            return ClassificationResult(label="important", confidence=0.9, reason="Sender in allowlist (auth pass)", rule_hit="allowlist")
        return ClassificationResult(label="manual_review", confidence=0.5, reason="Allowlist sender but auth not verified", rule_hit="allowlist_no_auth")

    if email.from_email.lower() in [s.lower() for s in settings.BLOCKED_SENDERS]:
        return ClassificationResult(label="junk", confidence=0.95, reason="Sender in blocklist", rule_hit="blocklist")

    if _contains_any(text_blob, IMPORTANT_KEYWORDS):
        return ClassificationResult(label="important", confidence=0.85, reason="Important keyword match", rule_hit="important_keywords")

    if email.has_attachments and _contains_any(text_blob, ["pdf", "invoice", "receipt", "contract"]):
        return ClassificationResult(label="important", confidence=0.8, reason="Document attachment detected", rule_hit="attachment_document")

    if _contains_any(text_blob, JUNK_KEYWORDS):
        return ClassificationResult(label="junk", confidence=0.8, reason="Junk keyword match", rule_hit="junk_keywords")

    if "list-unsubscribe" in {k.lower() for k in email.headers.keys()}:
        return ClassificationResult(label="junk", confidence=0.78, reason="List-Unsubscribe header present", rule_hit="list_unsubscribe")

    if _contains_any(text_blob, USEFUL_KEYWORDS):
        return ClassificationResult(label="useful", confidence=0.7, reason="Useful keyword match", rule_hit="useful_keywords")

    if _matches_people_sender(email.from_email):
        return ClassificationResult(label="important", confidence=0.65, reason="Likely person sender", rule_hit="person_sender")

    return None


def safe_delete_allowed(email: EmailMessage) -> bool:
    text_blob = f"{email.subject} {email.snippet} {email.body}".lower()
    if _contains_any(text_blob, SAFE_DELETE_BLOCKERS):
        return False

    protected_domains = [d.lower() for d in settings.PROTECTED_DOMAINS]
    if protected_domains:
        domain = email.from_email.split("@")[-1].lower() if "@" in email.from_email else ""
        if domain in protected_domains:
            return False

    return True


def _sender_auth_pass(email: EmailMessage) -> bool:
    # Trust only if SPF or DKIM (or DMARC) passed in Authentication-Results
    auth = email.headers.get("Authentication-Results", "").lower()
    if "dkim=pass" in auth or "spf=pass" in auth or "dmarc=pass" in auth:
        return True
    return False

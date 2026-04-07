from __future__ import annotations

import json
import logging
import re
from typing import Optional

from .config import settings
from .llm_client import ollama_chat
from .models import EmailMessage, ClassificationResult
from .rules_engine import apply_rules

logger = logging.getLogger(__name__)


LLM_SYSTEM = (
    "You are an email classification agent. "
    "Classify into: important, useful, junk, manual_review. "
    "Return strict JSON with keys: label, confidence, reason."
)


def classify_email(email: EmailMessage) -> ClassificationResult:
    rule_result = apply_rules(email)
    if rule_result:
        return rule_result

    if not settings.ENABLE_LLM:
        return ClassificationResult(label="manual_review", confidence=0.4, reason="LLM disabled", llm_used=False)

    llm_result = _classify_with_llm(email)
    if llm_result:
        return llm_result

    return ClassificationResult(label="manual_review", confidence=0.4, reason="LLM failed", llm_used=True)


def _classify_with_llm(email: EmailMessage) -> Optional[ClassificationResult]:
    body = email.body[:2000]
    headers = email.headers

    if settings.LLM_REDACT:
        body = _redact_pii(body)
        headers = _redact_headers(headers)

    messages = [
        {"role": "system", "content": LLM_SYSTEM},
        {
            "role": "user",
            "content": (
                "Classify email:\n"
                f"From: {email.from_email}\n"
                f"Subject: {email.subject}\n"
                f"Snippet: {email.snippet}\n"
                f"Body: {body}\n"
                f"Headers: {json.dumps(headers)[:2000]}\n"
                f"Labels: {email.labels}\n"
            ),
        },
    ]

    for attempt in range(3):
        try:
            content = ollama_chat(settings.OLLAMA_BASE_URL, settings.OLLAMA_MODEL, messages)
            parsed = json.loads(_extract_json(content))
            label = str(parsed.get("label", "manual_review")).strip().lower()
            if label not in {"important", "useful", "junk", "manual_review"}:
                label = "manual_review"
            return ClassificationResult(
                label=label,
                confidence=float(parsed.get("confidence", 0.5)),
                reason=parsed.get("reason", "LLM"),
                llm_used=True,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("LLM classify failed attempt %s: %s", attempt + 1, exc)

    return None


def _extract_json(text: str) -> str:
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        return text[start : end + 1]
    return text


def _redact_pii(text: str) -> str:
    text = re.sub(r"[\w\.-]+@[\w\.-]+", "[redacted_email]", text)
    text = re.sub(r"\b\d{10,}\b", "[redacted_number]", text)
    return text


def _redact_headers(headers: dict) -> dict:
    safe = {}
    for k, v in headers.items():
        key = k.lower()
        if key in {"from", "subject", "date", "message-id"}:
            safe[k] = v
    return safe

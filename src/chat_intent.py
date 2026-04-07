from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Optional

from .config import settings
from .llm_client import ollama_chat


@dataclass
class Intent:
    action: str
    account: Optional[str] = None
    email_id: Optional[str] = None


SYSTEM_PROMPT = (
    "You are a strict intent parser for an email assistant. "
    "Return ONLY JSON with keys: action, account, email_id. "
    "Allowed actions: summary, list_important, list_junk, scan, stats, manual_list, keep, junk, help."
)


def parse_intent(text: str) -> Intent:
    # Rule-based shortcuts
    t = text.lower()
    if any(k in t for k in ["привет", "что у меня", "что по почте", "что там", "почта"]):
        return Intent(action="summary")
    if "важн" in t:
        return Intent(action="list_important")
    if "спам" in t or "мусор" in t:
        if "удал" in t or "очист" in t:
            return Intent(action="junk")
        return Intent(action="list_junk")
    if "скан" in t or "провер" in t:
        return Intent(action="scan")
    if "стат" in t:
        return Intent(action="stats")
    if "manual" in t or "ручн" in t:
        return Intent(action="manual_list")

    if not settings.ENABLE_LLM:
        return Intent(action="help")

    # LLM fallback
    try:
        content = ollama_chat(
            settings.OLLAMA_BASE_URL,
            settings.OLLAMA_MODEL,
            [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": text},
            ],
        )
        data = json.loads(_extract_json(content))
        action = str(data.get("action", "help")).strip().lower()
        if action not in {"summary","list_important","list_junk","scan","stats","manual_list","keep","junk","help"}:
            action = "help"
        return Intent(action=action, account=data.get("account"), email_id=data.get("email_id"))
    except Exception:
        return Intent(action="help")


def _extract_json(text: str) -> str:
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        return text[start : end + 1]
    return text

from __future__ import annotations

import httpx


def ollama_chat(base_url: str, model: str, messages: list[dict]) -> str:
    url = f"{base_url}/api/chat"
    payload = {"model": model, "messages": messages, "stream": False}
    with httpx.Client(timeout=30) as client:
        resp = client.post(url, json=payload)
        resp.raise_for_status()
        data = resp.json()
        return data.get("message", {}).get("content", "")

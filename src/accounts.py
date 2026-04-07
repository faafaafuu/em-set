from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import List

from .config import settings


@dataclass
class AccountConfig:
    name: str
    credentials_file: str
    token_file: str
    user_id: str = "me"


def load_accounts() -> List[AccountConfig]:
    if not os.path.exists(settings.ACCOUNTS_FILE):
        return []
    with open(settings.ACCOUNTS_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    return [AccountConfig(**a) for a in data.get("accounts", [])]


def save_accounts(accounts: List[AccountConfig]) -> None:
    os.makedirs(os.path.dirname(settings.ACCOUNTS_FILE), exist_ok=True)
    with open(settings.ACCOUNTS_FILE, "w", encoding="utf-8") as f:
        json.dump({"accounts": [a.__dict__ for a in accounts]}, f, indent=2)


def ensure_accounts_interactive() -> None:
    if os.path.exists(settings.ACCOUNTS_FILE):
        return
    print("No Gmail accounts configured. Let's add one or more accounts.")
    count = int(input("How many Gmail accounts to configure? ").strip() or "1")
    accounts: List[AccountConfig] = []
    for idx in range(count):
        name = input(f"Account {idx+1} name (e.g. work): ").strip()
        credentials = input("Path to credentials.json: ").strip()
        token = input("Path to token.json (will be created if missing): ").strip()
        user_id = input("Gmail user id (default 'me'): ").strip() or "me"
        accounts.append(AccountConfig(name=name, credentials_file=credentials, token_file=token, user_id=user_id))
    save_accounts(accounts)
    print("Saved accounts to", settings.ACCOUNTS_FILE)

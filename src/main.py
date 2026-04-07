from __future__ import annotations

import base64
import hashlib
import os
import secrets
from dataclasses import dataclass
from getpass import getpass
from typing import Dict

from .config import settings
from .database import Database
from .gmail_client import GmailClient
from .logging_setup import setup_logging
from .processor import EmailProcessor


@dataclass
class UserRecord:
    username: str
    salt_b64: str
    hash_b64: str


def _hash_password(password: str, salt: bytes) -> bytes:
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 200_000)


def _ensure_user(db: Database) -> None:
    users = db.get_users()
    if users:
        return
    print("No users configured. Create admin user for CLI access.")
    username = input("Username: ").strip()
    password = getpass("Password: ").strip()
    salt = secrets.token_bytes(16)
    pw_hash = _hash_password(password, salt)
    db.upsert_user(username, base64.b64encode(salt).decode("utf-8"), base64.b64encode(pw_hash).decode("utf-8"))
    print("User created.")


def _login(db: Database) -> bool:
    users = [UserRecord(**u) for u in db.get_users()]
    if not users:
        return False
    username = input("Login: ").strip()
    password = getpass("Password: ").strip()
    for u in users:
        if secrets.compare_digest(u.username, username):
            salt = base64.b64decode(u.salt_b64)
            expected = base64.b64decode(u.hash_b64)
            actual = _hash_password(password, salt)
            return secrets.compare_digest(actual, expected)
    return False


def _ensure_account(db: Database) -> None:
    accounts = db.list_accounts()
    if accounts:
        return
    print("No Gmail accounts configured. Add one now.")
    name = input("Account name (e.g. work): ").strip() or "default"
    credentials = input("Path to credentials.json: ").strip()
    token = input("Path to token.json (will be created if missing): ").strip() or f"data/token_{name}.json"
    user_id = input("Gmail user id (default 'me'): ").strip() or "me"
    db.upsert_account(name, credentials, token, user_id)
    print("Account saved.")


def _load_processors(db: Database) -> Dict[str, EmailProcessor]:
    processors: Dict[str, EmailProcessor] = {}
    for a in db.list_accounts():
        gmail = GmailClient(a["credentials_file"], a["token_file"], a["user_id"])
        processors[a["name"]] = EmailProcessor(gmail, db, a["name"])
    return processors


def _print_help() -> None:
    print("Commands:")
    print("  help")
    print("  accounts")
    print("  add-account")
    print("  scan [account|all]")
    print("  manual list")
    print("  manual keep <account> <email_id>")
    print("  manual junk <account> <email_id>")
    print("  stats")
    print("  exit")


def main() -> None:
    setup_logging()
    db = Database()

    _ensure_user(db)
    if not _login(db):
        print("Unauthorized")
        return

    _ensure_account(db)
    processors = _load_processors(db)

    _print_help()
    while True:
        try:
            raw = input("> ").strip()
        except KeyboardInterrupt:
            print("\nBye")
            return

        if not raw:
            continue
        parts = raw.split()
        cmd = parts[0].lower()

        if cmd in {"exit", "quit"}:
            return
        if cmd == "help":
            _print_help()
            continue
        if cmd == "accounts":
            for name in processors.keys():
                print(name)
            continue
        if cmd == "add-account":
            _ensure_account(db)
            processors = _load_processors(db)
            continue
        if cmd == "scan":
            target = parts[1] if len(parts) > 1 else "all"
            if target == "all":
                for name, p in processors.items():
                    print(name, p.scan_and_process())
            else:
                if target not in processors:
                    print("Account not found")
                else:
                    print(processors[target].scan_and_process())
            continue
        if cmd == "manual":
            if len(parts) < 2:
                print("manual list | manual keep <account> <email_id> | manual junk <account> <email_id>")
                continue
            sub = parts[1]
            if sub == "list":
                items = db.list_manual_review(limit=50)
                for it in items:
                    print(it)
            elif sub in {"keep", "junk"}:
                if len(parts) < 4:
                    print("manual keep <account> <email_id>")
                    continue
                account = parts[2]
                email_id = parts[3]
                if account not in processors:
                    print("Account not found")
                    continue
                if sub == "keep":
                    processors[account].gmail.add_label(email_id, "important_ai")
                else:
                    if settings.CLEANUP_MODE == "delete":
                        processors[account].gmail.trash(email_id)
                    elif settings.CLEANUP_MODE == "spam":
                        processors[account].gmail.spam(email_id)
                    else:
                        processors[account].gmail.archive(email_id)
                db.remove_manual_review(account, email_id)
                print("ok")
            continue
        if cmd == "stats":
            print(db.stats())
            continue

        print("Unknown command. Type 'help'.")


if __name__ == "__main__":
    main()

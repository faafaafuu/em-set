from __future__ import annotations

import time
from datetime import datetime, timezone, timedelta

from .database import Database
from .gmail_client import GmailClient
from .logging_setup import setup_logging
from .processor import EmailProcessor
from .chat_intent import parse_intent
from .config import settings


def _ensure_user(db: Database) -> None:
    users = db.get_users()
    if users:
        return
    from getpass import getpass
    import base64, secrets, hashlib

    print("No users configured. Create admin user for CLI access.")
    username = input("Username: ").strip()
    password = getpass("Password: ").strip()
    salt = secrets.token_bytes(16)
    pw_hash = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 200_000)
    db.upsert_user(username, base64.b64encode(salt).decode("utf-8"), base64.b64encode(pw_hash).decode("utf-8"))
    print("User created.")


def _login(db: Database) -> bool:
    import base64, hashlib, secrets
    from getpass import getpass

    users = db.get_users()
    if not users:
        return False
    username = input("Login: ").strip()
    password = getpass("Password: ").strip()
    for u in users:
        if secrets.compare_digest(u["username"], username):
            salt = base64.b64decode(u["salt_b64"])
            expected = base64.b64decode(u["hash_b64"])
            actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 200_000)
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


def _load_processors(db: Database) -> dict[str, EmailProcessor]:
    processors: dict[str, EmailProcessor] = {}
    for a in db.list_accounts():
        gmail = GmailClient(a["credentials_file"], a["token_file"], a["user_id"])
        processors[a["name"]] = EmailProcessor(gmail, db, a["name"])
    return processors


def _summarize(db: Database) -> str:
    since = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
    stats = db.stats_since(since)
    if not stats:
        return "Нет данных за последние 24 часа. Скажите 'скан', чтобы проверить почту."
    return (
        "За 24 часа: "
        f"important={stats.get('important',0)}, useful={stats.get('useful',0)}, junk={stats.get('junk',0)}, "
        f"manual_review={stats.get('manual_review',0)}."
    )


def _print_help() -> None:
    print("Примеры: 'что у меня по почте', 'покажи важные', 'удали спам', 'скан', 'статистика'")


def main() -> None:
    setup_logging()
    db = Database()

    _ensure_user(db)
    if not _login(db):
        print("Unauthorized")
        return

    _ensure_account(db)
    processors = _load_processors(db)

    print("Готов. Можно спрашивать про почту.")
    while True:
        try:
            raw = input("> ").strip()
        except KeyboardInterrupt:
            print("\nBye")
            return

        if not raw:
            continue

        intent = parse_intent(raw)

        if intent.action == "help":
            _print_help()
            continue

        if intent.action == "stats":
            print(_summarize(db))
            continue

        if intent.action == "scan":
            for name, p in processors.items():
                print(name, p.scan_and_process())
            continue

        if intent.action == "summary":
            # perform scan then summarize
            for name, p in processors.items():
                p.scan_and_process()
            print(_summarize(db))
            continue

        if intent.action == "manual_list":
            items = db.list_manual_review(limit=50)
            if not items:
                print("Пусто")
            for it in items:
                print(it)
            continue

        if intent.action == "list_important":
            recent = db.recent_actions(limit=20)
            important = [r for r in recent if r.get("classification") == "important"]
            if not important:
                print("Важных не найдено. Могу сделать скан.")
            else:
                for r in important[:10]:
                    print(f"{r['account']} | {r['sender']} | {r['subject']}")
            continue

        if intent.action == "list_junk":
            recent = db.recent_actions(limit=20)
            junk = [r for r in recent if r.get("classification") == "junk"]
            if not junk:
                print("Спама не найдено. Могу сделать скан.")
            else:
                for r in junk[:10]:
                    print(f"{r['account']} | {r['sender']} | {r['subject']}")
            continue

        if intent.action == "junk":
            if settings.DRY_RUN:
                print("DRY_RUN включен. Выключите DRY_RUN в src/config.py для удаления.")
                continue
            confirm = input("Удалить/спамить мусорные письма по правилам? (yes/no): ").strip().lower()
            if confirm != "yes":
                print("Отменено")
                continue
            for name, p in processors.items():
                print(name, p.scan_and_process())
            continue

        if intent.action == "keep" and intent.account and intent.email_id:
            if intent.account not in processors:
                print("Account not found")
            else:
                processors[intent.account].gmail.add_label(intent.email_id, "important_ai")
                db.remove_manual_review(intent.account, intent.email_id)
                print("ok")
            continue

        print("Не понял запрос. Скажи 'помощь' или 'что у меня по почте'.")


if __name__ == "__main__":
    main()

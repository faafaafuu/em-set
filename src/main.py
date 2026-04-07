from __future__ import annotations

import time

from .database import Database
from .gmail_client import GmailClient
from .logging_setup import setup_logging
from .processor import EmailProcessor
from .scheduler import start_scheduler
from .auth import ensure_users_interactive
from .accounts import ensure_accounts_interactive, load_accounts


def main() -> None:
    setup_logging()
    ensure_users_interactive()
    ensure_accounts_interactive()

    db = Database()
    accounts = load_accounts()
    processors = []
    for a in accounts:
        gmail = GmailClient(a.credentials_file, a.token_file, a.user_id)
        processors.append(EmailProcessor(gmail, db, a.name))

    start_scheduler(processors, db)

    while True:
        time.sleep(60)


if __name__ == "__main__":
    main()

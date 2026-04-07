from __future__ import annotations

import imaplib
import email
from typing import List


class ImapFallbackClient:
    def __init__(self, host: str, username: str, password: str) -> None:
        self.host = host
        self.username = username
        self.password = password

    def list_messages(self) -> List[str]:
        with imaplib.IMAP4_SSL(self.host) as imap:
            imap.login(self.username, self.password)
            imap.select("INBOX")
            _, data = imap.search(None, "ALL")
            return data[0].split()

    def fetch_message(self, msg_id: bytes) -> email.message.Message:
        with imaplib.IMAP4_SSL(self.host) as imap:
            imap.login(self.username, self.password)
            imap.select("INBOX")
            _, data = imap.fetch(msg_id, "(RFC822)")
            return email.message_from_bytes(data[0][1])

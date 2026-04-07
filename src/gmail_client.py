from __future__ import annotations

import base64
import logging
import os
import re
from datetime import datetime, timedelta, timezone
from email import message_from_bytes
from typing import List, Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from .config import settings
from .models import EmailMessage

logger = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.settings.basic",
]


class GmailClient:
    def __init__(self, credentials_file: str, token_file: str, user_id: str = "me") -> None:
        self.credentials_file = credentials_file
        self.token_file = token_file
        self.user_id = user_id
        self.service = self._authenticate()

    def _authenticate(self):
        creds = None
        if os.path.exists(self.token_file):
            creds = Credentials.from_authorized_user_file(self.token_file, SCOPES)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(self.credentials_file, SCOPES)
                creds = flow.run_local_server(port=0)
            with open(self.token_file, "w", encoding="utf-8") as token:
                token.write(creds.to_json())
        return build("gmail", "v1", credentials=creds)

    def list_messages(self, minutes_back: int = 60, max_results: int = 50) -> List[str]:
        after = int((datetime.now(timezone.utc) - timedelta(minutes=minutes_back)).timestamp())
        query = f"after:{after}"
        results = (
            self.service.users()
            .messages()
            .list(userId=self.user_id, q=query, maxResults=max_results)
            .execute()
        )
        messages = results.get("messages", [])
        return [m["id"] for m in messages]

    def get_message(self, message_id: str) -> EmailMessage:
        msg = (
            self.service.users()
            .messages()
            .get(userId=self.user_id, id=message_id, format="raw")
            .execute()
        )
        raw = base64.urlsafe_b64decode(msg["raw"].encode("UTF-8"))
        email_msg = message_from_bytes(raw)

        headers = {k: v for k, v in email_msg.items()}
        subject = headers.get("Subject", "")
        from_email = headers.get("From", "")

        body = self._extract_body(email_msg)
        snippet = msg.get("snippet", "")

        labels = msg.get("labelIds", [])
        has_attachments = self._has_attachments(email_msg)

        internal_date = None
        if "internalDate" in msg:
            internal_date = datetime.fromtimestamp(int(msg["internalDate"]) / 1000, tz=timezone.utc)

        return EmailMessage(
            id=message_id,
            thread_id=msg.get("threadId"),
            from_email=from_email,
            subject=subject,
            snippet=snippet,
            body=body,
            headers=headers,
            labels=labels,
            has_attachments=has_attachments,
            internal_date=internal_date,
        )

    def _extract_body(self, email_msg) -> str:
        if email_msg.is_multipart():
            parts = []
            for part in email_msg.walk():
                ctype = part.get_content_type()
                if ctype == "text/plain" and part.get_payload(decode=True):
                    parts.append(part.get_payload(decode=True).decode(errors="ignore"))
            return "\n".join(parts)
        payload = email_msg.get_payload(decode=True)
        if payload:
            return payload.decode(errors="ignore")
        return ""

    def _has_attachments(self, email_msg) -> bool:
        if not email_msg.is_multipart():
            return False
        for part in email_msg.walk():
            filename = part.get_filename()
            if filename:
                return True
        return False

    def mark_read(self, message_id: str) -> None:
        self._modify_labels(message_id, remove_labels=["UNREAD"])

    def add_label(self, message_id: str, label_name: str) -> None:
        label_id = self._ensure_label(label_name)
        self._modify_labels(message_id, add_labels=[label_id])

    def remove_label(self, message_id: str, label_name: str) -> None:
        label_id = self._find_label_id(label_name)
        if label_id:
            self._modify_labels(message_id, remove_labels=[label_id])

    def archive(self, message_id: str) -> None:
        self._modify_labels(message_id, remove_labels=["INBOX"])

    def delete(self, message_id: str) -> None:
        self.service.users().messages().delete(userId=self.user_id, id=message_id).execute()

    def trash(self, message_id: str) -> None:
        self.service.users().messages().trash(userId=self.user_id, id=message_id).execute()

    def spam(self, message_id: str) -> None:
        self._modify_labels(message_id, add_labels=["SPAM"], remove_labels=["INBOX"])

    def send_mail(self, to_email: str, subject: str, body: str) -> None:
        from email.message import EmailMessage
        from email.utils import parseaddr

        name, addr = parseaddr(to_email)
        if "\r" in addr or "\n" in addr or "@" not in addr:
            raise ValueError("Invalid recipient address")

        msg = EmailMessage()
        msg["To"] = addr
        msg["Subject"] = subject
        msg.set_content(body)

        b64 = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")
        self.service.users().messages().send(
            userId=self.user_id, body={"raw": b64}
        ).execute()

    def _modify_labels(self, message_id: str, add_labels: Optional[List[str]] = None, remove_labels: Optional[List[str]] = None) -> None:
        add_labels = add_labels or []
        remove_labels = remove_labels or []
        body = {"addLabelIds": add_labels, "removeLabelIds": remove_labels}
        self.service.users().messages().modify(userId=self.user_id, id=message_id, body=body).execute()

    def _ensure_label(self, label_name: str) -> str:
        label_id = self._find_label_id(label_name)
        if label_id:
            return label_id
        created = (
            self.service.users()
            .labels()
            .create(userId=self.user_id, body={"name": label_name})
            .execute()
        )
        return created["id"]

    def _find_label_id(self, label_name: str) -> Optional[str]:
        labels = self.service.users().labels().list(userId=self.user_id).execute().get("labels", [])
        for label in labels:
            if label["name"].lower() == label_name.lower():
                return label["id"]
        return None

    def find_unsubscribe_links(self, email: EmailMessage) -> List[str]:
        links = []
        header = email.headers.get("List-Unsubscribe", "")
        if header:
            links.extend(re.findall(r"<([^>]+)>", header))
        # also scan body for unsubscribe links
        links.extend(re.findall(r"https?://[^\s]+unsubscribe[^\s]+", email.body, flags=re.I))
        return list(dict.fromkeys(links))

    def create_filter(self, criteria: dict, action: dict) -> bool:
        try:
            self.service.users().settings().filters().create(
                userId=settings.GMAIL_USER_ID,
                body={"criteria": criteria, "action": action},
            ).execute()
            return True
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to create filter: %s", exc)
            return False

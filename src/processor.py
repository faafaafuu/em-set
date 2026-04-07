from __future__ import annotations

import hashlib
import logging
from datetime import datetime

from .classifier import classify_email
from .config import settings
from .database import Database
from .gmail_client import GmailClient
from .models import ActionRecord, EmailMessage, ManualReviewItem, ClassificationResult
from .notifier import notify_important
from .rules_engine import safe_delete_allowed
from .unsubscribe import attempt_unsubscribe

logger = logging.getLogger(__name__)


class EmailProcessor:
    def __init__(self, gmail: GmailClient, db: Database, account: str) -> None:
        self.gmail = gmail
        self.db = db
        self.account = account

    def scan_and_process(self) -> dict:
        message_ids = self.gmail.list_messages(
            minutes_back=settings.SCAN_WINDOW_MINUTES,
            max_results=settings.MAX_RESULTS_PER_SCAN,
        )
        stats = {
            "scanned": 0,
            "important": 0,
            "useful": 0,
            "junk": 0,
            "manual_review": 0,
            "archived": 0,
            "deleted": 0,
            "spammed": 0,
            "unsubscribe": 0,
        }

        for message_id in message_ids:
            email = self.gmail.get_message(message_id)
            stats["scanned"] += 1

            content_hash = self._hash_email(email)
            if self.db.is_duplicate_hash(content_hash):
                logger.info("Skip duplicate email %s", message_id)
                continue

            classification = classify_email(email)
            if classification.llm_used and classification.label == "junk" and settings.REQUIRE_RULE_FOR_JUNK:
                classification = ClassificationResult(
                    label="manual_review",
                    confidence=0.4,
                    reason="LLM junk downgraded to manual review",
                    llm_used=True,
                )
            action_taken = self._decide_action(email, classification)

            unsubscribe_result = attempt_unsubscribe(self.gmail, email) if classification.label == "junk" else None
            if unsubscribe_result and unsubscribe_result.success:
                stats["unsubscribe"] += 1

            if not settings.DRY_RUN:
                self._execute_action(email, action_taken)

            if classification.label == "important":
                notify_important(self.gmail, email, classification)

            if classification.label == "manual_review":
                self.db.add_manual_review(
                    ManualReviewItem(
                        account=self.account,
                        email_id=email.id,
                        sender=email.from_email,
                        subject=email.subject,
                        reason=classification.reason,
                        created_at=datetime.utcnow(),
                    )
                )

            if classification.label == "junk":
                self.db.sender_junk_increment(email.from_email)

            self.db.add_action(
                ActionRecord(
                    account=self.account,
                    email_id=email.id,
                    sender=email.from_email,
                    subject=email.subject,
                    classification=classification.label,
                    action_taken=action_taken,
                    unsubscribe_attempted=bool(unsubscribe_result and unsubscribe_result.attempted),
                    timestamp=datetime.utcnow(),
                    content_hash=content_hash,
                )
            )

            stats[classification.label] += 1
            if action_taken == "archive":
                stats["archived"] += 1
            elif action_taken == "delete":
                stats["deleted"] += 1
            elif action_taken == "spam":
                stats["spammed"] += 1

        return stats

    def _hash_email(self, email: EmailMessage) -> str:
        base = f"{email.from_email}|{email.subject}|{email.snippet}|{email.body[:500]}"
        return hashlib.sha256(base.encode("utf-8")).hexdigest()

    def _decide_action(self, email: EmailMessage, classification) -> str:
        if classification.label == "important":
            if not settings.DRY_RUN:
                self.gmail.add_label(email.id, "important_ai")
            return "keep"

        if classification.label == "useful":
            if not settings.DRY_RUN:
                self.gmail.add_label(email.id, "useful_later")
            return "archive"

        if classification.label == "manual_review":
            if not settings.DRY_RUN:
                self.gmail.add_label(email.id, "manual_review")
            return "manual_review"

        # junk
        junk_count = self.db.sender_junk_count(email.from_email)
        if junk_count >= settings.JUNK_REPEAT_THRESHOLD:
            # aggressive handling after repeated junk
            if settings.CLEANUP_MODE == "spam":
                return "spam"
            if settings.CLEANUP_MODE == "delete" and safe_delete_allowed(email):
                return "delete"
            return "archive"

        if classification.confidence >= settings.JUNK_CONFIDENCE_THRESHOLD and safe_delete_allowed(email):
            return settings.CLEANUP_MODE

        return "archive"

    def _execute_action(self, email: EmailMessage, action: str) -> None:
        if action == "archive":
            self.gmail.archive(email.id)
        elif action == "delete":
            self.gmail.trash(email.id)
        elif action == "spam":
            self.gmail.spam(email.id)

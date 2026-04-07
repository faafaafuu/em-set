from datetime import datetime

from src.processor import EmailProcessor
from src.models import EmailMessage
from src.database import Database
from src.config import settings


class FakeGmail:
    def __init__(self):
        self.actions = []

    def list_messages(self, minutes_back: int, max_results: int):
        return ["1"]

    def get_message(self, message_id: str) -> EmailMessage:
        return EmailMessage(
            id=message_id,
            from_email="promo@shop.com",
            subject="special offer",
            snippet="",
            body="",
            headers={"List-Unsubscribe": "<mailto:unsub@shop.com>"},
            labels=[],
            has_attachments=False,
            internal_date=datetime.utcnow(),
        )

    def add_label(self, message_id: str, label_name: str) -> None:
        self.actions.append(("label", label_name))

    def archive(self, message_id: str) -> None:
        self.actions.append(("archive", message_id))

    def trash(self, message_id: str) -> None:
        self.actions.append(("trash", message_id))

    def spam(self, message_id: str) -> None:
        self.actions.append(("spam", message_id))


class DummyDB(Database):
    def __init__(self):
        super().__init__(path=":memory:")


def test_processor_dry_run(monkeypatch):
    monkeypatch.setattr(settings, "DRY_RUN", True)
    gmail = FakeGmail()
    db = DummyDB()
    processor = EmailProcessor(gmail, db, "acc1")
    stats = processor.scan_and_process()
    assert stats["scanned"] == 1
    assert stats["junk"] == 1
    assert gmail.actions == []


def test_processor_archive_when_low_confidence(monkeypatch):
    monkeypatch.setattr(settings, "DRY_RUN", False)
    monkeypatch.setattr(settings, "CLEANUP_MODE", "delete")
    monkeypatch.setattr(settings, "JUNK_CONFIDENCE_THRESHOLD", 0.95)
    gmail = FakeGmail()
    db = DummyDB()
    processor = EmailProcessor(gmail, db, "acc1")
    processor.scan_and_process()
    assert ("archive", "1") in gmail.actions

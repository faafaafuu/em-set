from datetime import datetime
from pathlib import Path

from src.database import Database
from src.models import ActionRecord


def test_database_insert_and_duplicate(tmp_path: Path):
    db_path = tmp_path / "db.sqlite"
    db = Database(path=str(db_path))

    action = ActionRecord(
        account="acc1",
        email_id="1",
        sender="a@example.com",
        subject="hi",
        classification="junk",
        action_taken="archive",
        unsubscribe_attempted=False,
        timestamp=datetime.utcnow(),
        content_hash="hash1",
    )
    db.add_action(action)
    assert db.is_duplicate_hash("hash1") is True


def test_sender_junk_counter(tmp_path: Path):
    db = Database(path=str(tmp_path / "db.sqlite"))
    db.sender_junk_increment("x@example.com")
    db.sender_junk_increment("x@example.com")
    assert db.sender_junk_count("x@example.com") == 2

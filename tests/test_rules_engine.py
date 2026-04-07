import pytest
from datetime import datetime

from src.models import EmailMessage
from src import rules_engine
from src.config import settings


def make_email(subject="", body="", from_email="test@example.com", headers=None):
    return EmailMessage(
        id="1",
        from_email=from_email,
        subject=subject,
        snippet="",
        body=body,
        headers=headers or {},
        labels=[],
        has_attachments=False,
        internal_date=datetime.utcnow(),
    )


def test_important_keyword_rule():
    email = make_email(subject="Password reset", body="")
    result = rules_engine.apply_rules(email)
    assert result is not None
    assert result.label == "important"


def test_junk_keyword_rule():
    email = make_email(subject="Special offer for you")
    result = rules_engine.apply_rules(email)
    assert result is not None
    assert result.label == "junk"


def test_list_unsubscribe_rule():
    email = make_email(headers={"List-Unsubscribe": "<mailto:unsubscribe@example.com>"})
    result = rules_engine.apply_rules(email)
    assert result is not None
    assert result.label == "junk"


def test_allowlist_overrides(monkeypatch):
    monkeypatch.setattr(settings, "ALLOWED_SENDERS", ["vip@example.com"])
    email = make_email(from_email="vip@example.com")
    result = rules_engine.apply_rules(email)
    assert result.label == "important"


def test_safe_delete_blocker():
    email = make_email(subject="Action required now")
    assert rules_engine.safe_delete_allowed(email) is False

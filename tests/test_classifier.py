from datetime import datetime

from src.models import EmailMessage
from src.classifier import classify_email
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


def test_classifier_uses_rules():
    email = make_email(subject="invoice #123")
    result = classify_email(email)
    assert result.label == "important"


def test_classifier_fallback_to_manual_review(monkeypatch):
    monkeypatch.setattr(settings, "ENABLE_LLM", False)
    email = make_email(subject="hello")
    result = classify_email(email)
    assert result.label == "manual_review"


def test_classifier_junk_rules():
    email = make_email(subject="special offer")
    result = classify_email(email)
    assert result.label == "junk"

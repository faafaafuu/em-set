from __future__ import annotations

from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class EmailMessage(BaseModel):
    id: str
    thread_id: Optional[str] = None
    from_email: str
    subject: str
    snippet: str
    body: str
    headers: dict[str, str] = Field(default_factory=dict)
    labels: List[str] = Field(default_factory=list)
    has_attachments: bool = False
    internal_date: Optional[datetime] = None


class ClassificationResult(BaseModel):
    label: str  # important/useful/junk/manual_review
    confidence: float
    reason: str
    rule_hit: Optional[str] = None
    llm_used: bool = False


class ActionRecord(BaseModel):
    account: str
    email_id: str
    sender: str
    subject: str
    classification: str
    action_taken: str
    unsubscribe_attempted: bool
    timestamp: datetime
    content_hash: str


class UnsubscribeResult(BaseModel):
    attempted: bool
    success: bool
    method: Optional[str] = None  # mailto/url
    detail: Optional[str] = None


class ManualReviewItem(BaseModel):
    account: str
    email_id: str
    sender: str
    subject: str
    reason: str
    created_at: datetime

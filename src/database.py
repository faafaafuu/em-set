from __future__ import annotations

import os
import sqlite3
from datetime import datetime
from typing import List, Optional, Tuple

from .config import settings
from .models import ActionRecord, ManualReviewItem


class Database:
    def __init__(self, path: Optional[str] = None) -> None:
        self.path = path or settings.DATABASE_PATH
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._get_conn() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS actions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    account TEXT,
                    email_id TEXT,
                    sender TEXT,
                    subject TEXT,
                    classification TEXT,
                    action_taken TEXT,
                    unsubscribe_attempted INTEGER,
                    timestamp TEXT,
                    content_hash TEXT
                )
                """
            )
            conn.execute(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS idx_actions_hash
                ON actions(content_hash)
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS manual_review (
                    account TEXT,
                    email_id TEXT,
                    sender TEXT,
                    subject TEXT,
                    reason TEXT,
                    created_at TEXT,
                    PRIMARY KEY (account, email_id)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS sender_stats (
                    sender TEXT PRIMARY KEY,
                    junk_count INTEGER,
                    last_seen TEXT
                )
                """
            )

    def add_action(self, action: ActionRecord) -> None:
        with self._get_conn() as conn:
            conn.execute(
                """
                INSERT INTO actions(account, email_id, sender, subject, classification, action_taken,
                                    unsubscribe_attempted, timestamp, content_hash)
                VALUES(?,?,?,?,?,?,?,?,?)
                """,
                (
                    action.account,
                    action.email_id,
                    action.sender,
                    action.subject,
                    action.classification,
                    action.action_taken,
                    1 if action.unsubscribe_attempted else 0,
                    action.timestamp.isoformat(),
                    action.content_hash,
                ),
            )

    def recent_actions(self, limit: int = 50) -> List[dict]:
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM actions ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
        return [dict(r) for r in rows]

    def stats(self) -> dict:
        with self._get_conn() as conn:
            rows = conn.execute(
                """
                SELECT classification, COUNT(*) as cnt
                FROM actions
                GROUP BY classification
                """
            ).fetchall()
        return {r["classification"]: r["cnt"] for r in rows}

    def stats_since(self, iso_timestamp: str) -> dict:
        with self._get_conn() as conn:
            rows = conn.execute(
                """
                SELECT classification, COUNT(*) as cnt
                FROM actions
                WHERE timestamp >= ?
                GROUP BY classification
                """,
                (iso_timestamp,),
            ).fetchall()
        return {r["classification"]: r["cnt"] for r in rows}

    def add_manual_review(self, item: ManualReviewItem) -> None:
        with self._get_conn() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO manual_review(account, email_id, sender, subject, reason, created_at)
                VALUES(?,?,?,?,?,?)
                """,
                (
                    item.account,
                    item.email_id,
                    item.sender,
                    item.subject,
                    item.reason,
                    item.created_at.isoformat(),
                ),
            )

    def list_manual_review(self, limit: int = 50) -> List[dict]:
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM manual_review ORDER BY created_at DESC LIMIT ?", (limit,)
            ).fetchall()
        return [dict(r) for r in rows]

    def remove_manual_review(self, account: str, email_id: str) -> None:
        with self._get_conn() as conn:
            conn.execute("DELETE FROM manual_review WHERE account = ? AND email_id = ?", (account, email_id))

    def sender_junk_increment(self, sender: str) -> None:
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT junk_count FROM sender_stats WHERE sender = ?", (sender,)
            ).fetchone()
            if row:
                conn.execute(
                    "UPDATE sender_stats SET junk_count = junk_count + 1, last_seen = ? WHERE sender = ?",
                    (datetime.utcnow().isoformat(), sender),
                )
            else:
                conn.execute(
                    "INSERT INTO sender_stats(sender, junk_count, last_seen) VALUES(?,?,?)",
                    (sender, 1, datetime.utcnow().isoformat()),
                )

    def sender_junk_count(self, sender: str) -> int:
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT junk_count FROM sender_stats WHERE sender = ?", (sender,)
            ).fetchone()
        return int(row["junk_count"]) if row else 0

    def is_duplicate_hash(self, content_hash: str) -> bool:
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT 1 FROM actions WHERE content_hash = ?", (content_hash,)
            ).fetchone()
        return row is not None

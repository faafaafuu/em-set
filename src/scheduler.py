from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import List

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from .database import Database
from .processor import EmailProcessor
from .config import settings
from .notifier import send_summary

logger = logging.getLogger(__name__)


def start_scheduler(processors: List[EmailProcessor], db: Database) -> BackgroundScheduler:
    scheduler = BackgroundScheduler()

    for p in processors:
        scheduler.add_job(
            p.scan_and_process,
            "interval",
            minutes=settings.SCAN_INTERVAL_MINUTES,
            id=f"scan_job_{p.account}",
            replace_existing=True,
        )

    scheduler.add_job(
        lambda: daily_summary(processors, db),
        CronTrigger(hour=9, minute=0),
        id="daily_summary",
        replace_existing=True,
    )

    scheduler.add_job(
        lambda: weekly_cleanup(db),
        CronTrigger(day_of_week="sun", hour=2, minute=0),
        id="weekly_cleanup",
        replace_existing=True,
    )

    scheduler.start()
    return scheduler


def daily_summary(processors: List[EmailProcessor], db: Database) -> None:
    since = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    stats = db.stats_since(since)
    logger.info("Daily summary (last 24h): %s", stats)
    # send to first account by default
    if processors:
        send_summary(processors[0].gmail, stats)


def weekly_cleanup(db: Database) -> None:
    logger.info("Weekly cleanup executed")

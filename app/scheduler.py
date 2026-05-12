"""APScheduler setup.

Dua jenis job:
  1. `scrape_product` — dijalankan segera saat produk baru ditambahkan.
  2. `publish_scheduled` — dijalankan pada `ScheduledPost.scheduled_at`.

Kita pakai `BackgroundScheduler` (in-process) dengan SQLAlchemyJobStore supaya
job persistent antar restart.
"""
from __future__ import annotations

from datetime import datetime

from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.schedulers.background import BackgroundScheduler

from app.config import get_settings
from app.services.post_service import publish_scheduled, scrape_product

_settings = get_settings()

scheduler = BackgroundScheduler(
    jobstores={
        "default": SQLAlchemyJobStore(url=_settings.database_url),
    },
    timezone=_settings.timezone,
)


def start() -> None:
    if not scheduler.running:
        scheduler.start()


def shutdown() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)


def enqueue_scrape(product_id: int) -> None:
    scheduler.add_job(
        scrape_product,
        trigger="date",
        run_date=datetime.utcnow(),
        args=[product_id],
        id=f"scrape-{product_id}",
        replace_existing=True,
    )


def enqueue_publish(scheduled_post_id: int, run_at: datetime) -> None:
    scheduler.add_job(
        publish_scheduled,
        trigger="date",
        run_date=run_at,
        args=[scheduled_post_id],
        id=f"publish-{scheduled_post_id}",
        replace_existing=True,
    )

"""Orchestration: scrape produk, format caption, publish ke platform."""
from __future__ import annotations

import logging
from datetime import datetime

from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import (
    PostLog,
    PostStatus,
    Product,
    ProductStatus,
    ScheduledPost,
)
from app.publishers import get_publisher
from app.scrapers import detect_source, get_scraper

log = logging.getLogger(__name__)

# Batas karakter kira-kira (X = 280, Threads = 500). Kita conservative.
MAX_CAPTION_LEN = 270


def scrape_product(product_id: int) -> None:
    """Ambil metadata produk dari URL dan simpan ke DB."""
    with SessionLocal() as db:
        product = db.get(Product, product_id)
        if not product:
            return
        source = detect_source(product.url)
        if not source:
            product.status = ProductStatus.failed
            product.error = "Unknown source (URL bukan Shopee/TikTok)"
            db.commit()
            return
        try:
            data = get_scraper(source).fetch(product.url)
            product.title = data.title
            product.price = data.price
            product.image_url = data.image_url
            product.description = data.description
            product.status = ProductStatus.ready
            product.error = None
        except Exception as e:  # noqa: BLE001
            log.exception("scrape failed")
            product.status = ProductStatus.failed
            product.error = str(e)[:500]
        db.commit()


def build_caption(product: Product, template: str | None = None) -> str:
    """Buat caption default. `template` boleh pakai placeholder {title} {price} {url}."""
    tpl = template or "{title}\n{price}\n\nCheck it out: {url}"
    text = tpl.format(
        title=product.title or "",
        price=product.price or "",
        url=product.url,
    )
    if len(text) > MAX_CAPTION_LEN:
        text = text[: MAX_CAPTION_LEN - 1].rstrip() + "…"
    return text


def publish_scheduled(scheduled_post_id: int) -> None:
    """Dipanggil scheduler pada waktu terjadwal."""
    with SessionLocal() as db:
        sp = db.get(ScheduledPost, scheduled_post_id)
        if not sp or sp.status != PostStatus.scheduled:
            return
        product = sp.product
        if product.status != ProductStatus.ready:
            _log(db, sp, False, message=f"Product not ready (status={product.status})")
            sp.status = PostStatus.failed
            db.commit()
            return

        caption = sp.caption or build_caption(product)
        publisher = get_publisher(sp.platform)
        result = publisher.post(caption, image_url=product.image_url)

        _log(db, sp, result.success, result.remote_post_id, result.message)
        sp.status = PostStatus.posted if result.success else PostStatus.failed
        db.commit()


def _log(
    db: Session,
    sp: ScheduledPost,
    success: bool,
    remote_post_id: str | None = None,
    message: str | None = None,
) -> None:
    db.add(
        PostLog(
            scheduled_post_id=sp.id,
            attempted_at=datetime.utcnow(),
            success=success,
            remote_post_id=remote_post_id,
            message=message,
        )
    )

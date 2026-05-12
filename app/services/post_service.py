"""Orchestration: scrape produk, format caption, publish ke platform."""
from __future__ import annotations

import logging
from datetime import datetime

from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import (
    Platform,
    PostLog,
    PostStatus,
    Product,
    ProductStatus,
    ScheduledPost,
)
from app.publishers import get_publisher
from app.scrapers import detect_source, get_scraper

log = logging.getLogger(__name__)

# Batas karakter per platform. Threads 500, X 280.
# Kita kurangi sedikit untuk margin aman (emoji counts differently, dsb.)
CAPTION_LIMITS: dict[Platform, int] = {
    Platform.threads: 490,
    Platform.twitter: 275,
}

DEFAULT_TEMPLATE = "{title}\n{price}\n\nCheck it out: {url}"


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


def build_caption(
    product: Product,
    platform: Platform,
    template: str | None = None,
) -> str:
    """Buat caption untuk platform tertentu.

    - Placeholder: {title}, {price}, {url}
    - Jika kepanjangan: pangkas **{title}** lebih dulu (URL & price tetap) supaya
      link tetap bisa diklik. Ini lebih baik daripada potong di ekor.
    """
    tpl = template or DEFAULT_TEMPLATE
    limit = CAPTION_LIMITS.get(platform, 275)

    title = product.title or ""
    price = product.price or ""
    url = product.url

    # Coba dulu dengan title full
    text = tpl.format(title=title, price=price, url=url)
    if len(text) <= limit:
        return text

    # Hitung budget untuk title: limit - panjang semua field non-title dalam template
    fixed = tpl.format(title="", price=price, url=url)
    budget = limit - len(fixed) - 1  # -1 untuk ellipsis
    if budget < 10:
        # Template-nya sudah kepanjangan bahkan tanpa title — fallback potong ekor
        return text[: limit - 1].rstrip() + "…"

    trimmed_title = title[:budget].rstrip() + "…"
    return tpl.format(title=trimmed_title, price=price, url=url)


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

        caption = sp.caption or build_caption(product, sp.platform)
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

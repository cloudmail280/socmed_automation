"""Shopee scraper.

Strategi: parse shopid & itemid dari URL, panggil endpoint JSON publik
`/api/v4/item/get?itemid=...&shopid=...`. Endpoint ini sering dipakai
oleh frontend Shopee sendiri.

CATATAN: Shopee rajin ganti struktur & ketat soal anti-bot. Implementasi
ini adalah skeleton yang perlu di-tune (rotasi header, proxy) untuk
pemakaian nyata.
"""
from __future__ import annotations

import re

import httpx

from app.config import get_settings
from app.scrapers.base import BaseScraper, ProductData

_ID_PATTERNS = [
    # https://shopee.co.id/Product-Name-i.<shopid>.<itemid>
    re.compile(r"i\.(?P<shop>\d+)\.(?P<item>\d+)"),
    # https://shopee.co.id/product/<shopid>/<itemid>
    re.compile(r"/product/(?P<shop>\d+)/(?P<item>\d+)"),
]


class ShopeeScraper(BaseScraper):
    API_URL = "https://shopee.co.id/api/v4/item/get"

    def __init__(self) -> None:
        s = get_settings()
        self._client = httpx.Client(
            timeout=s.scraper_timeout,
            headers={
                "User-Agent": s.scraper_user_agent,
                "Accept": "application/json",
                "Referer": "https://shopee.co.id/",
                "X-Requested-With": "XMLHttpRequest",
            },
        )

    @staticmethod
    def _extract_ids(url: str) -> tuple[str, str]:
        for pat in _ID_PATTERNS:
            m = pat.search(url)
            if m:
                return m.group("shop"), m.group("item")
        raise ValueError(f"Cannot parse Shopee IDs from URL: {url}")

    def fetch(self, url: str) -> ProductData:
        shop_id, item_id = self._extract_ids(url)
        r = self._client.get(self.API_URL, params={"itemid": item_id, "shopid": shop_id})
        r.raise_for_status()
        data = r.json().get("data") or {}
        if not data:
            raise RuntimeError("Empty Shopee response (rate-limited or invalid item)")

        title = data.get("name") or "Produk Shopee"
        price_raw = data.get("price")  # price × 100000
        price = f"Rp{int(price_raw) / 100000:,.0f}" if price_raw else None

        image_hash = (data.get("images") or [None])[0]
        image_url = (
            f"https://cf.shopee.co.id/file/{image_hash}" if image_hash else None
        )
        description = data.get("description")

        return ProductData(
            title=title,
            price=price,
            image_url=image_url,
            description=description,
            url=url,
        )

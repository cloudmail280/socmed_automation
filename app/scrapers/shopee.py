"""Shopee scraper.

Strategi: parse shopid & itemid dari URL, panggil endpoint JSON publik
`/api/v4/item/get?itemid=...&shopid=...`. Endpoint ini sering dipakai
oleh frontend Shopee sendiri.

Kita pisah:
  - `_extract_ids(url)`     : murni string parsing → mudah di-test
  - `_parse_payload(data)`  : murni dict → ProductData → mudah di-test
  - `fetch(url)`            : I/O nyata (httpx), bisa di-inject client

CATATAN: Shopee rajin ganti struktur & ketat soal anti-bot. Implementasi
ini adalah skeleton yang perlu di-tune (rotasi header, proxy) untuk
pemakaian nyata.
"""
from __future__ import annotations

import re
from typing import Any

import httpx

from app.config import get_settings
from app.scrapers.base import BaseScraper, ProductData
from app.utils.retry import retry

_ID_PATTERNS = [
    # https://shopee.co.id/Product-Name-i.<shopid>.<itemid>
    re.compile(r"i\.(?P<shop>\d+)\.(?P<item>\d+)"),
    # https://shopee.co.id/product/<shopid>/<itemid>
    re.compile(r"/product/(?P<shop>\d+)/(?P<item>\d+)"),
]

# Exceptions yang layak di-retry (network + 5xx). 4xx lain biarkan fail cepat.
_RETRYABLE = (httpx.TransportError, httpx.TimeoutException)


class ShopeeScraper(BaseScraper):
    API_URL = "https://shopee.co.id/api/v4/item/get"

    def __init__(self, client: httpx.Client | None = None) -> None:
        s = get_settings()
        self._client = client or httpx.Client(
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

    @staticmethod
    def _parse_payload(payload: dict[str, Any], url: str) -> ProductData:
        data = payload.get("data") or {}
        if not data:
            raise RuntimeError("Empty Shopee response (rate-limited or invalid item)")

        title = data.get("name") or "Produk Shopee"
        price_raw = data.get("price")  # Shopee menyimpan harga × 100000
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

    @retry(attempts=3, base_delay=1.0, exceptions=_RETRYABLE)
    def _get(self, shop_id: str, item_id: str) -> dict[str, Any]:
        r = self._client.get(
            self.API_URL, params={"itemid": item_id, "shopid": shop_id}
        )
        r.raise_for_status()
        return r.json()

    def fetch(self, url: str) -> ProductData:
        shop_id, item_id = self._extract_ids(url)
        payload = self._get(shop_id, item_id)
        return self._parse_payload(payload, url)

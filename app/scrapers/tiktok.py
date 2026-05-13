"""TikTok scraper.

TikTok Shop & video page membutuhkan rendering JavaScript, jadi kita pakai
Playwright (headless Chromium) untuk load halaman lalu ekstrak metadata
dari `<meta>` tag Open Graph + JSON-LD.

Desain dipisah supaya testable:
  - `_parse_html(html, url)` : murni string → ProductData (unit-testable)
  - `_render(url)`           : I/O nyata (Playwright)
  - `fetch(url)`             : _render → _parse_html, dibungkus retry

CATATAN: TikTok punya anti-bot yang agresif. Untuk pemakaian rutin kamu
perlu rotasi user-agent & proxy residential, delay antar request, dan
fallback manual kalau gagal.

Install browser sekali: `playwright install chromium`.
"""
from __future__ import annotations

import json
import re

from app.scrapers.base import BaseScraper, ProductData
from app.utils.retry import retry


class TikTokScraper(BaseScraper):
    # TikTok flaky — retry lebih agresif sedikit
    @retry(attempts=3, base_delay=2.0)
    def fetch(self, url: str) -> ProductData:
        html = self._render(url)
        return self._parse_html(html, url)

    # --- I/O ---------------------------------------------------------------
    def _render(self, url: str) -> str:
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as e:  # pragma: no cover
            raise RuntimeError(
                "Playwright belum terinstall. Jalankan `pip install playwright` "
                "dan `playwright install chromium`."
            ) from e

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            ctx = browser.new_context()
            page = ctx.new_page()
            page.goto(url, wait_until="domcontentloaded", timeout=30_000)
            page.wait_for_timeout(2_000)  # biar JS sempat render
            content = page.content()
            browser.close()
            return content

    # --- Pure parsing (unit-testable) --------------------------------------
    @staticmethod
    def _meta(html: str, prop: str) -> str | None:
        m = re.search(
            rf'<meta[^>]+property=["\']{re.escape(prop)}["\'][^>]+content=["\']([^"\']+)["\']',
            html,
            re.I,
        )
        return m.group(1) if m else None

    @classmethod
    def _parse_html(cls, html: str, url: str) -> ProductData:
        title = cls._meta(html, "og:title") or "Produk TikTok"
        image_url = cls._meta(html, "og:image")
        description = cls._meta(html, "og:description")

        price: str | None = None
        for m in re.finditer(
            r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.+?)</script>',
            html,
            re.I | re.S,
        ):
            try:
                data = json.loads(m.group(1))
            except json.JSONDecodeError:
                continue
            offers = (data or {}).get("offers") if isinstance(data, dict) else None
            if isinstance(offers, dict):
                amount = offers.get("price") or offers.get("lowPrice")
                currency = offers.get("priceCurrency", "")
                if amount:
                    price = f"{currency} {amount}".strip()
                    break

        return ProductData(
            title=title,
            price=price,
            image_url=image_url,
            description=description,
            url=url,
        )

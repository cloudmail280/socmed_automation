"""TikTok scraper.

TikTok Shop & video page membutuhkan rendering JavaScript, jadi kita pakai
Playwright (headless Chromium) untuk load halaman lalu ekstrak metadata
dari `<meta>` tag Open Graph + JSON-LD.

CATATAN: TikTok punya anti-bot yang agresif. Untuk pemakaian rutin kamu
perlu:
  - Rotasi user-agent & proxy residential
  - Delay antar request
  - Fallback manual kalau gagal

Install browser sekali: `playwright install chromium`.
"""
from __future__ import annotations

import json
import re

from app.scrapers.base import BaseScraper, ProductData


class TikTokScraper(BaseScraper):
    def fetch(self, url: str) -> ProductData:
        # Import lazy supaya test/dev tanpa Playwright tetep bisa load module.
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as e:  # pragma: no cover
            raise RuntimeError(
                "Playwright belum terinstall. Jalankan `pip install playwright` "
                "dan `playwright install chromium`."
            ) from e

        html = self._render(url, sync_playwright)
        return self._parse(html, url)

    def _render(self, url: str, sync_playwright) -> str:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            ctx = browser.new_context()
            page = ctx.new_page()
            page.goto(url, wait_until="domcontentloaded", timeout=30_000)
            # Kasih waktu JS render produk
            page.wait_for_timeout(2_000)
            content = page.content()
            browser.close()
            return content

    @staticmethod
    def _meta(html: str, prop: str) -> str | None:
        m = re.search(
            rf'<meta[^>]+property=["\']{re.escape(prop)}["\'][^>]+content=["\']([^"\']+)["\']',
            html,
            re.I,
        )
        return m.group(1) if m else None

    def _parse(self, html: str, url: str) -> ProductData:
        title = self._meta(html, "og:title") or "Produk TikTok"
        image_url = self._meta(html, "og:image")
        description = self._meta(html, "og:description")

        price = None
        # Coba tarik dari JSON-LD kalau ada
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

"""Unit tests untuk TikTok scraper (parsing saja, tanpa browser)."""
from __future__ import annotations

from pathlib import Path

from app.scrapers.tiktok import TikTokScraper

FIX = Path(__file__).parent / "fixtures"


def test_parse_product_with_jsonld_offer():
    html = (FIX / "tiktok_product.html").read_text()
    data = TikTokScraper._parse_html(html, "https://www.tiktok.com/@x/video/123")
    assert data.title == "Wireless Earbuds ANC Pro"
    assert data.image_url == "https://p16-sign.tiktokcdn.com/img/abc.jpg"
    assert data.description.startswith("ANC aktif")
    assert data.price == "IDR 499000"


def test_parse_html_without_price():
    html = (FIX / "tiktok_no_price.html").read_text()
    data = TikTokScraper._parse_html(html, "https://www.tiktok.com/@y/video/456")
    assert data.title == "Video Kucing Lucu"
    assert data.image_url.endswith("thumb.jpg")
    assert data.price is None


def test_parse_missing_meta_falls_back_to_default_title():
    data = TikTokScraper._parse_html("<html><body></body></html>", "http://x")
    assert data.title == "Produk TikTok"
    assert data.image_url is None
    assert data.price is None

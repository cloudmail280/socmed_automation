"""Scraper registry — pilih scraper berdasarkan URL."""
from app.models import Source
from app.scrapers.base import BaseScraper, ProductData
from app.scrapers.shopee import ShopeeScraper
from app.scrapers.tiktok import TikTokScraper


def detect_source(url: str) -> Source | None:
    u = url.lower()
    if "shopee." in u:
        return Source.shopee
    if "tiktok.com" in u or "vt.tiktok" in u:
        return Source.tiktok
    return None


def get_scraper(source: Source) -> BaseScraper:
    if source == Source.shopee:
        return ShopeeScraper()
    if source == Source.tiktok:
        return TikTokScraper()
    raise ValueError(f"No scraper for source {source}")


__all__ = ["BaseScraper", "ProductData", "detect_source", "get_scraper"]

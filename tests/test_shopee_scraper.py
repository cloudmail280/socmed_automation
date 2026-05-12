"""Unit tests untuk Shopee scraper (pure parsing + injected client)."""
from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest

from app.scrapers.shopee import ShopeeScraper

FIX = Path(__file__).parent / "fixtures"


def _load(name: str) -> dict:
    return json.loads((FIX / name).read_text())


class TestExtractIds:
    def test_slug_style(self):
        url = "https://shopee.co.id/Sepatu-Keren-i.987.123456789"
        assert ShopeeScraper._extract_ids(url) == ("987", "123456789")

    def test_product_style(self):
        url = "https://shopee.co.id/product/987/123456789"
        assert ShopeeScraper._extract_ids(url) == ("987", "123456789")

    def test_invalid_url(self):
        with pytest.raises(ValueError):
            ShopeeScraper._extract_ids("https://tokopedia.com/x/y")


class TestParsePayload:
    def test_full_product(self):
        url = "https://shopee.co.id/x-i.987.123"
        data = ShopeeScraper._parse_payload(_load("shopee_item.json"), url)
        assert data.title == "Sepatu Lari Pro X"
        # 34990000000 / 100000 = 349900
        assert data.price == "Rp349,900"
        assert data.image_url == "https://cf.shopee.co.id/file/abcd1234efgh5678"
        assert data.description.startswith("Sepatu lari ringan")
        assert data.url == url

    def test_empty_data_raises(self):
        with pytest.raises(RuntimeError):
            ShopeeScraper._parse_payload(_load("shopee_empty.json"), "http://x")


class TestFetchWithMock:
    def test_fetch_end_to_end(self):
        payload = _load("shopee_item.json")

        def handler(request: httpx.Request) -> httpx.Response:
            assert request.url.path == "/api/v4/item/get"
            assert request.url.params["shopid"] == "987"
            assert request.url.params["itemid"] == "123"
            return httpx.Response(200, json=payload)

        client = httpx.Client(
            transport=httpx.MockTransport(handler),
            base_url="https://shopee.co.id",
        )
        scraper = ShopeeScraper(client=client)
        result = scraper.fetch("https://shopee.co.id/slug-i.987.123")
        assert result.title == "Sepatu Lari Pro X"

    def test_fetch_retries_on_transport_error(self):
        """Gagal 2x (ConnectError), sukses di attempt ke-3."""
        payload = _load("shopee_item.json")
        calls = {"n": 0}

        def handler(request: httpx.Request) -> httpx.Response:
            calls["n"] += 1
            if calls["n"] < 3:
                raise httpx.ConnectError("boom", request=request)
            return httpx.Response(200, json=payload)

        client = httpx.Client(
            transport=httpx.MockTransport(handler),
            base_url="https://shopee.co.id",
        )
        scraper = ShopeeScraper(client=client)
        # Hilangkan delay supaya test cepat
        scraper._get.__wrapped__  # sanity: dekorator ada
        result = scraper.fetch("https://shopee.co.id/x-i.1.2")
        assert result.title == "Sepatu Lari Pro X"
        assert calls["n"] == 3

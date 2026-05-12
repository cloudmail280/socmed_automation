"""Tests untuk caption builder: per-platform limit & smart trimming."""
from __future__ import annotations

from types import SimpleNamespace

from app.models import Platform
from app.services.post_service import CAPTION_LIMITS, build_caption


def _product(title: str, price: str = "Rp99,000", url: str = "https://x.id/p/1"):
    return SimpleNamespace(title=title, price=price, url=url)


def test_short_caption_unchanged():
    p = _product("Sepatu Lari")
    out = build_caption(p, Platform.twitter)
    assert "Sepatu Lari" in out
    assert "Rp99,000" in out
    assert p.url in out
    assert len(out) <= CAPTION_LIMITS[Platform.twitter]


def test_twitter_limit_enforced():
    p = _product("A" * 500)
    out = build_caption(p, Platform.twitter)
    assert len(out) <= CAPTION_LIMITS[Platform.twitter]
    # URL harus tetap ada (kita potong title, bukan ekor)
    assert p.url in out
    # Ellipsis menandakan title di-trim
    assert "…" in out


def test_threads_allows_more_than_twitter():
    p = _product("B" * 400)
    twitter_out = build_caption(p, Platform.twitter)
    threads_out = build_caption(p, Platform.threads)
    assert len(threads_out) > len(twitter_out)
    assert len(threads_out) <= CAPTION_LIMITS[Platform.threads]


def test_custom_template_with_placeholders():
    p = _product("Headphone XYZ", price="$49")
    out = build_caption(p, Platform.twitter, template="New: {title} — {price}\n{url}")
    assert out == "New: Headphone XYZ — $49\nhttps://x.id/p/1"


def test_url_preserved_when_title_trimmed():
    """Regression: saat title di-trim, URL tetap utuh & bisa diklik."""
    p = _product("X" * 1000, url="https://shopee.co.id/penting-i.1.2")
    out = build_caption(p, Platform.twitter)
    assert "https://shopee.co.id/penting-i.1.2" in out

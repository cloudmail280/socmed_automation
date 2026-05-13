"""Tests untuk retry util."""
from __future__ import annotations

import pytest

from app.utils.retry import retry


def test_retry_succeeds_first_try():
    calls = {"n": 0}

    @retry(attempts=3, base_delay=0)
    def fn() -> str:
        calls["n"] += 1
        return "ok"

    assert fn() == "ok"
    assert calls["n"] == 1


def test_retry_succeeds_after_failures():
    calls = {"n": 0}

    @retry(attempts=3, base_delay=0)
    def fn() -> str:
        calls["n"] += 1
        if calls["n"] < 3:
            raise ValueError("flaky")
        return "ok"

    assert fn() == "ok"
    assert calls["n"] == 3


def test_retry_raises_after_exhausting_attempts():
    calls = {"n": 0}

    @retry(attempts=2, base_delay=0)
    def fn() -> None:
        calls["n"] += 1
        raise RuntimeError("never")

    with pytest.raises(RuntimeError, match="never"):
        fn()
    assert calls["n"] == 2


def test_retry_only_catches_specified_exceptions():
    calls = {"n": 0}

    @retry(attempts=3, base_delay=0, exceptions=(ValueError,))
    def fn() -> None:
        calls["n"] += 1
        raise TypeError("not retryable")

    with pytest.raises(TypeError):
        fn()
    assert calls["n"] == 1  # tidak di-retry

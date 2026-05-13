"""Tests untuk BasicAuthMiddleware (pakai Starlette TestClient)."""
from __future__ import annotations

import base64

import pytest
from starlette.applications import Starlette
from starlette.responses import PlainTextResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from app.auth import BasicAuthMiddleware


def _make_app() -> Starlette:
    async def home(_):
        return PlainTextResponse("home")

    async def health(_):
        return PlainTextResponse("ok")

    app = Starlette(routes=[Route("/", home), Route("/healthz", health)])
    app.add_middleware(BasicAuthMiddleware, username="admin", password="s3cret")
    return app


@pytest.fixture
def client() -> TestClient:
    return TestClient(_make_app())


def _basic(user: str, pw: str) -> dict[str, str]:
    token = base64.b64encode(f"{user}:{pw}".encode()).decode()
    return {"Authorization": f"Basic {token}"}


def test_no_credentials_returns_401(client: TestClient):
    r = client.get("/")
    assert r.status_code == 401
    assert r.headers.get("www-authenticate", "").lower().startswith("basic")


def test_wrong_password_returns_401(client: TestClient):
    r = client.get("/", headers=_basic("admin", "wrong"))
    assert r.status_code == 401


def test_correct_credentials_pass(client: TestClient):
    r = client.get("/", headers=_basic("admin", "s3cret"))
    assert r.status_code == 200
    assert r.text == "home"


def test_healthz_excluded_from_auth(client: TestClient):
    r = client.get("/healthz")
    assert r.status_code == 200


def test_malformed_header_returns_401(client: TestClient):
    r = client.get("/", headers={"Authorization": "Basic !!!not-base64!!!"})
    assert r.status_code == 401

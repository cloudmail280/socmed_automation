"""HTTP Basic Auth middleware.

Dipasang di `main.py` kalau `AUTH_USERNAME` & `AUTH_PASSWORD` diisi di .env.
Kalau keduanya kosong, middleware tidak diaktifkan (dev mode).

Path yang di-exclude (health check, static) bisa diatur di constructor.
"""
from __future__ import annotations

import base64
import hmac

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class BasicAuthMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app,
        *,
        username: str,
        password: str,
        exclude_paths: tuple[str, ...] = ("/healthz", "/static"),
        realm: str = "socmed-automation",
    ) -> None:
        super().__init__(app)
        self._username = username
        self._password = password
        self._exclude_paths = exclude_paths
        self._realm = realm

    def _is_excluded(self, path: str) -> bool:
        return any(path == p or path.startswith(p + "/") for p in self._exclude_paths)

    def _check(self, header: str | None) -> bool:
        if not header or not header.lower().startswith("basic "):
            return False
        try:
            decoded = base64.b64decode(header.split(" ", 1)[1]).decode("utf-8")
        except (ValueError, UnicodeDecodeError):
            return False
        user, _, pw = decoded.partition(":")
        # constant-time compare untuk hindari timing attack
        return hmac.compare_digest(user, self._username) and hmac.compare_digest(
            pw, self._password
        )

    async def dispatch(self, request: Request, call_next):
        if self._is_excluded(request.url.path):
            return await call_next(request)
        if self._check(request.headers.get("authorization")):
            return await call_next(request)
        return Response(
            status_code=401,
            content="Unauthorized",
            headers={"WWW-Authenticate": f'Basic realm="{self._realm}"'},
        )

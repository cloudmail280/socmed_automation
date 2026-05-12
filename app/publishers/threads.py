"""Threads (Meta) publisher via Graph API.

Flow dua langkah:
  1. POST /{user_id}/threads  -> bikin container (media_type=TEXT/IMAGE)
  2. POST /{user_id}/threads_publish  -> publish container

Docs: https://developers.facebook.com/docs/threads
"""
from __future__ import annotations

import httpx

from app.config import get_settings
from app.publishers.base import BasePublisher, PublishResult
from app.utils.retry import retry

GRAPH_BASE = "https://graph.threads.net/v1.0"
_RETRYABLE = (httpx.TransportError, httpx.TimeoutException)


class ThreadsPublisher(BasePublisher):
    def __init__(self) -> None:
        s = get_settings()
        self.token = s.threads_access_token
        self.user_id = s.threads_user_id
        self._client = httpx.Client(timeout=30)

    @retry(attempts=3, base_delay=1.5, exceptions=_RETRYABLE)
    def _create_container(self, text: str, image_url: str | None) -> str:
        params = {
            "access_token": self.token,
            "text": text,
        }
        if image_url:
            params["media_type"] = "IMAGE"
            params["image_url"] = image_url
        else:
            params["media_type"] = "TEXT"

        r = self._client.post(f"{GRAPH_BASE}/{self.user_id}/threads", params=params)
        r.raise_for_status()
        return r.json()["id"]

    @retry(attempts=3, base_delay=1.5, exceptions=_RETRYABLE)
    def _publish_container(self, container_id: str) -> str:
        r = self._client.post(
            f"{GRAPH_BASE}/{self.user_id}/threads_publish",
            params={"creation_id": container_id, "access_token": self.token},
        )
        r.raise_for_status()
        return r.json()["id"]

    def post(self, text: str, image_url: str | None = None) -> PublishResult:
        if not self.token or not self.user_id:
            return PublishResult(
                success=False, message="Threads credentials missing in .env"
            )
        try:
            container_id = self._create_container(text, image_url)
            post_id = self._publish_container(container_id)
            return PublishResult(success=True, remote_post_id=post_id)
        except httpx.HTTPStatusError as e:
            return PublishResult(
                success=False, message=f"HTTP {e.response.status_code}: {e.response.text[:300]}"
            )
        except Exception as e:  # noqa: BLE001
            return PublishResult(success=False, message=str(e))

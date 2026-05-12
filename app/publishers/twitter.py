"""X (Twitter) publisher via API v2 + media upload via v1.1.

Free tier: 500 post / bulan. Media upload butuh OAuth 1.0a user context.
"""
from __future__ import annotations

import tempfile
from pathlib import Path

import httpx

from app.config import get_settings
from app.publishers.base import BasePublisher, PublishResult
from app.utils.retry import retry

_RETRYABLE = (httpx.TransportError, httpx.TimeoutException)


class TwitterPublisher(BasePublisher):
    def __init__(self) -> None:
        s = get_settings()
        self._settings = s
        self._api_v1 = None
        self._client_v2 = None

    def _lazy_init(self) -> None:
        if self._client_v2 is not None:
            return
        import tweepy  # imported lazily to avoid hard dep at import time

        s = self._settings
        auth = tweepy.OAuth1UserHandler(
            s.x_api_key, s.x_api_secret, s.x_access_token, s.x_access_token_secret
        )
        self._api_v1 = tweepy.API(auth)
        self._client_v2 = tweepy.Client(
            bearer_token=s.x_bearer_token or None,
            consumer_key=s.x_api_key,
            consumer_secret=s.x_api_secret,
            access_token=s.x_access_token,
            access_token_secret=s.x_access_token_secret,
        )

    @retry(attempts=3, base_delay=1.0, exceptions=_RETRYABLE)
    def _download_image(self, image_url: str) -> Path:
        r = httpx.get(image_url, timeout=30, follow_redirects=True)
        r.raise_for_status()
        suffix = Path(image_url.split("?")[0]).suffix or ".jpg"
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
        tmp.write(r.content)
        tmp.close()
        return Path(tmp.name)

    def post(self, text: str, image_url: str | None = None) -> PublishResult:
        s = self._settings
        if not (s.x_api_key and s.x_api_secret and s.x_access_token and s.x_access_token_secret):
            return PublishResult(success=False, message="X credentials missing in .env")
        try:
            self._lazy_init()
            media_ids: list[str] = []
            if image_url:
                path = self._download_image(image_url)
                try:
                    media = self._api_v1.media_upload(filename=str(path))
                    media_ids.append(media.media_id_string)
                finally:
                    path.unlink(missing_ok=True)

            resp = self._client_v2.create_tweet(
                text=text,
                media_ids=media_ids or None,
            )
            tweet_id = str(resp.data.get("id")) if resp and resp.data else None
            return PublishResult(success=True, remote_post_id=tweet_id)
        except Exception as e:  # noqa: BLE001
            return PublishResult(success=False, message=str(e))

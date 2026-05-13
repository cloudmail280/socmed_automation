"""Publisher registry."""
from app.models import Platform
from app.publishers.base import BasePublisher, PublishResult
from app.publishers.threads import ThreadsPublisher
from app.publishers.twitter import TwitterPublisher


def get_publisher(platform: Platform) -> BasePublisher:
    if platform == Platform.threads:
        return ThreadsPublisher()
    if platform == Platform.twitter:
        return TwitterPublisher()
    raise ValueError(f"No publisher for platform {platform}")


__all__ = ["BasePublisher", "PublishResult", "get_publisher"]

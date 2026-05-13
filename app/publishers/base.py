"""Publisher interface."""
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class PublishResult:
    success: bool
    remote_post_id: str | None = None
    message: str | None = None


class BasePublisher(ABC):
    @abstractmethod
    def post(self, text: str, image_url: str | None = None) -> PublishResult:
        """Publish a post. `image_url` is optional (text-only fallback)."""
        raise NotImplementedError

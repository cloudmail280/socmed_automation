"""Scraper interface."""
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class ProductData:
    title: str
    price: str | None
    image_url: str | None
    description: str | None
    url: str


class BaseScraper(ABC):
    @abstractmethod
    def fetch(self, url: str) -> ProductData:
        """Fetch product metadata from URL. Raises on failure."""
        raise NotImplementedError

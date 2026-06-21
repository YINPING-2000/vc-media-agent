import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Article:
    url: str
    title: str
    source_name: str
    source_region: str
    published_at: Optional[datetime] = None
    content_preview: Optional[str] = None  # 用于辅助摘要，非必须


class BaseScraper(ABC):
    def __init__(self, source: dict):
        self.source = source
        self.name = source["name"]
        self.display_name = source["display_name"]
        self.region = source["region"]
        self.requires_proxy = source.get("requires_proxy", False)

    @property
    def proxy(self) -> Optional[str]:
        if self.requires_proxy:
            return os.environ.get("HTTP_PROXY")
        return None

    @abstractmethod
    def scrape(self) -> list[Article]:
        pass

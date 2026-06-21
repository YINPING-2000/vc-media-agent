import logging
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

import feedparser
import requests

from .base import Article, BaseScraper

logger = logging.getLogger(__name__)


class RssScraper(BaseScraper):
    def scrape(self) -> list[Article]:
        url = self.source.get("url", "")
        if not url:
            logger.warning(f"[{self.name}] No URL configured, skipping.")
            return []

        proxies = {"http": self.proxy, "https": self.proxy} if self.proxy else None

        try:
            response = requests.get(url, proxies=proxies, timeout=20)
            response.raise_for_status()
            feed = feedparser.parse(response.content)
        except Exception as e:
            logger.error(f"[{self.name}] Failed to fetch RSS: {e}")
            return []

        articles = []
        for entry in feed.entries:
            try:
                article_url = entry.get("link", "")
                title = entry.get("title", "").strip()
                if not article_url or not title:
                    continue

                published_at = _parse_date(entry)
                preview = _extract_preview(entry)

                articles.append(Article(
                    url=article_url,
                    title=title,
                    source_name=self.display_name,
                    source_region=self.region,
                    published_at=published_at,
                    content_preview=preview,
                ))
            except Exception as e:
                logger.warning(f"[{self.name}] Skipping entry due to error: {e}")
                continue

        logger.info(f"[{self.name}] Scraped {len(articles)} articles.")
        return articles


def _parse_date(entry) -> datetime | None:
    for field in ("published", "updated", "created"):
        raw = entry.get(f"{field}_parsed") or entry.get(field)
        if raw is None:
            continue
        try:
            if isinstance(raw, str):
                return parsedate_to_datetime(raw).astimezone(timezone.utc)
            # feedparser returns time.struct_time for *_parsed fields
            import time
            import calendar
            ts = calendar.timegm(raw)
            return datetime.fromtimestamp(ts, tz=timezone.utc)
        except Exception:
            continue
    return None


def _extract_preview(entry, max_chars: int = 500) -> str | None:
    content = ""
    if entry.get("content"):
        content = entry["content"][0].get("value", "")
    elif entry.get("summary"):
        content = entry["summary"]
    elif entry.get("description"):
        content = entry["description"]

    if not content:
        return None

    # 去除 HTML 标签（简单处理）
    import re
    text = re.sub(r"<[^>]+>", " ", content)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:max_chars] if text else None

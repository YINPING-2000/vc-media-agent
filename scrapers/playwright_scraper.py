import logging
from datetime import datetime, timezone

from playwright.sync_api import sync_playwright

from .base import Article, BaseScraper

logger = logging.getLogger(__name__)


class PlaywrightScraper(BaseScraper):
    def scrape(self) -> list[Article]:
        selectors = self.source.get("selectors", {})
        url = self.source.get("url", "")
        if not url:
            logger.warning(f"[{self.name}] No URL configured, skipping.")
            return []

        articles = []
        try:
            with sync_playwright() as p:
                launch_args = {}
                if self.proxy:
                    launch_args["proxy"] = {"server": self.proxy}

                browser = p.chromium.launch(headless=True, **launch_args)
                page = browser.new_page()
                page.goto(url, timeout=30000, wait_until="domcontentloaded")
                page.wait_for_timeout(2000)

                items = page.query_selector_all(selectors.get("article_list", ""))
                for item in items:
                    try:
                        title_el = item.query_selector(selectors.get("title", ""))
                        link_el = item.query_selector(selectors.get("link", "a"))
                        date_el = item.query_selector(selectors.get("date", ""))

                        title = title_el.inner_text().strip() if title_el else ""
                        href = link_el.get_attribute("href") if link_el else ""
                        if not title or not href:
                            continue

                        # 补全相对路径
                        if href.startswith("/"):
                            from urllib.parse import urlparse
                            parsed = urlparse(url)
                            href = f"{parsed.scheme}://{parsed.netloc}{href}"

                        published_at = None
                        if date_el:
                            date_str = date_el.inner_text().strip()
                            published_at = _parse_date_str(date_str)

                        articles.append(Article(
                            url=href,
                            title=title,
                            source_name=self.display_name,
                            source_region=self.region,
                            published_at=published_at,
                        ))
                    except Exception as e:
                        logger.warning(f"[{self.name}] Skipping item: {e}")
                        continue

                browser.close()
        except Exception as e:
            logger.error(f"[{self.name}] Playwright scrape failed: {e}")

        logger.info(f"[{self.name}] Scraped {len(articles)} articles.")
        return articles


def _parse_date_str(date_str: str) -> datetime | None:
    import re
    from datetime import timedelta

    now = datetime.now(timezone.utc)

    # 相对时间：X小时前、X天前
    m = re.search(r"(\d+)\s*小时前", date_str)
    if m:
        return now - timedelta(hours=int(m.group(1)))
    m = re.search(r"(\d+)\s*天前", date_str)
    if m:
        return now - timedelta(days=int(m.group(1)))

    # 绝对时间：2026-06-18 或 06-18
    for fmt in ("%Y-%m-%d", "%m-%d", "%Y/%m/%d"):
        try:
            dt = datetime.strptime(date_str.strip(), fmt)
            if dt.year == 1900:
                dt = dt.replace(year=now.year)
            return dt.replace(tzinfo=timezone.utc)
        except ValueError:
            continue

    return None

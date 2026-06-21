#!/usr/bin/env python3
"""
vc-media-agent CLI

Usage:
  python main.py --crawl-now
  python main.py --push-now
  python main.py --historical --since=2026-01-01
"""
import argparse
import logging
import os
import sys
from datetime import datetime, timezone

import yaml

from scrapers import RssScraper, PlaywrightScraper
from storage import (
    get_client,
    upsert_article,
    get_unpushed_articles,
    get_unsummarized_articles,
    update_summary,
    mark_articles_pushed,
)
from summarizer import summarize_articles
from notifier import push_daily_digest

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger("main")

SOURCES_PATH = os.path.join(os.path.dirname(__file__), "config", "sources.yaml")


def load_sources() -> list[dict]:
    with open(SOURCES_PATH, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return [s for s in data.get("sources", []) if s.get("enabled", True)]


def run_crawl(since: datetime | None = None) -> None:
    """Scrape all enabled sources and save new articles to Supabase."""
    sources = load_sources()
    client = get_client()
    total_new = 0

    for source in sources:
        scraper_type = source.get("type", "rss")
        if scraper_type == "rss":
            scraper = RssScraper(source)
        elif scraper_type == "playwright":
            scraper = PlaywrightScraper(source)
        else:
            logger.warning(f"Unknown scraper type '{scraper_type}' for {source['name']}")
            continue

        try:
            articles = scraper.scrape()
        except Exception as e:
            logger.error(f"[{source['name']}] Scrape error: {e}")
            continue

        new_count = 0
        for article in articles:
            if since and article.published_at and article.published_at < since:
                continue
            inserted = upsert_article(
                client,
                url=article.url,
                source_name=article.source_name,
                source_region=article.source_region,
                title=article.title,
                published_at=article.published_at,
            )
            if inserted:
                new_count += 1

        logger.info(f"[{source['name']}] {new_count} new articles saved.")
        total_new += new_count

    logger.info(f"Crawl complete. {total_new} new articles total.")

    # Immediately summarize any articles without summaries
    run_summarize()


def run_summarize() -> None:
    """Fetch unsummarized articles and generate Claude summaries."""
    client = get_client()
    unsummarized = get_unsummarized_articles(client, limit=200)

    if not unsummarized:
        logger.info("No unsummarized articles.")
        return

    logger.info(f"Summarizing {len(unsummarized)} articles...")
    summaries = summarize_articles(unsummarized)

    for article_id, summary in summaries.items():
        update_summary(client, article_id, summary)

    logger.info(f"Summarized {len(summaries)} articles.")


def run_push() -> None:
    """Push unsent articles to Feishu."""
    client = get_client()
    articles = get_unpushed_articles(client)

    if not articles:
        logger.info("No articles to push.")
        return

    logger.info(f"Pushing {len(articles)} articles to Feishu...")
    success = push_daily_digest(articles)

    if success:
        ids = [a["id"] for a in articles]
        mark_articles_pushed(client, ids)
        logger.info("Push complete and articles marked.")
    else:
        logger.error("Push failed; articles not marked as pushed.")
        sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(description="VC Media Agent")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--crawl-now", action="store_true", help="Scrape all sources and summarize")
    group.add_argument("--push-now", action="store_true", help="Push today's articles to Feishu")
    group.add_argument("--historical", action="store_true", help="Historical crawl (use with --since)")
    parser.add_argument("--since", type=str, default=None, help="ISO date YYYY-MM-DD for --historical")

    args = parser.parse_args()

    if args.crawl_now:
        run_crawl()
    elif args.push_now:
        run_push()
    elif args.historical:
        since_dt = None
        if args.since:
            try:
                since_dt = datetime.fromisoformat(args.since).replace(tzinfo=timezone.utc)
            except ValueError:
                logger.error(f"Invalid --since date: {args.since}. Expected YYYY-MM-DD.")
                sys.exit(1)
        run_crawl(since=since_dt)


if __name__ == "__main__":
    main()

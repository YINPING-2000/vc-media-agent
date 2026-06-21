import hashlib
import os
from datetime import datetime, timezone
from typing import Optional

from supabase import create_client, Client


def get_client() -> Client:
    url = os.environ["SUPABASE_URL"]
    key = os.environ["SUPABASE_KEY"]
    return create_client(url, key)


def url_hash(url: str) -> str:
    return hashlib.sha256(url.encode()).hexdigest()


def upsert_article(
    client: Client,
    url: str,
    source_name: str,
    source_region: str,
    title: str,
    summary: Optional[str] = None,
    published_at: Optional[datetime] = None,
) -> bool:
    """Insert article if not exists. Returns True if newly inserted."""
    hash_val = url_hash(url)
    existing = (
        client.table("articles")
        .select("id")
        .eq("url_hash", hash_val)
        .execute()
    )
    if existing.data:
        return False

    client.table("articles").insert({
        "url_hash": hash_val,
        "url": url,
        "source_name": source_name,
        "source_region": source_region,
        "title": title,
        "summary": summary,
        "published_at": published_at.isoformat() if published_at else None,
        "scraped_at": datetime.now(timezone.utc).isoformat(),
    }).execute()
    return True


def get_unpushed_articles(client: Client) -> list[dict]:
    """Return all articles not yet pushed, ordered by published_at desc."""
    result = (
        client.table("articles")
        .select("*")
        .is_("pushed_at", "null")
        .not_.is_("summary", "null")
        .order("published_at", desc=True)
        .execute()
    )
    return result.data or []


def get_unsummarized_articles(client: Client, limit: int = 50) -> list[dict]:
    """Return articles without summary, for Claude to process."""
    result = (
        client.table("articles")
        .select("id, url, title, source_name")
        .is_("summary", "null")
        .order("scraped_at", desc=False)
        .limit(limit)
        .execute()
    )
    return result.data or []


def update_summary(client: Client, article_id: int, summary: str) -> None:
    client.table("articles").update({"summary": summary}).eq("id", article_id).execute()


def mark_articles_pushed(client: Client, article_ids: list[int]) -> None:
    now = datetime.now(timezone.utc).isoformat()
    client.table("articles").update({"pushed_at": now}).in_("id", article_ids).execute()

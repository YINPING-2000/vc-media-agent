import logging
import os
from datetime import datetime, timezone, timedelta

import requests

logger = logging.getLogger(__name__)

BJT = timezone(timedelta(hours=8))


def push_daily_digest(articles: list[dict]) -> bool:
    """
    Push today's articles to a Feishu group bot via webhook.

    Args:
        articles: list of dicts from get_unpushed_articles(), each has:
                  id, title, url, source_name, source_region, summary, published_at

    Returns:
        True if push succeeded (HTTP 200 + code=0), False otherwise.
    """
    webhook_url = os.environ.get("FEISHU_WEBHOOK_URL")
    if not webhook_url:
        raise EnvironmentError("FEISHU_WEBHOOK_URL is not set")

    if not articles:
        logger.info("[lark_bot] No articles to push.")
        return True

    today = datetime.now(BJT).strftime("%Y-%m-%d")
    intl = [a for a in articles if a.get("source_region") == "intl"]
    domestic = [a for a in articles if a.get("source_region") == "cn"]

    elements = []

    elements.append({
        "tag": "div",
        "text": {
            "content": f"**🗓 {today} VC 日报**\n共 {len(articles)} 篇 · 国际 {len(intl)} · 国内 {len(domestic)}",
            "tag": "lark_md",
        },
    })
    elements.append({"tag": "hr"})

    def _article_element(article: dict) -> dict:
        title = article.get("title", "（无标题）")
        url = article.get("url", "")
        source = article.get("source_name", "")
        summary = article.get("summary", "")

        link_text = f"[{title}]({url})" if url else title
        body = f"**{link_text}**\n📰 {source}\n{summary}"
        return {
            "tag": "div",
            "text": {"content": body, "tag": "lark_md"},
        }

    if intl:
        elements.append({
            "tag": "div",
            "text": {"content": "**🌏 国际**", "tag": "lark_md"},
        })
        for a in intl:
            elements.append(_article_element(a))
            elements.append({"tag": "hr"})

    if domestic:
        elements.append({
            "tag": "div",
            "text": {"content": "**🇨🇳 国内**", "tag": "lark_md"},
        })
        for a in domestic:
            elements.append(_article_element(a))
            elements.append({"tag": "hr"})

    payload = {
        "msg_type": "interactive",
        "card": {
            "schema": "2.0",
            "body": {
                "direction": "vertical",
                "elements": elements,
            },
            "header": {
                "title": {
                    "content": f"VC 日报 {today}",
                    "tag": "plain_text",
                },
                "template": "blue",
            },
        },
    }

    try:
        resp = requests.post(webhook_url, json=payload, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        if data.get("code") == 0 or data.get("StatusCode") == 0:
            logger.info(f"[lark_bot] Pushed {len(articles)} articles successfully.")
            return True
        else:
            logger.error(f"[lark_bot] Feishu API returned error: {data}")
            return False
    except Exception as e:
        logger.error(f"[lark_bot] Push failed: {e}")
        return False

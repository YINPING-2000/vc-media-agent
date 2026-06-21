import logging
import os

import anthropic

logger = logging.getLogger(__name__)

MODEL = "claude-sonnet-4-6"

SYSTEM_PROMPT = (
    "你是一位专注于创业投资领域的内容编辑。"
    "用户将给你提供文章标题和可能的正文片段，"
    "请用2-3句话写一段简洁的中文摘要，突出核心观点或关键事件。"
    "只输出摘要正文，不要加标题、序号或解释。"
)


def summarize_articles(articles: list[dict]) -> dict[int, str]:
    """
    Summarize a batch of articles using Claude API.

    Args:
        articles: list of dicts with keys: id, title, source_name, content_preview (optional)

    Returns:
        dict mapping article id -> summary string
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise EnvironmentError("ANTHROPIC_API_KEY is not set")

    client = anthropic.Anthropic(api_key=api_key)
    results: dict[int, str] = {}

    for article in articles:
        article_id = article["id"]
        title = article.get("title", "")
        source = article.get("source_name", "")
        preview = article.get("content_preview") or ""

        user_content = f"媒体来源：{source}\n文章标题：{title}"
        if preview:
            user_content += f"\n正文片段：{preview[:400]}"

        try:
            response = client.messages.create(
                model=MODEL,
                max_tokens=256,
                system=[
                    {
                        "type": "text",
                        "text": SYSTEM_PROMPT,
                        "cache_control": {"type": "ephemeral"},
                    }
                ],
                messages=[{"role": "user", "content": user_content}],
            )
            summary = response.content[0].text.strip()
            results[article_id] = summary
            logger.info(f"[summarizer] Article {article_id} summarized.")
        except Exception as e:
            logger.error(f"[summarizer] Failed to summarize article {article_id}: {e}")

    return results

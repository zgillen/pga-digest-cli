import logging
from dataclasses import dataclass

import feedparser

logger = logging.getLogger(__name__)


@dataclass
class Article:
    title: str
    url: str
    source: str
    summary: str


def fetch_articles(urls: list[str], max_per_feed: int = 5) -> list[Article]:
    articles: list[Article] = []
    for url in urls:
        try:
            feed = feedparser.parse(url)
            source = feed.feed.get("title", url)
            for entry in feed.entries[:max_per_feed]:
                summary = entry.get("summary", entry.get("description", ""))
                # Strip HTML tags simply
                import re
                summary = re.sub(r"<[^>]+>", "", summary)[:300]
                articles.append(
                    Article(
                        title=entry.get("title", ""),
                        url=entry.get("link", ""),
                        source=source,
                        summary=summary,
                    )
                )
        except Exception:
            logger.warning("Failed to fetch feed: %s", url, exc_info=True)
    return articles

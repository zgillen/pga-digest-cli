import logging
from dataclasses import dataclass

import anthropic

logger = logging.getLogger(__name__)


@dataclass
class NewsStory:
    title: str
    url: str
    source: str
    summary: str


def fetch_pga_news(api_key: str, tournament_name: str | None = None) -> list[NewsStory]:
    """Use Claude with web search to find today's most relevant PGA Tour stories."""
    client = anthropic.Anthropic(api_key=api_key)

    if tournament_name:
        query = (
            f"Find the 5 most relevant and recent PGA Tour news stories from today or this week. "
            f"Focus on stories related to the {tournament_name} and any other major PGA Tour news. "
            f"Search pgatour.com, golfchannel.com, golf.com, golfdigest.com, and espn.com/golf. "
            f"For each story return: title, URL, source name, and a one-sentence summary. "
            f"Format as a numbered list like:\n"
            f"1. Title | URL | Source | Summary\n"
            f"Only include stories with real URLs you found via search."
        )
    else:
        query = (
            f"Find the 5 most relevant and recent PGA Tour news stories from today or this week. "
            f"Search pgatour.com, golfchannel.com, golf.com, golfdigest.com, and espn.com/golf. "
            f"For each story return: title, URL, source name, and a one-sentence summary. "
            f"Format as a numbered list like:\n"
            f"1. Title | URL | Source | Summary\n"
            f"Only include stories with real URLs you found via search."
        )

    try:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1000,
            tools=[{"type": "web_search_20250305", "name": "web_search"}],
            messages=[{"role": "user", "content": query}],
        )

        # Extract the text response
        text = ""
        for block in response.content:
            if hasattr(block, "text"):
                text += block.text

        return _parse_stories(text)

    except Exception:
        logger.warning("Failed to fetch PGA news via web search", exc_info=True)
        return []


def _parse_stories(text: str) -> list[NewsStory]:
    """Parse the numbered list response into NewsStory objects."""
    stories = []
    for line in text.strip().splitlines():
        line = line.strip()
        if not line or not line[0].isdigit():
            continue
        # Remove leading number and dot
        parts = line.split(". ", 1)
        if len(parts) < 2:
            continue
        fields = parts[1].split(" | ")
        if len(fields) < 4:
            continue
        title, url, source, summary = fields[0], fields[1], fields[2], fields[3]
        if not url.startswith("http"):
            continue
        stories.append(NewsStory(title=title.strip(), url=url.strip(), source=source.strip(), summary=summary.strip()))
    return stories

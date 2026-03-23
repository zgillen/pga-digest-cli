import anthropic

from .config import AppConfig
from .datagolf_api import (
    LeaderboardPlayer,
    PreTournamentPick,
    RankedPlayer,
    Tournament,
)
from .feeds import Article
from .news_search import NewsStory


def _fmt_score(score: int) -> str:
    if score == 0:
        return "E"
    return f"+{score}" if score > 0 else str(score)


def _build_prompt(
    current_tournament: Tournament | None,
    leaderboard: list[LeaderboardPlayer],
    upcoming_tournament: Tournament | None,
    pre_tournament_picks: list[PreTournamentPick],
    world_rankings: list[RankedPlayer],
    articles: list[Article],
    news_stories: list[NewsStory],
) -> str:
    sections = []

    if current_tournament and leaderboard:
        lb_lines = []
        for p in leaderboard[:10]:
            rounds = [str(r) for r in p.rounds if r != 0]
            rounds_str = " / ".join(rounds) if rounds else "-"
            lb_lines.append(
                f"  {p.position}. {p.player_name} — {_fmt_score(p.total)} "
                f"(Today: {_fmt_score(p.today)}, Thru: {p.thru}) [{rounds_str}]"
            )
        sections.append(
            f"CURRENT TOURNAMENT: {current_tournament.event_name} at {current_tournament.course}\n"
            + "\n".join(lb_lines)
        )
    elif not current_tournament:
        sections.append("No tournament currently in progress.")

    if upcoming_tournament:
        sections.append(
            f"UPCOMING: {upcoming_tournament.event_name} at {upcoming_tournament.course} "
            f"starting {upcoming_tournament.start_date}"
        )
        if pre_tournament_picks:
            picks_lines = [
                f"  {p.player_name} — Win: {p.win_probability:.1%}, "
                f"Top 5: {p.top5_probability:.1%}, Top 10: {p.top10_probability:.1%}"
                for p in pre_tournament_picks[:8]
            ]
            sections.append("PRE-TOURNAMENT FAVORITES:\n" + "\n".join(picks_lines))

    if world_rankings:
        rank_lines = [
            f"  {p.rank}. {p.player_name} ({p.country})"
            for p in world_rankings[:10]
        ]
        sections.append("WORLD RANKINGS (DataGolf):\n" + "\n".join(rank_lines))

    if news_stories:
        news_lines = [
            f"  - [{s.title}]({s.url}) — {s.source}: {s.summary}"
            for s in news_stories[:5]
        ]
        sections.append("TODAY'S TOP STORIES:\n" + "\n".join(news_lines))

    if articles:
        article_lines = [f"  - {a.title} ({a.source}): {a.summary}" for a in articles[:5]]
        sections.append("MORE GOLF NEWS (RSS):\n" + "\n".join(article_lines))

    return "\n\n".join(sections)


def generate_digest(
    config: AppConfig,
    current_tournament: Tournament | None,
    leaderboard: list[LeaderboardPlayer],
    upcoming_tournament: Tournament | None,
    pre_tournament_picks: list[PreTournamentPick],
    world_rankings: list[RankedPlayer],
    articles: list[Article],
    news_stories: list[NewsStory],
) -> str:
    prompt = _build_prompt(
        current_tournament,
        leaderboard,
        upcoming_tournament,
        pre_tournament_picks,
        world_rankings,
        articles,
        news_stories,
    )

    client = anthropic.Anthropic(api_key=config.anthropic_api_key)

    system = (
        "You are a knowledgeable, enthusiastic golf writer producing a daily PGA Tour digest email. "
        "Write in a conversational but informed tone — like a friend who really knows golf. "
        "Cover the leaderboard with color and context, preview upcoming events, highlight the most "
        "interesting news, and always include a 'Worth Reading' section with at least 3 article links. "
        "Keep it engaging and well-organized. Use markdown formatting with clear section headers (##). "
        "Always include the full clickable URLs for each story in the Worth Reading section. "
        "Do not fabricate stats or players — only use the data provided."
    )

    message = client.messages.create(
        model=config.narrator.model,
        max_tokens=2000,
        temperature=config.narrator.temperature,
        system=system,
        messages=[{"role": "user", "content": f"Here is today's PGA Tour data:\n\n{prompt}\n\nWrite the daily digest email."}],
    )

    return message.content[0].text

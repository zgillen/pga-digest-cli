import anthropic

from .config import AppConfig
from .datagolf_api import (
    BettingEdge,
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
    mode: str,
    current_tournament: Tournament | None,
    leaderboard: list[LeaderboardPlayer],
    upcoming_tournaments: list[Tournament],
    pre_tournament_picks: list[PreTournamentPick],
    best_bets: list[BettingEdge],
    live_best_bets: list[BettingEdge],
    world_rankings: list[RankedPlayer],
    articles: list[Article],
    news_stories: list[NewsStory],
) -> str:
    sections = []

    if mode == "leaderboard":
        if current_tournament and leaderboard:
            lb_lines = []
            for p in leaderboard[:15]:
                rounds = [str(r) for r in p.rounds if r != 0]
                rounds_str = " / ".join(rounds) if rounds else "-"
                thru_str = f"Thru: {p.thru}" if str(p.thru) not in ("0", "-", "") else "Not yet started today"
                lb_lines.append(
                    f"  {p.position}. {p.player_name} — {_fmt_score(p.total)} total "
                    f"(Today: {_fmt_score(p.today)}, {thru_str}) [{rounds_str}]"
                )
            sections.append(
                f"LIVE LEADERBOARD: {current_tournament.event_name} at {current_tournament.course}\n"
                "NOTE: Players showing 'Not yet started today' have only completed Round 1. "
                "Do not describe them as currently playing or assign them a Round 2 score.\n"
                + "\n".join(lb_lines)
            )
        else:
            sections.append("No tournament currently in progress.")

        if pre_tournament_picks:
            picks_lines = [
                f"  {p.player_name} — Win: {p.win_probability:.1%}, Top 10: {p.top10_probability:.1%}"
                for p in pre_tournament_picks[:5]
            ]
            sections.append("PRE-TOURNAMENT FAVORITES (for context):\n" + "\n".join(picks_lines))

        if live_best_bets:
            bet_lines = [
                f"  {b.player_name} — DG Model: {b.dg_win_pct:.1%} | "
                f"Best Book: {b.book_odds} ({b.book_name}, implied {b.book_win_pct:.1%}) | "
                f"Edge: +{b.edge:.1%}"
                for b in live_best_bets
            ]
            sections.append(
                "LIVE BETTING EDGES (DataGolf model vs current sportsbook odds):\n"
                + "\n".join(bet_lines)
            )

    elif mode in ("preview", "preview_bets"):
        if upcoming_tournaments:
            upcoming_lines = [
                f"  {t.event_name} at {t.course} — starts {t.start_date}"
                for t in upcoming_tournaments
            ]
            sections.append("UPCOMING SCHEDULE:\n" + "\n".join(upcoming_lines))

        if pre_tournament_picks:
            picks_lines = [
                f"  {p.player_name} — Win: {p.win_probability:.1%}, "
                f"Top 5: {p.top5_probability:.1%}, Top 10: {p.top10_probability:.1%}, "
                f"Make Cut: {p.make_cut_probability:.1%}"
                for p in pre_tournament_picks[:10]
            ]
            sections.append("DATAGOLF WIN PROBABILITIES:\n" + "\n".join(picks_lines))

        if best_bets:
            bet_lines = [
                f"  {b.player_name} — DG Model: {b.dg_win_pct:.1%} | "
                f"Best Book: {b.book_odds} ({b.book_name}, implied {b.book_win_pct:.1%}) | "
                f"Edge: +{b.edge:.1%}"
                for b in best_bets
            ]
            sections.append(
                "BEST BETS (DataGolf model vs sportsbook odds — positive edge plays):\n"
                + "\n".join(bet_lines)
            )

    elif mode == "recap":
        if current_tournament:
            sections.append(
                f"LAST WEEK: {current_tournament.event_name} at {current_tournament.course}"
            )
        if upcoming_tournaments:
            upcoming_lines = [
                f"  {t.event_name} at {t.course} — starts {t.start_date}"
                for t in upcoming_tournaments
            ]
            sections.append(
                "UPCOMING SCHEDULE (next 3 weeks):\n" + "\n".join(upcoming_lines) +
                "\n(Note: DataGolf projections release Monday afternoon — full preview + best bets coming Tuesday/Wednesday)"
            )

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


def _get_system_prompt(mode: str) -> str:
    base = (
        "You are a knowledgeable, enthusiastic golf writer producing a daily PGA Tour digest email. "
        "Write in a conversational but informed tone — like a smart friend who really knows golf and betting. "
        "Use markdown formatting with clear section headers (##). "
        "Always include a 'Worth Reading' section at the end with at least 3 clickable article links. "
        "IMPORTANT: Use ONLY the upcoming schedule data provided to describe what tournaments are coming up and in what order. "
        "Do NOT use your own knowledge of the golf calendar — it may be outdated or wrong. "
        "Never skip or omit tournaments that appear in the schedule data. "
        "Do not fabricate stats or players — only use the data provided."
    )
    if mode == "leaderboard":
        return base + (
            " Today is a tournament day (Thursday-Sunday). Lead with the live leaderboard — "
            "who's leading, who's making a move, who's falling back. Give it energy and drama. "
            "IMPORTANT: Players marked 'Not yet started today' have only completed Round 1 — "
            "do not describe them as currently playing or give them a Round 2 score. "
            "Only describe players who have a Thru value as actively playing. "
            "Then include a 'Best Live Bets' section that explains each betting edge play in plain English: "
            "why DataGolf likes them, what the value is, and which book has the best odds. "
            "Keep the betting section punchy and actionable."
        )
    elif mode == "preview_bets":
        return base + (
            " Today is Wednesday. Preview the upcoming tournament and then include a 'Best Bets' section. "
            "For each bet, explain in plain English why DataGolf's model likes this player more than "
            "the books do — course fit, recent form, strokes gained edge. Make it feel like sharp "
            "handicapping advice, not just a list of numbers. Note that these are DataGolf model edges "
            "and not guaranteed — always bet responsibly."
        )
    elif mode == "preview":
        return base + (
            " Today is Tuesday. Preview the upcoming tournament — the course, the favorites, "
            "who's in form based on DataGolf win probabilities, and key storylines to follow. "
            "Use the upcoming schedule provided to accurately describe what tournaments are coming up "
            "and in what order. Build anticipation for the week ahead."
        )
    else:
        return base + (
            " Today is Monday. Recap last week's tournament and introduce this week's event. "
            "Use the upcoming schedule provided to accurately describe what's coming up — "
            "do not assume tournament order from your training data. "
            "Note that full DataGolf projections and best bets will be in Tuesday/Wednesday's emails. "
            "Keep it conversational and set the table for the week."
        )


def generate_digest(
    config: AppConfig,
    mode: str,
    current_tournament: Tournament | None,
    leaderboard: list[LeaderboardPlayer],
    upcoming_tournaments: list[Tournament],
    pre_tournament_picks: list[PreTournamentPick],
    best_bets: list[BettingEdge],
    live_best_bets: list[BettingEdge],
    world_rankings: list[RankedPlayer],
    articles: list[Article],
    news_stories: list[NewsStory],
) -> str:
    prompt = _build_prompt(
        mode,
        current_tournament,
        leaderboard,
        upcoming_tournaments,
        pre_tournament_picks,
        best_bets,
        live_best_bets,
        world_rankings,
        articles,
        news_stories,
    )

    client = anthropic.Anthropic(api_key=config.anthropic_api_key)

    message = client.messages.create(
        model=config.narrator.model,
        max_tokens=3000,
        temperature=config.narrator.temperature,
        system=_get_system_prompt(mode),
        messages=[{"role": "user", "content": f"Here is today's PGA Tour data:\n\n{prompt}\n\nWrite the daily digest email."}],
    )

    return message.content[0].text

import anthropic

from .config import AppConfig
from .datagolf_api import (
    BettingEdge,
    FieldPlayer,
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
    field_players: list[FieldPlayer],
    articles: list[Article],
    news_stories: list[NewsStory],
) -> str:
    sections = []

    if mode == "recap":
        if current_tournament:
            sections.append(
                f"LAST WEEK'S TOURNAMENT: {current_tournament.event_name} at {current_tournament.course}"
            )
        if upcoming_tournaments:
            upcoming_lines = [
                f"  {t.event_name} at {t.course} — starts {t.start_date}"
                for t in upcoming_tournaments
            ]
            sections.append("UPCOMING SCHEDULE (next 3 weeks):\n" + "\n".join(upcoming_lines))
        if world_rankings:
            rank_lines = [
                f"  {p.rank}. {p.player_name} ({p.country})"
                for p in world_rankings[:25]
            ]
            sections.append("WORLD RANKINGS (DataGolf top 25):\n" + "\n".join(rank_lines))

    elif mode == "preview":
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
                for p in pre_tournament_picks[:15]
            ]
            sections.append("DATAGOLF WIN PROBABILITIES:\n" + "\n".join(picks_lines))

    elif mode == "preview_bets":
        if upcoming_tournaments:
            sections.append(
                f"THIS WEEK: {upcoming_tournaments[0].event_name} at {upcoming_tournaments[0].course}"
            )
        if field_players:
            pairing_lines = [
                f"  {f.player_name} — Tee: {f.tee_time}, {f.starting_hole}, "
                f"with {f.partner1 or 'TBD'} & {f.partner2 or 'TBD'}"
                for f in field_players[:30]
                if f.tee_time and f.tee_time != "TBD"
            ]
            if pairing_lines:
                sections.append("R1 TEE TIMES & PAIRINGS:\n" + "\n".join(pairing_lines))
        if pre_tournament_picks:
            picks_lines = [
                f"  {p.player_name} — Win: {p.win_probability:.1%}, Top 10: {p.top10_probability:.1%}"
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
                "BEST BETS (DataGolf model vs sportsbook odds):\n" + "\n".join(bet_lines)
            )

    elif mode == "thursday":
        if current_tournament:
            sections.append(
                f"TOURNAMENT UNDERWAY: {current_tournament.event_name} at {current_tournament.course}"
            )
        if field_players:
            pairing_lines = [
                f"  {f.player_name} — Tee: {f.tee_time}, {f.starting_hole}, "
                f"with {f.partner1 or 'TBD'} & {f.partner2 or 'TBD'}"
                for f in field_players[:30]
                if f.tee_time and f.tee_time != "TBD"
            ]
            if pairing_lines:
                sections.append("TODAY'S NOTABLE PAIRINGS:\n" + "\n".join(pairing_lines))
        if best_bets:
            bet_lines = [
                f"  {b.player_name} — DG Model: {b.dg_win_pct:.1%} | "
                f"Best Book: {b.book_odds} ({b.book_name}, implied {b.book_win_pct:.1%}) | "
                f"Edge: +{b.edge:.1%}"
                for b in best_bets
            ]
            sections.append("BEST BETS FOR ROUND 1:\n" + "\n".join(bet_lines))

    elif mode == "leaderboard":
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
                "NOTE: Players showing 'Not yet started today' have only completed the previous round. "
                "Do not describe them as currently playing or assign them a score for today.\n"
                + "\n".join(lb_lines)
            )
        else:
            sections.append("No tournament currently in progress.")

        if live_best_bets:
            bet_lines = [
                f"  {b.player_name} — DG Model: {b.dg_win_pct:.1%} | "
                f"Best Book: {b.book_odds} ({b.book_name}, implied {b.book_win_pct:.1%}) | "
                f"Edge: +{b.edge:.1%}"
                for b in live_best_bets
            ]
            sections.append(
                "BEST LIVE BETS (DataGolf live model vs current book odds):\n"
                + "\n".join(bet_lines)
            )

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
        "You are a knowledgeable, enthusiastic golf writer producing a daily PGA Tour digest email "
        "called 'The Fairway Finder'. "
        "Write in a conversational but informed tone — like a smart friend who really knows golf and betting. "
        "Use markdown formatting with clear section headers (##). "
        "Always include a 'Worth Reading' section at the end with at least 3 clickable article links. "
        "IMPORTANT: Use ONLY the schedule data provided — do not assume tournament order from training data. "
        "Do not fabricate stats or players — only use the data provided."
    )

    if mode == "recap":
        return base + (
            " Today is Monday. Lead with a DEEP DIVE recap of last week's tournament — "
            "who won, key moments, storylines, what it means for the season. At least 3-4 paragraphs. "
            "Then show the world rankings as a formatted table (top 25). "
            "End with a sneak peek at next week's tournament — where it is, what type of course, "
            "what kind of player tends to do well there."
        )
    elif mode == "preview":
        return base + (
            " Today is Tuesday. Write a DEEP DIVE preview of the upcoming tournament — "
            "where it is, the course layout and conditions, who the defending champion is, "
            "what types of golfers (ball strikers, putters, bombers, grinders) tend to excel there, "
            "and key storylines to follow. Then cover the DataGolf win probabilities "
            "and who the model likes this week. At least 3-4 paragraphs of preview content."
        )
    elif mode == "preview_bets":
        return base + (
            " Today is Wednesday. Cover the tee times and notable pairings to watch in Round 1. "
            "Then include a 'Best Bets' section — for each bet explain in plain English why "
            "DataGolf's model likes this player more than the books do. "
            "Make it feel like sharp handicapping advice. Always bet responsibly."
        )
    elif mode == "thursday":
        return base + (
            " Today is Thursday — Round 1 is about to begin. "
            "Cover any headline news that has come in since Wednesday morning's email. "
            "Highlight the most interesting pairings to watch today. "
            "Include a Best Bets section for Round 1 with actionable plays. "
            "Keep it punchy and focused — people are checking this before they watch golf."
        )
    elif mode == "leaderboard":
        return base + (
            " Today is Friday, Saturday, or Sunday — tournament is in full swing. "
            "Lead with the live leaderboard — who's leading, who's making a move, "
            "who's falling back. Give it energy and drama. "
            "IMPORTANT: Players marked 'Not yet started today' have only completed previous rounds — "
            "do not describe them as currently playing or give them a score for today. "
            "Then include a 'Best Live Bets' section explaining each value play in plain English."
        )
    return base


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
    field_players: list[FieldPlayer],
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
        field_players,
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

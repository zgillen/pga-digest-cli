import anthropic

from .config import AppConfig
from .datagolf_api import (
    BettingEdge,
    FieldPlayer,
    LeaderboardPlayer,
    LeaderboardPlayerSG,
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


def _fmt_sg(val: float) -> str:
    return f"+{val:.2f}" if val > 0 else f"{val:.2f}"


def _build_prompt(
    mode: str,
    current_tournament: Tournament | None,
    leaderboard: list[LeaderboardPlayer],
    strokes_gained: list[LeaderboardPlayerSG],
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
                f"TOURNAMENT UNDERWAY: {current_tournament.event_name} at {current_tournament.course} "
                f"(Round {current_tournament.current_round} — {current_tournament.round_status})"
            )
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
            sg_lookup = {p.player_name: p for p in strokes_gained}

            lb_lines = []
            for p in leaderboard[:15]:
                rounds = [str(r) for r in p.rounds if r != 0]
                rounds_str = " / ".join(rounds) if rounds else "-"
                thru_str = f"Thru: {p.thru}" if str(p.thru) not in ("0", "-", "") else "Not yet started today"

                sg = sg_lookup.get(p.player_name)
                if sg:
                    sg_str = (
                        f" | SG: Total {_fmt_sg(sg.sg_total)}, "
                        f"OTT {_fmt_sg(sg.sg_ott)}, "
                        f"APP {_fmt_sg(sg.sg_app)}, "
                        f"PUTT {_fmt_sg(sg.sg_putt)}"
                    )
                else:
                    sg_str = ""

                lb_lines.append(
                    f"  {p.position}. {p.player_name} — {_fmt_score(p.total)} total "
                    f"(Today: {_fmt_score(p.today)}, {thru_str}) [{rounds_str}]{sg_str}"
                )

            status = current_tournament.round_status.lower()
            if any(word in status for word in ("suspend", "delay", "weather", "horn", "darkness")):
                status_note = (
                    f"\nROUND STATUS: SUSPENDED/DELAYED — Round {current_tournament.current_round} "
                    "has been interrupted. Scores shown reflect where play was halted and are NOT "
                    "final round scores. Do not describe any round as complete unless thru shows 'F'."
                )
            elif "complete" in status or "official" in status:
                status_note = f"\nROUND STATUS: Round {current_tournament.current_round} is complete."
            else:
                status_note = ""

            sections.append(
                f"LIVE LEADERBOARD: {current_tournament.event_name} at {current_tournament.course} "
                f"(Round {current_tournament.current_round} — {current_tournament.round_status})"
                + status_note + "\n"
                "NOTE: Players showing 'Not yet started today' have only completed the previous round.\n"
                "SG = Strokes Gained (cumulative for tournament). Use these to explain HOW players "
                "are performing — gaining strokes off the tee, on approach, or putting.\n"
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
        "CRITICAL: Do NOT use your training knowledge to add player narratives, career achievements, "
        "historical records, or recent tournament results. Your training data has a cutoff date and "
        "may contain factual errors about recent results — for example who won which major. "
        "When describing players on the leaderboard, derive all narrative from the strokes gained "
        "and score data provided — e.g. 'leading the field gaining +3.2 strokes on approach' "
        "rather than making claims about their game or career. "
        "Do not fabricate stats or players — only use the data provided."
    )

    if mode == "recap":
        return base + (
            " Today is Monday. Lead with a DEEP DIVE recap of last week's tournament — "
            "who won, what the scores tell us, key storylines from the data. At least 3-4 paragraphs. "
            "Then show the world rankings as a formatted table (top 25). "
            "End with a sneak peek at next week's tournament from the schedule provided."
        )
    elif mode == "preview":
        return base + (
            " Today is Tuesday. Write a DEEP DIVE preview of the upcoming tournament — "
            "where it is, the course, and who the DataGolf model likes this week. "
            "At least 3-4 paragraphs. Only reference player context derivable from the probability data."
        )
    elif mode == "preview_bets":
        return base + (
            " Today is Wednesday. Cover the tee times and notable pairings to watch in Round 1. "
            "Then include a 'Best Bets' section explaining why DataGolf's model likes each player "
            "based on the edge data provided. Do not add player background from training data. "
            "Always bet responsibly."
        )
    elif mode == "thursday":
        return base + (
            " Today is Thursday — Round 1 is about to begin. "
            "Cover headline news from the provided stories only. "
            "Include a Best Bets section for Round 1 based strictly on the edge data provided. "
            "Keep it punchy and focused."
        )
    elif mode == "leaderboard":
        return base + (
            " Today is Friday, Saturday, or Sunday — tournament is in full swing. "
            "Lead with the live leaderboard — who's leading, who's making a move. "
            "Use the strokes gained data to explain HOW players are performing — "
            "e.g. 'leading the field in strokes gained approach at +3.2' is great color. "
            "CRITICAL: Do NOT add player career context or historical claims from your training data "
            "as this information may be outdated or factually incorrect. "
            "Stick entirely to what the score and strokes gained numbers show. "
            "Players marked 'Not yet started today' have only completed previous rounds — do not "
            "describe them as currently playing. "
            "If round status shows SUSPENDED or DELAYED, lead with that news. "
            "Then include a 'Best Live Bets' section explaining each value play from the data."
        )
    return base


def generate_digest(
    config: AppConfig,
    mode: str,
    current_tournament: Tournament | None,
    leaderboard: list[LeaderboardPlayer],
    strokes_gained: list[LeaderboardPlayerSG],
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
        strokes_gained,
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

import argparse
from datetime import date, datetime

from .config import load_config
from .datagolf_api import (
    get_best_bets,
    get_current_tournament,
    get_live_best_bets,
    get_live_leaderboard,
    get_pre_tournament_picks,
    get_upcoming_tournaments,
    get_world_rankings,
)
from .emailer import send_email
from .feeds import fetch_articles
from .narrator import generate_digest
from .news_search import fetch_pga_news


def get_day_mode() -> str:
    day = datetime.utcnow().weekday()
    if day == 0:
        return "recap"
    elif day == 1:
        return "preview"
    elif day == 2:
        return "preview_bets"
    else:
        return "leaderboard"


def main() -> None:
    parser = argparse.ArgumentParser(description="PGA Tour daily digest")
    parser.add_argument("--no-email", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--mode",
        choices=["recap", "preview", "preview_bets", "leaderboard"],
        help="Override day mode",
    )
    subparsers = parser.add_subparsers(dest="command")
    subparsers.add_parser("test-email")
    args = parser.parse_args()

    config = load_config()

    if args.command == "test-email":
        print("Sending test email...")
        send_email(config, "PGA Digest — Test Email", "Your PGA Digest email is configured correctly! ⛳")
        print("Done.")
        return

    mode = args.mode or get_day_mode()
    print(f"Mode: '{mode}' ({datetime.utcnow().strftime('%A')})")

    print("Fetching tournament data...")
    current_tournament = get_current_tournament(config.datagolf_api_key)
    upcoming_tournaments = get_upcoming_tournaments(config.datagolf_api_key)
    world_rankings = get_world_rankings(config.datagolf_api_key)

    leaderboard = []
    if mode == "leaderboard" and current_tournament:
        leaderboard = get_live_leaderboard(config.datagolf_api_key)

    pre_tournament_picks = []
    if mode in ("preview", "preview_bets", "leaderboard"):
        pre_tournament_picks = get_pre_tournament_picks(config.datagolf_api_key)

    best_bets = []
    if mode == "preview_bets":
        print("Fetching pre-tournament betting edges...")
        best_bets = get_best_bets(config.datagolf_api_key)

    live_best_bets = []
    if mode == "leaderboard":
        print("Fetching live betting edges...")
        live_best_bets = get_live_best_bets(config.datagolf_api_key)

    print("Fetching news articles...")
    articles = fetch_articles(config.feeds.urls)

    print("Searching for today's top PGA Tour stories...")
    tournament_name = current_tournament.event_name if current_tournament else (
        upcoming_tournaments[0].event_name if upcoming_tournaments else None
    )
    news_stories = fetch_pga_news(config.anthropic_api_key, tournament_name)

    if args.dry_run:
        print(f"\n=== RAW DATA (mode: {mode}) ===")
        print(f"Current tournament: {current_tournament}")
        print(f"Leaderboard entries: {len(leaderboard)}")
        print(f"Upcoming tournaments: {[t.event_name for t in upcoming_tournaments]}")
        print(f"Pre-tournament picks: {len(pre_tournament_picks)}")
        print(f"Best bets: {len(best_bets)}")
        print(f"Live best bets: {len(live_best_bets)}")
        print(f"World rankings: {len(world_rankings)}")
        print(f"RSS articles: {len(articles)}")
        print(f"News stories found: {len(news_stories)}")
        return

    print("Generating digest with Claude...")
    digest = generate_digest(
        config=config,
        mode=mode,
        current_tournament=current_tournament,
        leaderboard=leaderboard,
        upcoming_tournaments=upcoming_tournaments,
        pre_tournament_picks=pre_tournament_picks,
        best_bets=best_bets,
        live_best_bets=live_best_bets,
        world_rankings=world_rankings,
        articles=articles,
        news_stories=news_stories,
    )

    today = date.today().strftime("%B %d, %Y")
    subject = config.email.subject.format(date=today)

    if args.no_email:
        print(f"\nSubject: {subject}\n")
        print(digest)
    else:
        send_email(config, subject, digest)

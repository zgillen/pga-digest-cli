import argparse
import smtplib
from datetime import date
from email.mime.text import MIMEText

from .config import load_config
from .datagolf_api import (
    get_current_tournament,
    get_fantasy_projections,
    get_live_leaderboard,
    get_pre_tournament_picks,
    get_upcoming_tournament,
    get_world_rankings,
)
from .emailer import send_email
from .feeds import fetch_articles
from .narrator import generate_digest


def main() -> None:
    parser = argparse.ArgumentParser(description="PGA Tour daily digest")
    parser.add_argument("--no-email", action="store_true", help="Print to terminal instead of sending email")
    parser.add_argument("--dry-run", action="store_true", help="Show raw data without calling Claude or sending email")
    subparsers = parser.add_subparsers(dest="command")
    subparsers.add_parser("test-email", help="Send a test email to verify Gmail setup")
    args = parser.parse_args()

    config = load_config()

    # Test email mode
    if args.command == "test-email":
        print("Sending test email...")
        send_email(config, "PGA Digest — Test Email", "Your PGA Digest email is configured correctly! ⛳")
        print("Test email sent successfully.")
        return

    # Fetch all data
    print("Fetching tournament data...")
    current_tournament = get_current_tournament(config.datagolf_api_key)
    leaderboard = get_live_leaderboard(config.datagolf_api_key) if current_tournament else []
    upcoming_tournament = get_upcoming_tournament(config.datagolf_api_key)
    pre_tournament_picks = get_pre_tournament_picks(config.datagolf_api_key)
    world_rankings = get_world_rankings(config.datagolf_api_key)
    fantasy_projections = get_fantasy_projections(config.datagolf_api_key)

    print("Fetching news articles...")
    articles = fetch_articles(config.feeds.urls)

    if args.dry_run:
        print("\n=== RAW DATA ===")
        print(f"Current tournament: {current_tournament}")
        print(f"Leaderboard entries: {len(leaderboard)}")
        print(f"Upcoming tournament: {upcoming_tournament}")
        print(f"Pre-tournament picks: {len(pre_tournament_picks)}")
        print(f"World rankings: {len(world_rankings)}")
        print(f"Fantasy projections: {len(fantasy_projections)}")
        print(f"Articles: {len(articles)}")
        return

    print("Generating digest with Claude...")
    digest = generate_digest(
        config=config,
        current_tournament=current_tournament,
        leaderboard=leaderboard,
        upcoming_tournament=upcoming_tournament,
        pre_tournament_picks=pre_tournament_picks,
        world_rankings=world_rankings,
        fantasy_projections=fantasy_projections,
        articles=articles,
    )

    today = date.today().strftime("%B %d, %Y")
    subject = config.email.subject.format(date=today)

    if args.no_email:
        print(f"\nSubject: {subject}\n")
        print(digest)
    else:
        send_email(config, subject, digest)

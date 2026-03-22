# PGA Digest CLI

A daily email digest for PGA Tour fans. Fetches live leaderboard data, world rankings, fantasy projections, and news via the DataGolf API, then uses Claude to write it up in a conversational tone.

## What You Get

- **Live leaderboard** during tournament rounds
- **Upcoming tournament preview** with DataGolf win probabilities
- **World rankings** (top 10)
- **Fantasy golf picks** (DraftKings projections + ownership)
- **Golf news** from RSS feeds

## Quick Start

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
# Edit .env with your keys

pga-digest --no-email     # Print to terminal
pga-digest --dry-run      # Show raw data only
pga-digest test-email     # Verify Gmail works
pga-digest                # Send the email
```

## Required API Keys

- **Anthropic API key** — [console.anthropic.com](https://console.anthropic.com)
- **DataGolf API key** — [datagolf.com](https://datagolf.com)
- **Gmail App Password** — [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)

## GitHub Actions (Automatic Daily Email)

Add these secrets to your repo under Settings → Environments → digest:

| Secret | Value |
|--------|-------|
| `ANTHROPIC_API_KEY` | Your Anthropic key |
| `DATAGOLF_API_KEY` | Your DataGolf key |
| `GMAIL_ADDRESS` | Your Gmail address |
| `GMAIL_APP_PASSWORD` | Gmail app password (no spaces) |
| `EMAIL_RECIPIENTS` | Comma-separated recipient emails |

The workflow runs daily at 8am Eastern automatically.

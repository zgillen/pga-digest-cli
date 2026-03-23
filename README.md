# PGA Tour Daily Digest

A smart daily email digest for PGA Tour fans. Automatically adjusts its content based on the day of the week — recapping last week on Monday, previewing the upcoming tournament Tuesday/Wednesday, and covering the live leaderboard Thursday through Sunday.

Powered by the DataGolf API for stats and betting edges, Claude for writing, and Gmail for delivery.

## What You Get

**Monday — Recap & Intro**
- Last week's tournament recap
- This week's event introduction
- World rankings, top stories

**Tuesday — Full Preview**
- Upcoming tournament preview with course breakdown
- DataGolf win probabilities for the field
- World rankings, top stories, worth reading links

**Wednesday — Preview + Best Bets**
- Everything from Tuesday, plus:
- **Best Bets** section — players where DataGolf's model shows positive edge vs sportsbook odds, explained in plain English

**Thursday–Sunday — Live Coverage**
- Live leaderboard with round-by-round scores
- Pre-tournament favorites for context
- **Best Live Bets** section — DataGolf live model vs current book odds
- Top stories, worth reading links

## Schedule

Sends daily at **9am Eastern** via GitHub Actions. No server required.

## Setup

### 1. Accounts needed
- [Anthropic API key](https://console.anthropic.com) (~$1/month)
- [DataGolf API key](https://datagolf.com) (Scratch Plus plan)
- Gmail account + [App Password](https://myaccount.google.com/apppasswords)

### 2. GitHub Secrets
Add these under **Settings → Environments → digest**:

| Secret | Value |
|--------|-------|
| `ANTHROPIC_API_KEY` | Your Anthropic key |
| `DATAGOLF_API_KEY` | Your DataGolf key |
| `GMAIL_ADDRESS` | Your Gmail address |
| `GMAIL_APP_PASSWORD` | Gmail app password (no spaces) |
| `EMAIL_RECIPIENTS` | Comma-separated recipient emails |

### 3. Config
Edit `config.toml` to set your recipient email and adjust RSS feed URLs if desired.

## Manual Testing

Go to **Actions → Daily PGA Digest → Run workflow** and select a mode to test:

| Mode | Content |
|------|---------|
| `recap` | Monday format |
| `preview` | Tuesday format |
| `preview_bets` | Wednesday format with Best Bets |
| `leaderboard` | Thursday–Sunday format with Live Bets |

## Architecture
```
DataGolf API  →  Tournament data, live leaderboard, win probabilities, betting edges
RSS Feeds     →  Golf news articles
Web Search    →  Today's top stories from major golf outlets
                        |
                Claude Sonnet  →  Day-aware conversational digest
                        |
                Gmail SMTP  →  Formatted HTML email
```

## Cost

- Anthropic API: ~$1–2/month
- DataGolf: Scratch Plus subscription required
- GitHub Actions: Free

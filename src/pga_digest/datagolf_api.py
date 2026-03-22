import logging
from dataclasses import dataclass

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

BASE_URL = "https://feeds.datagolf.com"


@dataclass
class Tournament:
    event_name: str
    course: str
    start_date: str
    end_date: str
    tour: str


@dataclass
class LeaderboardPlayer:
    player_name: str
    position: int
    total: int          # score relative to par (e.g. -12)
    today: int          # today's score relative to par
    thru: str           # holes completed ("F" if finished)
    rounds: list[int]   # round-by-round scores


@dataclass
class RankedPlayer:
    rank: int
    player_name: str
    country: str
    dg_rating: float


@dataclass
class FantasyProjection:
    player_name: str
    projected_ownership: float
    projected_score: float
    win_probability: float
    top10_probability: float


@dataclass
class PreTournamentPick:
    player_name: str
    win_probability: float
    top5_probability: float
    top10_probability: float
    make_cut_probability: float


def _get(api_key: str, path: str, params: dict | None = None) -> dict:
    url = f"{BASE_URL}/{path}"
    p = {"file_format": "json", "key": api_key}
    if params:
        p.update(params)
    resp = httpx.get(url, params=p, timeout=15)
    resp.raise_for_status()
    return resp.json()


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=4), reraise=True)
def get_current_tournament(api_key: str) -> Tournament | None:
    """Get the current or most recently active tournament."""
    try:
        data = _get(api_key, "preds/in-play", {"tour": "pga"})
        info = data.get("info", {})
        if not info:
            return None
        return Tournament(
            event_name=info.get("event_name", "Unknown"),
            course=info.get("course", "Unknown"),
            start_date=info.get("start_date", ""),
            end_date=info.get("end_date", ""),
            tour="PGA",
        )
    except Exception:
        logger.warning("Failed to fetch current tournament", exc_info=True)
        return None


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=4), reraise=True)
def get_live_leaderboard(api_key: str) -> list[LeaderboardPlayer]:
    """Get live leaderboard for the current tournament."""
    try:
        data = _get(api_key, "preds/in-play", {"tour": "pga"})
        players = []
        for p in data.get("data", [])[:20]:  # top 20
            players.append(
                LeaderboardPlayer(
                    player_name=p.get("player_name", "Unknown"),
                    position=p.get("current_pos", 0),
                    total=p.get("total", 0),
                    today=p.get("today", 0),
                    thru=str(p.get("thru", "-")),
                    rounds=[
                        p.get("R1", 0),
                        p.get("R2", 0),
                        p.get("R3", 0),
                        p.get("R4", 0),
                    ],
                )
            )
        return sorted(players, key=lambda x: x.position)
    except Exception:
        logger.warning("Failed to fetch live leaderboard", exc_info=True)
        return []


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=4), reraise=True)
def get_upcoming_tournament(api_key: str) -> Tournament | None:
    """Get the next upcoming tournament."""
    try:
        data = _get(api_key, "get-schedule", {"tour": "pga", "upcoming_only": "yes"})
        schedule = data.get("schedule", [])
        if not schedule:
            return None
        t = schedule[0]
        return Tournament(
            event_name=t.get("event_name", "Unknown"),
            course=t.get("course", "Unknown"),
            start_date=t.get("date", ""),
            end_date=t.get("end_date", t.get("date", "")),
            tour="PGA",
        )
    except Exception:
        logger.warning("Failed to fetch upcoming tournament", exc_info=True)
        return None


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=4), reraise=True)
def get_world_rankings(api_key: str, top_n: int = 10) -> list[RankedPlayer]:
    """Get current DataGolf world rankings."""
    try:
        data = _get(api_key, "preds/get-dg-rankings")
        rankings = []
        for p in data.get("rankings", [])[:top_n]:
            rankings.append(
                RankedPlayer(
                    rank=p.get("rank", 0),
                    player_name=p.get("player_name", "Unknown"),
                    country=p.get("country", ""),
                    dg_rating=float(p.get("dg_id", 0)),
                )
            )
        return rankings
    except Exception:
        logger.warning("Failed to fetch world rankings", exc_info=True)
        return []


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=4), reraise=True)
def get_pre_tournament_picks(api_key: str, top_n: int = 10) -> list[PreTournamentPick]:
    """Get pre-tournament win probabilities."""
    try:
        data = _get(api_key, "preds/pre-tournament", {"tour": "pga"})
        picks = []
        for p in data.get("baseline", [])[:top_n]:
            picks.append(
                PreTournamentPick(
                    player_name=p.get("player_name", "Unknown"),
                    win_probability=float(p.get("win", 0)),
                    top5_probability=float(p.get("top_5", 0)),
                    top10_probability=float(p.get("top_10", 0)),
                    make_cut_probability=float(p.get("make_cut", 0)),
                )
            )
        return sorted(picks, key=lambda x: x.win_probability, reverse=True)
    except Exception:
        logger.warning("Failed to fetch pre-tournament picks", exc_info=True)
        return []


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=4), reraise=True)
def get_fantasy_projections(api_key: str, site: str = "draftkings", top_n: int = 10) -> list[FantasyProjection]:
    """Get fantasy golf projections."""
    try:
        data = _get(
            api_key,
            "preds/fantasy-projection-defaults",
            {"tour": "pga", "site": site, "slate": "main"},
        )
        projections = []
        for p in data.get("projections", [])[:top_n]:
            projections.append(
                FantasyProjection(
                    player_name=p.get("player_name", "Unknown"),
                    projected_ownership=float(p.get("proj_ownership", 0)),
                    projected_score=float(p.get("proj_points", 0)),
                    win_probability=float(p.get("win", 0)),
                    top10_probability=float(p.get("top_10", 0)),
                )
            )
        return sorted(projections, key=lambda x: x.projected_score, reverse=True)
    except Exception:
        logger.warning("Failed to fetch fantasy projections", exc_info=True)
        return []

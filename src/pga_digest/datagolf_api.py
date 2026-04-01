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
    total: int
    today: int
    thru: str
    rounds: list[int]


@dataclass
class RankedPlayer:
    rank: int
    player_name: str
    country: str
    dg_rating: float


@dataclass
class PreTournamentPick:
    player_name: str
    win_probability: float
    top5_probability: float
    top10_probability: float
    make_cut_probability: float


@dataclass
class BettingEdge:
    player_name: str
    dg_win_pct: float
    book_win_pct: float
    edge: float
    book_odds: str
    book_name: str


@dataclass
class FieldPlayer:
    player_name: str
    tee_time: str
    starting_hole: str
    partner1: str
    partner2: str


def _get(api_key: str, path: str, params: dict | None = None) -> dict:
    url = f"{BASE_URL}/{path}"
    p = {"file_format": "json", "key": api_key}
    if params:
        p.update(params)
    resp = httpx.get(url, params=p, timeout=15)
    resp.raise_for_status()
    return resp.json()


def _american_to_pct(odds: float) -> float:
    if odds > 0:
        return 100 / (odds + 100)
    else:
        return abs(odds) / (abs(odds) + 100)


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=4), reraise=True)
def get_current_tournament(api_key: str) -> Tournament | None:
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
    try:
        data = _get(api_key, "preds/in-play", {"tour": "pga"})
        players = []
        for p in data.get("data", [])[:20]:
            players.append(
                LeaderboardPlayer(
                    player_name=p.get("player_name", "Unknown"),
                    position=p.get("current_pos", 0),
                    total=p.get("total", 0),
                    today=p.get("today", 0),
                    thru=str(p.get("thru", "-")),
                    rounds=[p.get("R1", 0), p.get("R2", 0), p.get("R3", 0), p.get("R4", 0)],
                )
            )
        return sorted(players, key=lambda x: x.position)
    except Exception:
        logger.warning("Failed to fetch live leaderboard", exc_info=True)
        return []


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=4), reraise=True)
def get_upcoming_tournaments(api_key: str, next_n: int = 3) -> list[Tournament]:
    try:
        data = _get(api_key, "get-schedule", {"tour": "pga", "upcoming_only": "yes"})
        schedule = data.get("schedule", [])
        tournaments = []
        for t in schedule[:next_n]:
            tournaments.append(Tournament(
                event_name=t.get("event_name", "Unknown"),
                course=t.get("course", "Unknown"),
                start_date=t.get("date", ""),
                end_date=t.get("end_date", t.get("date", "")),
                tour="PGA",
            ))
        return tournaments
    except Exception:
        logger.warning("Failed to fetch upcoming tournaments", exc_info=True)
        return []


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=4), reraise=True)
def get_world_rankings(api_key: str, top_n: int = 25) -> list[RankedPlayer]:
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
def get_pre_tournament_picks(api_key: str, top_n: int = 15) -> list[PreTournamentPick]:
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
def get_field_players(api_key: str) -> list[FieldPlayer]:
    try:
        data = _get(api_key, "field-updates", {"tour": "pga"})
        players = []
        field = data.get("field", [])
        for entry in field:
            tee_time = entry.get("teetime", "TBD") or "TBD"
            starting_hole = str(entry.get("start_hole", "1"))
            groupings = entry.get("groupings", [])
            partner1 = groupings[0] if len(groupings) > 0 else ""
            partner2 = groupings[1] if len(groupings) > 1 else ""
            players.append(FieldPlayer(
                player_name=entry.get("player_name", "Unknown"),
                tee_time=tee_time,
                starting_hole=f"Hole {starting_hole}",
                partner1=partner1,
                partner2=partner2,
            ))
        return players
    except Exception:
        logger.warning("Failed to fetch field players", exc_info=True)
        return []


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=4), reraise=True)
def get_best_bets(api_key: str, top_n: int = 5, min_edge: float = 0.02) -> list[BettingEdge]:
    try:
        data = _get(
            api_key,
            "betting-tools/outrights",
            {"tour": "pga", "market": "win", "odds_format": "american"},
        )
        edges = []
        for p in data.get("odds", []):
            dg_win = float(p.get("baseline_history_fit", p.get("datagolf_baseline", 0)) or 0)
            if dg_win <= 0:
                continue
            best_book_pct = 0.0
            best_book_odds = ""
            best_book_name = ""
            books = ["draftkings", "fanduel", "betmgm", "caesars", "pinnacle", "bet365", "bovada", "betonline"]
            for book in books:
                odds_val = p.get(book)
                if odds_val is None:
                    continue
                try:
                    odds_float = float(odds_val)
                    implied_pct = _american_to_pct(odds_float)
                    if implied_pct > best_book_pct:
                        best_book_pct = implied_pct
                        best_book_odds = f"+{int(odds_float)}" if odds_float > 0 else str(int(odds_float))
                        best_book_name = book.capitalize()
                except (ValueError, TypeError):
                    continue
            if best_book_pct <= 0:
                continue
            edge = dg_win - best_book_pct
            if edge >= min_edge:
                edges.append(BettingEdge(
                    player_name=p.get("player_name", "Unknown"),
                    dg_win_pct=dg_win,
                    book_win_pct=best_book_pct,
                    edge=edge,
                    book_odds=best_book_odds,
                    book_name=best_book_name,
                ))
        return sorted(edges, key=lambda x: x.edge, reverse=True)[:top_n]
    except Exception:
        logger.warning("Failed to fetch betting edges", exc_info=True)
        return []


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=4), reraise=True)
def get_live_best_bets(api_key: str, top_n: int = 5, min_edge: float = 0.02) -> list[BettingEdge]:
    try:
        live_data = _get(api_key, "preds/in-play", {"tour": "pga", "odds_format": "percent"})
        live_probs: dict[str, float] = {}
        for p in live_data.get("data", []):
            name = p.get("player_name", "")
            win = p.get("win", 0)
            if name and win:
                live_probs[name] = float(win)
        if not live_probs:
            return []
        book_data = _get(
            api_key,
            "betting-tools/outrights",
            {"tour": "pga", "market": "win", "odds_format": "american"},
        )
        edges = []
        books = ["draftkings", "fanduel", "betmgm", "caesars", "pinnacle", "bet365", "bovada", "betonline"]
        for p in book_data.get("odds", []):
            name = p.get("player_name", "")
            dg_win = live_probs.get(name, 0)
            if dg_win <= 0:
                continue
            best_book_pct = 0.0
            best_book_odds = ""
            best_book_name = ""
            for book in books:
                odds_val = p.get(book)
                if odds_val is None:
                    continue
                try:
                    odds_float = float(odds_val)
                    implied_pct = _american_to_pct(odds_float)
                    if implied_pct > best_book_pct:
                        best_book_pct = implied_pct
                        best_book_odds = f"+{int(odds_float)}" if odds_float > 0 else str(int(odds_float))
                        best_book_name = book.capitalize()
                except (ValueError, TypeError):
                    continue
            if best_book_pct <= 0:
                continue
            edge = dg_win - best_book_pct
            if edge >= min_edge:
                edges.append(BettingEdge(
                    player_name=name,
                    dg_win_pct=dg_win,
                    book_win_pct=best_book_pct,
                    edge=edge,
                    book_odds=best_book_odds,
                    book_name=best_book_name,
                ))
        return sorted(edges, key=lambda x: x.edge, reverse=True)[:top_n]
    except Exception:
        logger.warning("Failed to fetch live betting edges", exc_info=True)
        return []

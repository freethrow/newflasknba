"""
Thin wrapper around the balldontlie.io v1 API.

Team lookup results are cached in-process for 1 hour.
Game results are fetched fresh on every call (callers should use HTMX lazy-load).
"""
import time

import requests

_BASE = "https://api.balldontlie.io/v1"

# module-level team cache: full_name -> team_id
_team_cache: dict[str, int] = {}
_team_cache_time: float = 0.0
_TEAM_TTL = 3600


def _headers(api_key: str) -> dict:
    return {"Authorization": api_key}


def _load_teams(api_key: str) -> None:
    global _team_cache, _team_cache_time
    resp = requests.get(
        f"{_BASE}/teams",
        headers=_headers(api_key),
        params={"per_page": 100},
        timeout=5,
    )
    resp.raise_for_status()
    teams = resp.json().get("data", [])
    _team_cache = {t["full_name"]: t["id"] for t in teams}
    _team_cache_time = time.time()


def get_team_id(name: str, api_key: str) -> int | None:
    if not _team_cache or time.time() - _team_cache_time > _TEAM_TTL:
        try:
            _load_teams(api_key)
        except Exception:
            return None
    return _team_cache.get(name)


def get_series_games(home: str, away: str, api_key: str, season: int = 2025) -> list:
    """Return all playoff games between home and away teams for the given season."""
    home_id = get_team_id(home, api_key)
    away_id = get_team_id(away, api_key)
    if not home_id or not away_id:
        return []

    resp = requests.get(
        f"{_BASE}/games",
        headers=_headers(api_key),
        params={
            "team_ids[]": [home_id, away_id],
            "seasons[]": [season],
            "postseason": "true",
            "per_page": 100,
        },
        timeout=5,
    )
    resp.raise_for_status()
    games = resp.json().get("data", [])

    # Keep only head-to-head matchups between these two teams
    both = {home_id, away_id}
    games = [
        g for g in games
        if g["home_team"]["id"] in both and g["visitor_team"]["id"] in both
    ]
    games.sort(key=lambda g: g["date"])
    return games


def series_standing(games: list) -> tuple[int, int]:
    """Return (home_wins, away_wins) from a list of finished head-to-head games.
    'Home' here means the series home team (first in our Series record),
    identified as the team with the lower API id (arbitrary but consistent).
    We instead track by team name stored on first game seen.
    """
    if not games:
        return 0, 0
    # Use the first game to establish which API team is our 'series home'
    first = games[0]
    series_home_id = first["home_team"]["id"]

    hw = aw = 0
    for g in games:
        if g["status"] != "Final":
            continue
        if g["home_team_score"] > g["visitor_team_score"]:
            winner_id = g["home_team"]["id"]
        else:
            winner_id = g["visitor_team"]["id"]
        if winner_id == series_home_id:
            hw += 1
        else:
            aw += 1
    return hw, aw

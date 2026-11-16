"""MLB data from the MLB Stats API (statsapi.mlb.com).

Free for personal, non-commercial use. `fetch_*` functions do HTTP;
`parse_*` functions are pure and turn JSON into source-neutral dataclasses.
"""
from contextlib import contextmanager
from datetime import date, datetime, timedelta
from typing import Dict, Iterator, List, Optional, Tuple

import httpx

from app.models import GameStatus
from app.sources.base import (
    GameData,
    InningData,
    StandingData,
    TeamData,
    make_client,
)

BASE_URL = "https://statsapi.mlb.com/api/v1"
SPORT_ID = 1
LEAGUE_IDS = "103,104"  # American League, National League
LOGO_URL = "https://www.mlbstatic.com/team-logos/{id}.svg"

# Regular season + postseason rounds. Spring training and exhibitions are skipped.
GAME_TYPES = {
    "R": "regular",
    "F": "postseason",  # Wild Card Series
    "D": "postseason",  # Division Series
    "L": "postseason",  # League Championship Series
    "W": "postseason",  # World Series
}

# The API has no team colors, so they are kept here (primary, secondary).
TEAM_COLORS: Dict[int, Tuple[str, str]] = {
    108: ("#BA0021", "#003263"),  # Angels
    109: ("#A71930", "#E3D4AD"),  # D-backs
    110: ("#DF4601", "#000000"),  # Orioles
    111: ("#BD3039", "#0C2340"),  # Red Sox
    112: ("#0E3386", "#CC3433"),  # Cubs
    113: ("#C6011F", "#000000"),  # Reds
    114: ("#00385D", "#E50022"),  # Guardians
    115: ("#333366", "#C4CED4"),  # Rockies
    116: ("#0C2340", "#FA4616"),  # Tigers
    117: ("#002D62", "#EB6E1F"),  # Astros
    118: ("#004687", "#BD9B60"),  # Royals
    119: ("#005A9C", "#EF3E42"),  # Dodgers
    120: ("#AB0003", "#14225A"),  # Nationals
    121: ("#002D72", "#FF5910"),  # Mets
    133: ("#003831", "#EFB21E"),  # Athletics
    134: ("#27251F", "#FDB827"),  # Pirates
    135: ("#2F241D", "#FFC425"),  # Padres
    136: ("#0C2C56", "#005C5C"),  # Mariners
    137: ("#FD5A1E", "#27251F"),  # Giants
    138: ("#C41E3A", "#0C2340"),  # Cardinals
    139: ("#092C5C", "#8FBCE6"),  # Rays
    140: ("#003278", "#C0111F"),  # Rangers
    141: ("#134A8E", "#1D2D5C"),  # Blue Jays
    142: ("#002B5C", "#D31145"),  # Twins
    143: ("#E81828", "#002D72"),  # Phillies
    144: ("#CE1141", "#13274F"),  # Braves
    145: ("#27251F", "#C4CED4"),  # White Sox
    146: ("#00A3E0", "#EF3340"),  # Marlins
    147: ("#0C2340", "#C4CED4"),  # Yankees
    158: ("#12284B", "#FFC52F"),  # Brewers
}


# ---------- parsing (pure) ----------


def parse_status(status: dict) -> str:
    detailed = status.get("detailedState", "")
    if detailed.startswith("Postponed"):
        return GameStatus.POSTPONED
    if detailed.startswith("Cancelled"):
        return GameStatus.CANCELLED
    if detailed.startswith("Suspended"):
        return GameStatus.SUSPENDED
    abstract = status.get("abstractGameState")
    if abstract == "Final":
        return GameStatus.FINAL
    if abstract == "Live":
        return GameStatus.IN_PROGRESS
    return GameStatus.SCHEDULED


def parse_team(raw: dict) -> TeamData:
    team_id = raw["id"]
    colors = TEAM_COLORS.get(team_id, (None, None))
    league = raw.get("league") or {}
    division = raw.get("division") or {}
    return TeamData(
        source_id=str(team_id),
        name=raw["name"],
        short_name=raw.get("teamName") or raw.get("clubName") or raw["name"],
        abbreviation=raw.get("abbreviation") or raw["name"][:3].upper(),
        sub_league=league.get("abbreviation"),
        division=division.get("nameShort"),
        logo_url=LOGO_URL.format(id=team_id),
        primary_color=colors[0],
        secondary_color=colors[1],
    )


def parse_teams(payload: dict) -> List[TeamData]:
    return [parse_team(t) for t in payload.get("teams", [])]


def _parse_time(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def parse_game(raw: dict) -> GameData:
    linescore = raw.get("linescore") or {}
    totals = linescore.get("teams") or {}
    decisions = raw.get("decisions") or {}
    teams = raw["teams"]
    status = parse_status(raw.get("status", {}))
    has_score = status in (GameStatus.FINAL, GameStatus.IN_PROGRESS, GameStatus.SUSPENDED)

    innings = [
        InningData(
            inning=inn["num"],
            away_runs=(inn.get("away") or {}).get("runs"),
            home_runs=(inn.get("home") or {}).get("runs"),
        )
        for inn in linescore.get("innings", [])
    ]

    def pitcher(key: str) -> Optional[str]:
        return (decisions.get(key) or {}).get("fullName")

    return GameData(
        source_id=str(raw["gamePk"]),
        season=int(raw["season"]),
        game_date=date.fromisoformat(raw["officialDate"]),
        start_time=_parse_time(raw.get("gameDate")),
        status=status,
        game_type=GAME_TYPES.get(raw.get("gameType", "R"), "other"),
        round_name=raw.get("seriesDescription") if raw.get("gameType") != "R" else None,
        away_team=parse_team(teams["away"]["team"]),
        home_team=parse_team(teams["home"]["team"]),
        away_score=teams["away"].get("score") if has_score else None,
        home_score=teams["home"].get("score") if has_score else None,
        away_hits=(totals.get("away") or {}).get("hits") if has_score else None,
        home_hits=(totals.get("home") or {}).get("hits") if has_score else None,
        away_errors=(totals.get("away") or {}).get("errors") if has_score else None,
        home_errors=(totals.get("home") or {}).get("errors") if has_score else None,
        venue=(raw.get("venue") or {}).get("name"),
        winning_pitcher=pitcher("winner"),
        losing_pitcher=pitcher("loser"),
        save_pitcher=pitcher("save"),
        innings=innings,
    )


def parse_schedule(payload: dict) -> List[GameData]:
    games = []
    for day in payload.get("dates", []):
        for raw in day.get("games", []):
            if raw.get("gameType") in GAME_TYPES:
                games.append(parse_game(raw))
    return games


def _record(splits: List[dict], kind: str) -> Optional[str]:
    for s in splits:
        if s.get("type") == kind:
            return f"{s['wins']}-{s['losses']}"
    return None


def parse_standings(payload: dict) -> List[StandingData]:
    rows = []
    for group in payload.get("records", []):
        group_name = group["division"].get("nameShort") or group["division"]["name"]
        for t in group.get("teamRecords", []):
            splits = (t.get("records") or {}).get("splitRecords", [])
            rows.append(
                StandingData(
                    team_source_id=str(t["team"]["id"]),
                    group_name=group_name,
                    rank=int(t["divisionRank"]),
                    wins=t["wins"],
                    losses=t["losses"],
                    pct=t["winningPercentage"],
                    games_back=t["gamesBack"],
                    home_record=_record(splits, "home"),
                    away_record=_record(splits, "away"),
                    last_ten=_record(splits, "lastTen"),
                    streak=(t.get("streak") or {}).get("streakCode"),
                    run_differential=t.get("runDifferential"),
                    clinched=bool(t.get("clinched")),
                )
            )
    return rows


# ---------- fetching (HTTP) ----------


@contextmanager
def _client(client: Optional[httpx.Client]):
    """Use the caller's client, or open (and later close) a new one."""
    if client is not None:
        yield client
    else:
        with make_client() as c:
            yield c


def _get(client: httpx.Client, path: str, **params) -> dict:
    resp = client.get(f"{BASE_URL}{path}", params=params)
    resp.raise_for_status()
    return resp.json()


def fetch_teams(season: int, client: Optional[httpx.Client] = None) -> List[TeamData]:
    with _client(client) as c:
        payload = _get(c, "/teams", sportId=SPORT_ID, season=season, hydrate="division,league")
    return parse_teams(payload)


def fetch_season_dates(season: int, client: Optional[httpx.Client] = None) -> Tuple[date, date]:
    """First regular-season day and last postseason day."""
    with _client(client) as c:
        payload = _get(c, f"/seasons/{season}", sportId=SPORT_ID)
    info = payload["seasons"][0]
    end = info.get("postSeasonEndDate") or info["regularSeasonEndDate"]
    return date.fromisoformat(info["regularSeasonStartDate"]), date.fromisoformat(end)


def _chunks(start: date, end: date, days: int) -> Iterator[Tuple[date, date]]:
    cur = start
    while cur <= end:
        stop = min(cur + timedelta(days=days - 1), end)
        yield cur, stop
        cur = stop + timedelta(days=1)


def fetch_games(start: date, end: date, client: Optional[httpx.Client] = None) -> List[GameData]:
    """All regular-season and postseason games between two dates (inclusive)."""
    games: List[GameData] = []
    with _client(client) as c:
        for chunk_start, chunk_end in _chunks(start, end, days=31):
            payload = _get(
                c,
                "/schedule",
                sportId=SPORT_ID,
                startDate=chunk_start.isoformat(),
                endDate=chunk_end.isoformat(),
                gameType=",".join(GAME_TYPES),
                hydrate="linescore,decisions,team,venue,seriesStatus",
            )
            games.extend(parse_schedule(payload))
    return games


def fetch_standings(season: int, client: Optional[httpx.Client] = None) -> List[StandingData]:
    with _client(client) as c:
        payload = _get(
            c,
            "/standings",
            leagueId=LEAGUE_IDS,
            season=season,
            standingsTypes="regularSeason",
            hydrate="division",
        )
    return parse_standings(payload)

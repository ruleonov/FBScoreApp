"""Source-neutral data shapes.

Every source module turns its raw data (JSON, HTML) into these dataclasses.
`app.ingest` then saves them to the database. Keeping parsing separate from
saving means parsers can be tested with saved sample files and no database.
"""
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import List, Optional

import httpx

USER_AGENT = "BaseballScore/0.1 (personal, non-commercial learning project)"


def make_client() -> httpx.Client:
    return httpx.Client(
        timeout=30.0,
        headers={"User-Agent": USER_AGENT},
        transport=httpx.HTTPTransport(retries=3),
        follow_redirects=True,
    )


@dataclass
class TeamData:
    source_id: str
    name: str
    short_name: str
    abbreviation: str
    sub_league: Optional[str] = None
    division: Optional[str] = None
    logo_url: Optional[str] = None
    primary_color: Optional[str] = None
    secondary_color: Optional[str] = None


@dataclass
class InningData:
    inning: int
    away_runs: Optional[int]
    home_runs: Optional[int]


@dataclass
class GameData:
    source_id: str
    season: int
    game_date: date
    status: str
    away_team: TeamData
    home_team: TeamData
    start_time: Optional[datetime] = None
    game_type: str = "regular"
    round_name: Optional[str] = None
    away_score: Optional[int] = None
    home_score: Optional[int] = None
    away_hits: Optional[int] = None
    home_hits: Optional[int] = None
    away_errors: Optional[int] = None
    home_errors: Optional[int] = None
    venue: Optional[str] = None
    winning_pitcher: Optional[str] = None
    losing_pitcher: Optional[str] = None
    save_pitcher: Optional[str] = None
    innings: List[InningData] = field(default_factory=list)


@dataclass
class StandingData:
    team_source_id: str
    group_name: str
    rank: int
    wins: int
    losses: int
    pct: str
    games_back: str
    ties: int = 0
    home_record: Optional[str] = None
    away_record: Optional[str] = None
    last_ten: Optional[str] = None
    streak: Optional[str] = None
    run_differential: Optional[int] = None
    clinched: bool = False

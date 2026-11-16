"""Database models shared by every league.

Each source (MLB API, npb.jp, ...) is converted into these tables, so the
web pages never need to know where the data came from.
"""
from datetime import date, datetime, timezone
from typing import Optional

from sqlmodel import Field, SQLModel, UniqueConstraint


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class GameStatus:
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    FINAL = "final"
    POSTPONED = "postponed"
    SUSPENDED = "suspended"
    CANCELLED = "cancelled"


class League(SQLModel, table=True):
    id: str = Field(primary_key=True)  # "mlb", "npb", "kbo", "wbc", "olympics"
    name: str
    sort_order: int = 0


class Team(SQLModel, table=True):
    __table_args__ = (UniqueConstraint("league_id", "source_id"),)

    id: Optional[int] = Field(default=None, primary_key=True)
    league_id: str = Field(foreign_key="league.id", index=True)
    source_id: str  # the team's id in the source system
    name: str  # "New York Yankees"
    short_name: str  # "Yankees"
    abbreviation: str  # "NYY"
    sub_league: Optional[str] = None  # "AL" / "NL", "Central" / "Pacific"
    division: Optional[str] = None  # "AL East"
    logo_url: Optional[str] = None
    primary_color: Optional[str] = None  # "#0C2340"
    secondary_color: Optional[str] = None


class Game(SQLModel, table=True):
    __table_args__ = (UniqueConstraint("league_id", "source_id"),)

    id: Optional[int] = Field(default=None, primary_key=True)
    league_id: str = Field(foreign_key="league.id", index=True)
    source_id: str
    season: int = Field(index=True)
    game_date: date = Field(index=True)  # local date the game was played
    start_time: Optional[datetime] = None  # UTC
    game_type: str = "regular"  # "regular", "postseason", "pool", ...
    round_name: Optional[str] = None  # "World Series", "Pool A", ...
    status: str = GameStatus.SCHEDULED
    away_team_id: int = Field(foreign_key="team.id")
    home_team_id: int = Field(foreign_key="team.id")
    away_score: Optional[int] = None
    home_score: Optional[int] = None
    away_hits: Optional[int] = None
    home_hits: Optional[int] = None
    away_errors: Optional[int] = None
    home_errors: Optional[int] = None
    innings: Optional[int] = None
    venue: Optional[str] = None
    winning_pitcher: Optional[str] = None
    losing_pitcher: Optional[str] = None
    save_pitcher: Optional[str] = None
    updated_at: datetime = Field(default_factory=utcnow)


class InningScore(SQLModel, table=True):
    game_id: int = Field(foreign_key="game.id", primary_key=True)
    inning: int = Field(primary_key=True)
    away_runs: Optional[int] = None
    home_runs: Optional[int] = None  # None = bottom half not played ("X")


class Standing(SQLModel, table=True):
    league_id: str = Field(foreign_key="league.id", primary_key=True)
    season: int = Field(primary_key=True)
    team_id: int = Field(foreign_key="team.id", primary_key=True)
    group_name: str  # "AL East", "Central League", "Pool A"
    rank: int
    wins: int
    losses: int
    ties: int = 0
    pct: str  # ".605" — kept as text, the way leagues print it
    games_back: str  # "-" for the leader
    home_record: Optional[str] = None  # "55-26"
    away_record: Optional[str] = None
    last_ten: Optional[str] = None
    streak: Optional[str] = None  # "W3" / "L1"
    run_differential: Optional[int] = None
    clinched: bool = False
    updated_at: datetime = Field(default_factory=utcnow)

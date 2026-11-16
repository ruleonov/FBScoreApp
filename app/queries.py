"""Read-side helpers used by the web pages."""
from collections import OrderedDict
from dataclasses import dataclass
from datetime import date
from typing import Dict, List, Optional

from sqlmodel import Session, func, select

from app.models import Game, InningScore, Standing, Team


@dataclass
class GameView:
    game: Game
    away: Team
    home: Team
    innings: List[InningScore]

    @property
    def winner_side(self) -> Optional[str]:
        g = self.game
        if g.away_score is None or g.home_score is None or g.away_score == g.home_score:
            return None
        return "away" if g.away_score > g.home_score else "home"

    @property
    def max_inning_runs(self) -> int:
        """Tallest bar in the runs-by-inning chart (at least 1)."""
        runs = [r for i in self.innings for r in (i.away_runs, i.home_runs) if r]
        return max(runs, default=1)


def _teams(session: Session, ids) -> Dict[int, Team]:
    ids = set(ids)
    if not ids:
        return {}
    return {t.id: t for t in session.exec(select(Team).where(Team.id.in_(ids))).all()}


def _views(session: Session, games: List[Game], with_innings: bool = False) -> List[GameView]:
    teams = _teams(session, [g.away_team_id for g in games] + [g.home_team_id for g in games])
    innings: Dict[int, List[InningScore]] = {}
    if with_innings and games:
        rows = session.exec(
            select(InningScore)
            .where(InningScore.game_id.in_([g.id for g in games]))
            .order_by(InningScore.inning)
        ).all()
        for row in rows:
            innings.setdefault(row.game_id, []).append(row)
    return [
        GameView(g, teams[g.away_team_id], teams[g.home_team_id], innings.get(g.id, []))
        for g in games
    ]


def latest_game_date(session: Session, league_id: str, on_or_before: date) -> Optional[date]:
    return session.exec(
        select(func.max(Game.game_date)).where(
            Game.league_id == league_id, Game.game_date <= on_or_before
        )
    ).first()


def neighbor_dates(session: Session, league_id: str, day: date):
    prev_day = session.exec(
        select(func.max(Game.game_date)).where(Game.league_id == league_id, Game.game_date < day)
    ).first()
    next_day = session.exec(
        select(func.min(Game.game_date)).where(Game.league_id == league_id, Game.game_date > day)
    ).first()
    return prev_day, next_day


def games_on(session: Session, league_id: str, day: date) -> List[GameView]:
    games = session.exec(
        select(Game)
        .where(Game.league_id == league_id, Game.game_date == day)
        .order_by(Game.start_time, Game.id)
    ).all()
    return _views(session, list(games), with_innings=True)


def game_detail(session: Session, game_id: int) -> Optional[GameView]:
    game = session.get(Game, game_id)
    if game is None:
        return None
    return _views(session, [game], with_innings=True)[0]


def latest_season(session: Session, league_id: str) -> Optional[int]:
    return session.exec(
        select(func.max(Standing.season)).where(Standing.league_id == league_id)
    ).first()


def standings(session: Session, league_id: str, season: int) -> "OrderedDict[str, list]":
    """{group_name: [(Standing, Team), ...]} sorted by group, then rank."""
    rows = session.exec(
        select(Standing, Team)
        .join(Team, Team.id == Standing.team_id)
        .where(Standing.league_id == league_id, Standing.season == season)
        .order_by(Standing.group_name, Standing.rank)
    ).all()
    groups: "OrderedDict[str, list]" = OrderedDict()
    for standing, team in rows:
        groups.setdefault(standing.group_name, []).append((standing, team))
    return groups

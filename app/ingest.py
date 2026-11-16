"""Save source-neutral data (app.sources.base) into the database.

All functions are upserts: running them twice gives the same result, so a
backfill or a scheduled refresh can safely repeat.
"""
from dataclasses import asdict
from typing import Dict, Iterable

from sqlmodel import Session, delete, select

from app.models import Game, GameStatus, InningScore, Standing, Team, utcnow
from app.sources.base import GameData, StandingData, TeamData

# A game that already finished must not be overwritten by an older entry for
# the same game (the API lists a postponed game on both its original and
# its make-up date).
_FINISHED = {GameStatus.FINAL}


def upsert_team(session: Session, league_id: str, data: TeamData) -> Team:
    team = session.exec(
        select(Team).where(Team.league_id == league_id, Team.source_id == data.source_id)
    ).first()
    if team is None:
        team = Team(league_id=league_id, **asdict(data))
    else:
        # Only fill in values we have; a game's team stub lacks e.g. division.
        for key, value in asdict(data).items():
            if value is not None:
                setattr(team, key, value)
    session.add(team)
    session.flush()
    return team


def upsert_teams(session: Session, league_id: str, teams: Iterable[TeamData]) -> int:
    count = 0
    for data in teams:
        upsert_team(session, league_id, data)
        count += 1
    session.commit()
    return count


def upsert_games(session: Session, league_id: str, games: Iterable[GameData]) -> int:
    team_cache: Dict[str, Team] = {}

    def team_for(data: TeamData) -> Team:
        if data.source_id not in team_cache:
            team_cache[data.source_id] = upsert_team(session, league_id, data)
        return team_cache[data.source_id]

    count = 0
    for data in games:
        game = session.exec(
            select(Game).where(Game.league_id == league_id, Game.source_id == data.source_id)
        ).first()
        if game is not None and game.status in _FINISHED and data.status not in _FINISHED:
            continue

        fields = asdict(data)
        fields.pop("innings")
        fields.pop("away_team")
        fields.pop("home_team")
        fields["away_team_id"] = team_for(data.away_team).id
        fields["home_team_id"] = team_for(data.home_team).id
        fields["innings"] = len(data.innings) or None
        fields["updated_at"] = utcnow()

        if game is None:
            game = Game(league_id=league_id, **fields)
        else:
            for key, value in fields.items():
                setattr(game, key, value)
        session.add(game)
        session.flush()

        session.exec(delete(InningScore).where(InningScore.game_id == game.id))
        for inn in data.innings:
            session.add(
                InningScore(
                    game_id=game.id,
                    inning=inn.inning,
                    away_runs=inn.away_runs,
                    home_runs=inn.home_runs,
                )
            )
        count += 1
    session.commit()
    return count


def replace_standings(
    session: Session, league_id: str, season: int, rows: Iterable[StandingData]
) -> int:
    """Standings are a snapshot, so the season's old rows are replaced."""
    teams = {
        t.source_id: t
        for t in session.exec(select(Team).where(Team.league_id == league_id)).all()
    }
    session.exec(
        delete(Standing).where(Standing.league_id == league_id, Standing.season == season)
    )
    count = 0
    for row in rows:
        team = teams.get(row.team_source_id)
        if team is None:
            continue  # unknown team; fetch teams first
        fields = asdict(row)
        fields.pop("team_source_id")
        session.add(Standing(league_id=league_id, season=season, team_id=team.id, **fields))
        count += 1
    session.commit()
    return count

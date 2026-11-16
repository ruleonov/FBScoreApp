from datetime import date

from fastapi.testclient import TestClient
from sqlmodel import select

from app.ingest import replace_standings, upsert_games, upsert_teams
from app.main import app
from app.models import Game, GameStatus, InningScore, Standing
from app.sources import mlb
from tests.conftest import load_fixture


# ---------- parsing ----------


def test_parse_status():
    assert mlb.parse_status({"abstractGameState": "Final", "detailedState": "Final"}) == "final"
    assert mlb.parse_status({"abstractGameState": "Final", "detailedState": "Postponed"}) == "postponed"
    assert mlb.parse_status({"abstractGameState": "Final", "detailedState": "Cancelled"}) == "cancelled"
    assert mlb.parse_status({"abstractGameState": "Live", "detailedState": "Suspended: Rain"}) == "suspended"
    assert mlb.parse_status({"abstractGameState": "Live", "detailedState": "In Progress"}) == "in_progress"
    assert mlb.parse_status({"abstractGameState": "Preview", "detailedState": "Scheduled"}) == "scheduled"


def test_parse_world_series_game():
    games = mlb.parse_schedule(load_fixture("mlb_schedule.json"))
    ws = [g for g in games if g.round_name == "World Series"][0]
    assert ws.game_date == date(2026, 10, 28)
    assert ws.status == GameStatus.FINAL
    assert ws.game_type == "postseason"
    assert (ws.away_team.abbreviation, ws.away_score) == ("MIL", 4)
    assert (ws.home_team.abbreviation, ws.home_score) == ("TB", 1)
    assert ws.winning_pitcher and ws.losing_pitcher
    assert len(ws.innings) == 9
    assert sum(i.away_runs for i in ws.innings) == ws.away_score
    assert ws.away_team.logo_url.endswith("/158.svg")
    assert ws.away_team.primary_color == "#12284B"


def test_regular_season_game_has_no_round_name():
    games = mlb.parse_schedule(load_fixture("mlb_schedule.json"))
    regular = [g for g in games if g.game_date == date(2026, 9, 20)]
    assert regular and all(g.game_type == "regular" and g.round_name is None for g in regular)


def test_parse_teams_has_divisions():
    teams = {t.abbreviation: t for t in mlb.parse_teams(load_fixture("mlb_teams.json"))}
    assert teams["NYY"].division == "AL East"
    assert teams["NYY"].sub_league == "AL"
    assert teams["NYY"].name == "New York Yankees"


def test_parse_standings():
    rows = mlb.parse_standings(load_fixture("mlb_standings.json"))
    assert len(rows) == 10  # two divisions in the fixture
    leader = [r for r in rows if r.rank == 1][0]
    assert leader.games_back == "-"
    assert leader.home_record and leader.away_record and leader.last_ten
    assert leader.streak[0] in "WL"


# ---------- saving ----------


def test_ingest_is_idempotent(session):
    upsert_teams(session, "mlb", mlb.parse_teams(load_fixture("mlb_teams.json")))
    games = mlb.parse_schedule(load_fixture("mlb_schedule.json"))
    upsert_games(session, "mlb", games)
    upsert_games(session, "mlb", games)

    assert len(session.exec(select(Game)).all()) == len(games)
    ws = session.exec(select(Game).where(Game.round_name == "World Series")).one()
    innings = session.exec(select(InningScore).where(InningScore.game_id == ws.id)).all()
    assert len(innings) == 9


def test_postponed_entry_does_not_overwrite_final(session):
    games = mlb.parse_schedule(load_fixture("mlb_schedule.json"))
    final = games[0]
    upsert_games(session, "mlb", [final])

    # Same game id listed again as postponed (as the API does for make-up games).
    final.status = GameStatus.POSTPONED
    final.away_score = final.home_score = None
    upsert_games(session, "mlb", [final])

    saved = session.exec(select(Game).where(Game.source_id == final.source_id)).one()
    assert saved.status == GameStatus.FINAL
    assert saved.away_score is not None


def test_standings_replace(session):
    upsert_teams(session, "mlb", mlb.parse_teams(load_fixture("mlb_teams.json")))
    rows = mlb.parse_standings(load_fixture("mlb_standings.json"))
    replace_standings(session, "mlb", 2026, rows)
    first = len(session.exec(select(Standing)).all())
    replace_standings(session, "mlb", 2026, rows)
    # Only teams present in the trimmed teams fixture are saved, and no duplicates.
    assert len(session.exec(select(Standing)).all()) == first > 0


# ---------- web pages ----------


def test_pages_render(session):
    upsert_teams(session, "mlb", mlb.parse_teams(load_fixture("mlb_teams.json")))
    upsert_games(session, "mlb", mlb.parse_schedule(load_fixture("mlb_schedule.json")))
    replace_standings(session, "mlb", 2026, mlb.parse_standings(load_fixture("mlb_standings.json")))
    ws = session.exec(select(Game).where(Game.round_name == "World Series")).one()

    with TestClient(app) as client:
        r = client.get("/mlb")  # defaults to the latest day with games
        assert r.status_code == 200 and "World Series" in r.text

        r = client.get("/mlb?day=2026-12-25")
        assert r.status_code == 200 and "No games on this day" in r.text

        r = client.get(f"/mlb/game/{ws.id}")
        assert r.status_code == 200 and "Runs by inning" in r.text

        r = client.get("/mlb/standings")
        assert r.status_code == 200 and "AL East" in r.text

        assert client.get("/mlb/game/999999").status_code == 404

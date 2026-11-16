"""Load a whole season (or a date range) into the database.

Examples:
    python -m scripts.backfill mlb 2026
    python -m scripts.backfill mlb 2026 --start 2026-09-01 --end 2026-09-30
"""
import argparse
import sys
from datetime import date

from sqlmodel import Session

from app.db import engine, init_db
from app.ingest import replace_standings, upsert_games, upsert_teams
from app.sources import mlb
from app.sources.base import make_client


def backfill_mlb(season: int, start: date = None, end: date = None) -> None:
    with make_client() as client, Session(engine) as session:
        teams = mlb.fetch_teams(season, client)
        print(f"teams:     {upsert_teams(session, 'mlb', teams)}")

        if start is None or end is None:
            season_start, season_end = mlb.fetch_season_dates(season, client)
            start, end = start or season_start, end or season_end
        print(f"games:     fetching {start} to {end} ...")
        games = mlb.fetch_games(start, end, client)
        print(f"games:     {upsert_games(session, 'mlb', games)}")

        rows = mlb.fetch_standings(season, client)
        print(f"standings: {replace_standings(session, 'mlb', season, rows)}")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("league", choices=["mlb"])
    parser.add_argument("season", type=int)
    parser.add_argument("--start", type=date.fromisoformat)
    parser.add_argument("--end", type=date.fromisoformat)
    args = parser.parse_args(argv)

    init_db()
    if args.league == "mlb":
        backfill_mlb(args.season, args.start, args.end)
    return 0


if __name__ == "__main__":
    sys.exit(main())

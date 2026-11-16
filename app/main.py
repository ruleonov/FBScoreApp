"""BaseballScore web app.

Run:  .venv/bin/uvicorn app.main:app --reload
"""
from contextlib import asynccontextmanager
from datetime import date
from pathlib import Path
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlmodel import Session

from app import queries
from app.db import get_session, init_db
from app.i18n import template_context

APP_DIR = Path(__file__).parent

@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    yield


app = FastAPI(title="BaseballScore", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=APP_DIR / "static"), name="static")
templates = Jinja2Templates(directory=APP_DIR / "templates")

LEAGUE_TABS = [
    ("mlb", "MLB", True),
    ("npb", "NPB", False),
    ("kbo", "KBO", False),
    ("wbc", "WBC", False),
    ("olympics", "Olympics", False),
]

MLB_DIVISION_ORDER = ["AL East", "AL Central", "AL West", "NL East", "NL Central", "NL West"]


def render(request: Request, name: str, **context):
    ctx = template_context("en")
    ctx.update(request=request, league_tabs=LEAGUE_TABS, **context)
    return templates.TemplateResponse(request, name, ctx)


@app.get("/")
def home():
    return RedirectResponse("/mlb")


@app.get("/mlb")
def mlb_scores(
    request: Request,
    day: Optional[date] = None,
    session: Session = Depends(get_session),
):
    # With no date, show the most recent day that had games (useful in the offseason).
    if day is None:
        day = queries.latest_game_date(session, "mlb", date.today()) or date.today()
    games = queries.games_on(session, "mlb", day)
    prev_day, next_day = queries.neighbor_dates(session, "mlb", day)
    return render(
        request,
        "scores.html",
        league="mlb",
        tab="scores",
        day=day,
        games=games,
        prev_day=prev_day,
        next_day=next_day,
    )


@app.get("/mlb/standings")
def mlb_standings(
    request: Request,
    season: Optional[int] = None,
    session: Session = Depends(get_session),
):
    season = season or queries.latest_season(session, "mlb")
    groups = queries.standings(session, "mlb", season) if season else {}
    groups = {name: groups[name] for name in MLB_DIVISION_ORDER if name in groups}
    return render(
        request, "standings.html", league="mlb", tab="standings", season=season, groups=groups
    )


@app.get("/mlb/game/{game_id}")
def mlb_game(request: Request, game_id: int, session: Session = Depends(get_session)):
    view = queries.game_detail(session, game_id)
    if view is None or view.game.league_id != "mlb":
        raise HTTPException(status_code=404)
    return render(request, "game.html", league="mlb", tab="scores", v=view)

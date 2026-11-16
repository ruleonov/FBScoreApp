import os
from pathlib import Path

from sqlmodel import Session, SQLModel, create_engine

from app.models import League

ROOT = Path(__file__).resolve().parent.parent
DATABASE_URL = os.environ.get(
    "BASEBALLSCORE_DB", f"sqlite:///{ROOT / 'data' / 'baseballscore.db'}"
)

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

LEAGUES = [
    League(id="mlb", name="MLB", sort_order=1),
    League(id="npb", name="NPB", sort_order=2),
    League(id="kbo", name="KBO", sort_order=3),
    League(id="wbc", name="World Baseball Classic", sort_order=4),
    League(id="olympics", name="Olympics", sort_order=5),
]


def init_db(eng=None) -> None:
    eng = eng or engine
    if eng.url.drivername == "sqlite" and eng.url.database:
        Path(eng.url.database).parent.mkdir(parents=True, exist_ok=True)
    SQLModel.metadata.create_all(eng)
    with Session(eng) as session:
        for league in LEAGUES:
            session.merge(league)
        session.commit()


def get_session():
    with Session(engine) as session:
        yield session

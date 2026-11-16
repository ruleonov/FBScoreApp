import json
import os
import tempfile
from pathlib import Path

# Point the app at a throwaway database before anything imports app.db.
_tmp = tempfile.mkdtemp(prefix="baseballscore-test-")
os.environ["BASEBALLSCORE_DB"] = f"sqlite:///{Path(_tmp) / 'test.db'}"

import pytest  # noqa: E402
from sqlmodel import Session, SQLModel  # noqa: E402

from app.db import engine, init_db  # noqa: E402

FIXTURES = Path(__file__).parent / "fixtures"


def load_fixture(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text())


@pytest.fixture
def session():
    SQLModel.metadata.drop_all(engine)
    init_db(engine)
    with Session(engine) as s:
        yield s

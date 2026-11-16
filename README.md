# BaseballScore

Final results and standings for MLB, NPB, KBO, the World Baseball Classic and the Olympics.
Personal, non-commercial learning project. Mascot: Pheebik (Фибик).

## Setup

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

## Load data

```bash
.venv/bin/python -m scripts.backfill mlb 2026
```

Re-running is safe: games and teams are updated in place, standings are replaced.

## Run

```bash
.venv/bin/uvicorn app.main:app --reload
```

Then open http://127.0.0.1:8000.

## Test

```bash
.venv/bin/python -m pytest -q
```

## Layout

| Path | What it does |
|---|---|
| `app/sources/` | One module per data source. `parse_*` functions are pure; `fetch_*` do HTTP. |
| `app/ingest.py` | Saves parsed data into the database (upserts). |
| `app/models.py` | League, Team, Game, InningScore, Standing tables shared by all leagues. |
| `app/queries.py` | Read helpers for the pages. |
| `app/main.py` | FastAPI routes. |
| `app/templates/` | Jinja2 pages. All text goes through `_()` for translation. |
| `app/i18n.py` | Translation setup (English now, Russian later). |
| `scripts/backfill.py` | Loads a season or date range. |
| `tests/fixtures/` | Saved real API responses used by the tests. |

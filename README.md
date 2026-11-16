# FBScoreApp

MLB final results and division standings, with the interface in Russian
(team names stay in English). Personal, non-commercial learning project.
Mascot: Pheebik (Фибик). Telegram: https://t.me/baseballpeople

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

## Changing interface text

Text is written in English inside `_()` and translated in
`app/translations/ru/LC_MESSAGES/messages.po`. After changing it:

```bash
.venv/bin/pybabel extract -F babel.cfg -k N_ -o app/translations/messages.pot .
.venv/bin/pybabel update -i app/translations/messages.pot -d app/translations
.venv/bin/pybabel compile -d app/translations
```

A test fails if any text is left untranslated.

## Layout

| Path | What it does |
|---|---|
| `app/sources/` | One module per data source. `parse_*` functions are pure; `fetch_*` do HTTP. |
| `app/ingest.py` | Saves parsed data into the database (upserts). |
| `app/models.py` | League, Team, Game, InningScore, Standing tables shared by all leagues. |
| `app/queries.py` | Read helpers for the pages. |
| `app/main.py` | FastAPI routes. |
| `app/templates/` | Jinja2 pages. All text goes through `_()` for translation. |
| `app/i18n.py` | Translation setup; Russian is the default language. |
| `app/translations/` | Russian translations (`.po` source, compiled `.mo`). |
| `scripts/backfill.py` | Loads a season or date range. |
| `tests/fixtures/` | Saved real API responses used by the tests. |

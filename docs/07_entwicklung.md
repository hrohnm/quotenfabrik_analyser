# 07 – Entwicklung

## Voraussetzungen
- Python 3.12+
- Docker + Docker Compose (für PostgreSQL 16)
- Umgebungsvariablen (lokal in `.env`, niemals committen):

| Variable | Beispiel | Zweck |
|---|---|---|
| `API_FOOTBALL_KEY` | – | API-Key von api-sports.io |
| `DATABASE_URL` | `postgresql+psycopg://qf:qf@localhost:5432/quotenfabrik` | DB-Verbindung |
| `QF_LEAGUES` | `78` | aktive Ligen (API-IDs) |
| `QF_FD_LEAGUES` | `D1` | football-data.co.uk-Kürzel |
| `QF_API_MAX_RPS` | `4` | Drosselung API-Football |
| `QF_API_QUOTA_RESERVE` | `500` | Requests, die nie verbraucht werden (Reserve für Snapshots) |

## Setup

```bash
cp .env.example .env              # Werte eintragen
docker compose up -d db
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
alembic upgrade head
```

## CLI (`qf`)

| Befehl | Wirkung | API-Kosten |
|---|---|---|
| `qf status` | Quota, Abo-Ende, letzter Import | 0 |
| `qf ingest football-data --seasons 2015-2026` | CSVs laden + normalisieren | 0 |
| `qf ingest api-football --seasons 2015-2026 [--half-stats]` | Backfill Fixtures + Details | ≈200 (+700 mit Halbzeit-Stats) |
| `qf ingest injuries --seasons 2021-2026` | Ausfälle | ≈6 |
| `qf map-teams` | football-data ↔ API verknüpfen, Report ausgeben | 0 |
| `qf odds snapshot` | aktueller Quotenstand aller kommenden Spiele | 2–4 |
| `qf rebuild core --from-raw` | `core.*` aus Rohdaten neu aufbauen | 0 |
| `qf analyse --fixture <id>` / `--next-matchday` | Modelle + Pattern rechnen | 0 |
| `qf backtest --market 1x2 --from 2019 --to 2026` | Walk-Forward-Backtest | 0 |
| `qf serve` | FastAPI starten (`/docs` für OpenAPI) | 0 |

## Tests & Qualität

```bash
pytest                    # Unit-Tests (ohne Netz; API-Antworten als Fixtures unter tests/data/)
pytest -m integration     # gegen echte DB (Docker)
ruff check . && ruff format --check .
```

- Tests dürfen **nie** echte API-Requests auslösen. Beispielantworten liegen anonymisiert unter `backend/tests/data/`.
- Für Modelle: Test gegen Leakage (Vorhersage für Spiel X darf sich nicht ändern, wenn Daten nach X hinzukommen).

## Git
- Commits klein und thematisch, englische Commit-Messages im Imperativ.
- Migrationen und zugehörige Modelländerungen im selben Commit.
- `docs/` bei Schema-, Architektur- oder Pattern-Änderungen mitpflegen.

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
cp .env.example .env              # API_FOOTBALL_KEY eintragen
docker compose up -d db           # PostgreSQL 16 (alternativ lokale Installation, DATABASE_URL anpassen)
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
alembic upgrade head              # Schemas raw + core anlegen
```

## CLI (`qf`)

| Befehl | Wirkung | API-Kosten |
|---|---|---|
| `qf status` | Quota und Abo-Ende (warnt 7 Tage vorher) | 0 |
| `qf ingest football-data --seasons 2015-2026` | CSVs laden, roh speichern, normalisieren | 0 |
| `qf ingest api-football --seasons 2015-2026 [--half-stats] [--no-details] [--no-injuries]` | Spielplan, Ergebnisse, Events, Lineups, Team-/Spieler-Stats, Ausfälle; bereits geladene Details werden übersprungen | ≈20 pro Saison (+≈306 mit `--half-stats` ab 2024) |
| `qf map-teams` | football-data-Teamnamen ↔ API-Team-IDs, Spiele verknüpfen, Report | 0 |
| `qf odds snapshot` | aktuelle Quoten (nur Betano/Pinnacle/Bet365, nur Änderungen) | 2–4 |
| `qf odds reference-data` | Buchmacher- und Wettarten-Stammdaten | 2 |
| `qf rebuild` | `core.*` aus `raw.*` neu aufbauen (nach Parser-Änderungen) | 0 |
| `qf quality` | Datenqualitäts-Report pro Saison | 0 |

Laufender Betrieb (Cron, bis ein Scheduler eingebaut ist):

```cron
# Quoten-Archiv alle 3 Stunden
5 */3 * * *   cd /pfad/backend && .venv/bin/qf odds snapshot
# Aktuelle Saison täglich nachziehen (Ergebnisse, Details, Halbzeit-Stats, Ausfälle)
30 4 * * *    cd /pfad/backend && .venv/bin/qf ingest api-football --seasons 2026 --half-stats
45 4 * * 2    cd /pfad/backend && .venv/bin/qf ingest football-data --seasons 2026 && .venv/bin/qf map-teams
```

## Tests & Qualität

```bash
pytest                    # Unit-Tests (ohne Netz; API-Antworten als Fixtures unter tests/data/)
QF_TEST_DATABASE_URL=postgresql+psycopg://qf:qf@localhost:5432/quotenfabrik_test pytest
                          # inkl. Integrationstests gegen PostgreSQL (DB wird geleert!)
ruff check . && ruff format --check .
```

- Tests dürfen **nie** echte API-Requests auslösen. Beispielantworten liegen anonymisiert unter `backend/tests/data/`.
- Für Modelle: Test gegen Leakage (Vorhersage für Spiel X darf sich nicht ändern, wenn Daten nach X hinzukommen).

## Git
- Commits klein und thematisch, englische Commit-Messages im Imperativ.
- Migrationen und zugehörige Modelländerungen im selben Commit.
- `docs/` bei Schema-, Architektur- oder Pattern-Änderungen mitpflegen.

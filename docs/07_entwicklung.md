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
| `ODDSPAPI_API_KEY` | – | OddsPapi-Key (Betano-Quoten); `API_OddsPap` wird ebenfalls akzeptiert |
| `QF_ODDSPAPI_TOURNAMENTS` | `35` | OddsPapi-Turnier-IDs, gleiche Reihenfolge wie `QF_LEAGUES` |
| `QF_ODDSPAPI_BOOKMAKERS` | `betano.de,pinnacle` | Buchmacher für Quotenverläufe (max. 3) |
| `QF_ODDSPAPI_REQUEST_RESERVE` | `20` | abrechenbare Requests pro Monat, die nie verbraucht werden |

## Setup

```bash
cp .env.example .env              # API_FOOTBALL_KEY eintragen
docker compose up -d db           # PostgreSQL 16 (alternativ lokale Installation, DATABASE_URL anpassen)
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
alembic upgrade head              # Schemas raw + core anlegen
```

### Schnellstart mit Seed (ohne API-Abrufe)

GitHub Codespaces / VS Code Dev Container: `.devcontainer/` richtet alles automatisch ein (siehe `README.md`).

```bash
docker compose up -d db                # leeres Volume: Seed wird automatisch eingespielt (scripts/db-init/)
bash scripts/ensure_schema.sh          # Migrationsstand setzen (stamp nach Seed, sonst upgrade)
# bestehendes Volume: ./scripts/seed_import.sh --force  oder  cd backend && qf seed import --force
cd backend && uvicorn quotenfabrik.api.main:app --port 8000
cd frontend-private && npm install && npm run dev   # http://localhost:3000
```

Details zum Seed: `seed/README.md`.

## CLI (`qf`)

| Befehl | Wirkung | API-Kosten |
|---|---|---|
| `qf status` | Quota und Abo-Ende (warnt 7 Tage vorher) | 0 |
| `qf ingest football-data --seasons 2015-2026` | CSVs laden, roh speichern, normalisieren | 0 |
| `qf ingest api-football --seasons 2015-2026 [--half-stats] [--no-details] [--no-injuries]` | Spielplan, Ergebnisse, Events, Lineups, Team-/Spieler-Stats, Ausfälle; bereits geladene Details werden übersprungen | ≈20 pro Saison (+≈306 mit `--half-stats` ab 2024) |
| `qf map-teams` | football-data-Teamnamen ↔ API-Team-IDs, Spiele verknüpfen, Report | 0 |
| `qf odds snapshot` | aktuelle Quoten (nur Betano/Pinnacle/Bet365, nur Änderungen) | 2–4 |
| `qf odds reference-data` | Buchmacher- und Wettarten-Stammdaten | 2 |
| `qf oddspapi status` / `markets` / `fixtures` / `history` / `players` / `update` | Betano-Quoten über OddsPapi (siehe `08_betano_quellen.md`) | OddsPapi: 0–1 je Befehl (Free-Plan 250/Monat) |
| `qf model evaluate --seasons 2022-2026` | Walk-Forward-Evaluation aller Marktgruppen ohne Quoten → `analytics.*` + `docs/09_modell_evaluation.md` | 0 |
| `qf model forecast --days 10` | Prognosen + Pattern für kommende Spiele → `analytics.predictions` / `analytics.pattern_results` | 0 |
| `qf model backtest --seasons 2016-2026` | rückwirkende Walk-Forward-Prognosen aller beendeten Spiele inkl. Ergebnis → Explorer/Auswertung | 0 |
| `qf value backtest [--validation-until 2021] [--method shin]` | Prognosen gegen historische football-data-Quoten (1X2, Ü/U 2,5): Prognosegüte vs. Markt, Value-Wetten, ROI, CLV → `docs/10_quoten_backtest.md` | 0 |
| `qf value betano` | Betano-Nebenmärkte (OddsPapi-Verläufe) gegen faire Preise des marktbasierten Modells `mkt-v1` (Fit auf Pinnacle) zu 48/24/6/1 h vor Anpfiff: Edge, CLV, Marge je Markt → `docs/11_betano_nebenmaerkte.md` | 0 |
| `qf picks build [--if-empty]` / `qf picks report` | 3 Tipps pro Spiel und Profil für alle Prognosen speichern (`analytics.picks`, läuft auch nach `qf model forecast` / `backtest`) / Trefferquote → `docs/12_tipps.md` | 0 |
| `qf model settle` | Ergebnis (eingetreten ja/nein) für Prognosen beendeter Spiele eintragen | 0 |
| `qf seed export` / `qf seed import [--force]` | Datenbank-Seed schreiben / einspielen (`seed/quotenfabrik_seed.dump`) | 0 |
| `qf model show <fixture_id>` | letzte Prognose eines Spiels: Hauptmärkte, faire Quoten, Torschützen, Pattern-Signale | 0 |
| `qf rebuild` | `core.*` aus `raw.*` neu aufbauen (nach Parser-Änderungen, inkl. OddsPapi) | 0 |
| `qf quality` | Datenqualitäts-Report pro Saison | 0 |

Laufender Betrieb (Cron, bis ein Scheduler eingebaut ist):

```cron
# Quoten-Archiv alle 3 Stunden
5 */3 * * *   cd /pfad/backend && .venv/bin/qf odds snapshot
# Aktuelle Saison täglich nachziehen (Ergebnisse, Details, Halbzeit-Stats, Ausfälle)
30 4 * * *    cd /pfad/backend && .venv/bin/qf ingest api-football --seasons 2026 --half-stats
45 4 * * 2    cd /pfad/backend && .venv/bin/qf ingest football-data --seasons 2026 && .venv/bin/qf map-teams
# Betano-Quotenverläufe (OddsPapi, kostenlos) alle 3 Stunden, Spielplan max. 1x/Woche
15 */3 * * *  cd /pfad/backend && .venv/bin/qf oddspapi update
# Prognosen für die nächsten 10 Tage und Abrechnung beendeter Spiele
0 6,12,18 * * * cd /pfad/backend && .venv/bin/qf model settle && .venv/bin/qf model forecast
# Spielernamen für Torschützen-Märkte an Spieltagen (Fr/Sa/So, je 1 Request)
0 10 * * 5,6,0 cd /pfad/backend && .venv/bin/qf oddspapi players
```

## REST-API (`backend/quotenfabrik/api`)

`uvicorn quotenfabrik.api.main:app --port 8000`, OpenAPI unter `http://localhost:8000/docs`.

| Endpunkt | Inhalt |
|---|---|
| `GET /api/meta` | Ligen, Saisons, Teams, Märkte, Labels |
| `GET /api/days?from&to` | Tage mit Spielen (Kalender Europe/Berlin) |
| `GET /api/fixtures?date=YYYY-MM-DD` (oder `from`/`to`, `season`, `team`) | Spiele mit Kurzprognose (1X2, Ü2,5, BTTS) |
| `GET /api/fixtures/{id}` | Detail: alle Märkte, Torschützen, Pattern (vor Anpfiff berechnet), Statistik, Tore |
| `GET /api/explorer?market&selection&line&…` | Prognosen eines Marktes über viele Spiele + Zusammenfassung |
| `GET /api/stats/overview|markets|confidence|calibration|seasons|scorers` | Trefferquoten und Kalibrierung |
| `GET /api/stats/picks?profile&season` | Trefferquote der 3 Tipps pro Spiel (einzeln, Kombi, je Saison/Rang/Markt) |

Prognosequelle je Spiel: letzte `forecast`-Prognose **vor Anpfiff**, sonst `backtest`.

## Frontend

Siehe `frontend-private/README.md` (Next.js, `npm run dev`, `npm run build`, `npx eslint src`).

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

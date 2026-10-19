# Quotenfabrik Analyser

Analyse-Tool zur Optimierung und Auswertung von Sportwetten. Für jede Marktgruppe – 1X2, Über/Unter gesamt,
Über/Unter pro Team, Über/Unter pro Halbzeit und Torschützen – werden spezialisierte Analysepattern berechnet,
mit Buchmacherquoten verglichen und per Backtest validiert.

**Proof of Value:** 1. und 2. Bundesliga, Daten von [API-Football](https://www.api-football.com/) (Pro Plan) und
[football-data.co.uk](https://www.football-data.co.uk/) (historische Ergebnisse und Quoten seit 2015/16).

## Aufbau

| Bereich | Ordner | Status |
|---|---|---|
| Backend: Datenimport, PostgreSQL, Analytik, REST-API | `backend/` | in Arbeit |
| Privates Frontend: Spieltage, Tipps, Spiel-Detail, Daten-Explorer, Auswertung | `frontend-private/` | in Arbeit |
| Öffentliches Frontend: Login & Abo-Modell | `frontend-public/` | später |

## Schnellstart

**GitHub Codespaces (empfohlen zum Testen):** Repository → *Code* → *Codespaces* → *Create codespace on main*.
Der Devcontainer (`.devcontainer/`) startet PostgreSQL 16, spielt beim ersten Start den Seed ein (alle Daten und
Prognosen, ≈ 1–2 Minuten), installiert Backend und Frontend und startet beides automatisch:
Frontend auf Port **3000** (öffnet sich im Browser), API auf Port **8000** (`/docs`).
API-Keys sind zum Ansehen nicht nötig; für neue Datenabrufe als Codespaces-Secrets `API_FOOTBALL_KEY` und
`ODDSPAPI_API_KEY` hinterlegen.

Start-Status: `cat /tmp/qf-services.log` (Logs der Dienste: `/tmp/api.log`, `/tmp/frontend.log`).
Neuer Seed nach `git pull`: `cd backend && .venv/bin/qf seed import --force` (ersetzt die Datenbank; der
PostgreSQL-Client 16 ist im Devcontainer installiert, in älteren Codespaces vorher
`sudo bash .devcontainer/install-pg-client.sh`). Ist die Datenbank leer, spielt der Start den Seed automatisch ein.
Dienste starten: `bash .devcontainer/start.sh` – startet nur, was noch nicht läuft. Neu starten (z. B. nach `git pull`):
`bash .devcontainer/restart.sh`. Setup erneut ausführen:
`bash .devcontainer/post-create.sh`.

**Lokal mit Docker:**

```bash
docker compose up -d db          # erster Start mit leerem Volume spielt seed/ automatisch ein
cd backend && python -m venv .venv && .venv/bin/pip install -e ".[dev]" && bash ../scripts/ensure_schema.sh
.venv/bin/uvicorn quotenfabrik.api.main:app --port 8000
cd frontend-private && npm install && npm run dev           # http://localhost:3000
```

## Dokumentation

1. [Datenquellen](docs/01_datenquellen.md) – was API-Football und football-data.co.uk liefern (live geprüft)
2. [Architektur](docs/02_architektur.md)
3. [Datenmodell](docs/03_datenmodell.md) – PostgreSQL-Schemas
4. [Analysepattern](docs/04_analysepattern.md) – Pattern-Katalog je Marktgruppe
5. [Modelle & Backtesting](docs/05_modelle_und_backtesting.md)
6. [Roadmap](docs/06_roadmap.md)
7. [Entwicklung](docs/07_entwicklung.md) – Setup, CLI, Tests
8. [Betano-Quellen](docs/08_betano_quellen.md) – Betano-Quoten über OddsPapi
9. [Modell-Evaluation](docs/09_modell_evaluation.md) – Ergebnisse Phase 2 (automatisch erzeugt)
10. [Quoten-Backtest](docs/10_quoten_backtest.md) – 1X2 und Ü/U 2,5 gegen historische Quoten (Phase 3, automatisch erzeugt)
11. [Betano-Nebenmärkte](docs/11_betano_nebenmaerkte.md) – Betano-Quoten gegen faire Preise aus Pinnacle (Phase 3, automatisch erzeugt)
12. [Tipps](docs/12_tipps.md) – 3 Tipps pro Spiel, Trefferquote einzeln und als Kombi (automatisch erzeugt)

Die Berichte 09–12 gibt es je Liga: ohne Suffix für die Bundesliga, mit `_2_bundesliga` für die 2. Bundesliga
(z. B. [`docs/12_tipps_2_bundesliga.md`](docs/12_tipps_2_bundesliga.md)).

Hinweise für KI-gestützte Entwicklung: [CLAUDE.md](CLAUDE.md)

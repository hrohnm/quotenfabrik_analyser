# Quotenfabrik Analyser

Analyse-Tool zur Optimierung und Auswertung von Sportwetten. Für jede Marktgruppe – 1X2, Über/Unter gesamt,
Über/Unter pro Team, Über/Unter pro Halbzeit und Torschützen – werden spezialisierte Analysepattern berechnet,
mit Buchmacherquoten verglichen und per Backtest validiert.

**Proof of Value:** 1. Bundesliga, Daten von [API-Football](https://www.api-football.com/) (Pro Plan) und
[football-data.co.uk](https://www.football-data.co.uk/) (historische Ergebnisse und Quoten seit 2015/16).

## Aufbau

| Bereich | Ordner | Status |
|---|---|---|
| Backend: Datenimport, PostgreSQL, Analytik, REST-API | `backend/` | in Arbeit |
| Privates Frontend: Analysen & Wett-Tracking | `frontend-private/` | geplant |
| Öffentliches Frontend: Login & Abo-Modell | `frontend-public/` | später |

## Dokumentation

1. [Datenquellen](docs/01_datenquellen.md) – was API-Football und football-data.co.uk liefern (live geprüft)
2. [Architektur](docs/02_architektur.md)
3. [Datenmodell](docs/03_datenmodell.md) – PostgreSQL-Schemas
4. [Analysepattern](docs/04_analysepattern.md) – Pattern-Katalog je Marktgruppe
5. [Modelle & Backtesting](docs/05_modelle_und_backtesting.md)
6. [Roadmap](docs/06_roadmap.md)
7. [Entwicklung](docs/07_entwicklung.md) – Setup, CLI, Tests

Hinweise für KI-gestützte Entwicklung: [CLAUDE.md](CLAUDE.md)

# CLAUDE.md – Quotenfabrik Analyser

Leitfaden für Claude (und Menschen), die an diesem Repository arbeiten. Kurz halten, aktuell halten.

## Projektziel

Ein Analyse-Tool zur Optimierung und Auswertung von Sportwetten. Für jede Marktgruppe werden
spezialisierte Analysepattern berechnet, mit Buchmacherquoten verglichen (Value) und per Backtest
validiert. **Proof of Value (PoV): nur 1. Bundesliga** (API-Football `league=78`, football-data.co.uk `D1`).

**Vorgehen:** Zuerst Pattern und Modelle trainieren und auf Ergebnisdaten validieren (Kalibrierung).
Erst danach folgt die Value-Suche mit Quoten. Der Quoten-Snapshot-Job läuft trotzdem früh im Hintergrund,
damit das Archiv wächst (verpasste Quoten sind nicht nachholbar).

Marktgruppen (Reihenfolge = Priorität):
1. 1X2 (Spielausgang)
2. Über/Unter Tore gesamt
3. Über/Unter Tore pro Team (Heim / Gast)
4. Über/Unter Tore pro Halbzeit (1. HZ / 2. HZ, gesamt und pro Team)
5. Torschützen (Anytime, erster Torschütze)

## Die drei Bereiche der App

| Bereich | Ordner | Status |
|---|---|---|
| 1. Backend (Ingest, DB, Analytik, REST-API) | `backend/` | in Arbeit |
| 2. Privates Frontend (eigene Analyse & Wett-Tracking) | `frontend-private/` | geplant |
| 3. Öffentliches Frontend (Login, Abo-Modell) | `frontend-public/` | später |

Das öffentliche Frontend spricht **nie** direkt mit der DB oder den Datenquellen, nur mit der Backend-API.

## Tech-Stack

- **Python 3.12+**, FastAPI, SQLAlchemy 2.x (typed ORM), Alembic (Migrationen), psycopg 3
- **PostgreSQL 16** – Schemas `raw`, `core`, `analytics` (siehe `docs/03_datenmodell.md`)
- pandas / numpy / scipy für Modelle, pytest, ruff (Lint + Format)
- Frontends: TypeScript + Next.js (React) für privates und öffentliches Frontend

## Dokumentation (zuerst lesen, bevor du etwas änderst)

| Datei | Inhalt |
|---|---|
| `docs/01_datenquellen.md` | API-Football & football-data.co.uk: Endpunkte, geprüfte Felder, Limits, Quota-Budget |
| `docs/02_architektur.md` | Komponenten, Datenfluss, Jobs, Deployment |
| `docs/03_datenmodell.md` | PostgreSQL-Schema |
| `docs/04_analysepattern.md` | Pattern-Katalog pro Marktgruppe |
| `docs/05_modelle_und_backtesting.md` | Wahrscheinlichkeitsmodelle, Value-Berechnung, Backtest-Methodik |
| `docs/06_roadmap.md` | Phasen & offene Entscheidungen |
| `docs/07_entwicklung.md` | Setup, Befehle, Konventionen |

## Harte Regeln

- **API-Key niemals committen oder loggen.** Er liegt in der Umgebungsvariable `API_FOOTBALL_KEY`.
  Lokale Werte in `.env` (gitignored), Vorlage in `.env.example`.
- **Quota schonen:** Pro Plan = 7.500 Requests/Tag (Reset 00:00 UTC), 300 Requests/Minute.
  Überschreitungen können zu einer **Firewall-Sperre ohne Vorwarnung** führen → Client drosselt hart auf
  ≤ 4 Requests/Sekunde und bricht bei `x-ratelimit-requests-remaining` < Sicherheitsreserve ab.
- **Jede API-Antwort roh speichern** (`raw.api_responses`, JSONB) bevor sie verarbeitet wird.
  Neu-Verarbeitung erfolgt aus der Rohdatenablage, nicht durch erneutes Abrufen.
- `/status` kostet keine Quota → für Healthchecks nutzen. Logos/Bilder kosten keine Quota, aber Rate-Limit → lokal cachen.
- **Pre-Match-Quoten der API sind nur 1–14 Tage vor dem Spiel verfügbar, Historie nur 7 Tage.**
  Deshalb laufen Quoten-Snapshots als Job; verpasste Quoten sind unwiederbringlich verloren.
- **Kein Data Leakage:** Features und Modelle für ein Spiel dürfen nur Daten verwenden, die *vor* Anpfiff
  bekannt waren (Walk-Forward). Tests müssen das abdecken.
- **Zielbuchmacher ist Betano** (API-ID 32). Referenz: Pinnacle (ID 4), Ersatz für fehlende Märkte: Bet365 (ID 8).
  Andere Buchmacher werden nicht gespeichert. API-Football liefert aktuell keine Betano-Quoten für die Bundesliga
  (siehe `docs/01_datenquellen.md`).
- Historische Quoten für Backtests kommen aus **football-data.co.uk** (1X2, Ü/U 2.5, Asian Handicap,
  jeweils Eröffnungs- und Schlussquote). Für alle anderen Märkte gibt es nur unser eigenes Snapshot-Archiv.
- Wahrscheinlichkeiten intern immer als Dezimalwert 0–1, Quoten als Dezimalquote. Zeiten in UTC (`timestamptz`).
- Teams werden intern über die **API-Football Team-ID** identifiziert; football-data-Namen werden über
  `core.team_aliases` gemappt.

## Konventionen

- Code, Bezeichner und Commit-Messages auf Englisch; Dokumentation und UI-Texte auf Deutsch.
- Jede Marktgruppe ist ein eigenes Modul unter `backend/quotenfabrik/analytics/markets/` mit derselben
  Schnittstelle (siehe `docs/04_analysepattern.md`, Abschnitt „Gemeinsame Schnittstelle“).
- Schema-Änderungen nur über Alembic-Migrationen, nie per Hand.
- Neue Analysen brauchen einen Backtest- oder Kalibrierungsnachweis, bevor sie ins Frontend kommen.

## Häufige Befehle

Siehe `docs/07_entwicklung.md`. Kurzfassung:

```bash
docker compose up -d db                       # PostgreSQL starten
cd backend && pip install -e ".[dev]"         # Abhängigkeiten
alembic upgrade head                          # Schema anlegen
qf ingest football-data --seasons 2015-2026   # Historie (kostet keine API-Quota)
qf ingest api-football --seasons 2015-2026    # Fixtures + Details (~250 Requests)
qf odds snapshot                              # Quoten-Snapshot (Cron alle 3 h)
pytest && ruff check .
```

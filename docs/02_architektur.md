# 02 – Architektur

## Überblick

```
                ┌──────────────────────┐      ┌────────────────────────┐
                │  API-Football (v3)   │      │  football-data.co.uk   │
                └──────────┬───────────┘      └───────────┬────────────┘
                           │ GET (gedrosselt)             │ CSV
                ┌──────────▼──────────────────────────────▼────────────┐
                │  Ingest-Jobs (Python, Scheduler)                     │
                │  1. Rohdaten → raw.*   2. Normalisieren → core.*     │
                └──────────────────────────┬───────────────────────────┘
                                           │
                ┌──────────────────────────▼───────────────────────────┐
                │  PostgreSQL 16   raw │ core │ analytics │ app        │
                └──────────────────────────┬───────────────────────────┘
                                           │
                ┌──────────────────────────▼───────────────────────────┐
                │  Analytik-Engine                                     │
                │  Features → Modelle → Marktwahrscheinlichkeiten      │
                │  → Pattern/Signale → Value (vs. Quoten) → Backtest   │
                └──────────────────────────┬───────────────────────────┘
                                           │
                ┌──────────────────────────▼───────────────────────────┐
                │  REST-API (FastAPI)   /internal/*   /public/*        │
                └───────────────┬────────────────────────┬─────────────┘
                                │                        │
                   ┌────────────▼─────────┐   ┌──────────▼──────────────┐
                   │ Privates Frontend    │   │ Öffentliches Frontend   │
                   │ (nur ich, VPN/Auth)  │   │ (Login, Abo, Paywall)   │
                   └──────────────────────┘   └─────────────────────────┘
```

## 1. Backend (`backend/`)

Ein Python-Paket `quotenfabrik` mit klar getrennten Schichten:

```
backend/
  pyproject.toml
  alembic/                    # Migrationen
  quotenfabrik/
    config.py                 # Settings aus Umgebungsvariablen (pydantic-settings)
    db.py                     # Engine, Session
    models/                   # SQLAlchemy-Modelle je Schema (raw, core, analytics, app)
    sources/
      api_football.py         # HTTP-Client: Drosselung, Quota-Wächter, Retry, Roh-Speicherung
      football_data.py        # CSV-Download + Spalten-Normalisierung
    ingest/
      fixtures.py             # Spielplan + Details (Events, Lineups, Stats, Spieler)
      odds.py                 # Quoten-Snapshots (nur Änderungen speichern)
      football_data.py        # Historische Ergebnisse + Quoten
      team_mapping.py         # Alias-Mapping football-data ↔ API-Team-IDs
    analytics/
      features/               # Rolling-Form, Heim/Auswärts-Splits, Halbzeit-Anteile, Spieler-Anteile
      models/                 # Dixon-Coles, Halbzeit-Poisson, Torschützen-Modell
      markets/                # je Marktgruppe ein Modul (1x2, totals, team_totals, halves, scorers)
      value.py                # Margin entfernen, EV, Kelly
      backtest.py             # Walk-Forward-Backtests
    api/
      main.py                 # FastAPI-App
      routers/                # fixtures, analyses, odds, backtests, bets
    jobs/                     # Scheduler-Einstiegspunkte
    cli.py                    # `qf`-Kommandozeile (Typer)
  tests/
```

### Datenfluss pro Abruf

1. Client prüft Quota (`/status` beim Start, danach Response-Header) und Minutenbudget.
2. Antwort wird **unverändert** in `raw.api_responses` gespeichert (Endpoint, Parameter, Zeitstempel, JSONB, Hash).
3. Normalisierer schreibt in `core.*` (idempotent per Upsert, Primärschlüssel = API-IDs).
4. Wird ein Parser verbessert, werden `core.*`-Daten aus `raw.*` neu aufgebaut – **ohne** neue API-Requests.

### Jobs (Scheduler)

| Job | Zeitplan | Inhalt |
|---|---|---|
| `odds_snapshot` | alle 3 h | `/odds?league=78&season=…` alle Seiten, nur geänderte Quoten speichern |
| `odds_pre_kickoff` | T-60 und T-10 min je Spiel | Schlussquoten-Näherung für CLV-Messung |
| `fixtures_sync` | 1×/Tag + stündlich an Spieltagen | Spielplan, Ergebnisse, Verschiebungen |
| `fixture_details` | 2 h nach Abpfiff | Events, Stats, Spieler via `ids` |
| `lineups` | T-40 und T-20 min | Aufstellungen → Torschützen-Modell neu rechnen |
| `injuries` | 2×/Tag | Ausfälle |
| `football_data_sync` | 1×/Tag (Mo/Di) | aktuelle Saison-CSV inkl. Schlussquoten |
| `analyses_refresh` | nach jedem Daten-Update | Modelle fitten, Pattern + Value für kommende Spiele |
| `subscription_check` | 1×/Tag | `/status`: Abo-Ende, Quota-Verbrauch |

Zunächst reicht APScheduler im Backend-Prozess (oder System-Cron + CLI). Bei mehreren Ligen später auf eine Queue
(z. B. Celery/RQ mit Redis) umstellen.

## 2. Privates Frontend (`frontend-private/`)

Zielgruppe: nur ich. Funktionen:

- **Spieltags-Dashboard**: kommende Spiele mit Modellwahrscheinlichkeiten, fairen Quoten, besten Buchmacherquoten, Edge.
- **Detailansicht pro Spiel**: Tabs je Marktgruppe mit den Pattern aus `docs/04_analysepattern.md`.
- **Wett-Tracking**: eigene Wetten erfassen (Markt, Quote, Einsatz, Buchmacher), automatische Abrechnung,
  ROI, CLV (Closing Line Value), Auswertung nach Markt/Buchmacher/Edge-Bereich.
- **Backtest-Ansicht**: Ergebnisse der Backtests, Kalibrierungsplots.
- **Datenqualität**: letzter Import, Quota-Verbrauch, fehlende Snapshots, ungemappte Teams.

Schutz: Basic Auth / einzelner Login hinter Reverse Proxy, nicht öffentlich indexiert.

## 3. Öffentliches Frontend (`frontend-public/`, später)

- Registrierung/Login, Abo-Stufen (z. B. Free: Basis-Pattern; Pro: Value-Signale, alle Märkte).
- Zahlungsabwicklung über einen Anbieter (z. B. Stripe) mit Webhooks ins Backend (`app.subscriptions`).
- Eigene API-Routen `/public/*` mit Rollenprüfung; zeitverzögerte oder gefilterte Inhalte für Free-Nutzer.
- **Rechtliches vor dem Start klären** (siehe `docs/06_roadmap.md`): Lizenzbedingungen von API-Football und
  football-data.co.uk für die Weiterveröffentlichung, Glücksspiel-Werberecht (GlüStV), Impressum/Datenschutz,
  Haftungsausschluss.

## Technologie-Entscheidungen

| Thema | Entscheidung | Begründung |
|---|---|---|
| Datenbank | **PostgreSQL 16** | JSONB für Rohdaten, Partitionierung für Quoten-Snapshots, parallele Jobs, Mehrbenutzerbetrieb für das öffentliche Frontend |
| Backend | Python + FastAPI | Statistik-Ökosystem (scipy, pandas) und API in einer Sprache |
| ORM/Migrationen | SQLAlchemy 2 + Alembic | Standard, typisiert |
| Frontends | TypeScript, React | Offen: Vite-SPA für privat (einfach) vs. Next.js für beide (SSR/SEO für öffentlich). Vorschlag: **Next.js für beide**, gemeinsame UI-Komponenten |
| Lokale Umgebung | Docker Compose (Postgres, später Backend + Frontends) | reproduzierbar |
| Deployment | offen (z. B. ein VPS mit Docker Compose oder Managed Postgres + Container-Hosting) | Entscheidung vor Phase 4 |

## Sicherheit

- Secrets nur über Umgebungsvariablen (`API_FOOTBALL_KEY`, `DATABASE_URL`, später Stripe-Keys).
- DB-Rollen: `qf_ingest` (schreibt raw/core), `qf_app` (liest core/analytics, schreibt app), `qf_public` (nur Views).
- Öffentliche API nur lesend auf vorberechnete Ergebnisse, nie auf Rohdaten.

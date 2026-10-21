# CLAUDE.md – Quotenfabrik Analyser

Leitfaden für Claude (und Menschen), die an diesem Repository arbeiten. Kurz halten, aktuell halten.

## Projektziel

Ein Analyse-Tool zur Optimierung und Auswertung von Sportwetten. Für jede Marktgruppe werden
spezialisierte Analysepattern berechnet, mit Buchmacherquoten verglichen (Value) und per Backtest
validiert. **Proof of Value (PoV): 1. und 2. Bundesliga** (API-Football `league=78` / `79`, football-data.co.uk `D1` / `D2`,
OddsPapi-Turnier `35` / `44`). Ligen kommen aus `QF_LEAGUES` & Co. – Code ist ligaunabhängig, Berichte je Liga
(`docs/09…12`, für weitere Ligen mit Suffix, z. B. `docs/12_tipps_2_bundesliga.md`).

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
| 2. Privates Frontend (eigene Analyse & Wett-Tracking) | `frontend-private/` | in Arbeit (Spieltage, Detail, Explorer, Auswertung, Einstellungen) |
| 3. Öffentliches Frontend (Login, Abo-Modell) | `frontend-public/` | später |

Das öffentliche Frontend spricht **nie** direkt mit der DB oder den Datenquellen, nur mit der Backend-API.

## Tech-Stack

- **Python 3.12+**, FastAPI, SQLAlchemy 2.x (typed ORM), Alembic (Migrationen), psycopg 3
- **PostgreSQL 16** – Schemas `raw`, `core`, `analytics`, `app` (Konfiguration; siehe `docs/03_datenmodell.md`)
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
| `docs/08_betano_quellen.md` | Betano-Quoten über OddsPapi (Test, Umsetzung, Quota) |
| `docs/09_modell_evaluation.md` | Automatisch erzeugter Evaluationsbericht der Modelle (Phase 2) |
| `docs/10_quoten_backtest.md` | Automatisch erzeugter Quoten-Backtest 1X2 / Ü/U 2,5 gegen football-data (Phase 3) |
| `docs/12_tipps.md` | Automatisch erzeugt: 3 Tipps pro Spiel, Trefferquote einzeln und als Kombi |
| `docs/13_deployment_vps.md` | Installation auf einem VPS (Hostinger): Docker-Stack per Docker Manager oder manuell (systemd, nginx), Cron, Updates |
| `docs/14_gemeinsames_modell.md` | Automatisch erzeugt: gemeinsames Modell über verbundene Ligen vs. getrennte Modelle (`qf model joint-eval`) |
| `docs/15_europapokal.md` | Automatisch erzeugt: Europapokal-Backtest der gemeinsamen Stärkeskala (`qf model cup-eval`) |
| `docs/18_spielstil.md` | Automatisch erzeugt: Spielstil (Schüsse, Ballbesitz, Verwertung, …) gegen die Tor-Erwartung des Modells (`qf model style-eval`) |
| `docs/19_schuesse_im_modell.md` | Automatisch erzeugt: Schüsse im Tor-Modell (Mischung aus Toren und Schuss-Erwartung) gegen das reine Tor-Modell (`qf model shots-eval`) |
| `docs/20_kalibrierung.md` | Automatisch erzeugt: Nachkalibrierung je Markt gegen die rohen Prognosen (`qf model calibration-eval`, nicht aktiv: kein belastbarer Gewinn) |
| `docs/17_form.md` | Automatisch erzeugt: Form-Pattern (Punkte über/unter Modell-Erwartung) gegen das nächste Spiel (`qf model form-eval`) |
| `docs/16_tageskombis.md` | Automatisch erzeugt: Backtest der Tageskombis (Tore Über, Team-Tore Über, Doppelte Chance, Quote 5–10, `qf combos report`) |
| `docs/11_betano_nebenmaerkte.md` | Automatisch erzeugt: Betano-Nebenmärkte gegen faire Preise aus Pinnacle (`mkt-v1`, Phase 3) |

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
- **Zielbuchmacher ist Betano.** Quelle für Betano-Quoten ist **OddsPapi** (`betano.de`, Key in `ODDSPAPI_API_KEY`),
  Referenz Pinnacle (`pinnacle`). API-Football liefert keine Betano-Quoten für die Bundesliga (Pinnacle/Bet365 dort
  nur als Ergänzung). Details: `docs/08_betano_quellen.md`.
- **OddsPapi Free-Plan: nur 250 Requests pro Monat.** `/v4/historical-odds` ist kostenlos (5 s Cooldown) und wird für
  Snapshots und Historie genutzt; abrechenbare Endpunkte (`/fixtures`, `/odds-by-tournaments`, …) nur sparsam.
- **Keine asiatischen Märkte** (Asian Handicap, Asian Goal Lines mit x.0/x.25/x.75): Betano bietet sie in Deutschland
  nicht an. Nur x.5-Linien und europäisches Handicap.
- Historische Quoten für Backtests kommen aus **football-data.co.uk** (1X2, Ü/U 2.5,
  jeweils Eröffnungs- und Schlussquote). Für alle anderen Märkte gibt es nur unser eigenes Snapshot-Archiv.
- Wahrscheinlichkeiten intern immer als Dezimalwert 0–1, Quoten als Dezimalquote. Zeiten in UTC (`timestamptz`).
- **Ligen und Einstellungen kommen aus der DB** (`app.leagues`, `app.settings`, Zugriff nur über `quotenfabrik/app_config.py`);
  `QF_LEAGUES` & Co. sind nur Fallback. Neue Schwellen/Parameter als `SettingDef` in `app_config.SETTINGS` ergänzen.
  Ligaarten: `full` (alles, `app_config.league_ids()`), `ratings` (nur Ergebnisse für die Stärkeskala,
  `app_config.ratings_leagues()`) und `cup` (Europapokal, verbindet die Ligen, `app_config.cup_leagues()`).
  Frontend und Prognosen: `app_config.shown_league_ids()` (volle Ligen + Pokale); Stärke-Ligen nie anzeigen.
  Quoten-Snapshots nur für volle Ligen; Spieldetails für volle Ligen und die Pokale der letzten 2 Saisons. Pokalspiele: Prognose mit dem Europa-Pool
  (`service.run_cup_forecast/backtest`), Abrechnung nach 90 Minuten (`ft_*` = API `score.fulltime`), Endspiele neutral,
  keine eigene Ligaebene. Torschützen aus allen Wettbewerben mit Spielerdaten (volle Ligen + Spieldetails der
  Pokale der letzten 2 Saisons, `analytics.data.load_competitions`), Pattern über alle Wettbewerbe.
- **Nach jedem Liga-Import entsteht automatisch ein Backup** (`backups/`, ersetzt standardmäßig den Seed), damit
  verbrauchte Requests nicht verloren gehen.
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
docker compose up -d db                       # nur PostgreSQL starten (leeres Volume → Seed automatisch)
docker compose up -d --build                  # kompletter Server-Stack (Variablen: docs/13_deployment_vps.md)
bash scripts/ensure_schema.sh                 # Migrationen bzw. stamp nach Seed
cd backend && pip install -e ".[dev]"         # Abhängigkeiten
alembic upgrade head                          # Schema anlegen
qf ingest football-data --seasons 2015-2026   # Historie (kostet keine API-Quota)
qf ingest api-football --seasons 2015-2026 --half-stats   # Backfill (~1.000 Requests)
qf map-teams && qf quality                    # Verknüpfen + Datenqualität prüfen
qf odds snapshot                              # Quoten-Snapshot API-Football (Cron alle 3 h)
qf oddspapi update                            # Betano-Verläufe über OddsPapi (Cron alle 3 h, kostenlos)
qf model evaluate --seasons 2022-2026         # Walk-Forward-Evaluation → docs/09_modell_evaluation.md
qf model forecast && qf model show <id>       # Prognosen für kommende Spiele
qf model joint-eval                           # gemeinsames Modell über Ligen vs. getrennt → docs/14_gemeinsames_modell.md
qf model cup-eval                             # Europapokal-Backtest der Stärkeskala → docs/15_europapokal.md
qf model form-eval                            # Form-Pattern gegen das nächste Spiel → docs/17_form.md
qf model style-eval                           # Spielstil gegen die Tor-Erwartung → docs/18_spielstil.md
qf model shots-eval                           # Schüsse im Tor-Modell vs. nur Tore → docs/19_schuesse_im_modell.md
qf model calibration-eval                     # Nachkalibrierung je Markt vs. roh → docs/20_kalibrierung.md
qf model backtest && qf model settle          # rückwirkende Prognosen / Ergebnisse eintragen
qf value backtest                             # Prognosen gegen historische Quoten → docs/10_quoten_backtest.md
qf value betano                               # Betano-Nebenmärkte vs. faire Preise → docs/11_betano_nebenmaerkte.md
qf picks build && qf picks report             # 3 Tipps pro Spiel speichern / Trefferquote → docs/12_tipps.md
qf combos report                              # Tageskombis im Backtest → docs/16_tageskombis.md
qf seed import                                # Datenbank aus seed/quotenfabrik_seed.dump (statt API-Abruf)
qf backup                                     # Backup nach backups/ (auch automatisch nach Liga-Import)
uvicorn quotenfabrik.api.main:app --port 8000 # REST-API für das Frontend
cd ../frontend-private && npm run dev          # privates Frontend auf :3000
pytest && ruff check . && ruff format --check .
```

## Code-Struktur (Backend)

- `quotenfabrik/sources/` – reine Abrufe (API-Football-Client mit Drosselung/Quota-Wächter, football-data-Download)
- `quotenfabrik/ingest/parsers.py` – reine Funktionen Payload → Zeilen (ohne DB, unit-getestet)
- `quotenfabrik/ingest/*.py` – `process_*` (Payload → DB, auch für `qf rebuild`) und `sync_*` (Abruf + Verarbeitung)
- `quotenfabrik/sources/oddspapi.py`, `ingest/oddspapi*.py` – Betano-Quotenverläufe (OddsPapi), Spiel-/Team-Mapping
- `quotenfabrik/markets.py` – welche Wettarten zu welcher Marktgruppe gehören, für API-Football und OddsPapi
  (asiatische Märkte ausgeschlossen)
- `quotenfabrik/analytics/` – Modelle (Dixon-Coles mit Toren + Schüssen aufs Tor als Zielgröße, Halbzeiten, Torschützen; über verbundene Ligen gemeinsam,
  `app_config.model_pool`, Nachweis `joint_eval.py`), Märkte, Pattern, Evaluation,
  Value-Rechnung (`value.py`: Margenentfernung, EV, Kelly, CLV), Quoten-Backtest (`odds_backtest.py`),
  Betano-/Pinnacle-Preise je Spiel und Auswahl (`bookmaker_odds.py`, für API und Tageskombis), marktbasiertes Modell `mkt-v1` (`market_model.py`: faire Preise aller Märkte aus Pinnacle) und Betano-Abgleich
  (`betano_value.py`), 3 Tipps pro Spiel (`picks.py`, Tabelle `analytics.picks`), Tageskombis (`combos.py`),
  Form und letzte Spiele aller Wettbewerbe (`form.py`), Spielstil-Profile (`style.py`, Nachweis `style_eval.py`),
  Einschätzung in Textform je Spiel (`preview.py`, regelbasiert aus den Detaildaten)
  (Details: `docs/05_modelle_und_backtesting.md`, Ergebnisse: `docs/09_modell_evaluation.md`)
- `quotenfabrik/bets.py` – Wett-Tracking (`app.bets`, `app.bet_legs`): Abrechnung aus Ergebnissen, Auswertung
- `quotenfabrik/app_config.py` – Einstellungen (Standard + `app.settings`) und Ligen (`app.leagues`, Fallback env)
- `quotenfabrik/pipeline.py` – Import-Schritte je Liga (CLI und Jobs); `jobs.py` – Hintergrund-Jobs (`app.jobs`,
  Prozess `qf jobs run <id>`); `backup.py` – Backups; `reports.py` – Berichtspfade je Liga
- `quotenfabrik/api/` – FastAPI (`routers/`: meta, fixtures, explorer, stats, admin = Einstellungsseite), Labels in `api/labels.py`
- `frontend-private/` – Next.js App Router (`src/app/spieltage`, `tipps`, `wetten`, `spiel/[id]`, `explorer`, `auswertung`, `einstellungen`)
- `.devcontainer/` – GitHub Codespaces: App-Container + PostgreSQL, Seed beim ersten Start, startet API und Frontend
- `docker-compose.yml` + `docker/` – kompletter Server-Stack (db mit Seed, api, cron, frontend, caddy mit HTTPS und Passwort),
  z. B. über den Hostinger Docker Manager; `deploy/` – dasselbe ohne Docker (systemd, nginx, Crontab, `update.sh`);
  Zeitpläne in `docker/crontab` und `deploy/crontab` gemeinsam pflegen (siehe `docs/13_deployment_vps.md`)
- `seed/` – Datenbank-Seed (pg_dump); nur bewusst neu erzeugen (`qf seed export`), jede Version vergrößert die Git-Historie
- Tests: `backend/tests/`, Beispielantworten unter `backend/tests/data/` – Tests machen nie echte API-Requests

# 07 – Entwicklung

## Voraussetzungen
- Python 3.12+
- Docker + Docker Compose (für PostgreSQL 16)
- Umgebungsvariablen (lokal in `.env`, niemals committen):

| Variable | Beispiel | Zweck |
|---|---|---|
| `API_FOOTBALL_KEY` | – | API-Key von api-sports.io |
| `DATABASE_URL` | `postgresql+psycopg://qf:qf@localhost:5432/quotenfabrik` | DB-Verbindung |
| `QF_LEAGUES` | `78,79` | Start-Ligen (API-IDs: 78 = Bundesliga, 79 = 2. Bundesliga); nur Fallback, solange `app.leagues` leer ist – Ligen werden auf der Einstellungsseite verwaltet |
| `QF_FD_LEAGUES` | `D1,D2` | football-data.co.uk-Kürzel, gleiche Reihenfolge wie `QF_LEAGUES` |
| `QF_API_MAX_RPS` | `4` | Drosselung API-Football |
| `QF_API_QUOTA_RESERVE` | `500` | Requests, die nie verbraucht werden (Reserve für Snapshots); auf der Einstellungsseite überschreibbar, ebenso `QF_API_MAX_RPS` und `QF_ODDSPAPI_REQUEST_RESERVE` |
| `ODDSPAPI_API_KEY` | – | OddsPapi-Key (Betano-Quoten); `API_OddsPap` wird ebenfalls akzeptiert |
| `QF_ODDSPAPI_TOURNAMENTS` | `35,44` | OddsPapi-Turnier-IDs, gleiche Reihenfolge wie `QF_LEAGUES` |
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
| `qf ingest live` | Ergebnisse von Spielen, deren reguläres Ende erreicht ist (Anpfiff + 110 Min., noch ohne Endergebnis, höchstens 2 Tage zurück; verschoben/abgesagt ausgenommen), über `/fixtures?ids=` inkl. Tore und Aufstellungen, danach Prognosen, Tipps und Wetten abrechnen; im selben Abruf bestätigte Aufstellungen der Spiele, die in der nächsten Stunde anpfeifen und noch keine haben (Cron alle 15 Minuten) | 1 pro 20 fällige Spiele, sonst 0 |
| `qf ingest results [--seasons aktuell] [--league 39]` | Ergebnisse der Stärke-Ligen und Europapokale (Einstellungsseite → „Stärke-Ligen und Europapokal“); Europapokale der laufenden und vorigen Saison zusätzlich mit Spieldetails (Aufstellungen, Tore, Spielerstatistik für Torschützen) | 1 pro Saison und Wettbewerb, Pokal-Details 1 pro 20 Spiele |
| `qf ingest api-football --seasons 2015-2026 [--half-stats] [--no-details] [--no-injuries]` | Spielplan, Ergebnisse, Events, Lineups, Team-/Spieler-Stats, Ausfälle; bereits geladene Details werden übersprungen | ≈20 pro Saison (+≈306 mit `--half-stats` ab 2024) |
| `qf map-teams` | football-data-Teamnamen ↔ API-Team-IDs, Spiele verknüpfen, Report | 0 |
| `qf odds snapshot` | aktuelle Quoten (nur Betano/Pinnacle/Bet365, nur Änderungen) | 2–4 |
| `qf odds reference-data` | Buchmacher- und Wettarten-Stammdaten | 2 |
| `qf oddspapi status` / `markets` / `fixtures` / `history` / `players` / `update` | Betano-Quoten über OddsPapi (siehe `08_betano_quellen.md`) | OddsPapi: 0–1 je Befehl (Free-Plan 250/Monat) |
| `qf model evaluate --seasons 2022-2026` | Walk-Forward-Evaluation aller Marktgruppen ohne Quoten → `analytics.*` + `docs/09_modell_evaluation.md` | 0 |
| `qf model joint-eval [--validation 2018-2020 --test 2021-2026]` | Gemeinsames Modell über verbundene Ligen gegen getrennte Modelle (Walk-Forward, 1X2/Ü-U/BTTS, Auf-/Absteiger) → `docs/14_gemeinsames_modell.md` | 0 |
| `qf model form-eval` | Form-Pattern (Punkte minus Modell-Erwartung der letzten 6 Spiele aller Wettbewerbe) gegen das nächste Spiel → `docs/17_form.md` | 0 |
| `qf model style-eval` | Spielstil (Schüsse, Ballbesitz, Verwertung, Defensive, Intensität aus den letzten 12 Ligaspielen) gegen die Tor-Erwartung des Modells: Korrelationen, Test auf späteren Saisons, Ballbesitz-Duelle → `docs/18_spielstil.md` | 0 |
| `qf model shots-eval [--validation 2018-2020 --test 2021-2026]` | Schüsse im Tor-Modell: Varianten (Schüsse aufs Tor / alle, Gewicht 0,25–0,75) auf den Validierungssaisons, beste gegen nur Tore auf den Testsaisons → `docs/19_schuesse_im_modell.md` | 0 |
| `qf model lineup-eval [--seasons 2021-2026]` | Voraussichtliche Startelf (letzte Startelf, gemeldete Ausfälle durch Spieler derselben Position ersetzt) gegen die bestätigte → `docs/21_aufstellung.md` | 0 |
| `qf model availability-eval` | Termine (Ruhetage, Europapokal ≤ 4 Tage davor/danach, Spiele in 14 Tagen), gemeldete Ausfälle (gewichtet mit der Rolle der Spieler) und Rotation in der bestätigten Elf: Situationen gegen die Modell-Erwartung und Korrektur des Tor-Modells (Validierung 2016–2020 bzw. 2021–2023, Test danach) → `docs/22_ausfaelle_und_belastung.md` | 0 |
| `qf model calibration-eval [--seasons 2018-2026]` | Nachkalibrierung je Markt/Linie (logistisch, jede Saison mit den Saisons davor) gegen die rohen Backtest-Prognosen → `docs/20_kalibrierung.md` | 0 |
| `qf model cup-eval [--validation 2019-2021 --test 2022-2026]` | Europapokal: gemeinsames Modell über alle Ligen und Pokale, Walk-Forward auf Pokalspielen (Basisrate, ohne Pokalspiele, gemeinsam, eigener Heimvorteil) + Auswirkung auf die eigenen Ligen → `docs/15_europapokal.md` | 0 |
| `qf model forecast --days 10` (auch Europapokale, `--league 2`) | Prognosen + Pattern für kommende Spiele → `analytics.predictions` / `analytics.pattern_results` | 0 |
| `qf model backtest --seasons 2016-2026` | rückwirkende Walk-Forward-Prognosen aller beendeten Spiele inkl. Ergebnis → Explorer/Auswertung | 0 |
| `qf value backtest [--validation-until 2021] [--method shin]` | Prognosen gegen historische football-data-Quoten (1X2, Ü/U 2,5): Prognosegüte vs. Markt, Value-Wetten, ROI, CLV → `docs/10_quoten_backtest.md` | 0 |
| `qf value betano` | Betano-Nebenmärkte (OddsPapi-Verläufe) gegen faire Preise des marktbasierten Modells `mkt-v1` (Fit auf Pinnacle) zu 48/24/6/1 h vor Anpfiff: Edge, CLV, Marge je Markt → `docs/11_betano_nebenmaerkte.md` | 0 |
| `qf value clv` | Closing Line Value der Tipps: Betano-Quote beim Tipp gegen den fairen Pinnacle-Schlusspreis, mit Vergleichsgruppe gleicher Quotenhöhe, je Profil/Markt/Vorlauf/Liga → `docs/23_clv.md` | 0 |
| `qf model decisions [--apply]` | Tippschein: Entscheidungsmodell mit allen Informationen (Form, Spielstil, Termine, Ausfälle, Pattern) walk-forward trainieren, Konfidenz je Entscheidung, Bericht `docs/24_tippschein.md`; `--apply` bewertet nur neue Prognosen | 0 |
| `qf picks freeze [--date JJJJ-MM-TT]` | Tipps und Tageskombis des Tages fixieren (Cron nach der Prognose um 6, 12, 18 Uhr UTC): der gewählte Prognoselauf jedes Spiels des Tages wird festgehalten (`analytics.frozen_runs`), die Tageskombis einmal gespeichert (`analytics.day_combos`, nur noch nicht angepfiffene Spiele). Spätere Prognosen ändern sie nicht; wiederholte Läufe fixieren nur neue Spiele | 0 |
| `qf picks build [--if-empty]` / `qf picks report` | 3 Tipps pro Spiel und Profil für alle Prognosen speichern (`analytics.picks`, läuft auch nach `qf model forecast` / `backtest`) / Trefferquote → `docs/12_tipps.md` | 0 |
| `qf combos report` | Backtest der Tageskombis (Tore Über, Team-Tore Über, Doppelte Chance, Zielquote 5–10) in drei Varianten → `docs/16_tageskombis.md` | 0 |
| `qf model settle` | Ergebnis (eingetreten ja/nein) für Prognosen beendeter Spiele eintragen | 0 |
| `qf seed export` / `qf seed import [--force] [--file backup.dump]` | Datenbank-Seed schreiben / einspielen (`seed/quotenfabrik_seed.dump` oder ein Backup) | 0 |
| `qf backup [--reason manuell]` | Backup der Datenbank nach `backups/` (pg_dump, die letzten N bleiben; ersetzt standardmäßig auch den Seed) | 0 |
| `qf jobs run <id>` | Hintergrund-Job aus `app.jobs` ausführen (startet die API selbst, manuell nur zum Debuggen) | je nach Job |
| `qf model show <fixture_id>` | letzte Prognose eines Spiels: Hauptmärkte, faire Quoten, Torschützen, Pattern-Signale | 0 |
| `qf rebuild` | `core.*` aus `raw.*` neu aufbauen (nach Parser-Änderungen, inkl. OddsPapi) | 0 |
| `qf quality` | Datenqualitäts-Report pro Saison | 0 |

Laufender Betrieb (Cron, bis ein Scheduler eingebaut ist; fertige Crontab für den Server: `deploy/crontab`,
Installation: `docs/13_deployment_vps.md`):

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
| `GET /api/fixtures/{id}` | Detail (Tipps mit `explain`: warum dieser Tipp, warum wahrscheinlich – Profil, Ligaschnitt, Modell-Erwartung, Pattern, Markt, bisherige Trefferquote): Einschätzung in Textform (`preview`: Überschrift, Kurzfazit, Abschnitte; regelbasiert, nur Daten vor Anpfiff), letzte 10 Spiele beider Teams in allen Wettbewerben mit Form (`form`), Spielstil beider Teams mit Rang im Wettbewerb und Stil-Etiketten (`style`), alle Märkte (je Auswahl `betano`, `pinnacle` ohne Marge, `edge` = p × Betano − 1; letzte Quote vor Anpfiff aus OddsPapi), Torschützen, Pattern (vor Anpfiff berechnet), Statistik, Tore, Termine und Personal (`context`: letztes und nächstes Spiel beider Teams aller Wettbewerbe, gemeldete Ausfälle mit Rolle des Spielers in den letzten 10 Spielen – Fakten, nicht im Modell), Aufstellungen (`lineups`: `status` confirmed = offizielle Startelf und Bank, predicted = eigene Schätzung mit Basis-Spiel und ersetzten Ausfällen; je Team Formation, Trikotfarben, gemeldete Ausfälle), Spielereignisse (`events`: Tore, Elfmeter, Eigentore, Karten, Gelb-Rot, Wechsel, VAR mit Seite und laufendem Spielstand) |
| `GET /api/explorer?market&selection&line&…` | Prognosen eines Marktes über viele Spiele + Zusammenfassung |
| `GET /api/stats/overview|markets|confidence|calibration|seasons|scorers` | Trefferquoten und Kalibrierung |
| `GET /api/stats/picks?profile&season` | Trefferquote der 3 Tipps pro Spiel (einzeln, Kombi, je Saison/Rang/Markt) |
| `GET /api/combos?date=YYYY-MM-DD` | Tageskombis eines Tages mit echten Betano-Quoten, sonst geschätzt (Einstellungen „Tageskombis“: Zielquote, Wahrscheinlichkeitsfenster, Marge, max. Tipps); fixierte Tage aus `analytics.day_combos` (`frozen_at`, Ergebnis je Tipp aktuell), sonst berechnet (`frozen_at` = null) |
| `GET /api/teams/{id}?season=` | Teamseite, Kopf: Wettbewerbe der Saison mit Tabellenplatz, Stadion (Bild), Trainer (Foto), Form, Kennzahlen, Serien, Punkte gegen die Modell-Erwartung; ohne `season` die aktuelle |
| `GET /api/teams/{id}/stats?season=&competition=` | Heim/Auswärts-Kennzahlen, Tore nach Spielminute, Serien, Spielstatistik pro Spiel gegen den Ligaschnitt, Punkte gegen die Modell-Erwartung |
| `GET /api/teams/{id}/squad?season=` | Kader der Saison (alle Wettbewerbe mit Spielerdaten): Einsätze, Minuten, Tore, Vorlagen, Karten, Note, Rückennummer, Ausfall-Status; häufigste Startelf und Rotation |
| `GET /api/competitions/{id}?season=` | Wettbewerbsseite: Kopf (Logo, Flagge, Fortschritt der Saison), Tabelle(n) – bei Pokalen Liga-/Gruppenphase und K.-o.-Runden mit Gesamtergebnis –, Ligazahlen |
| `GET /api/competitions/{id}/table?season=&group=` | Tabelle gesamt, Heim, Auswärts, 1./2. Halbzeit, letzte 5, erwartete Punkte laut Modell, Tabellenplatz je Spieltag |
| `GET /api/competitions/{id}/stats?season=` | Ligazahlen mit den 3 Vorsaisons, Tore nach Spielminute, Halbzeiten, Karten/Ecken/Fouls pro Spiel, Elfmeter, Eigentore, Teams im Vergleich (Schüsse, xG, Verwertung, …) |
| `GET /api/competitions/{id}/players?season=` | Spieler-Ranglisten: Tore, Vorlagen, Scorerpunkte, pro 90 Minuten, Note, Karten |
| `GET /api/players/{id}?season=` | Spielerseite: Mannschaft, Rückennummer, Position, Ausfall-Status, nächstes Spiel mit Torschützen-Prognose, Saisonwerte (gesamt, pro 90 Minuten, je Wettbewerb, Anteil an der Mannschaft), Saisons, Elfmeter |
| `GET /api/players/{id}/matches?season=` | Einsätze der Saison mit Minuten, Toren, Vorlagen, Schüssen, Karten, Note und Prognose „trifft“ vor dem Spiel; Prognose gegen Ergebnis (kumuliert) |
| `GET /api/players/{id}/absences` | Gemeldete Ausfälle (ab 2021) mit Grund und Zusammenfassung |
| `GET /api/competitions/{id}/betting?season=` / `GET /api/teams/{id}/betting?season=` | „Wetten & Modell“ für die beendeten Spiele des Wettbewerbs bzw. der Mannschaft: Trefferquote des Modells je Marktgruppe und Kernmarkt mit Erwartung, Kalibrierung, 3 Tipps je Profil (Einzel, Kombi, Tipp-Arten), Betano gegen Pinnacle (Auszahlung, Anteil über Pinnacle) und Modell (Anteil mit Vorteil, Rendite dieser Auswahlen), eigene Wetten |
| `GET /api/players/{id}/bets` | Eigene Wetten mit Torschützen-Tipp auf den Spieler |
| `GET /api/search?q=` | Suche nach Mannschaften der angezeigten Wettbewerbe und Spielern (Einsätze in den letzten 2 Jahren), Kopfzeile |
| `GET /api/fixtures/{id}/league` | Liga-Details der Saison des Spiels: Tabelle (gesamt, Heim, Auswärts, Stand vor dem Spiel; Pokale: Liga- bzw. Gruppenphase), Torjäger, Vorlagen, Torschützen beider Teams, Ligazahlen |
| `GET /api/bets[?all=true]`, `POST /api/bets`, `PATCH` / `DELETE /api/bets/{id}` | Wetten des aktuellen Auswertungszeitraums (`all`: auch frühere; rechnet offene Wetten vorher ab) mit Auswertung und Bankroll / erfassen / Status, Einsatz, Quote, Auszahlung (`payout`, `payout_auto`) korrigieren / löschen |
| `POST /api/bankroll`, `DELETE /api/bankroll/{id}`, `POST /api/bets/reset` | Bankroll-Buchung (Startkapital, Einzahlung, Auszahlung) / löschen / Auswertung zurücksetzen (neuer Zeitraum, optional Startkapital und alte Wetten löschen) |

Einstellungsseite (`/api/admin/*`):

| Endpunkt | Inhalt |
|---|---|
| `GET /api/admin/status` | Key vorhanden?, Kontingent API-Football (`/status`, kostenlos) und OddsPapi, Backups, Reserven |
| `GET` / `PUT /api/admin/settings` | Einstellungen mit Standard, Hilfetext und Grenzen / speichern (422 bei ungültigen Werten) |
| `GET /api/admin/leagues`, `PATCH /api/admin/leagues/{id}` | konfigurierte Ligen / aktiv schalten, Kürzel oder OddsPapi-Turnier ändern (Verknüpfungen des alten Turniers werden gelöst) |
| `GET /api/admin/leagues/search?q=` | Liga bei API-Football suchen (**1 Request**, roh gespeichert) |
| `GET /api/admin/football-data/codes`, `GET /api/admin/oddspapi/tournaments?q=` | Kürzel-Liste / Turniersuche (kostenlos, aus Rohdaten bzw. `quotenfabrik/data/oddspapi_tournaments.json`) |
| `GET /api/admin/leagues/estimate?first_season&last_season` | geschätzte API-Football-Requests für den Import |
| `GET /api/admin/leagues/presets`, `POST /api/admin/leagues/ratings` | 27 erste Ligen Europas (`quotenfabrik/data/european_leagues.json`, IDs gegen API-Football geprüft) / als Stärke-Ligen anlegen und Ergebnisse laden (Job `add_ratings`) |
| `POST /api/admin/leagues` | Liga anlegen und Job `add_league` starten; eine Stärke-Liga wird dabei zur vollen Liga hochgestuft (Ergebnisse bleiben) |
| `POST /api/admin/jobs`, `GET /api/admin/jobs[/{id}]` | Job starten (`models`, `picks`, `backup`, `add_league`, `odds` = Betano-Quoten einer Liga neu laden: OddsPapi-Spielplan (1 Request), Verknüpfung, Quotenverläufe inkl. bisher leerer Spiele) / Fortschritt |
| `GET /api/admin/backups[/{name}]` | Backups auflisten / herunterladen |

Job `add_league` (läuft als eigener Prozess `qf jobs run <id>`, immer nur ein Job gleichzeitig): football-data →
API-Football (Spiele, Details, Halbzeit-Stats ab 2024, Ausfälle) → Teams zuordnen → OddsPapi-Spielplan und -Verläufe
→ **Backup** (direkt nach dem Import, damit verbrauchte Requests nicht verloren gehen) → rückwirkende Prognosen +
Tipps → aktuelle Prognosen + Tipps → Berichte → Backup. Ein fehlgeschlagener Job kann erneut gestartet werden und lädt
nur Fehlendes nach (API-Football überspringt bereits gespeicherte Spiele).

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

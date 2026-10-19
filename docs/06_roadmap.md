# 06 – Roadmap

## Phase 0 – Fundament (jetzt)
- [x] API-Doku gelesen, Datenumfang live geprüft (`docs/01_datenquellen.md`)
- [x] Architektur, Datenmodell, Pattern-Katalog dokumentiert
- [x] Repo-Struktur, Docker Compose mit PostgreSQL 16, `.env.example`, `.gitignore`
- [x] Backend-Grundgerüst (Config, DB, Alembic, CLI `qf`)

## Phase 1 – Daten (Bundesliga)
- [x] API-Football-Client (Drosselung, Quota-Wächter, Roh-Speicherung)
- [x] Backfill API-Football 2015–2026: Fixtures, Events, Lineups, Team- und Spieler-Stats, Injuries
- [x] football-data.co.uk 2015/16–2026/27 importieren
- [x] Team-Mapping + Verknüpfung, Datenqualitäts-Report (fehlende Spiele, ungemappte Teams, xG-Abdeckung)
- [x] Quoten-Snapshot-Job gebaut (`qf odds snapshot`, nur Archivaufbau, ≈30 Requests/Tag – wird erst in Phase 3 ausgewertet)
- [ ] **Dauerhafte Umgebung**: PostgreSQL + Snapshot-Job + tägliche Aktualisierung auf einem dauerhaft laufenden Rechner/Server
      (die Cloud-Entwicklungsumgebung ist flüchtig – die dort importierten Daten gehen beim Beenden verloren)
- [x] Betano-Quelle getestet: OddsPapi liefert Betano DE inkl. kostenloser Quotenverläufe seit 01/2026 (`08_betano_quellen.md`)
- [x] OddsPapi-Ingest: Fixture-Mapping, Quotenverläufe Betano + Pinnacle (Backfill ab 04/2026, danach `qf oddspapi update`)
- [ ] Phase 3: OddsPapi-Spieler-IDs auf API-Football-Spieler mappen (Torschützen-Märkte)

## Phase 2 – Pattern & Modelle trainieren (Fokus, ohne Quoten)
- [x] Feature-Basis: Rolling-Form, Heim/Auswärts-Splits, Halbzeit-Anteile, Tor-Timing, Spieler-Anteile
- [x] Dixon-Coles-Modell (1X2, Ü/U gesamt, Team-Totals) mit Walk-Forward-Training
- [x] Halbzeitmodelle (1. / 2. HZ)
- [x] Torschützen-Modell
- [x] Pattern-Bibliothek je Marktgruppe (`04_analysepattern.md`)
- [x] Bewertung **ohne Quoten**: Log-Loss, Brier, Kalibrierungskurven je Markt und Linie, Vergleich gegen
      einfache Baselines (Ligaschnitt, Heim/Auswärts-Quoten); Pattern-Trefferquoten out-of-sample
- [x] Hyperparameter (Zeitgewichtung, Regularisierung, Fenster) per Validierungsperiode wählen
- [ ] Nächste Modell-Verbesserungen (aus `09_modell_evaluation.md`): Ü/U leicht unterschätzt bei 40–60 %
      (steigende Torquote der Liga → Trend im Ligaschnitt), xG-Mischung testen (ab 2023 voll verfügbar),
      Halbzeit-Modelle, offene Pattern (Ruhetage, Schiedsrichter, Ausfälle), Torschützen: Elfmeterschützen

## Phase 3 – Value-Suche mit Quoten
- [x] Margenentfernung (Shin/Power/proportional), Edge/EV, Kelly, CLV (`analytics/value.py`)
- [x] Backtest 1X2 und Ü/U 2.5 gegen football-data-Quoten (inkl. Pinnacle-Schlussquote) → `10_quoten_backtest.md`:
      **kein Value mit `dc-v1`** – Modell schlechter als der Markt, negativer CLV
- [x] Marktbasiertes Modell `mkt-v1` (Fit auf Pinnacle) und Betano-Nebenmärkte dagegen geprüft → `11_betano_nebenmaerkte.md`:
      Betano liegt bei < 1 % der Quoten über dem fairen Preis (Ø +0,8 %), CLV ≈ 0 → **kein systematischer Value**;
      Marge je Markt 4–17 %. „Exakte Tore Heim/Gast“ wegen widersprüchlicher Betano-Daten ausgeschlossen
- [ ] Quotenboosts/Aktionen bewerten: faire Preise aus `mkt-v1` für beliebige Betano-Angebote (Frontend)
- [ ] Torschützen: OddsPapi-Spieler ↔ API-Football-Spieler mappen, Betano-Torschützenquoten gegen Modell prüfen
- [ ] Reaktionszeit: Betano-Quoten nach Pinnacle-Bewegungen (Aufstellung, Ausfälle) – kurzzeitig veraltete Preise?
- [ ] Modell um Informationen erweitern, die es noch nicht nutzt (Aufstellungen, Ausfälle, xG) und erneut gegen den Markt testen
- [ ] Übrige Märkte gegen das eigene Snapshot-Archiv (CLV)
- [ ] Value-Erkennung + Paper-Trading-Protokoll

## Phase 3b – Privates Frontend (Next.js)
- [x] REST-API (`/api/*`, FastAPI)
- [x] Spieltagsübersicht (Spiele pro Tag), Spiel-Detail mit allen Märkten je Marktgruppe, Pattern, Statistik
- [x] Daten-Explorer inkl. rückwirkender Prognosen vergangener Spiele (`qf model backtest`)
- [x] Auswertung: Trefferquoten pro Liga/Saison/Markt, Konfidenz, Kalibrierung, Torschützen
- [x] Seed der Datenbank im Repository (`seed/`, `qf seed import`)
- [ ] Wett-Tracking mit ROI/CLV-Auswertung
- [ ] Betano-/Pinnacle-Quoten im Spiel-Detail (nach Markt-Mapping OddsPapi ↔ eigene Märkte, Phase 3)
- [ ] Datenqualitäts-Ansicht

## Phase 4 – Erweiterung
- [ ] Weitere Ligen (2. Bundesliga, Premier League, …) – Quota reicht problemlos
- [ ] Modell-Verbesserungen (xG-Integration, Stacking, Marktmischung)
- [ ] Hosting/Deployment, Backups, Monitoring

## Phase 5 – Öffentliches Frontend mit Abo
- [ ] Rechtliche Prüfung (siehe unten)
- [ ] Auth, Abo-Stufen, Zahlungsanbieter, Paywall
- [ ] Öffentliche API-Routen mit Rollenprüfung

## Getroffene Entscheidungen
- Datenbank: PostgreSQL 16
- Frontends: Next.js (React, TypeScript) für privat und öffentlich
- Reihenfolge: erst Pattern/Modelle trainieren und kalibrieren, danach Value-Suche mit Quoten
- Betano-Quoten über OddsPapi (`betano.de`), Free-Plan; kostenloser Historien-Endpunkt für Snapshots

## Offene Entscheidungen
| Thema | Optionen | Vorschlag |
|---|---|---|
| Hosting | VPS + Docker Compose / Managed Services | VPS für PoV |
| Scheduler | APScheduler im Prozess / Cron + CLI / Queue | APScheduler, später Queue |
| Abo-Verlängerung API-Football | Abo endet 15.11.2026, keine Auto-Verlängerung | rechtzeitig verlängern, sonst stoppt der Snapshot-Job (Free = 100 Req/Tag) |

## Rechtliche Punkte vor einem öffentlichen Angebot
- Nutzungsbedingungen von API-Football: Darf abgeleitete Analyse/Daten öffentlich und kostenpflichtig angeboten werden?
  Rohdaten (insb. Quoten) dürfen ggf. nicht weiterverteilt werden.
- football-data.co.uk: Nutzungsbedingungen für kommerzielle Nutzung prüfen.
- Werbung für Glücksspiel / Buchmacher-Verlinkung (GlüStV 2021, nur lizenzierte Anbieter), Jugendschutz.
- Impressum, Datenschutz (DSGVO), AGB für Abos, Widerrufsrecht, Haftungsausschluss („keine Gewinngarantie“).

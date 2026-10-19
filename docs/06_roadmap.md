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
- [ ] Feature-Basis: Rolling-Form, Heim/Auswärts-Splits, Halbzeit-Anteile, Tor-Timing, Spieler-Anteile
- [ ] Dixon-Coles-Modell (1X2, Ü/U gesamt, Team-Totals) mit Walk-Forward-Training
- [ ] Halbzeitmodelle (1. / 2. HZ)
- [ ] Torschützen-Modell
- [ ] Pattern-Bibliothek je Marktgruppe (`04_analysepattern.md`)
- [ ] Bewertung **ohne Quoten**: Log-Loss, Brier, Kalibrierungskurven je Markt und Linie, Vergleich gegen
      einfache Baselines (Ligaschnitt, Heim/Auswärts-Quoten); Pattern-Trefferquoten out-of-sample
- [ ] Hyperparameter (Zeitgewichtung, Regularisierung, Fenster) per Validierungsperiode wählen

## Phase 3 – Value-Suche mit Quoten
- [ ] Margenentfernung, Edge/EV, Kelly
- [ ] Backtest 1X2 und Ü/U 2.5 gegen football-data-Quoten (inkl. Pinnacle-Schlussquote)
- [ ] Übrige Märkte gegen das eigene Snapshot-Archiv (CLV)
- [ ] Value-Erkennung + Paper-Trading-Protokoll

## Phase 3b – Privates Frontend (Next.js)
- [ ] REST-API (`/internal/*`)
- [ ] Spieltags-Dashboard, Spiel-Detail mit Tabs je Marktgruppe
- [ ] Wett-Tracking mit ROI/CLV-Auswertung
- [ ] Backtest- und Datenqualitäts-Ansicht

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

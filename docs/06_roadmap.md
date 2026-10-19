# 06 – Roadmap

## Phase 0 – Fundament (jetzt)
- [x] API-Doku gelesen, Datenumfang live geprüft (`docs/01_datenquellen.md`)
- [x] Architektur, Datenmodell, Pattern-Katalog dokumentiert
- [ ] Repo-Struktur, Docker Compose mit PostgreSQL 16, `.env.example`, `.gitignore`
- [ ] Backend-Grundgerüst (Config, DB, Alembic, CLI `qf`)

## Phase 1 – Daten (Bundesliga)
- [ ] API-Football-Client (Drosselung, Quota-Wächter, Roh-Speicherung)
- [ ] **Quoten-Snapshot-Job sofort produktiv nehmen** (jeder Tag ohne Snapshots ist verlorenes Archiv)
- [ ] Backfill API-Football 2015–2026: Fixtures, Events, Lineups, Team- und Spieler-Stats, Injuries
- [ ] football-data.co.uk 2015/16–2026/27 importieren
- [ ] Team-Mapping + Verknüpfung, Datenqualitäts-Report (fehlende Spiele, ungemappte Teams, xG-Abdeckung)

## Phase 2 – Analytik
- [ ] Dixon-Coles-Modell + Walk-Forward-Backtest 1X2 und Ü/U 2.5 gegen Pinnacle-Schlussquoten
- [ ] Märkte Team-Totals und Halbzeiten (Modelle + Kalibrierung)
- [ ] Torschützen-Modell
- [ ] Pattern-Bibliothek je Marktgruppe (`04_analysepattern.md`)
- [ ] Value-Erkennung + Paper-Trading-Protokoll

## Phase 3 – Privates Frontend
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

## Offene Entscheidungen
| Thema | Optionen | Vorschlag |
|---|---|---|
| Frontend-Framework | Vite-SPA / Next.js | Next.js für beide Frontends |
| Hosting | VPS + Docker Compose / Managed Services | VPS für PoV |
| Scheduler | APScheduler im Prozess / Cron + CLI / Queue | APScheduler, später Queue |
| Abo-Verlängerung API-Football | Abo endet 15.11.2026, keine Auto-Verlängerung | rechtzeitig verlängern, sonst stoppt der Snapshot-Job (Free = 100 Req/Tag) |

## Rechtliche Punkte vor einem öffentlichen Angebot
- Nutzungsbedingungen von API-Football: Darf abgeleitete Analyse/Daten öffentlich und kostenpflichtig angeboten werden?
  Rohdaten (insb. Quoten) dürfen ggf. nicht weiterverteilt werden.
- football-data.co.uk: Nutzungsbedingungen für kommerzielle Nutzung prüfen.
- Werbung für Glücksspiel / Buchmacher-Verlinkung (GlüStV 2021, nur lizenzierte Anbieter), Jugendschutz.
- Impressum, Datenschutz (DSGVO), AGB für Abos, Widerrufsrecht, Haftungsausschluss („keine Gewinngarantie“).

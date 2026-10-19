# Seed

`quotenfabrik_seed.dump` ist ein komprimierter `pg_dump` (Format *custom*, PostgreSQL 16) der Schemas `raw`, `core`
und `analytics`. Damit startet eine neue Umgebung mit allen bisher abgerufenen Daten und berechneten Prognosen –
ohne API-Requests.

**Stand: 19.10.2026**

| Inhalt | Umfang |
|---|---|
| Spiele 2015/16 – 2026/27 (API-Football) inkl. Events, Aufstellungen, Team-/Spieler-Statistiken, Ausfälle | Bundesliga 3.688, 2. Bundesliga 3.686 |
| football-data.co.uk D1 + D2 (Ergebnisse, Statistiken, 1X2- und Ü/U-2,5-Quoten) | 6.840 Spiele |
| Rohantworten API-Football (`raw.api_responses`) | 1.757 |
| Betano- und Pinnacle-Quotenverläufe (OddsPapi, `core.odds_history`) | 2,16 Mio. Preisänderungen, ab April 2026 |
| Prognosen (`analytics.predictions`): Backtest 2016/17 – 2026/27 + aktuelle Prognose, beide Ligen | ≈ 994.000 |
| Tipps (`analytics.picks`): 3 pro Spiel und Profil | ≈ 56.000 |

Größe ≈ 63 MB (Schema-Revision in `quotenfabrik_seed.revision`).

Nicht enthalten: `raw.oddspapi_responses` (gzip-Rohantworten, ≈ 60 MB) – bei Bedarf kostenlos neu abrufbar
(`qf oddspapi history` nach Zurücksetzen von `history_final`).

## Einspielen

**Automatisch:** Beim ersten Start des PostgreSQL-Containers (leeres Volume) spielt `scripts/db-init/10-seed.sh` den
Seed ein – im Codespace/Devcontainer und mit `docker compose up -d db`. Danach `scripts/ensure_schema.sh` (setzt die
Migrationsversion des Seeds aus `seed/quotenfabrik_seed.revision` und führt neuere Migrationen aus; macht der
Devcontainer selbst).

**Manuell** (z. B. in eine bestehende Datenbank):

```bash
# mit lokalem pg_restore (PostgreSQL-Client 16)
cd backend && qf seed import            # leere Datenbank; --force löscht vorhandene Schemas

# oder über Docker Compose (kein lokales PostgreSQL nötig)
./scripts/seed_import.sh                # --force löscht vorhandene Schemas
```

Danach optional aktualisieren: `qf ingest api-football --seasons 2026 --half-stats`, `qf oddspapi update`,
`qf model forecast`, `qf model settle`.

## Neu erzeugen

```bash
cd backend && qf seed export   # überschreibt seed/quotenfabrik_seed.dump
```

Die Datei liegt im Git-Repository (≈ 33 MB). Nicht bei jeder Kleinigkeit neu committen – jeder Stand vergrößert die
Git-Historie.

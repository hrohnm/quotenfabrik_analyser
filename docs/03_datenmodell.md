# 03 – Datenmodell (PostgreSQL)

Vier Schemas mit klarer Verantwortung:

| Schema | Inhalt | Schreibt |
|---|---|---|
| `raw` | Unveränderte Antworten/Dateien der Quellen | Ingest |
| `core` | Normalisierte Fakten: Teams, Spiele, Events, Stats, Quoten | Ingest |
| `analytics` | Features, Modellläufe, Vorhersagen, Pattern, Backtests | Analytik |
| `app` | Konfiguration (Einstellungen, Ligen, Hintergrund-Jobs); später Benutzer, Abos, eigene Wetten | API |

Konventionen: Zeitstempel `timestamptz` (UTC), Quoten `numeric(8,3)`, Wahrscheinlichkeiten `double precision`,
IDs der API-Football als natürliche Primärschlüssel (`bigint`).

## Schema `raw`

```sql
raw.api_responses (
  id            bigserial primary key,
  endpoint      text not null,            -- z. B. 'fixtures', 'odds'
  params        jsonb not null,
  fetched_at    timestamptz not null default now(),
  status_code   int not null,
  quota_remaining int,                    -- aus x-ratelimit-requests-remaining
  payload       jsonb not null,
  payload_hash  text not null             -- sha256, um Duplikate zu erkennen
);
create index on raw.api_responses (endpoint, fetched_at);
create index on raw.api_responses using gin (params);

raw.football_data_files (
  id          bigserial primary key,
  league_code text not null,              -- 'D1'
  season_code text not null,              -- '2526'
  fetched_at  timestamptz not null default now(),
  sha256      text not null,
  content     bytea not null,             -- Original-CSV
  unique (league_code, season_code, sha256)
);
```

## Schema `core`

```sql
core.leagues   (id int pk, name text, country text)                        -- 78 = Bundesliga
core.seasons   (league_id int, year int, start_date date, end_date date, pk (league_id, year))
core.teams     (id int pk, name text, code text, logo_url text)
core.team_aliases (source text, alias text, team_id int fk, pk (source, alias))  -- source = 'football_data'
core.venues    (id int pk, name text, city text)
core.players   (id int pk, name text, firstname text, lastname text, birth_date date, nationality text)
core.bookmakers (id int pk, name text)
core.bet_types  (id int pk, name text, market_group text)                  -- market_group: '1x2','totals','team_totals','halves','scorers',NULL

core.fixtures (
  id              bigint primary key,       -- API fixture id
  league_id       int not null,
  season          int not null,
  round           text,
  matchday        int,                      -- aus round geparst
  kickoff_utc     timestamptz not null,
  status          text not null,            -- NS, FT, PST, …
  venue_id        int,
  referee         text,
  home_team_id    int not null,
  away_team_id    int not null,
  ft_home int, ft_away int,
  ht_home int, ht_away int,                 -- 2. HZ = ft - ht
  updated_at      timestamptz not null
);
create index on core.fixtures (league_id, season, kickoff_utc);

core.fixture_team_stats (
  fixture_id bigint, team_id int,
  period text check (period in ('FT','1H','2H')),
  shots_total int, shots_on int, shots_off int, shots_blocked int,
  shots_inside int, shots_outside int, corners int, fouls int, offsides int,
  possession numeric(5,2), yellow int, red int, gk_saves int,
  passes_total int, passes_accurate int, xg numeric(5,2),
  primary key (fixture_id, team_id, period)
);

core.fixture_events (
  id bigserial pk, fixture_id bigint, minute int, extra_minute int,
  team_id int, player_id int, assist_player_id int,
  type text, detail text, comments text
);
create index on core.fixture_events (fixture_id);
create index on core.fixture_events (player_id) where type = 'Goal';

core.fixture_lineups (
  fixture_id bigint, team_id int, formation text, coach_id int, coach_name text,
  primary key (fixture_id, team_id)
);

core.fixture_player_stats (
  fixture_id bigint, team_id int, player_id int,
  is_starter boolean, minutes int, position text, grid text, rating numeric(4,2), captain boolean,
  shots_total int, shots_on int, goals int, assists int,
  penalties_scored int, penalties_missed int, penalties_won int,
  key_passes int, offsides int, yellow int, red int,
  primary key (fixture_id, player_id)
);

core.injuries (
  fixture_id bigint, player_id int, team_id int, type text, reason text,
  primary key (fixture_id, player_id)
);

-- football-data.co.uk, eine Zeile pro Spiel
core.historical_matches (
  id bigserial pk,
  league_code text, season_code text, match_date date, kickoff_local time,
  home_alias text, away_alias text,
  fixture_id bigint references core.fixtures(id),   -- nach dem Mapping gesetzt
  ft_home int, ft_away int, ht_home int, ht_away int,
  hs int, as_ int, hst int, ast int, hc int, ac int, hf int, af int, hy int, ay int, hr int, ar int,
  hxg numeric(5,2), axg numeric(5,2),
  -- normierte Quoten (Eröffnung / Schluss)
  b365_h numeric, b365_d numeric, b365_a numeric,
  ps_h numeric,  ps_d numeric,  ps_a numeric,
  avg_h numeric, avg_d numeric, avg_a numeric, max_h numeric, max_d numeric, max_a numeric,
  b365c_h numeric, b365c_d numeric, b365c_a numeric,
  psc_h numeric,  psc_d numeric,  psc_a numeric,
  avgc_h numeric, avgc_d numeric, avgc_a numeric,
  b365_o25 numeric, b365_u25 numeric, ps_o25 numeric, ps_u25 numeric,
  avg_o25 numeric, avg_u25 numeric, psc_o25 numeric, psc_u25 numeric, avgc_o25 numeric, avgc_u25 numeric,
  raw_row jsonb not null,                              -- komplette Originalzeile
  unique (league_code, season_code, match_date, home_alias, away_alias)
);

-- Eigenes Quoten-Archiv (nur Änderungen)
core.odds_snapshots (
  fixture_id   bigint not null,
  bookmaker_id int not null,
  bet_id       int not null,
  selection    text not null,             -- 'Home', 'Over 2.5', Spielername …
  handicap     text not null default '',  -- '' wenn keine Linie (z. B. europäisches Handicap '-1')
  odd          numeric(8,3) not null,
  is_main      boolean,
  captured_at  timestamptz not null,
  api_updated_at timestamptz,             -- 'update' aus der API-Antwort
  primary key (fixture_id, bookmaker_id, bet_id, selection, handicap, captured_at)
);
-- Für den PoV nicht partitioniert (nur 3 Buchmacher, nur Änderungen). Ab mehreren Ligen: Monats-Partitionen.

-- Bequemer Zugriff
core.v_odds_latest   -- letzte Quote je (fixture, bookmaker, bet, selection, handicap)
core.v_odds_closing  -- letzte Quote vor Anpfiff (Closing-Näherung)
```

Speicherstrategie Quoten: Ein Snapshot liefert pro Spiel ≈ 6 Buchmacher × 50 Märkte × ~20 Werte. Gespeichert wird nur,
wenn sich die Quote gegenüber dem letzten Stand geändert hat, und nur für Bet-IDs mit `market_group IS NOT NULL`
(konfigurierbar). Der vollständige Rohstand liegt ohnehin in `raw.api_responses`.

## Schema `analytics`

```sql
analytics.model_runs (
  id bigserial pk, model_name text, model_version text, params jsonb,
  trained_until timestamptz, created_at timestamptz default now(), metrics jsonb
);

analytics.team_ratings (            -- Ergebnis eines Fits, für UI und Debugging
  model_run_id bigint, team_id int, attack double precision, defence double precision,
  attack_1h double precision, defence_1h double precision, attack_2h double precision, defence_2h double precision,
  primary key (model_run_id, team_id)
);

analytics.predictions (             -- Wahrscheinlichkeit je Markt-Selektion
  model_run_id bigint, fixture_id bigint, market text, selection text, line numeric,
  probability double precision, fair_odd numeric(8,3),
  created_at timestamptz default now(),
  primary key (model_run_id, fixture_id, market, selection, line)
);

analytics.pattern_results (         -- descriptive Pattern & Signale
  fixture_id bigint, market_group text, pattern_key text, computed_at timestamptz,
  value jsonb,                      -- z. B. {"hits": 8, "n": 10, "rate": 0.8}
  signal text,                      -- 'strong_over', null …
  primary key (fixture_id, market_group, pattern_key, computed_at)
);

analytics.value_bets (
  fixture_id bigint, model_run_id bigint, market text, selection text, line numeric,
  bookmaker_id int, odd numeric(8,3), probability double precision,
  edge double precision, ev double precision, kelly_fraction double precision,
  detected_at timestamptz, closing_odd numeric(8,3), clv double precision, result text
);

analytics.picks (                   -- 3 Tipps pro Spiel und Profil (qf picks build), Migration 0005
  id bigserial pk, model_run_id → model_runs, prediction_id → predictions (Ergebnis kommt von dort),
  fixture_id, profile text ('sicher' | 'ausgewogen' | 'mutig'), rank int, market_group, market, selection, line,
  probability, base_rate (Ligaschnitt 3 Saisons), score, reasons jsonb (stützende Pattern)
);

analytics.backtests (
  id bigserial pk, name text, market text, config jsonb, period_from date, period_to date,
  n_bets int, roi double precision, yield double precision, log_loss double precision,
  brier double precision, clv_mean double precision, created_at timestamptz default now(),
  details jsonb
);
```

## Schema `app`

Konfiguration der Einstellungsseite (Migration `0006`). Werte, die nicht in `app.settings` stehen, gelten mit dem
Standard aus `quotenfabrik/app_config.py` (`SETTINGS`). API-Keys stehen **nie** in der Datenbank.

```sql
app.settings (key text pk, value jsonb, updated_at timestamptz)    -- nur Abweichungen vom Standard
app.leagues (                       -- konfigurierte Ligen; leer → Fallback auf QF_LEAGUES / QF_FD_LEAGUES / …
  id bigint pk,                     -- API-Football league id
  name text, country text, fd_code text, oddspapi_tournament bigint,
  first_season int, active bool, added_at timestamptz,
  kind text                        -- 'full' | 'ratings' (0007) | 'cup' (0008): Stärke-Ligen und Europapokale nur Ergebnisse,
)                                  -- nicht im Frontend, keine Prognosen/Quoten
app.jobs (                          -- Hintergrund-Jobs der Einstellungsseite (Liga hinzufügen, Neuberechnung, Backup)
  id bigserial pk, kind text, params jsonb, status text,   -- queued | running | done | failed
  steps jsonb,                      -- [{name, label, status, message, log[], started_at, finished_at}]
  error text, created_at, started_at, finished_at timestamptz
)
```

Geplant (öffentliches Frontend):

```sql
app.users         (id uuid pk, email citext unique, password_hash text, role text, created_at timestamptz)
app.subscriptions (id uuid pk, user_id uuid, plan text, status text, provider_ref text, valid_until timestamptz)
```

Wett-Tracking (Migration `0009`, Seite `/wetten`): eine Wette = Einzelwette oder Kombi mit ihren Tipps (Beinen).
Beine mit Spiel und Modell-Markt werden nach Spielende automatisch abgerechnet (90 Minuten, wie die Prognosen);
eine Wette ist verloren, sobald ein Bein verloren ist, und gewonnen, wenn alle Beine gewonnen sind.

```sql
app.bets (
  id bigint pk, placed_at timestamptz default now(),
  source text default 'manuell',       -- tageskombi | tipps | manuell
  label text not null, bookmaker text default 'Betano',
  stake numeric(10,2), odds numeric(8,3),  -- tatsächliche Quote der Wette
  probability float,                   -- Modell-Chance bei Abgabe (für Erwartung vs. Ergebnis)
  status text default 'open' check (status in ('open','won','lost','void')),
  payout numeric(10,2), settled_at timestamptz, notes text
);
app.bet_legs (
  id bigint pk, bet_id bigint → app.bets on delete cascade, fixture_id bigint → core.fixtures (null = freier Text),
  market text, selection text, line numeric(5,2), label text not null,
  probability float, odds numeric(8,3), outcome boolean
);
-- Migration 0010: Bankroll und Auswertungszeitraum
app.bets.payout_manual boolean default false   -- Auszahlung von Hand korrigiert (Cashout, Boost), nicht Einsatz × Quote
app.bankroll_transactions (
  id bigint pk, at timestamptz default now(),
  kind text check (kind in ('start','deposit','withdrawal','reset')),  -- reset = neuer Auswertungszeitraum ab hier
  amount numeric(10,2) check (amount >= 0), note text
);
```

## OddsPapi (Betano-Quoten, Migration `0002`)

```sql
raw.oddspapi_responses (id, endpoint, params jsonb, fetched_at, sha256, content_gzip bytea)  -- gzip, Verläufe nur final
core.oddspapi_markets  (id pk, name, market_type, period, handicap, player_prop, market_group, outcomes jsonb)
core.oddspapi_fixtures (id text pk, tournament_id, season_id, start_time, status_id, participant1/2_id, participant1/2_name,
                        fixture_id → core.fixtures, updated_at, history_synced_at, history_final)
core.oddspapi_players  (id pk, name, player_id → API-Football-Spieler (Phase 3), updated_at)
core.odds_history (
  oddspapi_fixture_id, bookmaker ('betano.de' | 'pinnacle'), market_id, outcome_id, player_id (0 = kein Spielermarkt),
  changed_at, price numeric(8,3), active,
  primary key (oddspapi_fixture_id, bookmaker, market_id, outcome_id, player_id, changed_at)
)
```

**Umsetzungsstand:** `raw` und `core` sind als Migration `0001` umgesetzt (`backend/quotenfabrik/models/`).
Abweichungen zum Entwurf oben: `fixtures` hat zusätzlich `details_synced_at` / `half_stats_synced_at`,
`fixture_events` hat `seq` und `player_name`, `odds_snapshots` hat `suspended`. `analytics` und `app` folgen in Phase 2/3.

Die finalen Definitionen entstehen als Alembic-Migrationen; dieses Dokument wird bei Änderungen mitgepflegt.

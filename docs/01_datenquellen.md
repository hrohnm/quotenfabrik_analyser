# 01 – Datenquellen

Stand der Prüfung: 19.10.2026, live gegen die API mit dem Pro-Account getestet.

## 1. API-Football (api-sports.io, v3)

### Zugang & Limits

| Punkt | Wert |
|---|---|
| Base-URL | `https://v3.football.api-sports.io/` |
| Auth | Header `x-apisports-key` (nur GET, keine weiteren Header erlaubt) |
| Plan | Pro, 7.500 Requests/Tag, 300 Requests/Minute, aktiv bis 15.11.2026 |
| Tages-Reset | 00:00 UTC, ungenutzte Requests verfallen |
| Verlängerung | **keine automatische** – danach Rückfall auf Free (100/Tag, 10/min) |
| Rate-Limit-Header | `x-ratelimit-requests-limit`, `x-ratelimit-requests-remaining`, `X-RateLimit-Limit`, `X-RateLimit-Remaining` |
| Kostenlos | `/status` und Logos/Bilder (`media.api-sports.io`) zählen nicht zur Quota |

> Das Abo-Ende (15.11.2026) muss im Betrieb überwacht werden: `/status` liefert `subscription.end`.
> Der Ingest-Job warnt 7 Tage vorher.

### Bundesliga-Abdeckung (`/leagues?id=78`)

| Saisons | Events | Lineups | Team-Stats | Spieler-Stats | Verletzungen | Predictions | Quoten |
|---|---|---|---|---|---|---|---|
| 2015–2019 | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ | ❌ |
| 2020–2025 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ (historisch nicht mehr abrufbar) |
| 2026 (aktuell) | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |

Saison 2026 = Bundesliga 2026/27, 306 Spiele (zum Prüfzeitpunkt 54 beendet, 252 offen, 6. Spieltag gespielt).

### Relevante Endpunkte

| Endpunkt | Nutzen für uns | Update | Hinweise |
|---|---|---|---|
| `/fixtures?league=78&season=Y` | Spielplan, Ergebnis FT/HT, Schiedsrichter, Stadion | 15 s | 1 Request pro Saison |
| `/fixtures?ids=a-b-…` (max. 20) | **Events, Lineups, Team-Stats und Spieler-Stats in einer Antwort** | 15 s | effizientester Weg für Details: ~16 Requests pro Saison |
| `/fixtures/statistics?fixture=X&half=true` | Team-Stats **pro Halbzeit** (`statistics_1h`, `statistics_2h`) | 1 min | Halbzeit-Daten erst ab Saison 2024 |
| `/fixtures/events` | Tore mit Minute, Torschütze, Vorlage, Typ (Normal/Eigentor/Elfmeter), Karten, Wechsel, VAR | 15 s | VAR ab 2020/21 |
| `/fixtures/lineups` | Formation, Trainer, Startelf, Bank, Positions-Grid | 15 min | 20–40 min vor Anpfiff verfügbar |
| `/fixtures/players` | Minuten, Position, Rating, Schüsse, Tore, Vorlagen, Elfmeter, Pässe, Duelle … | 1 min | Basis für Torschützen-Modell |
| `/fixtures/headtohead?h2h=A-B` | Direkter Vergleich | 15 s | lässt sich auch aus eigener DB ableiten |
| `/injuries?league=78&season=Y` | Ausfälle („Missing Fixture“, „Questionable“) | 4 h | ab April 2021 |
| `/sidelined`, `/transfers` | Langzeitausfälle, Kaderwechsel | täglich | optional |
| `/standings` | Tabelle | stündlich | lässt sich auch selbst berechnen |
| `/teams/statistics` | aggregierte Saison-Stats pro Team | 15 s | eher für UI |
| `/players?league=78&season=Y` | Spieler-Saisonstatistiken (paginiert) | täglich | Ergänzung Torschützen |
| `/players/topscorers` | Top 20 Torschützen | täglich | nur UI |
| `/predictions?fixture=X` | Prognose der API (Poisson + Vergleichsstats) | stündlich | **als Benchmark speichern**, nicht als Eingabe |
| `/odds?league=78&season=2026` | Pre-Match-Quoten aller Buchmacher, paginiert (10/Seite) | 3 h | **nur 1–14 Tage vor Spiel, 7 Tage Historie** |
| `/odds/live` | In-Play-Quoten | 60 s | später |
| `/odds/bets`, `/odds/bookmakers` | Stammdaten Märkte/Buchmacher | täglich | 1×/Tag cachen |

### Geprüfte Datenfelder (Auszug)

**Fixture-Detail** (`/fixtures?ids=`): Keys `fixture, league, teams, goals, score, events, lineups, statistics, players`.
`score` enthält `halftime`, `fulltime`, `extratime`, `penalty` → 2. Halbzeit = FT − HT.

**Team-Statistiken**: Shots on Goal, Shots off Goal, Total Shots, Blocked Shots, Shots insidebox, Shots outsidebox,
Fouls, Corner Kicks, Offsides, Ball Possession, Yellow/Red Cards, Goalkeeper Saves, Total passes, Passes accurate, Passes %.
In aktuellen Saisons zusätzlich **`expected_goals`** und `Free Kicks` (in 2019 noch nicht vorhanden → xG-Abdeckung pro
Saison beim Ingest protokollieren).

**Spieler-Statistiken pro Spiel**: `games` (Minuten, Position, Rating, Kapitän, Einwechslung), `offsides`, `shots` (total, on),
`goals` (total, conceded, assists, saves), `passes`, `tackles`, `duels`, `dribbles`, `fouls`, `cards`, `penalty` (won, commited, scored, missed, saved).

**Events**: `time.elapsed`, `time.extra`, `team`, `player`, `assist`, `type` (Goal, Card, subst, Var), `detail`
(Normal Goal, Own Goal, Penalty, Missed Penalty, …).

### Quoten (Pre-Match)

Beispiel Bundesliga-Spiel (5 Tage vor Anpfiff abgefragt): 6 Buchmacher mit Quoten –
**Bet365 (85 Märkte)**, 1xBet (43), Marathonbet (46), William Hill (44), BetVictor (14), Pinnacle (12).

Bet-IDs für unsere Marktgruppen (`/odds/bets` liefert 338 Märkte):

| Marktgruppe | Bet-IDs |
|---|---|
| 1X2 | 1 Match Winner, 12 Double Chance, 2 Home/Away (DNB), 4 Asian Handicap, 9 Handicap Result |
| Ü/U gesamt | 5 Goals Over/Under, 50/336 Goal Line, 38 Exact Goals Number, 8 Both Teams Score, 25 Result/Total Goals |
| Ü/U pro Team | 16 Total - Home, 17 Total - Away, 40/41 Home/Away Team Exact Goals, 27/28 Clean Sheet |
| Ü/U Halbzeit | 6 Goals O/U First Half, 26 Goals O/U Second Half, 105–108 Team Total Goals 1st/2nd Half, 11 Highest Scoring Half, 13 First Half Winner, 34/35 BTTS 1st/2nd Half |
| Torschützen | 92 Anytime Goal Scorer, 93 First Goal Scorer, 94 Last Goal Scorer, 95 To Score Two or More, 231/218 Home/Away Anytime |

### Betano (Zielbuchmacher)

Betano ist der Buchmacher, auf dem tatsächlich gewettet wird. Prüfung am 19.10.2026:

- Betano ist in der API als Buchmacher **ID 32** gelistet.
- Für **alle 18 Bundesliga-Spiele** im Quotenfenster lieferte die API **keine Betano-Quoten**
  (nur William Hill, Bet365, Marathonbet, BetVictor, Pinnacle, 1xBet).
- Ligaübergreifend gab es an fünf geprüften Tagen nur **ein einziges Spiel** mit Betano-Quoten
  (Schottland, letztes Update 8 Tage alt). Die Abdeckung ist praktisch nicht vorhanden.
- football-data.co.uk enthält Betano ebenfalls nicht.

Konsequenz: Betano-Quoten müssen aus einer anderen Quelle kommen (siehe `06_roadmap.md`, offene Entscheidungen).
Der Snapshot-Job speichert nur noch **Betano (32)** und den Referenz-Buchmacher **Pinnacle (4)**, sowie Bet365 (8)
als Ersatz für Märkte, die Pinnacle nicht anbietet (Torschützen, viele Halbzeit-Märkte).

Wichtig:
- Pinnacle (sharpster Buchmacher, Referenz für „faire“ Quoten) bietet nur 12 Märkte – für Team-Totals, Halbzeiten
  und Torschützen ist **Bet365** die Hauptquelle.
- Asiatische Linien: mehrere Werte mit `handicap`; `main: true` markiert die Hauptlinie.
- Da die Historie nur 7 Tage beträgt, **muss der Snapshot-Job ab Tag 1 laufen**. Jeder verpasste Spieltag fehlt für immer im Archiv.

### Quota-Budget (Bundesliga-PoV)

| Aufgabe | Requests | Häufigkeit |
|---|---|---|
| Fixtures 12 Saisons (2015–2026) | 12 | einmalig |
| Details via `ids` (≈3.670 Spiele / 20) | ≈185 | einmalig |
| Halbzeit-Stats 2024–2026 (`half=true`, 1 pro Spiel) | ≈700 | einmalig, optional |
| Injuries 2021–2026 | ≈6 | einmalig |
| Spieler-Saisonstats (paginiert) | ≈12 × 20 | einmalig |
| **Initialer Backfill gesamt** | **≈1.150** | – |
| Quoten-Snapshot (2–4 Seiten alle 3 h) | ≈30 | täglich |
| Fixtures/Details aktuelle Saison | ≈10 | täglich |
| Lineups, Injuries, Predictions an Spieltagen | ≈40 | an Spieltagen |
| Kurz vor Anpfiff (T-60/T-15 min) Quoten-Snapshot pro Spiel | ≈20 | an Spieltagen |
| **Laufender Betrieb** | **≈100/Tag** | – |

→ Ein Prozent der Tagesquota. Genug Luft, um später weitere Ligen aufzunehmen.

## 2. football-data.co.uk

### Zugang

- CSV pro Saison und Liga: `https://www.football-data.co.uk/mmz4281/{YYZZ}/D1.csv` (z. B. `2526` = 2025/26).
  Leitet per 302 auf `football-data.co.uk` weiter → HTTP-Client muss Redirects folgen.
- Keine Authentifizierung, keine Quota. Höflich abrufen (1×/Tag für die laufende Saison reicht).
- Datei beginnt mit einem UTF-8 BOM, Datum im Format `DD/MM/YYYY` (UK-Zeit in `Time`).
- `Notes.txt` auf der Seite erklärt alle Spaltenkürzel.

### Inhalt (Bundesliga D1)

| Gruppe | Spalten | Hinweis |
|---|---|---|
| Ergebnis | FTHG, FTAG, FTR, HTHG, HTAG, HTR | Halbzeit vorhanden → 1./2. HZ ableitbar |
| Spielstatistik | HS, AS, HST, AST, HF, AF, HC, AC, HY, AY, HR, AR | Schüsse, Torschüsse, Fouls, Ecken, Karten |
| xG | HxG, AxG | **neu ab 2026/27**, ältere Saisons ohne xG |
| 1X2 Eröffnung | B365H/D/A, PSH/D/A (Pinnacle), BFE (Betfair Exchange), Max, Avg … | |
| 1X2 Schluss | B365CH…, PSCH…, MaxC…, AvgC… | **Closing Odds = wichtigster Benchmark** |
| Ü/U 2.5 | B365>2.5, P>2.5, Max>2.5, Avg>2.5 (+ Schluss mit `C`) | nur Linie 2.5 |
| Asian Handicap | AHh, B365AHH/A, PAHH/A, … (+ Schluss) | |

- Spaltennamen ändern sich über die Saisons (z. B. ältere Dateien: `Bb*`-Aggregatspalten, `IW`, `WH`, `VC`;
  neuere: `BFD`, `BMGM`, `CL`). Der Parser mappt bekannte Spalten auf ein festes Schema und legt **die komplette Zeile
  zusätzlich als JSONB** ab.
- Nicht enthalten: Team-Totals, Halbzeit-Ü/U, Torschützen-Quoten → für diese Märkte gibt es historisch **nur Ergebnis-
  Kalibrierung** (Brier/LogLoss), keine ROI-Backtests, bis unser Snapshot-Archiv groß genug ist.

### Geplante Historie

Saisons 2015/16 bis 2026/27 (12 Saisons, ≈3.670 Spiele) – deckungsgleich mit der API-Football-Historie mit Events.

## 3. Verknüpfung der Quellen

football-data hat keine IDs, nur Teamnamen („Bayern Munich“, „Ein Frankfurt“, „M'gladbach“…). Vorgehen:

1. Für jede football-data-Zeile API-Fixture mit gleichem Datum (±1 Tag wegen Zeitzonen) **und** identischem
   FT- und HT-Ergebnis suchen.
2. Aus allen eindeutigen Treffern per Mehrheitsentscheid `alias → team_id` ableiten und in `core.team_aliases` speichern.
3. Danach Zeilen über (Datum, Heim-ID, Gast-ID) eindeutig mit `core.fixtures` verknüpfen.
4. Nicht verknüpfte Zeilen landen in einem Report und werden manuell gemappt.

## 4. Was die Daten *nicht* hergeben

- Historische Quoten für Team-Totals, Halbzeit-Märkte und Torschützen → nur über eigenes Archiv ab jetzt.
- Bestätigte Aufstellungen erst 20–40 min vor Anpfiff → Torschützen-Modell arbeitet vorher mit erwarteten Einsatzminuten.
- xG nur in neueren Saisons → Modelle müssen ohne xG funktionieren und xG als optionalen Zusatz nutzen.

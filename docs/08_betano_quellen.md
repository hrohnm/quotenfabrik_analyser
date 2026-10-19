# 08 – Recherche: Quellen für Betano-Quoten

Stand: 19.10.2026. Hintergrund: API-Football liefert für die Bundesliga keine Betano-Quoten (siehe `01_datenquellen.md`).
Betano selbst bietet **keine öffentliche Entwickler-API** an. In Deutschland (GlüStV) sind Quoten-Feeds besonders
restriktiv geregelt.

> Hinweis: Die Anbieterseiten waren aus der Entwicklungsumgebung nicht direkt abrufbar (Netzwerkrichtlinie). Die Angaben
> stammen aus Suchergebnissen und sind überwiegend **Eigenwerbung der Anbieter** – vor einer Entscheidung mit einem
> Testzugang verifizieren (Bundesliga-Spiel abfragen, Märkte prüfen).

## Ergebnis des Live-Tests mit OddsPapi (19.10.2026) ✅

OddsPapi liefert **Betano DE** für die Bundesliga, inklusive kompletter Quotenverläufe. Getestet mit dem Free-Plan.

| Punkt | Ergebnis |
|---|---|
| API | `https://api.oddspapi.io/v4/…`, Auth per Query-Parameter `apiKey` |
| Bundesliga | `tournamentId = 35` (Fußball `sportId = 10`), Fixture-IDs wie `id1000003572513246` |
| Betano | Slug `betano.de` (laut OddsPapi Klon des internationalen `betano`-Feeds, identische Preise), Player Props enthalten |
| Free-Plan | **250 Requests pro Monat** für abrechenbare Endpunkte (`/fixtures`, `/odds`, `/odds-by-tournaments`, `/markets`, …) |
| `/v4/historical-odds` | **kostenlos** (zählt nicht zur Quota), Cooldown 5 s pro Abruf, max. 3 Buchmacher pro Abruf. Laut Doku Daten „seit Januar 2026“, **tatsächlich für die Bundesliga erst ab ca. April 2026** (Januar–März: 404 „No historical odds found“) |
| `/v4/account` | kostenlos, zeigt Verbrauch (`request_count` / `request_limit`) |
| Historie beendetes Spiel | Gladbach – Hoffenheim (18.10.): Betano **275 Märkte, ≈ 100.000 Preispunkte** vom 20.09. bis Anpfiff; Pinnacle 165 Märkte |
| Historie kommendes Spiel | Stuttgart – Gladbach (23.10.): Betano 174 Märkte, Verlauf seit 11.10. → **Snapshots ohne Quota-Verbrauch möglich** |

### Betano-Märkte (Beispielspiel) für unsere Marktgruppen

| Marktgruppe | Betano-Märkte (OddsPapi `marketType` / `period`) |
|---|---|
| 1X2 | `1x2`, `doublechance`, `drawnobet`, `spreads-european` (europ. Handicap, 8 Linien) |
| Ü/U gesamt | `totals` fulltime (0.5 … 8.5), `bothteamsscore`, `exactscore` |
| Ü/U pro Team | `teamtotals-team1/2` fulltime (0.5 … 5.5), `exactscore-team1/2` |
| Ü/U Halbzeit | `totals` p1/p2, `teamtotals-team1/2` p1/p2, `1x2` p1/p2, `bothteamsscore` p1/p2, `highestscoringh` |
| Torschützen | `players-anytimegoalscorer`, `players-firstgoalscorer`, `players-lastgoalscorer`, `players-goals` |

Hinweise:
- Der Feed enthält auch asiatische Linien (x.25/x.75, `spreads` = Asian Handicap), vermutlich weil `betano.de` den
  internationalen Feed klont. Wir verwenden weiter **nur x.5-Linien und europäisches Handicap**. Stichprobenartig mit
  der Betano-App abgleichen, ob die Preise identisch mit dem deutschen Angebot sind.
- Im Verlauf sind Spieler nur als ID enthalten. Namen liefert `/v4/odds-by-tournaments` (abrechenbar, 1 Request für
  alle kommenden Spiele) – aber **nur, wenn Betano die Torschützen-Märkte schon anbietet** (erst kurz vor dem Spieltag;
  5 Tage vorher waren sie noch nicht da). Deshalb `qf oddspapi players` an Spieltagen ausführen. Für Spiele vor dem
  ersten Lauf fehlen Namen zu älteren Spieler-IDs → Mapping auf API-Football-Spieler in Phase 3 (Name + Team).
- Schlussquote = letzter Preis vor Anpfiff aus dem Verlauf → **CLV-Messung für alle Märkte möglich**.

### Quota-Plan (Free-Plan, 250/Monat)
| Aufgabe | Endpunkt | Requests |
|---|---|---|
| Spielplan + OddsPapi-Fixture-IDs | `/fixtures?tournamentId=35` | ≈ 1 pro Woche |
| Spielernamen für Torschützen-Märkte | `/odds-by-tournaments` | ≈ 1–2 pro Spieltag |
| Quotenverläufe (Snapshots + Historie) | `/historical-odds` | 0 (kostenlos, 5 s Abstand) |
| **Summe** | | **≈ 15–20 pro Monat** |

Damit ist ein **Backfill aller verfügbaren Bundesliga-Verläufe** (ab ca. April 2026: Saisonende 2025/26 + laufende
Saison) mit Betano und Pinnacle kostenlos möglich.

### Umsetzung (`qf oddspapi …`)
| Befehl | Wirkung | Requests |
|---|---|---|
| `qf oddspapi status` | Plan, Monatsverbrauch, Buchmacher im Plan | 0 |
| `qf oddspapi markets` | Marktkatalog → `core.oddspapi_markets` (`market_group` = unsere Marktgruppe, NULL = nicht verfolgt) | 1 |
| `qf oddspapi fixtures --from 2026-01-01` | Spielplan → `core.oddspapi_fixtures`, Team-Mapping (`team_aliases`, source `oddspapi`) und Verknüpfung mit `core.fixtures` | 1 |
| `qf oddspapi history` | Verläufe aller offenen Spiele (bis 14 Tage voraus) → `core.odds_history`; nach Spielende final inkl. Rohdaten (gzip) | 0 |
| `qf oddspapi players` | Spielernamen für Torschützen-Märkte → `core.oddspapi_players` | 1 |
| `qf oddspapi update` | Laufbetrieb: Spielplan max. 1×/Woche, danach Verläufe | 0–1 |

Gespeichert werden nur verfolgte Märkte (97 von 1.122; keine asiatischen Linien, keine Ecken/Karten), nur Preise **vor
Anpfiff** und nur Änderungen von (Preis, aktiv). Schlussquote = letzter Eintrag vor Anpfiff.

## Ursprüngliche Recherche (vor dem Test)

## Kandidaten

| Anbieter | Betano DE? | Märkte laut Anbieter | Kosten (laut Anbieter) | Bewertung |
|---|---|---|---|---|
| **OddsPapi** (oddspapi.io) | eigener Eintrag „Betano DE“ (Slug `betano.de`) | 1X2, Über/Unter; weitere unklar | Free Tier (Angaben schwanken zwischen 250 und 5.000 Requests/Monat), historische Quoten pro Spiel mit Zeitstempeln (max. 3 Buchmacher pro Abruf) | **Favorit zum Testen**: Betano DE explizit gelistet, historische Kursverläufe |
| **odds-api.io** | Betano gelistet, Deutschland als Kernmarkt genannt | inkl. Player Props (Beispiele nur US-Sport) | unklar | zweiter Kandidat, Torschützen-Abdeckung prüfen |
| **The Odds API** (the-odds-api.com) | ❌ nur `betano_uk`; für DE z. B. `tipico_de` | 1X2, Totals, einige Props | Free Tier + Pakete | kein Betano DE → nur als Referenz brauchbar |
| **Apify-Actors** (Betano-Scraper, 14 Länder inkl. DE) | ja (Scraping) | alle Märkte inkl. Props | nutzungsbasiert | **nicht empfohlen**: Scraping, vermutlich Verstoß gegen Betano-AGB, bricht bei Seitenänderungen |
| SharpAPI, parse.bot | Betano gelistet | unklar | unklar | Werbeseiten ohne belastbare Details |

## Empfehlung (vor dem Test, inzwischen überholt: OddsPapi wird genutzt)

1. **Kurzfristig (jetzt):** Betano-Quote beim Wetten manuell im privaten Frontend erfassen. Für die Modellphase reicht das,
   da Quoten erst in Phase 3 (Value-Suche) gebraucht werden.
2. **Vor Phase 3:** Free-Tier-Zugang bei **OddsPapi** anlegen und für ein Bundesliga-Spiel prüfen:
   - Kommt `betano.de` mit Quoten zurück, und wie aktuell sind sie?
   - Welche unserer Märkte sind dabei (1X2, Ü/U, Team-Tore, Halbzeiten, Torschützen)?
   - Gibt es Schlussquoten bzw. Kursverläufe (für CLV)?
   - Reicht das Request-Kontingent für ≈ 9 Spiele × mehrere Snapshots pro Spieltag?
   - Nutzungsbedingungen: private Nutzung vs. spätere Veröffentlichung im Abo-Frontend.
3. Falls OddsPapi nicht passt: odds-api.io mit denselben Prüfpunkten testen.
4. Parallel im API-Football-Support-Chat nachfragen, ob Betano-Abdeckung für die Bundesliga geplant ist.

Der Quoten-Import ist so gebaut (`raw` → `core.odds_snapshots`), dass eine zweite Quelle als weiterer Ingest-Job
ergänzt werden kann, ohne das Datenmodell zu ändern (Buchmacher-ID + Markt-Mapping auf unsere `bet_id`s).

## Quellen
- [OddsPapi – Betano DE Odds API](https://oddspapi.io/sportsbooks/betano.de)
- [OddsPapi – Betano API: Access Betano Odds](https://oddspapi.io/blog/betano-api-odds-access/)
- [OddsPapi – Odds API Pricing 2026](https://oddspapi.io/blog/?p=2498)
- [odds-api.io – Betano Integration](https://odds-api.io/integrations/betano)
- [odds-api.io – Sportsbooks](https://odds-api.io/sportsbooks)
- [The Odds API – Bookmaker APIs](https://the-odds-api.com/sports-odds-data/bookmaker-apis.html)
- [Apify – Betano Odds API (Scraper)](https://apify.com/blackfalcondata/betano-odds-api)
- [SharpAPI – Betano](https://sharpapi.io/sportsbooks/betano-odds-api)

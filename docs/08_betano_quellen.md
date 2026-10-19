# 08 – Recherche: Quellen für Betano-Quoten

Stand: 19.10.2026. Hintergrund: API-Football liefert für die Bundesliga keine Betano-Quoten (siehe `01_datenquellen.md`).
Betano selbst bietet **keine öffentliche Entwickler-API** an. In Deutschland (GlüStV) sind Quoten-Feeds besonders
restriktiv geregelt.

> Hinweis: Die Anbieterseiten waren aus der Entwicklungsumgebung nicht direkt abrufbar (Netzwerkrichtlinie). Die Angaben
> stammen aus Suchergebnissen und sind überwiegend **Eigenwerbung der Anbieter** – vor einer Entscheidung mit einem
> Testzugang verifizieren (Bundesliga-Spiel abfragen, Märkte prüfen).

## Kandidaten

| Anbieter | Betano DE? | Märkte laut Anbieter | Kosten (laut Anbieter) | Bewertung |
|---|---|---|---|---|
| **OddsPapi** (oddspapi.io) | eigener Eintrag „Betano DE“ (Slug `betano.de`) | 1X2, Über/Unter; weitere unklar | Free Tier (Angaben schwanken zwischen 250 und 5.000 Requests/Monat), historische Quoten pro Spiel mit Zeitstempeln (max. 3 Buchmacher pro Abruf) | **Favorit zum Testen**: Betano DE explizit gelistet, historische Kursverläufe |
| **odds-api.io** | Betano gelistet, Deutschland als Kernmarkt genannt | inkl. Player Props (Beispiele nur US-Sport) | unklar | zweiter Kandidat, Torschützen-Abdeckung prüfen |
| **The Odds API** (the-odds-api.com) | ❌ nur `betano_uk`; für DE z. B. `tipico_de` | 1X2, Totals, einige Props | Free Tier + Pakete | kein Betano DE → nur als Referenz brauchbar |
| **Apify-Actors** (Betano-Scraper, 14 Länder inkl. DE) | ja (Scraping) | alle Märkte inkl. Props | nutzungsbasiert | **nicht empfohlen**: Scraping, vermutlich Verstoß gegen Betano-AGB, bricht bei Seitenänderungen |
| SharpAPI, parse.bot | Betano gelistet | unklar | unklar | Werbeseiten ohne belastbare Details |

## Empfehlung

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

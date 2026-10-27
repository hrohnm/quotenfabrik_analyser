# 05 – Modelle, Value-Berechnung & Backtesting

## 1. Basis: Dixon-Coles-Modell (volle Spielzeit)

- Tore Heim ~ Poisson(λ_h), Tore Gast ~ Poisson(λ_g)
- `log λ_h = µ + Heimvorteil + Angriff_heim − Abwehr_gast`, `log λ_g = µ + Angriff_gast − Abwehr_heim`
- Dixon-Coles-Korrektur ρ für die Ergebnisse 0:0, 1:0, 0:1, 1:1
- **Zeitgewichtung** `w = exp(−ξ · Tage_seit_Spiel)`, ξ per Kreuzvalidierung (typisch Halbwertszeit 4–8 Monate)
- L2-Regularisierung der Team-Parameter → Aufsteiger mit wenig Bundesliga-Daten werden zum Mittelwert gezogen
  (Option später: Zweitliga-Daten D2 von football-data.co.uk als Vorwissen für Aufsteiger)
- Optional: xG statt Toren als Zielgröße (bzw. Mischung) in Saisons mit xG
- **Schüsse in der Zielgröße (Standard):** Zielgröße = 75 % Tore + 25 % Schuss-Erwartung (Schüsse aufs Tor des Spiels ×
  Tore pro Schuss aufs Tor im Trainingsfenster). Schüsse zeigen die Stärke stabiler als Tore; im Walk-Forward-Test
  2021–2026 signifikant besser in 1X2, Ü/U 2,5 und Beide treffen (`docs/19_schuesse_im_modell.md`). Halbzeit-Modelle
  und Dixon-Coles-ρ bleiben bei echten Toren.
- Ergebnis: Ergebnismatrix P(i:j) für i, j = 0…10 → alle Märkte der Gruppen 1–3

## 2. Halbzeitmodelle

- Zwei getrennte Poisson-Modelle für Tore in der 1. und 2. Halbzeit (gleiche Struktur, eigene Parameter, ρ = 0)
- Konsistenzprüfung: Summe der Halbzeit-λ ≈ λ der vollen Spielzeit; Abweichungen > 5 % werden geloggt
- Liefert: HZ-Ü/U, Team-Tore je Halbzeit, torreichste Halbzeit, HZ/Endstand-Kombinationen

## 3. Torschützen-Modell

Siehe `04_analysepattern.md`, Abschnitt 5. Kalibrierung: Summe aller Spieler-λ eines Teams + Eigentor-Anteil = λ_team.

## 4. Erweiterungen (nach dem PoV)

- Negative Binomial / bivariate Poisson, falls Über-Dispersion nachweisbar
- Gradient-Boosting-Modell auf Pattern-Features als Korrektur des Basismodells (Stacking)
- Markt als Feature: Mischung aus Modell und Pinnacle-Wahrscheinlichkeit (oft stärker als jedes allein)

## 4b. Umsetzung Phase 2 (Stand 19.10.2026, Modell `dc-v1`)

Code: `backend/quotenfabrik/analytics/`

| Datei | Inhalt |
|---|---|
| `data.py` | Lädt Spiele (nur `Regular Season`), Spieler-Einsätze und Tor-Events aus `core` |
| `poisson.py` | Zeitgewichtetes Dixon-Coles-Modell (analytischer Gradient, L-BFGS, ~0,1 s pro Fit), Aufsteiger-Prior, optional xG-Mischung |
| `prediction.py` | `MatchModel` = Vollzeit-Modell + je ein Poisson-Modell für 1. und 2. Halbzeit → Ergebnismatrizen |
| `markets/` | Je Marktgruppe `probabilities(pred)` und `outcomes(match)` (gleiche Schlüssel `(market, selection, line)`) |
| `scorers.py` | Torschützen-Modell (Rate pro 90 Min. mit Positions-Shrinkage × erwartete Minuten × Team-Faktor) |
| `patterns.py` | Deskriptive Pattern je Marktgruppe mit Wilson-Intervall und Signal *hoch*/*niedrig* |
| `evaluation.py` | Walk-Forward je Spieltag, Vergleichswerte *Liga* und *Form*, Brier/Log-Loss/RPS/ECE, Kalibrierung, Pattern-Signal-Auswertung, Tuning |
| `service.py` | `qf model forecast` (speichert in `analytics.*`), `qf model evaluate` (Bericht `docs/09_modell_evaluation.md`), `qf model show` |

**Gewählte Parameter** (Validierung 2018–2021 für das Teammodell, 2020–2021 für Torschützen; Test ab 2022):

| Parameter | Wert | Bedeutung |
|---|---|---|
| ξ | 0,0015 / Tag | Zeitgewichtung, Halbwertszeit ≈ 15 Monate |
| Regularisierung | 10 (Halbzeiten 25) | zieht Teamstärken zum Mittelwert, Halbzeiten stärker (verrauschter) |
| Fenster | 3 Jahre | Trainingsdaten vor dem Spieltag |
| Aufsteiger-Prior | Angriff −0,3 / Abwehr −0,3 | Teams ohne Bundesligaspiel in den letzten 400 Tagen |
| Torschützen-Shrinkage | 15 × 90 Min. | Spieler mit wenig Spielzeit werden zum Positionsschnitt gezogen |
| Team-Faktor-Exponent | 0,6 | gedämpfte Anpassung der Spielerrate an die erwartete Torzahl des Teams im Spiel |

**2. Bundesliga:** gleiche Parameter wie die Bundesliga. Auf den Validierungssaisons 2018–2021 der 2. Liga wurden
Aufsteiger-Prior (−0,3 / −0,15 / 0) und ein eigenes Absteiger-Prior (0 / +0,15 / +0,3) verglichen: Die Standardwerte
(−0,3, kein Absteiger-Bonus) waren am besten, ein Absteiger-Bonus verschlechterte die Vorhersage leicht (Absteiger
haben meist noch Zweitliga-Spiele im 3-Jahres-Fenster). Es gibt daher keine ligaspezifischen Parameter.

**Gemeinsames Modell über Ligen** (Einstellung `model.joint`, Standard an; Nachweis: `docs/14_gemeinsames_modell.md`,
erzeugt von `qf model joint-eval`): Ligen, die sich Teams teilen (1. und 2. Bundesliga über Auf- und Absteiger),
werden in einem Fit gerechnet. Jede Liga bekommt eine Angriffs- und Abwehrebene; die Stärke eines Teams wird nicht
mehr zu 0, sondern zur zeitgewichteten Mischung der Ligaebenen gezogen, in denen es gespielt hat (Teams ohne Daten:
aktuelle Liga + Aufsteiger-Prior). Damit liegen alle Teams auf einer Skala, und ein Aufsteiger behält die Stärke,
die er in der unteren Liga gezeigt hat. Ergebnis (Test 2021/22–2026/27, 1X2-Log-Loss): Bundesliga signifikant besser
(−0,0042; bei Aufsteigern an Spieltag 1–10 −0,036), 2. Bundesliga ohne signifikanten Unterschied (+0,0005).
Bekannte Schwäche: Absteiger werden zu Saisonbeginn in der unteren Liga überschätzt. Ligen ohne gemeinsame Teams
werden weiterhin allein gerechnet; mit einer Liga ist das Modell identisch zum bisherigen. Grundlage für weitere
Ligen und den Europapokal (`docs/06_roadmap.md`).

**Europapokal** (Nachweis: `docs/15_europapokal.md`, `qf model cup-eval`): Stärke-Ligen (27 erste Ligen Europas,
nur Ergebnisse) und die drei Europapokale bilden einen Pool. Pokalspiele gehen in die Teamstärken ein, bilden aber
keine eigene Ligaebene; Endspiele zählen als neutraler Platz, Europapokalspiele haben einen eigenen Heimvorteil
(`cup_home_adv`), abgerechnet wird nach 90 Minuten (API `score.fulltime`). Teams aus nicht geladenen Ligen
(Qualifikation kleiner Länder) starten mit dem Aufsteiger-Prior. Ergebnis (Test 2022/23–2026/27, 4.044 Pokalspiele,
Log-Loss 1X2): 0,948 gegenüber 1,042 ohne Pokalspiele (Ligen gleich stark) und 1,044 Basisrate. Die eigenen Ligen
gewinnen durch den Europa-Pool nichts messbar und werden weiter nur mit verbundenen Ligen gerechnet.
Im Betrieb (`service.run_cup_forecast` / `run_cup_backtest`) werden Pokalspiele mit dem Europa-Pool vorhergesagt
(Fit je Kalenderwoche, Halbzeitmodelle ebenso), ohne Torschützen und Pattern; Tipps wie in der Liga, der
„Ligaschnitt“ ist dort der Schnitt des Wettbewerbs. Rückwirkende Prognosen: laufende und vorige Pokalsaison.

Halbzeit-Varianten (getrennte Modelle vs. fester Ligaanteil vs. teamspezifischer Anteil) wurden verglichen; getrennte
Modelle mit stärkerer Regularisierung waren minimal besser. Unterschiede sind klein – Halbzeit-Tore sind schwer vorherzusagen.

Ergebnisse: siehe **`docs/09_modell_evaluation.md`** (wird von `qf model evaluate` erzeugt).

**Fazit der ersten Evaluation** (Test 2022/23–2026/27, 1.278 Spiele, ohne Quoten):
- **1X2:** RPS 0,203 vs. 0,231 (Liga) / 0,218 (Form) → +12 % ggü. Liga, in jeder Testsaison besser; gut kalibriert.
- **Tore pro Team:** +6,7 % Brier-Skill ggü. Liga – das Modell trennt starke/schwache Angriffe und Abwehren gut.
- **Tore gesamt:** nur +1,6 %; Über-2,5 wird im Bereich 40–60 % leicht unterschätzt (Liga wird torreicher).
- **Halbzeiten:** +2,4 %; Halbzeit-Ergebnis +6,5 % RPS. Halbzeit-Tore bleiben schwer vorhersagbar.
- **Torschützen:** +2,8 % Brier ggü. Positions-/Startelf-Schnitt, gut kalibriert bis ≈ 40 %.
- **Pattern-Signale:** zeigen klare Unterschiede zum Ligaschnitt (z. B. „Heimteam 2+ Tore“ hoch: 72 % statt 51 %), das
  Modell kennt diese Information aber größtenteils bereits (Rest meist ≤ ±5 % bei n ≈ 100–250 → im Rauschen).
  Pattern dienen damit vor allem der **Erklärung** der Modellwerte; echte Zusatzinformation muss sich in Phase 3
  gegen die Quoten beweisen.
- Wichtig: Ein besseres Modell als Liga/Form heißt noch nicht, dass es besser als Betano/Pinnacle ist – das prüft Phase 3.

## 5. Quoten & Value

| Größe | Formel |
|---|---|
| Implizite Wahrscheinlichkeit | `1 / quote` |
| Marge (Overround) | `Σ 1/quote_i − 1` |
| Faire Wahrscheinlichkeit | Margenentfernung per **Shin-Methode** (Standard) oder Power-Methode; proportional nur als Fallback |
| Faire Quote | `1 / p_modell` |
| Edge / EV | `p_modell × quote − 1` |
| Kelly-Anteil | `(p × quote − 1) / (quote − 1)`, in der Praxis **¼-Kelly** und Kappung (z. B. max. 2 % Bankroll) |
| CLV | `quote_genommen / quote_closing − 1` (Closing = Pinnacle bzw. letzte Snapshot-Quote vor Anpfiff) |

Asiatische Märkte (Asian Handicap, Asian Goal Lines x.0/x.25/x.75) werden **nicht** betrachtet: Betano bietet sie in
Deutschland nicht an. Berücksichtigt werden nur x.5-Linien und das europäische (3-Weg-)Handicap.

## 6. Backtesting

### Grundsätze
- **Walk-Forward:** Für jeden Spieltag wird das Modell nur mit Spielen *vor* diesem Spieltag gefittet.
- Trainingsfenster rollierend (z. B. 3 Saisons, zeitgewichtet), Startpunkt ab Saison 2017/18, damit genug Vorlauf existiert.
- Hyperparameter (ξ, Regularisierung, Edge-Schwellen) nur auf einer **Validierungsperiode** wählen und auf einer
  getrennten **Testperiode** (z. B. die letzten 2 Saisons) einmalig bewerten – sonst Overfitting auf den Backtest.

### Metriken
| Kategorie | Metriken |
|---|---|
| Kalibrierung / Güte | Log-Loss, Brier-Score, Ranked Probability Score (1X2), Kalibrierungskurven |
| Benchmark | dieselben Metriken für die margenbereinigte **Pinnacle-Schlussquote** (sehr starker Benchmark) |
| Wett-Erfolg | Anzahl Wetten, Trefferquote, ROI/Yield, Profit-Kurve, Max. Drawdown |
| Robustheit | ROI-Konfidenzintervall (Bootstrap), Ergebnis je Saison, CLV (positiver CLV = belastbarster Indikator) |

### Was historisch backtestbar ist

| Marktgruppe | Historische Quoten | Backtest-Art |
|---|---|---|
| 1X2 | ✅ football-data (Eröffnung + Schluss, mehrere Buchmacher) | ROI + CLV + Kalibrierung |
| Ü/U 2.5 gesamt | ✅ football-data | ROI + CLV + Kalibrierung |
| Andere Ü/U-Linien, BTTS | ❌ | Kalibrierung; Quoten-Backtest ab eigenem Archiv |
| Team-Totals | ❌ | Kalibrierung; Archiv |
| Halbzeit-Märkte | ❌ | Kalibrierung; Archiv |
| Torschützen | ❌ | Kalibrierung; Archiv |

Für Märkte ohne historische Quoten zählt zunächst: **Ist das Modell gut kalibriert?** Sobald einige Spieltage im
Snapshot-Archiv liegen, wird gemessen, ob Modell-Value-Wetten positiven CLV gegen die Schlussquote erzielen –
das ist bereits nach wenigen Hundert Wetten aussagekräftiger als der ROI.

### Umsetzung Schritt 1 (Stand 19.10.2026): `qf value backtest`

Code: `analytics/value.py` (Margenentfernung Shin/Power/proportional, EV, Kelly, CLV, logarithmische Mischung) und
`analytics/odds_backtest.py` / `odds_report.py`. Rückwirkende Walk-Forward-Prognosen (`qf model backtest`) werden mit den
football-data-Quoten verglichen; Mischungsgewichte und Edge-Schwelle werden nur auf der Validierung (bis 2021/22)
gewählt, der Test (ab 2022/23) wird einmalig bewertet. Bet365 dient als Proxy für Betano (ähnliche Marge).
Ergebnis: **`docs/10_quoten_backtest.md`**.

**Fazit:** Für 1X2 und Ü/U 2,5 ist `dc-v1` schlechter als der Markt (Log-Loss 1X2 0,994 vs. 0,971), die Mischung gibt dem
Modell ein negatives Gewicht, der CLV der Value-Wetten ist negativ (−5 bis −7 %). Die 1X2-„Value“-Tipps sind überwiegend
Außenseiter, weil das Modell weniger extrem ist als der Markt. → Kein Value in den Hauptmärkten; nächste Schritte siehe
`06_roadmap.md` (marktbasiertes Modell für Nebenmärkte, zusätzliche Informationen).

### Weg 1: marktbasiertes Modell `mkt-v1` und Betano-Nebenmärkte (`qf value betano`)

`analytics/market_model.py` passt pro Spiel und Zeitpunkt fünf Parameter (erwartete Tore Heim/Gast, Anteil der
1.-Halbzeit-Tore je Team, Dixon-Coles-ρ) an die margenfreien Pinnacle-Quoten an (1X2, Ü/U, Team-Tore, Beide treffen,
jeweils Spiel und 1. Halbzeit; Kreuzentropie, jeder Markt gleich gewichtet). Damit lässt sich jeder Markt fair
bepreisen – auch solche, die Pinnacle nicht anbietet. `analytics/betano_value.py` vergleicht Betano-Quoten zum selben
Zeitpunkt (48/24/6/1 h vor Anpfiff) damit. Ergebnis: **`docs/11_betano_nebenmaerkte.md`**.

**Fazit:** Die fairen Preise sind gut kalibriert (Fit-Abweichung ≈ 0,4 %-Punkte). Betano liegt bei weniger als 1 % der
Quoten über dem fairen Preis und dann nur knapp (Ø +0,8 %, CLV ≈ 0) – die Nebenmärkte werden konsistent aus den
Hauptmärkten abgeleitet. Die Marge unterscheidet sich stark: ≈ 4–7 % (1X2, Doppelte Chance, Ü/U, Team-Tore) bis
≈ 10–17 % (Halbzeit-Ergebnis, Handicap, torreichste Halbzeit, exakte Toranzahl).

### Tippschein: 6 Entscheidungen pro Spiel (`analytics/decisions.py`)

Für jedes Spiel sechs feste Entscheidungen, jeweils die Seite, die das Modell für wahrscheinlicher hält: Sieger
(Heim / Unentschieden / Gast), Über 1,5 Tore, Über 2,5 Tore, Beide treffen, Tor in der 1. und in der 2. Halbzeit.
Auswertung (`/api/stats/decisions`, Tipps-Seite → „Tippschein“): Trefferquote gegen die Erwartung des Modells, gegen
„immer das Ergebnis, das in den Vorsaisons am häufigsten war“ (walk-forward) und zur letzten Betano-Quote.

**Backtest (27.10.2026, 1. + 2. Bundesliga, 5.634 Spiele):**

| Entscheidung | Modell tippt | getroffen | immer häufigstes | Vorsprung |
|---|---|--:|--:|--:|
| Sieger | Heim 72 %, Gast 28 %, nie Remis | 48,3 % | 43,5 % (Heim) | +5,3 Pkt. |
| Über 1,5 Tore | immer Ja | 81,5 % | 81,9 % | 0 |
| Über 2,5 Tore | Ja 83 % | 58,1 % | 60,0 % (Ja) | −1,4 Pkt. |
| Beide treffen | Ja 95 % | 58,1 % | 59,1 % (Ja) | −0,5 Pkt. |
| Tor 1. Halbzeit | immer Ja | 74,1 % | 74,3 % | 0 |
| Tor 2. Halbzeit | immer Ja | 82,6 % | 82,9 % | 0 |

Im Schnitt 4,0 von 6 richtig, alle 6 in 18 % der Spiele. Echten Mehrwert hat nur die Sieger-Entscheidung; bei den
Ja/Nein-Fragen liegt die Modell-Wahrscheinlichkeit fast immer auf derselben Seite der 50 % wie der Ligaschnitt, der
Tippschein entspricht dort „immer Ja“. Zur Betano-Quote sind alle Entscheidungen zusammen leicht negativ (−2,4 %).

### Kombi aus den Tipps eines Spiels (Bet Builder, `analytics/same_game.py`)

Die 3 Tipps eines Spiels hängen zusammen („Lazio trifft“ und „Lazio oder Remis“ treffen meist gemeinsam). Das Produkt
der Einzelwahrscheinlichkeiten unterschätzt deshalb die Kombi, das Produkt der Betano-Einzelquoten überschätzt die
Bet-Builder-Quote (Beispiel Sassuolo – Lazio: 1,18 × 1,35 × 1,19 = 1,90, Betano bot im Bet Builder 1,62).

Die gemeinsame Chance kommt aus den Halbzeit-Modellen: Tore je Team und Halbzeit sind unabhängige Poisson-Größen, ihre
Raten folgen exakt aus den gespeicherten P(Team trifft in der Halbzeit nicht). Auf diesem Raster (je 0–10 Tore) wird
jeder Tipp-Markt ausgewertet; der **Faktor** = P(alle) / Produkt der Einzelchancen auf dem Raster wird auf die
angezeigten Einzelwahrscheinlichkeiten angewendet (höchstens die kleinste davon).

**Geschätzte Bet-Builder-Quote:** Betano verbindet seine eigenen Einzelpreise auf dieselbe Weise. Die vier
Halbzeit-Torraten werden deshalb an die von den Betano-Einzelquoten implizierten Wahrscheinlichkeiten (1 / Quote, Marge
inklusive) angepasst – nahe an den Modellraten, wo die Tipps Spielraum lassen –, und die Bet-Builder-Quote ist das
Produkt der Einzelquoten ÷ Faktor auf diesem Raster. Die erste Version (Faktor des eigenen Modells) lag teils deutlich
daneben, weil der Zusammenhang von der Höhe der Wahrscheinlichkeiten abhängt und Betano die Spiele anders einschätzt:

| Spiel (27.10.2026) | Einzelquoten multipliziert | Betano Bet Builder | Schätzung neu | Schätzung alt |
|---|--:|--:|--:|--:|
| Sassuolo – Lazio | 1,90 | 1,62 | 1,62 | 1,49 |
| Großaspach – Augsburg | 1,38 | 1,28 | 1,28 | 1,24 |
| Rot-Weiß Essen – Leipzig | 1,64 | 1,42 | 1,42 | 1,18 |
| Hamburg – Frankfurt | 5,64 | 2,67 | 2,82 | 3,71 |

Modell-EV der Kombi = gemeinsame Modell-Chance × geschätzte Bet-Builder-Quote − 1 (Anzeige je Spiel).

**Backtest (27.10.2026, 16.902 abgerechnete Spiele × Profil, Kombi aus 3 Tipps):** getroffen 51,7 %, gemeinsame
Modell-Chance Ø 52,9 %, Produkt der Einzelchancen Ø 44,1 %. Log-Loss 0,656 statt 0,677, Brier 0,232 statt 0,241, in
allen drei Profilen besser; kalibriert in allen Bereichen (z. B. 50–60 %: erwartet 55,4 %, getroffen 54,8 %).

### Closing Line Value der Tipps (`qf value clv`)

`analytics/clv.py` misst für jeden Tipp die Betano-Quote zu dem Zeitpunkt, an dem er gezeigt wurde (Live: Fixieren des
Tages, sonst Prognose; Backtest: erster Anpfiff des Spieltags, das Modell kennt nur Spiele davor), gegen den
Schlussmarkt: **CLV** = genommene Betano-Quote × Pinnacle-Wahrscheinlichkeit ohne Marge beim Anpfiff − 1. Weil Betano
auf Favoriten weniger Marge nimmt, ist der Vergleich alle Auswahlen derselben Märkte und Spiele, gewichtet auf die
Quotenverteilung der Tipps; der **Abstand** (CLV − Vergleich, Standardfehler nach Spiel geclustert) zeigt, ob die
Auswahl des Modells Information enthält, die der Markt erst später einpreist. Ergebnis: **`docs/23_clv.md`**, im
Frontend auf der Tipps-Seite (`/api/stats/clv`, 1 h Cache) und je Tipp im Popover (Quote beim Tipp, zuletzt, CLV).

**Stand 26.10.2026** (1.447 Tipps, 180 Spiele mit Betano-Verlauf): CLV −3,0 %, Vergleichsgruppe −3,6 %, Abstand
+0,7 %-Punkte (≈ 3 Standardfehler). Das Modell trifft die Richtung der Marktbewegung leicht besser als der Zufall, die
Tipps liegen aber nach Betano-Marge unter dem fairen Schlusspreis → für Gewinn braucht es zusätzlich einen
Value-Filter (nächster Schritt: Value-Profil mit Backtest).

### Paper-Trading
Ab Inbetriebnahme werden alle Value-Signale automatisch als „Papierwetten“ in `analytics.value_bets` protokolliert
(mit Quote zum Signalzeitpunkt, Schlussquote, Ergebnis). So entsteht ein ehrlicher Live-Track-Record je Markt.

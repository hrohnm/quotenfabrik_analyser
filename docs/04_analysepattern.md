# 04 – Analysepattern pro Marktgruppe

> **Umsetzungsstand (Phase 2):** Modelle und Märkte in `backend/quotenfabrik/analytics/markets/` und `scorers.py`,
> deskriptive Pattern in `analytics/patterns.py` (≈ 50 Pattern pro Spiel: Serien mit Wilson-Signal, Tordifferenz/xG,
> Halbzeit-Anteile, Tor-Timing, Top-Torschützen). Noch offen aus dem Katalog unten: Ruhetage/englische Wochen,
> Schiedsrichter, Ausfälle-Gewichtung, Comeback-Verhalten, Gegnerstärke-Bereinigung der Serien.

Jede Marktgruppe kombiniert drei Ebenen:

1. **Modellwahrscheinlichkeit** – aus einem statistischen Modell (siehe `05_modelle_und_backtesting.md`).
2. **Deskriptive Pattern** – nachvollziehbare Kennzahlen („Heimteam traf in 9 der letzten 10 Heimspiele“),
   die das Modell bestätigen oder ihm widersprechen.
3. **Marktabgleich** – faire Quote vs. beste verfügbare Quote → Edge, EV, Kelly, Quotenbewegung.

## Gemeinsame Schnittstelle

Jedes Modul unter `analytics/markets/` implementiert:

```python
# backend/quotenfabrik/analytics/markets/<gruppe>.py
def probabilities(pred: MatchPrediction) -> list[MarketProbability]  # (market, selection, line, p)
def outcomes(match) -> dict[(market, selection, line), bool]          # tatsächliches Ergebnis → Evaluation/Abrechnung

# backend/quotenfabrik/analytics/patterns.py
def patterns_<gruppe>(ctx: PatternContext, home, away) -> list[PatternResult]
```

`PatternContext.build(matches, as_of, …)` enthält nur Daten vor `as_of` – so bleiben Pattern und Modelle frei von
Data Leakage (durch Tests abgesichert). Torschützen nutzen `ScorerModel` (`analytics/scorers.py`).


## Gemeinsame Bausteine (für alle Gruppen)

| Baustein | Beschreibung |
|---|---|
| Form-Fenster | letzte 5 / 10 Spiele gesamt sowie **nur Heim** bzw. **nur Auswärts** |
| Saison-Split | laufende Saison vs. Vorsaison, mit Gewichtung nach Anzahl Spiele |
| Gegnerstärke-Bereinigung | Kennzahlen relativ zur Stärke der Gegner (über Team-Ratings) |
| Liga-Baseline | Ligadurchschnitt derselben Saison als Referenz (z. B. Ü2.5-Quote der Bundesliga) |
| Shrinkage | kleine Stichproben werden zur Liga-Baseline gezogen (Bayes / empirische Bayes-Schätzung) |
| Kontext | Ruhetage, englische Woche, Ausfälle (Injuries), Schiedsrichter, Aufsteiger, Trainerwechsel |
| Signalstärke | jedes Pattern liefert Rate, Stichprobe n und Abweichung zur Baseline (z. B. Wilson-Intervall) |

## 1. 1X2 (Spielausgang)

**Modell:** Dixon-Coles (Poisson mit Korrektur für niedrige Ergebnisse, Zeitgewichtung) → Ergebnismatrix → P(1), P(X), P(2).
Daraus auch Doppelte Chance, Draw No Bet und europäisches Handicap (3-Weg). Keine asiatischen Märkte (bei Betano DE nicht verfügbar).

**Pattern:**
- Punkte pro Spiel (gesamt, Heim/Auswärts), Last-5/10-Form
- Tordifferenz und **xG-Differenz** pro Spiel (wo verfügbar), Schüsse/Torschüsse-Verhältnis als xG-Ersatz in älteren Saisons
- Team-Ratings (Angriff/Abwehr) und deren Trend über die letzten Spieltage
- Remis-Neigung: Remisquote beider Teams, Erwartete Tordifferenz nahe 0, beide Teams torarm
- Comeback/Führungsverhalten: Punkte nach Rückstand / nach Führung (aus Events)
- H2H (nur als schwaches Signal, kleine Stichprobe)
- Ausfälle: Anteil fehlender Stammspieler (Minutenanteil der Saison)
- Ruhetage-Differenz, Europapokal-Belastung
- Marktabgleich: Modell vs. Pinnacle-Quote (ohne Marge); Abweichung > Schwelle = Kandidat

## 2. Über/Unter Tore gesamt

**Modell:** Gleiche Ergebnismatrix; Summe der Tore → Ü/U 0.5 … 5.5 (nur x.5-Linien), exakte Toranzahl, BTTS.

**Pattern:**
- Ü-Quote je Linie (1.5/2.5/3.5) beider Teams, Heim/Auswärts-spezifisch, vs. Liga-Baseline
- Ø Tore erzielt + kassiert, Ø xG + xGA, Schüsse pro Spiel beider Teams
- Erwartete Gesamttore (λ_heim + λ_gast) vs. Linie des Marktes
- Varianz-Indikator: Anteil Spiele mit 0–1 bzw. 4+ Toren (Dispersion; Poisson-Annahme prüfen)
- BTTS-Quote beider Teams, Zu-Null-Quote, „failed to score“-Quote
- Spielstil-Proxy: Ballbesitz, Pässe, Fouls (temporeiche vs. kontrollierte Spiele)
- Schiedsrichter: Ø Tore/Elfmeter in seinen Spielen (nur bei ausreichendem n)
- Spieltag-/Saisonphase-Effekte (Saisonende, Abstiegskampf)
- Quotenbewegung: Linie/Quote seit Eröffnung (Snapshot-Archiv)

## 3. Über/Unter Tore pro Team (Heim / Gast)

**Modell:** Randverteilungen der Ergebnismatrix (λ_heim, λ_gast) → Team-Total-Linien 0.5/1.5/2.5/3.5, Clean Sheet, Win to Nil.

**Pattern:**
- Heimteam-Tore **zu Hause**, Gastteam-Tore **auswärts** (Rate ≥1, ≥2, ≥3 Tore)
- Gegentore des Gegners in der passenden Rolle (Gast kassiert auswärts …)
- Angriffsstärke × Abwehrschwäche des Gegners (aus Ratings) → erwartete Tore
- xG-Überperformance: Tore − xG der letzten N Spiele (Regressionskandidat)
- Abhängigkeit von Einzelspielern: Anteil der Tore des Top-Torschützen, fehlt er? (Injuries/Lineups)
- Torlose Serien und „Tore in Serie“, gegen Top-6 / gegen untere Tabellenhälfte
- Elfmeter-Anteil an Toren (volatil)

## 4. Über/Unter Tore pro Halbzeit

**Modell:** Eigene Poisson-Modelle für 1. und 2. Halbzeit (Team-Angriff/Abwehr je Halbzeit, Heimvorteil je Halbzeit),
da Teams sehr unterschiedliche Halbzeitprofile haben. → 1. HZ Ü/U 0.5/1.5/2.5, 2. HZ Ü/U, Team-Tore je Halbzeit,
torreichste Halbzeit, HZ-Ergebnis, BTTS je Halbzeit.

**Pattern:**
- Anteil der Tore (erzielt/kassiert) in der 1. HZ pro Team vs. Liga (~44 % in der 1. HZ als Richtwert prüfen)
- Tor-Timing-Verteilung in 15-Minuten-Intervallen (0–15, 16–30, 31–45+, 46–60, 61–75, 76–90+) aus Events
- Frühe Tore (bis Min. 30), späte Tore (ab Min. 75), Tore in Nachspielzeit
- Halbzeit-Statistiken (Schüsse, xG je Halbzeit, ab Saison 2024 über `half=true`)
- Reaktion auf Spielstand zur Pause: Tore in der 2. HZ bei Rückstand/Führung
- Wechselverhalten des Trainers (Zeitpunkt der ersten Wechsel) als Proxy für 2.-HZ-Dynamik
- 1. HZ Ü0.5-Quote beider Teams, 2. HZ Ü1.5-Quote beider Teams

## 5. Torschützen

**Modell:** Für jeden Spieler
`λ_spieler = λ_team × Anteil_spieler × (erwartete Minuten / 90)` und `P(trifft mind. 1×) = 1 − e^(−λ_spieler)`.
- `Anteil_spieler`: Anteil an Team-Toren **ohne Eigentore**, gewichtet über Schüsse/Torschüsse/xG je 90 Min.,
  Shrinkage zum Positionsdurchschnitt (Stürmer/Mittelfeld/Abwehr), Zeitgewichtung.
- Elfmeterschütze: separater Elfmeter-Anteil (Elfmeter pro Spiel des Teams × Schützenrolle).
- Erwartete Minuten: Startelf-Wahrscheinlichkeit aus den letzten Spielen; nach Lineup-Veröffentlichung exakt (Startelf ≈ 80–90 Min., Bank ≈ 15–20 Min.).
- Erster Torschütze: λ_spieler / (λ_heim + λ_gast) × P(mind. 1 Tor).

**Pattern:**
- Tore, Schüsse, Torschüsse pro 90 Min. (Saison, letzte 5 Spiele)
- Conversion-Rate (Tore / Schüsse) vs. Positionsschnitt → Glück/Regressionskandidat
- Startelf-Quote, Minuten-Trend, Rotation in englischen Wochen
- Elfmeterschütze ja/nein, Standardsituationen
- Heim/Auswärts-Split des Spielers, Torquote gegen ähnlich starke Gegner
- Gegner: Gegentore pro Spiel, Gegentore nach Position (Kopfball/Standard sofern aus Events ableitbar)
- Verfügbarkeit: Injuries, Sperren (Gelbsperren aus Karten-Events), bestätigte Aufstellung

## Signal-Logik (für UI und spätere Abos)

Ein Value-Kandidat entsteht, wenn
1. Edge = p_modell × quote − 1 ≥ Schwelle (konfigurierbar je Markt, z. B. 1X2 ≥ 3 %, Torschützen ≥ 10 %),
2. die Stichprobe der stützenden Pattern ausreicht (n ≥ Mindestwert) und
3. der Markt im Backtest/Kalibrierungstest nicht schlechter als der Markt-Benchmark abgeschnitten hat.

Jedes Signal speichert die beteiligten Pattern, damit später nachvollziehbar ist, welche Pattern profitabel waren
(Pattern-Attribution im Backtest).

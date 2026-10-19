# 05 – Modelle, Value-Berechnung & Backtesting

## 1. Basis: Dixon-Coles-Modell (volle Spielzeit)

- Tore Heim ~ Poisson(λ_h), Tore Gast ~ Poisson(λ_g)
- `log λ_h = µ + Heimvorteil + Angriff_heim − Abwehr_gast`, `log λ_g = µ + Angriff_gast − Abwehr_heim`
- Dixon-Coles-Korrektur ρ für die Ergebnisse 0:0, 1:0, 0:1, 1:1
- **Zeitgewichtung** `w = exp(−ξ · Tage_seit_Spiel)`, ξ per Kreuzvalidierung (typisch Halbwertszeit 4–8 Monate)
- L2-Regularisierung der Team-Parameter → Aufsteiger mit wenig Bundesliga-Daten werden zum Mittelwert gezogen
  (Option später: Zweitliga-Daten D2 von football-data.co.uk als Vorwissen für Aufsteiger)
- Optional: xG statt Toren als Zielgröße (bzw. Mischung) in Saisons mit xG
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

### Paper-Trading
Ab Inbetriebnahme werden alle Value-Signale automatisch als „Papierwetten“ in `analytics.value_bets` protokolliert
(mit Quote zum Signalzeitpunkt, Schlussquote, Ergebnis). So entsteht ein ehrlicher Live-Track-Record je Markt.

# 10 – Quoten-Backtest 1X2 und Über/Unter 2,5 (Phase 3, Schritt 1)

Automatisch erzeugt von `qf value backtest` am 19.10.2026 12:59 UTC (Modell `dc-v1`, Lauf `analytics.model_runs.id = 8`).

**Daten:** rückwirkende Walk-Forward-Prognosen (`qf model backtest`) gegen die historischen Quoten von football-data.co.uk. *Eröffnung* = Quote beim Erstellen der CSV (≈ Freitag bzw. Dienstag vor dem Spiel, also etwa dann, wenn wir wetten würden), *Schluss* = Quote kurz vor Anpfiff.

**Margenentfernung:** Shin-Methode. Marktwahrscheinlichkeit = Pinnacle, sonst Marktschnitt.

**Validierung / Test:** Blend-Gewichte und Edge-Schwelle werden nur auf den Saisons bis 2021/22 gewählt und danach einmalig auf den Testsaisons bewertet. Achtung: Die Modell-Hyperparameter wurden auf 2018–2021 gewählt – die Validierung ist für das Modell daher leicht geschönt, der Test nicht.

**Wetten:** je Spiel höchstens eine Wette (Auswahl mit der größten Edge über der Schwelle), Einsatz 1 Einheit zur Eröffnungsquote. *ROI* = Gewinn / Einsatz mit 95-%-Bootstrap-Intervall, *CLV* = Eröffnungsquote × margenfreie Schluss-Wahrscheinlichkeit − 1 (positiv = Quote war besser als der Schlusskurs; der belastbarste Indikator für echten Value). Bet365 dient als Proxy für Betano (ähnliche Marge, für Betano gibt es keine historischen Quoten).

## Fazit

- **1X2:** Log-Loss Modell 0,9940 vs. Markt (Eröffnung) 0,9713 → Modell schlechter als der Markt. Blend-Gewicht des Modells -0,20 (keine Zusatzinformation). Der Markt bewegt sich bei klaren Abweichungen nur in 48 % der Fälle Richtung Modell (Korrelation -0,04). Value-Wetten nach Modell @ Bet365: 683 Wetten, Ø Quote 4,76, ROI −26,2 %, CLV −7,2 %; auch die beste der vier Varianten hat CLV −5,0 %.
- **Über/Unter 2,5:** Log-Loss Modell 0,6553 vs. Markt (Eröffnung) 0,6460 → Modell schlechter als der Markt. Blend-Gewicht des Modells -0,40 (keine Zusatzinformation). Der Markt bewegt sich bei klaren Abweichungen nur in 41 % der Fälle Richtung Modell (Korrelation -0,10). Value-Wetten nach Modell @ Bet365: 624 Wetten, Ø Quote 2,13, ROI −10,3 %, CLV −5,6 %; auch die beste der vier Varianten hat CLV −2,5 %.

**Bewertung:** Das Modell ist zwar deutlich besser als einfache Vergleichswerte (Phase 2), aber schlechter als die Buchmacher. Value-Wetten nach Modell verlieren im Test ungefähr die Marge oder mehr, und der CLV ist negativ – die Quoten bewegen sich eher *vom* Modell weg. Bei 1X2 sind die „Value“-Tipps überwiegend Außenseiter: Das Modell ist dort weniger extrem als der Markt (Regularisierung zieht Teams zum Mittelwert), der Markt liegt richtig. Für 1X2 und Ü/U 2,5 gibt es mit `dc-v1` **keinen belastbaren Value**. Diese Hauptmärkte sind sehr effizient; Ansatzpunkte für Phase 3 sind daher (a) aus den Hauptmarkt-Quoten abgeleitete Wahrscheinlichkeiten für Nebenmärkte (Team-Tore, Halbzeiten, Torschützen), die Buchmacher oft weniger genau bepreisen (Hypothese, mit dem Betano-Archiv zu prüfen), und (b) Informationen, die das Modell noch nicht nutzt (Aufstellungen, Ausfälle, xG).

## 1X2

3105 Spiele; Validierung 2016/17 – 2021/22, Test 2022/23 – 2026/27. Ø Marge (Eröffnung, Test): Pinnacle 3,3 %, Bet365 (Proxy für Betano) 5,4 %, Marktschnitt 5,1 %.

### Prognosegüte (kleiner = besser)

| Quelle | Log-Loss Validierung | Log-Loss Test | Brier Test | RPS Test |
|---|---|---|---|---|
| Modell | 0,9976 | 0,9940 | 0,5933 | 0,2029 |
| Markt (Eröffnung) | 0,9847 | 0,9713 | 0,5773 | 0,1956 |
| Mischung | 0,9836 | 0,9707 | 0,5767 | 0,1956 |
| Markt (Schluss) | 0,9834 | 0,9701 | 0,5763 | 0,1955 |

Vergleich jeweils auf denselben Spielen mit vollständigen Quoten (Validierung 1835, Test 1269). *Mischung* = logarithmische Mischung p ∝ Markt^1,09 · Modell^-0,20 (Gewichte auf der Validierung geschätzt).

### Value-Wetten (Test)

| Wahrscheinlichkeit | Quote | Schwelle (Validierung) | Wetten | Treffer | Ø Quote | ROI | 95-%-Intervall | CLV | Max. Drawdown |
|---|---|---|---|---|---|---|---|---|---|
| Modell | Bet365 (Proxy für Betano) | Edge > 6 % (ROI +1,7 %) | 683 | 22,0 % | 4,76 | **−26,2 %** | −38,7 % … −13,2 % | −7,2 % | 205,2 E |
| Modell | Pinnacle | Edge > 8 % (ROI +5,7 %) | 591 | 22,0 % | 5,06 | **−19,6 %** | −34,3 % … −4,0 % | −5,7 % | 143,0 E |
| Mischung | Bet365 (Proxy für Betano) | Edge > 6 % (ROI +6,1 %) | 132 | 15,2 % | 7,29 | **−1,6 %** | −44,9 % … +51,4 % | −5,0 % | 43,1 E |
| Mischung | Pinnacle | Edge > 4 % (ROI +2,6 %) | 213 | 14,1 % | 6,77 | **−25,1 %** | −52,7 % … +3,7 % | −6,1 % | 105,6 E |

Alle Schwellen im Test (Modell @ Bet365) – zeigt, ob das Ergebnis an einer zufällig gewählten Schwelle hängt:

| Edge > | Wetten | ROI | CLV |
|---|---|---|---|
| 0 % | 1025 | −16,0 % | −6,5 % |
| 2 % | 897 | −19,9 % | −6,9 % |
| 4 % | 776 | −26,5 % | −7,0 % |
| 6 % | 683 | −26,2 % | −7,2 % |
| 8 % | 597 | −25,7 % | −7,3 % |
| 10 % | 527 | −28,0 % | −7,5 % |

Je Testsaison (Modell @ Bet365):

| Saison | Wetten | ROI | CLV |
|---|---|---|---|
| 2022/23 | 140 | +3,4 % | −5,6 % |
| 2023/24 | 175 | −28,0 % | −7,0 % |
| 2024/25 | 170 | −46,8 % | −9,4 % |
| 2025/26 | 166 | −35,0 % | −6,8 % |
| 2026/27 | 32 | +9,4 % | −6,5 % |

## Über/Unter 2,5

3105 Spiele; Validierung 2016/17 – 2021/22, Test 2022/23 – 2026/27. Ø Marge (Eröffnung, Test): Pinnacle 3,5 %, Bet365 (Proxy für Betano) 5,0 %, Marktschnitt 5,5 %.

### Prognosegüte (kleiner = besser)

| Quelle | Log-Loss Validierung | Log-Loss Test | Brier Test |
|---|---|---|---|
| Modell | 0,6557 | 0,6553 | 0,4630 |
| Markt (Eröffnung) | 0,6452 | 0,6460 | 0,4543 |
| Mischung | 0,6447 | 0,6456 | 0,4540 |
| Markt (Schluss) | 0,6405 | 0,6438 | 0,4522 |

Vergleich jeweils auf denselben Spielen mit vollständigen Quoten (Validierung 918, Test 1269). *Mischung* = logarithmische Mischung p ∝ Markt^1,44 · Modell^-0,40 (Gewichte auf der Validierung geschätzt).

### Value-Wetten (Test)

| Wahrscheinlichkeit | Quote | Schwelle (Validierung) | Wetten | Treffer | Ø Quote | ROI | 95-%-Intervall | CLV | Max. Drawdown |
|---|---|---|---|---|---|---|---|---|---|
| Modell | Bet365 (Proxy für Betano) | Edge > 2 % (ROI −8,0 %) | 624 | 46,3 % | 2,13 | **−10,3 %** | −18,8 % … −2,1 % | −5,6 % | 70,3 E |
| Modell | Pinnacle | Edge > 10 % (ROI −7,2 %) | 183 | 47,0 % | 2,15 | **−3,8 %** | −18,9 % … +12,2 % | −4,6 % | 13,7 E |
| Mischung | Bet365 (Proxy für Betano) | Edge > 0 % (ROI −2,6 %) | 388 | 54,4 % | 1,97 | **−3,4 %** | −12,6 % … +5,7 % | −2,5 % | 29,7 E |
| Mischung | Pinnacle | Edge > 4 % (ROI +8,5 %) | 89 | 41,6 % | 2,11 | **−14,5 %** | −36,0 % … +8,2 % | −2,5 % | 16,2 E |

Alle Schwellen im Test (Modell @ Bet365) – zeigt, ob das Ergebnis an einer zufällig gewählten Schwelle hängt:

| Edge > | Wetten | ROI | CLV |
|---|---|---|---|
| 0 % | 812 | −9,2 % | −5,4 % |
| 2 % | 624 | −10,3 % | −5,6 % |
| 4 % | 485 | −10,9 % | −5,8 % |
| 6 % | 370 | −5,8 % | −5,7 % |
| 8 % | 278 | −6,4 % | −5,8 % |
| 10 % | 208 | −10,7 % | −6,2 % |

Je Testsaison (Modell @ Bet365):

| Saison | Wetten | ROI | CLV |
|---|---|---|---|
| 2022/23 | 165 | −5,9 % | −6,5 % |
| 2023/24 | 122 | −8,8 % | −5,0 % |
| 2024/25 | 155 | −3,6 % | −4,1 % |
| 2025/26 | 154 | −19,1 % | −5,6 % |
| 2026/27 | 28 | −31,3 % | −11,3 % |

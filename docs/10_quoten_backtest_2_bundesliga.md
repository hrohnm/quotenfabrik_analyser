# 10 – Quoten-Backtest 1X2 und Über/Unter 2,5 (Phase 3, Schritt 1) · 2. Bundesliga

Automatisch erzeugt von `qf value backtest` am 19.10.2026 15:24 UTC (Modell `dc-v1`, Lauf `analytics.model_runs.id = 16`).

**Daten:** rückwirkende Walk-Forward-Prognosen (`qf model backtest`) gegen die historischen Quoten von football-data.co.uk. *Eröffnung* = Quote beim Erstellen der CSV (≈ Freitag bzw. Dienstag vor dem Spiel, also etwa dann, wenn wir wetten würden), *Schluss* = Quote kurz vor Anpfiff.

**Margenentfernung:** Shin-Methode. Marktwahrscheinlichkeit = Pinnacle, sonst Marktschnitt.

**Validierung / Test:** Blend-Gewichte und Edge-Schwelle werden nur auf den Saisons bis 2021/22 gewählt und danach einmalig auf den Testsaisons bewertet. Achtung: Die Modell-Hyperparameter wurden auf 2018–2021 gewählt – die Validierung ist für das Modell daher leicht geschönt, der Test nicht.

**Wetten:** je Spiel höchstens eine Wette (Auswahl mit der größten Edge über der Schwelle), Einsatz 1 Einheit zur Eröffnungsquote. *ROI* = Gewinn / Einsatz mit 95-%-Bootstrap-Intervall, *CLV* = Eröffnungsquote × margenfreie Schluss-Wahrscheinlichkeit − 1 (positiv = Quote war besser als der Schlusskurs; der belastbarste Indikator für echten Value). Bet365 dient als Proxy für Betano (ähnliche Marge, für Betano gibt es keine historischen Quoten).

## Fazit

- **1X2:** Log-Loss Modell 1,0509 vs. Markt (Eröffnung) 1,0353 → Modell schlechter als der Markt. Blend-Gewicht des Modells 0,06 (Zusatzinformation). Der Markt bewegt sich bei klaren Abweichungen nur in 48 % der Fälle Richtung Modell (Korrelation -0,02). Value-Wetten nach Modell @ Bet365: 487 Wetten, Ø Quote 3,62, ROI −13,2 %, CLV −6,4 %; auch die beste der vier Varianten hat CLV −2,2 %.
- **Über/Unter 2,5:** Log-Loss Modell 0,6812 vs. Markt (Eröffnung) 0,6722 → Modell schlechter als der Markt. Blend-Gewicht des Modells -0,38 (keine Zusatzinformation). Der Markt bewegt sich bei klaren Abweichungen nur in 54 % der Fälle Richtung Modell (Korrelation 0,06). Value-Wetten nach Modell @ Bet365: 199 Wetten, Ø Quote 2,19, ROI −8,6 %, CLV −6,0 %; auch die beste der vier Varianten hat CLV −3,5 %.

**Bewertung:** Das Modell ist zwar deutlich besser als einfache Vergleichswerte (Phase 2), aber schlechter als die Buchmacher. Value-Wetten nach Modell verlieren im Test ungefähr die Marge oder mehr, und der CLV ist negativ – die Quoten bewegen sich eher *vom* Modell weg. Bei 1X2 sind die „Value“-Tipps überwiegend Außenseiter: Das Modell ist dort weniger extrem als der Markt (Regularisierung zieht Teams zum Mittelwert), der Markt liegt richtig. Für 1X2 und Ü/U 2,5 gibt es mit `dc-v1` **keinen belastbaren Value**. Diese Hauptmärkte sind sehr effizient; Ansatzpunkte für Phase 3 sind daher (a) aus den Hauptmarkt-Quoten abgeleitete Wahrscheinlichkeiten für Nebenmärkte (Team-Tore, Halbzeiten, Torschützen), die Buchmacher oft weniger genau bepreisen (Hypothese, mit dem Betano-Archiv zu prüfen), und (b) Informationen, die das Modell noch nicht nutzt (Aufstellungen, Ausfälle, xG).

## 1X2

3123 Spiele; Validierung 2016/17 – 2021/22, Test 2022/23 – 2026/27. Ø Marge (Eröffnung, Test): Pinnacle 3,6 %, Bet365 (Proxy für Betano) 6,0 %, Marktschnitt 6,8 %.

### Prognosegüte (kleiner = besser)

| Quelle | Log-Loss Validierung | Log-Loss Test | Brier Test | RPS Test |
|---|---|---|---|---|
| Modell | 1,0708 | 1,0509 | 0,6328 | 0,2227 |
| Markt (Eröffnung) | 1,0608 | 1,0353 | 0,6221 | 0,2174 |
| Mischung | 1,0597 | 1,0372 | 0,6235 | 0,2181 |
| Markt (Schluss) | 1,0586 | 1,0346 | 0,6218 | 0,2173 |

Vergleich jeweils auf denselben Spielen mit vollständigen Quoten (Validierung 1836, Test 1287). *Mischung* = logarithmische Mischung p ∝ Markt^0,81 · Modell^0,06 (Gewichte auf der Validierung geschätzt).

### Value-Wetten (Test)

| Wahrscheinlichkeit | Quote | Schwelle (Validierung) | Wetten | Treffer | Ø Quote | ROI | 95-%-Intervall | CLV | Max. Drawdown |
|---|---|---|---|---|---|---|---|---|---|
| Modell | Bet365 (Proxy für Betano) | Edge > 10 % (ROI −3,0 %) | 487 | 27,5 % | 3,62 | **−13,2 %** | −26,9 % … +0,3 % | −6,4 % | 66,4 E |
| Modell | Pinnacle | Edge > 10 % (ROI +0,5 %) | 460 | 29,3 % | 3,52 | **−8,1 %** | −21,7 % … +6,9 % | −4,6 % | 43,3 E |
| Mischung | Bet365 (Proxy für Betano) | Edge > 10 % (ROI +30,6 %) | 16 | 6,2 % | 6,58 | **−70,3 %** | −100,0 % … −10,9 % | −2,2 % | 11,2 E |
| Mischung | Pinnacle | Edge > 8 % (ROI +20,3 %) | 27 | 11,1 % | 7,68 | **−28,2 %** | −100,0 % … +55,4 % | −7,0 % | 10,6 E |

Alle Schwellen im Test (Modell @ Bet365) – zeigt, ob das Ergebnis an einer zufällig gewählten Schwelle hängt:

| Edge > | Wetten | ROI | CLV |
|---|---|---|---|
| 0 % | 1038 | −10,0 % | −6,0 % |
| 2 % | 904 | −14,4 % | −6,1 % |
| 4 % | 796 | −12,9 % | −6,2 % |
| 6 % | 681 | −13,3 % | −6,1 % |
| 8 % | 565 | −15,0 % | −6,4 % |
| 10 % | 487 | −13,2 % | −6,4 % |

Je Testsaison (Modell @ Bet365):

| Saison | Wetten | ROI | CLV |
|---|---|---|---|
| 2022/23 | 92 | −10,9 % | −5,9 % |
| 2023/24 | 105 | −5,5 % | −4,6 % |
| 2024/25 | 133 | −5,8 % | −8,0 % |
| 2025/26 | 136 | −24,4 % | −7,2 % |
| 2026/27 | 21 | −37,6 % | −3,2 % |

## Über/Unter 2,5

3123 Spiele; Validierung 2016/17 – 2021/22, Test 2022/23 – 2026/27. Ø Marge (Eröffnung, Test): Pinnacle 3,8 %, Bet365 (Proxy für Betano) 6,0 %, Marktschnitt 6,6 %.

### Prognosegüte (kleiner = besser)

| Quelle | Log-Loss Validierung | Log-Loss Test | Brier Test |
|---|---|---|---|
| Modell | 0,6910 | 0,6812 | 0,4878 |
| Markt (Eröffnung) | 0,6789 | 0,6722 | 0,4793 |
| Mischung | 0,6770 | 0,6726 | 0,4797 |
| Markt (Schluss) | 0,6765 | 0,6709 | 0,4783 |

Vergleich jeweils auf denselben Spielen mit vollständigen Quoten (Validierung 918, Test 1287). *Mischung* = logarithmische Mischung p ∝ Markt^1,49 · Modell^-0,38 (Gewichte auf der Validierung geschätzt).

### Value-Wetten (Test)

| Wahrscheinlichkeit | Quote | Schwelle (Validierung) | Wetten | Treffer | Ø Quote | ROI | 95-%-Intervall | CLV | Max. Drawdown |
|---|---|---|---|---|---|---|---|---|---|
| Modell | Bet365 (Proxy für Betano) | Edge > 10 % (ROI −6,9 %) | 199 | 43,7 % | 2,19 | **−8,6 %** | −22,8 % … +6,4 % | −6,0 % | 18,7 E |
| Modell | Pinnacle | Edge > 10 % (ROI −1,3 %) | 218 | 45,0 % | 2,18 | **−7,6 %** | −20,7 % … +6,2 % | −3,8 % | 20,4 E |
| Mischung | Bet365 (Proxy für Betano) | Edge > 0 % (ROI +0,2 %) | 326 | 56,7 % | 1,70 | **−5,7 %** | −14,5 % … +3,2 % | −4,8 % | 29,6 E |
| Mischung | Pinnacle | Edge > 4 % (ROI +4,3 %) | 87 | 51,7 % | 1,82 | **−8,9 %** | −28,4 % … +9,2 % | −3,5 % | 14,5 E |

Alle Schwellen im Test (Modell @ Bet365) – zeigt, ob das Ergebnis an einer zufällig gewählten Schwelle hängt:

| Edge > | Wetten | ROI | CLV |
|---|---|---|---|
| 0 % | 757 | −6,8 % | −5,7 % |
| 2 % | 603 | −8,3 % | −5,4 % |
| 4 % | 484 | −8,1 % | −5,3 % |
| 6 % | 375 | −6,7 % | −5,3 % |
| 8 % | 273 | −7,5 % | −5,9 % |
| 10 % | 199 | −8,6 % | −6,0 % |

Je Testsaison (Modell @ Bet365):

| Saison | Wetten | ROI | CLV |
|---|---|---|---|
| 2022/23 | 35 | −25,1 % | −6,7 % |
| 2023/24 | 68 | −0,8 % | −6,4 % |
| 2024/25 | 46 | +0,4 % | −7,5 % |
| 2025/26 | 40 | −14,5 % | −2,4 % |
| 2026/27 | 10 | −22,2 % | −7,5 % |

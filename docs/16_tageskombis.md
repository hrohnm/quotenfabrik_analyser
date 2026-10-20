# 16 – Tageskombis: Erfolgschance im Backtest

Automatisch erzeugt von `qf combos report` am 20.10.2026 09:17 UTC. Wettbewerbe: Bundesliga, 2. Bundesliga, UEFA Champions League, UEFA Europa League, UEFA Europa Conference League; 1275 Spieltage mit rückwirkenden Prognosen (Walk-Forward, kein Data Leakage).

**Regeln:** Pro Tag bis zu drei Kombis – Tore gesamt Über, Tore einer Mannschaft Über, Doppelte Chance – über alle Spiele des Tages. Je Spiel und Art zählt der stärkste Tipp (Wahrscheinlichkeit plus Abweichung vom Ligaschnitt); die Kombis wählen abwechselnd, Spiele ohne Kombi werden bevorzugt. Aufgefüllt wird bis zur Zielquote 5–10. Die Quote je Tipp ist geschätzt: faire Quote × (1 − 5,0 % Marge). Gewonnen ist eine Kombi nur, wenn alle Tipps sitzen (nach 90 Minuten).

**Wichtig:** Auch bei perfekten Wahrscheinlichkeiten zahlt jeder Tipp die Buchmacher-Marge. Erwartete Rendite einer Kombi aus n Tipps ohne eigenen Vorteil: (1 − Marge)ⁿ − 1, bei 5 % Marge und 7 Tipps also ≈ −30 %. Gewinn entsteht nur, wenn das Modell die Wahrscheinlichkeiten besser kennt als der Buchmacher.

## Ergebnis je Variante

| Variante | Kombi | Kombis | getroffen | Modell erwartet | Ø Quote | Ø Tipps | Rendite (geschätzte Quote) |
|---|---|---:|---:|---:|---:|---:|---:|
| sicherere Tipps (65–90 %) | Tore gesamt – Über | 248 | 18,1 % | 12,8 % | 5,20 | 7,9 | -5,5 % |
| sicherere Tipps (65–90 %) | Tore Mannschaft – Über | 396 | 11,9 % | 13,0 % | 5,18 | 7,7 | -38,8 % |
| sicherere Tipps (65–90 %) | Doppelte Chance | 416 | 10,6 % | 12,6 % | 5,47 | 7,4 | -43,9 % |
| Standard (55–85 %) | Tore gesamt – Über | 616 | 14,4 % | 12,4 % | 5,76 | 6,8 | -18,0 % |
| Standard (55–85 %) | Tore Mannschaft – Über | 610 | 13,6 % | 13,0 % | 5,56 | 6,6 | -24,8 % |
| Standard (55–85 %) | Doppelte Chance | 575 | 11,8 % | 12,9 % | 5,57 | 6,7 | -34,5 % |
| riskantere Tipps (45–75 %) | Tore gesamt – Über | 855 | 13,8 % | 13,1 % | 6,31 | 4,3 | -15,4 % |
| riskantere Tipps (45–75 %) | Tore Mannschaft – Über | 836 | 12,7 % | 13,2 % | 6,18 | 4,4 | -23,9 % |
| riskantere Tipps (45–75 %) | Doppelte Chance | 708 | 11,7 % | 13,6 % | 5,85 | 5,0 | -32,4 % |

Getroffen > erwartet heißt: das Modell war bei diesen Tipps eher zu vorsichtig; die Rendite ist mit der geschätzten (nicht der echten) Quote gerechnet.

## Standard je Saison

| Saison | Kombi | Kombis | getroffen | Modell erwartet | Rendite |
|---|---|---:|---:|---:|---:|
| 2016/17 | Doppelte Chance | 24 | 8,3 % | 13,5 % | -49,2 % |
| 2016/17 | Tore Mannschaft – Über | 34 | 8,8 % | 13,6 % | -52,9 % |
| 2016/17 | Tore gesamt – Über | 32 | 12,5 % | 12,7 % | -30,4 % |
| 2017/18 | Doppelte Chance | 59 | 10,2 % | 12,6 % | -42,2 % |
| 2017/18 | Tore Mannschaft – Über | 57 | 17,5 % | 12,9 % | -3,1 % |
| 2017/18 | Tore gesamt – Über | 56 | 8,9 % | 12,4 % | -47,9 % |
| 2018/19 | Doppelte Chance | 58 | 15,5 % | 12,6 % | -10,8 % |
| 2018/19 | Tore Mannschaft – Über | 62 | 16,1 % | 13,1 % | -5,9 % |
| 2018/19 | Tore gesamt – Über | 53 | 11,3 % | 12,1 % | -36,5 % |
| 2019/20 | Doppelte Chance | 58 | 10,3 % | 13,0 % | -41,9 % |
| 2019/20 | Tore Mannschaft – Über | 55 | 10,9 % | 12,9 % | -39,3 % |
| 2019/20 | Tore gesamt – Über | 55 | 12,7 % | 12,2 % | -23,6 % |
| 2020/21 | Doppelte Chance | 60 | 16,7 % | 13,2 % | -12,3 % |
| 2020/21 | Tore Mannschaft – Über | 55 | 14,5 % | 12,8 % | -20,7 % |
| 2020/21 | Tore gesamt – Über | 58 | 17,2 % | 12,1 % | -2,1 % |
| 2021/22 | Doppelte Chance | 58 | 10,3 % | 13,3 % | -45,1 % |
| 2021/22 | Tore Mannschaft – Über | 56 | 12,5 % | 12,9 % | -33,0 % |
| 2021/22 | Tore gesamt – Über | 58 | 15,5 % | 12,3 % | -13,4 % |
| 2022/23 | Doppelte Chance | 60 | 5,0 % | 13,0 % | -73,1 % |
| 2022/23 | Tore Mannschaft – Über | 59 | 11,9 % | 12,9 % | -33,9 % |
| 2022/23 | Tore gesamt – Über | 62 | 14,5 % | 12,6 % | -21,0 % |
| 2023/24 | Doppelte Chance | 44 | 2,3 % | 12,5 % | -87,1 % |
| 2023/24 | Tore Mannschaft – Über | 65 | 16,9 % | 13,2 % | -7,0 % |
| 2023/24 | Tore gesamt – Über | 65 | 23,1 % | 12,6 % | 28,3 % |
| 2024/25 | Doppelte Chance | 55 | 10,9 % | 13,0 % | -37,5 % |
| 2024/25 | Tore Mannschaft – Über | 60 | 5,0 % | 12,9 % | -73,3 % |
| 2024/25 | Tore gesamt – Über | 64 | 17,2 % | 12,5 % | -0,6 % |
| 2025/26 | Doppelte Chance | 78 | 23,1 % | 12,5 % | 26,7 % |
| 2025/26 | Tore Mannschaft – Über | 81 | 17,3 % | 12,8 % | -5,2 % |
| 2025/26 | Tore gesamt – Über | 88 | 14,8 % | 12,3 % | -14,8 % |
| 2026/27 | Doppelte Chance | 21 | 4,8 % | 12,8 % | -75,0 % |
| 2026/27 | Tore Mannschaft – Über | 26 | 15,4 % | 12,8 % | -14,3 % |
| 2026/27 | Tore gesamt – Über | 25 | 0,0 % | 12,7 % | -100,0 % |

## Wie knapp war es? (Standard)

| Kombi | alle Tipps richtig | einer daneben | zwei oder mehr daneben |
|---|---:|---:|---:|
| Doppelte Chance | 11,8 % | 29,4 % | 58,8 % |
| Tore Mannschaft – Über | 13,6 % | 32,8 % | 53,6 % |
| Tore gesamt – Über | 14,4 % | 33,9 % | 51,6 % |

## Bewertung

- Tage mit Kombi: 690 von 1275 – an Tagen mit wenigen Spielen wird die Zielquote nicht erreicht, dann gibt es keine Kombi.
- Eine Kombi mit Quote 5–10 gewinnt erwartungsgemäß nur in rund 10–20 % der Fälle; längere Serien ohne Gewinn sind normal. Einsatz pro Kombi daher klein halten.
- Weniger, dafür riskantere Tipps verlieren weniger an Marge; sehr sichere Tipps brauchen viele Beine und kosten mehr Marge – die Varianten oben zeigen den Effekt.
- Ob sich das Spielen lohnt, entscheidet die echte Betano-Quote: im Wett-Tracking die tatsächliche Quote eintragen und Rendite gegen die Modell-Erwartung vergleichen.

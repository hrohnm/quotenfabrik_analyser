# 16 – Tageskombis: Erfolgschance im Backtest

Automatisch erzeugt von `qf combos report` am 20.10.2026 10:09 UTC. Wettbewerbe: Bundesliga, 2. Bundesliga, UEFA Champions League, UEFA Europa League, UEFA Europa Conference League; 1275 Spieltage mit rückwirkenden Prognosen (Walk-Forward, kein Data Leakage).

**Regeln:** Pro Tag bis zu drei Kombis – Tore gesamt Über, Tore einer Mannschaft Über, Doppelte Chance – über alle Spiele des Tages. Je Spiel und Art zählt der stärkste Tipp (Wahrscheinlichkeit plus Abweichung vom Ligaschnitt); die Kombis wählen abwechselnd, Spiele ohne Kombi werden bevorzugt. Aufgefüllt wird bis zur Zielquote 5–10. Die Quote je Tipp ist geschätzt: faire Quote × (1 − 5,0 % Marge); Tipps unter 1,20 werden ausgelassen. Gewonnen ist eine Kombi nur, wenn alle Tipps sitzen (nach 90 Minuten).

**Wichtig:** Auch bei perfekten Wahrscheinlichkeiten zahlt jeder Tipp die Buchmacher-Marge. Erwartete Rendite einer Kombi aus n Tipps ohne eigenen Vorteil: (1 − Marge)ⁿ − 1, bei 5 % Marge und 7 Tipps also ≈ −30 %. Gewinn entsteht nur, wenn das Modell die Wahrscheinlichkeiten besser kennt als der Buchmacher.

## Ergebnis je Variante

| Variante | Kombi | Kombis | getroffen | Modell erwartet | Ø Quote | Ø Tipps | Rendite |
|---|---|---:|---:|---:|---:|---:|---:|
| sicherere Tipps (65–90 %) | Tore gesamt – Über | 89 | 12,4 % | 13,0 % | 5,70 | 6,4 | -29,6 % |
| sicherere Tipps (65–90 %) | Tore Mannschaft – Über | 352 | 11,4 % | 12,8 % | 5,69 | 6,6 | -34,5 % |
| sicherere Tipps (65–90 %) | Doppelte Chance | 398 | 10,6 % | 12,7 % | 5,69 | 6,7 | -40,9 % |
| Standard (55–85 %) | Tore gesamt – Über | 599 | 13,0 % | 12,5 % | 6,15 | 5,5 | -21,2 % |
| Standard (55–85 %) | Tore Mannschaft – Über | 605 | 14,2 % | 12,9 % | 5,87 | 5,8 | -16,8 % |
| Standard (55–85 %) | Doppelte Chance | 552 | 12,5 % | 13,2 % | 5,64 | 6,2 | -30,0 % |
| Standard ohne Mindestquote je Tipp | Tore gesamt – Über | 616 | 14,4 % | 12,4 % | 5,76 | 6,8 | -18,1 % |
| Standard ohne Mindestquote je Tipp | Tore Mannschaft – Über | 610 | 13,6 % | 13,0 % | 5,56 | 6,6 | -24,7 % |
| Standard ohne Mindestquote je Tipp | Doppelte Chance | 577 | 11,8 % | 13,0 % | 5,58 | 6,7 | -34,7 % |
| riskantere Tipps (45–75 %) | Tore gesamt – Über | 852 | 13,6 % | 13,1 % | 6,30 | 4,3 | -16,7 % |
| riskantere Tipps (45–75 %) | Tore Mannschaft – Über | 837 | 12,7 % | 13,2 % | 6,18 | 4,4 | -24,3 % |
| riskantere Tipps (45–75 %) | Doppelte Chance | 710 | 12,1 % | 13,7 % | 5,84 | 4,9 | -30,0 % |

Getroffen > erwartet heißt: das Modell war bei diesen Tipps eher zu vorsichtig. Die Rendite ist mit der geschätzten Quote gerechnet, für Spiele mit OddsPapi-Verlauf (seit Januar 2026) mit der echten Betano-Schlussquote.

## Standard je Saison

| Saison | Kombi | Kombis | getroffen | Modell erwartet | Rendite |
|---|---|---:|---:|---:|---:|
| 2016/17 | Doppelte Chance | 20 | 10,0 % | 13,5 % | -46,7 % |
| 2016/17 | Tore Mannschaft – Über | 33 | 9,1 % | 13,1 % | -41,1 % |
| 2016/17 | Tore gesamt – Über | 31 | 6,5 % | 12,6 % | -62,8 % |
| 2017/18 | Doppelte Chance | 56 | 7,1 % | 13,0 % | -56,7 % |
| 2017/18 | Tore Mannschaft – Über | 57 | 15,8 % | 13,0 % | -7,8 % |
| 2017/18 | Tore gesamt – Über | 56 | 8,9 % | 12,4 % | -46,1 % |
| 2018/19 | Doppelte Chance | 58 | 17,2 % | 13,1 % | -5,9 % |
| 2018/19 | Tore Mannschaft – Über | 62 | 16,1 % | 13,3 % | -7,2 % |
| 2018/19 | Tore gesamt – Über | 53 | 13,2 % | 13,0 % | -26,2 % |
| 2019/20 | Doppelte Chance | 56 | 7,1 % | 13,0 % | -59,1 % |
| 2019/20 | Tore Mannschaft – Über | 55 | 12,7 % | 12,8 % | -25,0 % |
| 2019/20 | Tore gesamt – Über | 54 | 3,7 % | 12,2 % | -73,1 % |
| 2020/21 | Doppelte Chance | 57 | 15,8 % | 13,3 % | -11,4 % |
| 2020/21 | Tore Mannschaft – Über | 55 | 14,5 % | 12,8 % | -14,4 % |
| 2020/21 | Tore gesamt – Über | 53 | 20,8 % | 12,0 % | 34,7 % |
| 2021/22 | Doppelte Chance | 57 | 8,8 % | 13,2 % | -51,6 % |
| 2021/22 | Tore Mannschaft – Über | 55 | 16,4 % | 12,5 % | -5,3 % |
| 2021/22 | Tore gesamt – Über | 56 | 12,5 % | 12,4 % | -26,9 % |
| 2022/23 | Doppelte Chance | 55 | 12,7 % | 12,8 % | -28,8 % |
| 2022/23 | Tore Mannschaft – Über | 59 | 11,9 % | 13,3 % | -32,6 % |
| 2022/23 | Tore gesamt – Über | 61 | 18,0 % | 12,4 % | 8,6 % |
| 2023/24 | Doppelte Chance | 44 | 6,8 % | 12,5 % | -59,1 % |
| 2023/24 | Tore Mannschaft – Über | 64 | 15,6 % | 13,0 % | -8,9 % |
| 2023/24 | Tore gesamt – Über | 62 | 19,4 % | 12,7 % | 18,0 % |
| 2024/25 | Doppelte Chance | 52 | 11,5 % | 13,2 % | -38,9 % |
| 2024/25 | Tore Mannschaft – Über | 59 | 6,8 % | 12,6 % | -57,2 % |
| 2024/25 | Tore gesamt – Über | 62 | 16,1 % | 12,5 % | -8,3 % |
| 2025/26 | Doppelte Chance | 76 | 23,7 % | 13,5 % | 34,2 % |
| 2025/26 | Tore Mannschaft – Über | 80 | 15,0 % | 12,8 % | -13,3 % |
| 2025/26 | Tore gesamt – Über | 87 | 10,3 % | 12,5 % | -35,8 % |
| 2026/27 | Doppelte Chance | 21 | 4,8 % | 15,4 % | -75,9 % |
| 2026/27 | Tore Mannschaft – Über | 26 | 26,9 % | 13,2 % | 57,0 % |
| 2026/27 | Tore gesamt – Über | 24 | 8,3 % | 13,1 % | -47,9 % |

## Wie knapp war es? (Standard)

| Kombi | alle Tipps richtig | einer daneben | zwei oder mehr daneben |
|---|---:|---:|---:|
| Doppelte Chance | 12,5 % | 29,3 % | 58,2 % |
| Tore Mannschaft – Über | 14,2 % | 35,0 % | 50,7 % |
| Tore gesamt – Über | 13,0 % | 34,9 % | 52,1 % |

## Mit echten Betano-Quoten

Spieltage mit Betano-Verlauf (OddsPapi, seit Januar 2026): 40. Quote = letzte Betano-Quote vor Anpfiff. „Nur Value-Tipps“ nimmt nur Tipps, bei denen Modell-Wahrscheinlichkeit × Betano-Quote über 1 + Mindestvorteil liegt.

| Variante | Kombi | Kombis | getroffen | Modell erwartet | Ø Quote | Ø Tipps | Rendite |
|---|---|---:|---:|---:|---:|---:|---:|
| Standard, alle Tipps mit Betano-Quote | Tore gesamt – Über | 21 | 14,3 % | 13,3 % | 6,04 | 5,6 | -8,8 % |
| Standard, alle Tipps mit Betano-Quote | Tore Mannschaft – Über | 22 | 13,6 % | 12,8 % | 6,25 | 5,9 | -7,4 % |
| Standard, alle Tipps mit Betano-Quote | Doppelte Chance | 23 | 8,7 % | 16,7 % | 5,83 | 5,7 | -48,0 % |
| nur Value-Tipps (Vorteil ≥ 0 %) | Tore gesamt – Über | 1 | 100,0 % | 15,2 % | 7,45 | 5,0 | 644,7 % |
| nur Value-Tipps (Vorteil ≥ 0 %) | Tore Mannschaft – Über | 6 | 16,7 % | 20,5 % | 6,35 | 4,7 | -0,3 % |
| nur Value-Tipps (Vorteil ≥ 0 %) | Doppelte Chance | 16 | 25,0 % | 22,6 % | 6,53 | 3,6 | 50,7 % |
| nur Value-Tipps (Vorteil ≥ 5 %) | Tore Mannschaft – Über | 1 | 0,0 % | 24,0 % | 6,43 | 4,0 | -100,0 % |
| nur Value-Tipps (Vorteil ≥ 5 %) | Doppelte Chance | 13 | 38,5 % | 25,4 % | 6,68 | 3,2 | 145,7 % |

Wenige Kombis: die Rendite schwankt hier stark und ist noch kein Beleg für einen Vorteil.

## Bewertung

- Tage mit Kombi: 690 von 1275 – an Tagen mit wenigen Spielen wird die Zielquote nicht erreicht, dann gibt es keine Kombi.
- Eine Kombi mit Quote 5–10 gewinnt erwartungsgemäß nur in rund 10–20 % der Fälle; längere Serien ohne Gewinn sind normal. Einsatz pro Kombi daher klein halten.
- Weniger, dafür riskantere Tipps verlieren weniger an Marge; sehr sichere Tipps brauchen viele Beine und kosten mehr Marge – die Varianten oben zeigen den Effekt.
- Ob sich das Spielen lohnt, entscheidet die echte Betano-Quote: im Wett-Tracking die tatsächliche Quote eintragen und Rendite gegen die Modell-Erwartung vergleichen.

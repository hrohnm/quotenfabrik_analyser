# 09 – Modell-Evaluation (Phase 2, ohne Quoten) · 2. Bundesliga

Automatisch erzeugt von `qf model evaluate` am 19.10.2026 15:24 UTC (Modell `dc-v1`, Lauf `analytics.model_runs.id = 14`).

**Testzeitraum:** Saisons 2022/23, 2023/24, 2024/25, 2025/26, 2026/27 – 1296 Spiele, Walk-Forward je Spieltag (Training nur mit Spielen vor dem Spieltag).

**Vergleichswerte:** *Liga* = Häufigkeit des Ereignisses in den letzten 3 Saisons; *Form* = letzte 10 Heimspiele des Heimteams und letzte 10 Auswärtsspiele des Gastteams (geschrumpft zum Ligaschnitt).

**Kennzahlen:** Brier-Score (mittlerer quadratischer Fehler der Wahrscheinlichkeit, kleiner = besser), *Skill* = relative Verbesserung des Brier-Scores gegenüber dem Vergleichswert, *ECE* = mittlerer Kalibrierungsfehler (|vorhergesagt − eingetreten| über 10 Klassen).

**Parameter:** Zeitgewichtung ξ = 0.0015/Tag, Regularisierung 10.0 (Halbzeiten 25.0), Fenster 1095 Tage, Aufsteiger-Prior -0.3/-0.3; Torschützen: Shrinkage 15.0 × 90 Min., Team-Faktor-Exponent 0.6.

## Überblick

| Markt | Modell | Liga | Form | Bewertung |
|---|---|---|---|---|
| 1X2 (RPS) | 0.2223 | 0.2294 | 0.2278 | +3.1 % ggü. Liga |
| Halbzeit-Ergebnis (RPS) | 0.2070 | 0.2103 | 0.2104 | +1.6 % ggü. Liga |
| 1. Spielausgang (1X2) (Ø Brier, 5 Auswahlen) | 0.1620 | 0.1665 | 0.1655 | Skill +2.5 % ggü. Liga |
| 2. Über/Unter Tore gesamt (Ø Brier, 7 Auswahlen) | 0.1650 | 0.1638 | 0.1669 | Skill -0.6 % ggü. Liga |
| 3. Über/Unter Tore pro Team (Ø Brier, 9 Auswahlen) | 0.1624 | 0.1642 | 0.1648 | Skill +1.0 % ggü. Liga |
| 4. Über/Unter Tore pro Halbzeit (Ø Brier, 18 Auswahlen) | 0.1876 | 0.1881 | 0.1907 | Skill +0.2 % ggü. Liga |
| 5. Torschützen Anytime (Brier, 45253 Spieler-Einsätze) | 0.06302 | 0.06423 | – | Skill +1.9 % ggü. Positions-Schnitt |

## Saison für Saison (1X2-RPS und Über 2.5-Brier)

| Saison | Spiele | RPS Modell | RPS Liga | RPS Form | Brier Ü2.5 Modell | Brier Ü2.5 Liga |
|---|---|---|---|---|---|---|
| 2022/23 | 306 | 0.2196 | 0.2297 | 0.2270 | 0.2471 | 0.2441 |
| 2023/24 | 306 | 0.2203 | 0.2315 | 0.2268 | 0.2412 | 0.2390 |
| 2024/25 | 306 | 0.2224 | 0.2288 | 0.2307 | 0.2375 | 0.2412 |
| 2025/26 | 306 | 0.2264 | 0.2293 | 0.2285 | 0.2501 | 0.2445 |
| 2026/27 | 72 | 0.2242 | 0.2221 | 0.2209 | 0.2453 | 0.2435 |

## 1. Spielausgang (1X2)

| Markt | Auswahl | Linie | n | Quote eingetreten | Brier Modell | Brier Liga | Brier Form | Skill ggü. Liga | Skill ggü. Form | ECE |
|---|---|---|---|---|---|---|---|---|---|---|
| 1X2 | A |  | 1296 | 30.2 % | 0.2063 | 0.2112 | 0.2097 | +2.3 % | +1.6 % | 1.7 % |
| 1X2 | D |  | 1296 | 25.1 % | 0.1877 | 0.1882 | 0.1939 | +0.3 % | +3.2 % | 0.4 % |
| 1X2 | H |  | 1296 | 44.7 % | 0.2383 | 0.2476 | 0.2460 | +3.8 % | +3.1 % | 4.3 % |
| Europ. Handicap (Heim) | A | -2 | 1296 | 77.2 % | 0.1710 | 0.1760 | 0.1766 | +2.9 % | +3.2 % | 1.5 % |
| Europ. Handicap (Heim) | D | -2 | 1296 | 13.1 % | 0.1137 | 0.1142 | 0.1178 | +0.5 % | +3.5 % | 2.1 % |
| Europ. Handicap (Heim) | H | -2 | 1296 | 9.6 % | 0.0852 | 0.0873 | 0.0864 | +2.4 % | +1.4 % | 0.7 % |
| Europ. Handicap (Heim) | A | -1 | 1296 | 55.3 % | 0.2383 | 0.2476 | 0.2460 | +3.8 % | +3.1 % | 4.3 % |
| Europ. Handicap (Heim) | D | -1 | 1296 | 21.9 % | 0.1707 | 0.1714 | 0.1758 | +0.4 % | +2.9 % | 1.8 % |
| Europ. Handicap (Heim) | H | -1 | 1296 | 22.8 % | 0.1710 | 0.1760 | 0.1766 | +2.9 % | +3.2 % | 1.5 % |
| Europ. Handicap (Heim) | A | 1 | 1296 | 12.6 % | 0.1090 | 0.1102 | 0.1090 | +1.1 % | -0.0 % | 2.4 % |
| Europ. Handicap (Heim) | D | 1 | 1296 | 17.7 % | 0.1448 | 0.1457 | 0.1465 | +0.7 % | +1.2 % | 1.3 % |
| Europ. Handicap (Heim) | H | 1 | 1296 | 69.8 % | 0.2063 | 0.2112 | 0.2097 | +2.3 % | +1.6 % | 1.7 % |
| Europ. Handicap (Heim) | A | 2 | 1296 | 5.8 % | 0.0541 | 0.0546 | 0.0545 | +0.9 % | +0.8 % | 0.7 % |
| Europ. Handicap (Heim) | D | 2 | 1296 | 6.8 % | 0.0637 | 0.0634 | 0.0648 | -0.4 % | +1.7 % | 2.5 % |
| Europ. Handicap (Heim) | H | 2 | 1296 | 87.4 % | 0.1090 | 0.1102 | 0.1090 | +1.1 % | -0.0 % | 2.4 % |

## 2. Über/Unter Tore gesamt

| Markt | Auswahl | Linie | n | Quote eingetreten | Brier Modell | Brier Liga | Brier Form | Skill ggü. Liga | Skill ggü. Form | ECE |
|---|---|---|---|---|---|---|---|---|---|---|
| Beide treffen | yes |  | 1296 | 58.6 % | 0.2445 | 0.2429 | 0.2461 | -0.7 % | +0.6 % | 5.1 % |
| Exakte Toranzahl | 0 |  | 1296 | 5.4 % | 0.0514 | 0.0512 | 0.0524 | -0.3 % | +2.1 % | 0.4 % |
| Exakte Toranzahl | 1 |  | 1296 | 14.5 % | 0.1247 | 0.1244 | 0.1280 | -0.3 % | +2.6 % | 1.2 % |
| Exakte Toranzahl | 2 |  | 1296 | 21.1 % | 0.1672 | 0.1671 | 0.1708 | -0.0 % | +2.1 % | 2.4 % |
| Exakte Toranzahl | 3 |  | 1296 | 24.8 % | 0.1871 | 0.1867 | 0.1936 | -0.2 % | +3.4 % | 3.0 % |
| Exakte Toranzahl | 4 |  | 1296 | 16.6 % | 0.1383 | 0.1386 | 0.1410 | +0.2 % | +1.9 % | 0.3 % |
| Exakte Toranzahl | 5 |  | 1296 | 8.9 % | 0.0817 | 0.0810 | 0.0829 | -0.9 % | +1.4 % | 2.7 % |
| Exakte Toranzahl | 6+ |  | 1296 | 8.7 % | 0.0798 | 0.0799 | 0.0819 | +0.1 % | +2.6 % | 1.1 % |
| Tore gesamt | over | 0.5 | 1296 | 94.6 % | 0.0514 | 0.0512 | 0.0524 | -0.3 % | +2.1 % | 0.4 % |
| Tore gesamt | over | 1.5 | 1296 | 80.1 % | 0.1605 | 0.1596 | 0.1639 | -0.6 % | +2.1 % | 2.4 % |
| Tore gesamt | over | 2.5 | 1296 | 59.0 % | 0.2440 | 0.2423 | 0.2465 | -0.7 % | +1.0 % | 5.0 % |
| Tore gesamt | over | 3.5 | 1296 | 34.2 % | 0.2272 | 0.2254 | 0.2284 | -0.8 % | +0.5 % | 3.2 % |
| Tore gesamt | over | 4.5 | 1296 | 17.6 % | 0.1474 | 0.1452 | 0.1492 | -1.5 % | +1.2 % | 3.3 % |
| Tore gesamt | over | 5.5 | 1296 | 8.7 % | 0.0798 | 0.0799 | 0.0819 | +0.1 % | +2.6 % | 1.1 % |

## 3. Über/Unter Tore pro Team

| Markt | Auswahl | Linie | n | Quote eingetreten | Brier Modell | Brier Liga | Brier Form | Skill ggü. Liga | Skill ggü. Form | ECE |
|---|---|---|---|---|---|---|---|---|---|---|
| Zu null | away |  | 1296 | 19.2 % | 0.1527 | 0.1554 | 0.1550 | +1.8 % | +1.5 % | 1.3 % |
| Zu null | home |  | 1296 | 27.6 % | 0.1983 | 0.2001 | 0.1998 | +0.9 % | +0.8 % | 2.8 % |
| Tore Gastteam | over | 0.5 | 1296 | 72.4 % | 0.1983 | 0.2001 | 0.1998 | +0.9 % | +0.8 % | 2.8 % |
| Tore Gastteam | over | 1.5 | 1296 | 39.4 % | 0.2358 | 0.2392 | 0.2406 | +1.4 % | +2.0 % | 2.7 % |
| Tore Gastteam | over | 2.5 | 1296 | 15.7 % | 0.1327 | 0.1322 | 0.1334 | -0.4 % | +0.5 % | 1.5 % |
| Tore Gastteam | over | 3.5 | 1296 | 5.2 % | 0.0494 | 0.0491 | 0.0501 | -0.7 % | +1.5 % | 0.7 % |
| Tore Heimteam | over | 0.5 | 1296 | 80.8 % | 0.1527 | 0.1554 | 0.1550 | +1.8 % | +1.5 % | 1.3 % |
| Tore Heimteam | over | 1.5 | 1296 | 49.8 % | 0.2484 | 0.2504 | 0.2530 | +0.8 % | +1.8 % | 3.7 % |
| Tore Heimteam | over | 2.5 | 1296 | 22.8 % | 0.1718 | 0.1764 | 0.1754 | +2.6 % | +2.1 % | 1.1 % |
| Tore Heimteam | over | 3.5 | 1296 | 8.2 % | 0.0740 | 0.0753 | 0.0762 | +1.8 % | +2.8 % | 1.0 % |

## 4. Über/Unter Tore pro Halbzeit

| Markt | Auswahl | Linie | n | Quote eingetreten | Brier Modell | Brier Liga | Brier Form | Skill ggü. Liga | Skill ggü. Form | ECE |
|---|---|---|---|---|---|---|---|---|---|---|
| Beide treffen 1. HZ | yes |  | 1296 | 23.0 % | 0.1769 | 0.1774 | 0.1798 | +0.3 % | +1.6 % | 1.0 % |
| Beide treffen 2. HZ | yes |  | 1296 | 30.1 % | 0.2115 | 0.2109 | 0.2145 | -0.3 % | +1.4 % | 2.3 % |
| Torreichste Halbzeit | 1H |  | 1296 | 29.9 % | 0.2107 | 0.2101 | 0.2167 | -0.3 % | +2.8 % | 1.9 % |
| Torreichste Halbzeit | 2H |  | 1296 | 45.5 % | 0.2484 | 0.2482 | 0.2558 | -0.1 % | +2.9 % | 1.8 % |
| Torreichste Halbzeit | equal |  | 1296 | 24.5 % | 0.1852 | 0.1855 | 0.1893 | +0.2 % | +2.2 % | 0.7 % |
| Halbzeit-Ergebnis | A |  | 1296 | 26.6 % | 0.1923 | 0.1956 | 0.1958 | +1.7 % | +1.8 % | 0.4 % |
| Halbzeit-Ergebnis | D |  | 1296 | 39.2 % | 0.2384 | 0.2386 | 0.2424 | +0.1 % | +1.6 % | 0.3 % |
| Halbzeit-Ergebnis | H |  | 1296 | 34.2 % | 0.2216 | 0.2250 | 0.2249 | +1.5 % | +1.4 % | 1.0 % |
| Tore 1. HZ | over | 0.5 | 1296 | 73.5 % | 0.1950 | 0.1951 | 0.1988 | +0.0 % | +1.9 % | 0.9 % |
| Tore 1. HZ | over | 1.5 | 1296 | 39.1 % | 0.2386 | 0.2384 | 0.2424 | -0.1 % | +1.6 % | 2.5 % |
| Tore 1. HZ | over | 2.5 | 1296 | 15.5 % | 0.1318 | 0.1314 | 0.1335 | -0.3 % | +1.3 % | 1.1 % |
| Tore 2. HZ | over | 0.5 | 1296 | 82.4 % | 0.1462 | 0.1451 | 0.1492 | -0.8 % | +2.0 % | 1.7 % |
| Tore 2. HZ | over | 1.5 | 1296 | 49.7 % | 0.2507 | 0.2504 | 0.2554 | -0.1 % | +1.8 % | 3.7 % |
| Tore 2. HZ | over | 2.5 | 1296 | 23.5 % | 0.1808 | 0.1804 | 0.1853 | -0.3 % | +2.4 % | 1.1 % |
| Tore 2. HZ | over | 3.5 | 1296 | 7.4 % | 0.0690 | 0.0687 | 0.0703 | -0.4 % | +1.9 % | 1.6 % |
| Gastteam 1. HZ | over | 0.5 | 1296 | 45.0 % | 0.2452 | 0.2476 | 0.2501 | +1.0 % | +1.9 % | 0.4 % |
| Gastteam 1. HZ | over | 1.5 | 1296 | 13.0 % | 0.1131 | 0.1129 | 0.1145 | -0.1 % | +1.3 % | 0.8 % |
| Gastteam 2. HZ | over | 0.5 | 1296 | 51.6 % | 0.2498 | 0.2502 | 0.2538 | +0.1 % | +1.6 % | 2.6 % |
| Gastteam 2. HZ | over | 1.5 | 1296 | 17.2 % | 0.1414 | 0.1427 | 0.1438 | +0.9 % | +1.6 % | 0.3 % |
| Heimteam 1. HZ | over | 0.5 | 1296 | 51.5 % | 0.2475 | 0.2501 | 0.2500 | +1.0 % | +1.0 % | 1.4 % |
| Heimteam 1. HZ | over | 1.5 | 1296 | 16.9 % | 0.1394 | 0.1405 | 0.1405 | +0.8 % | +0.8 % | 1.8 % |
| Heimteam 2. HZ | over | 0.5 | 1296 | 60.9 % | 0.2376 | 0.2386 | 0.2409 | +0.4 % | +1.4 % | 2.5 % |
| Heimteam 2. HZ | over | 1.5 | 1296 | 23.6 % | 0.1799 | 0.1805 | 0.1848 | +0.3 % | +2.6 % | 1.2 % |

## 5. Torschützen (Anytime, mit bekannter Aufstellung)

45253 Spieler-Einsätze (Feldspieler in Startelf oder auf der Bank), 1039 ohne Vorgeschichte ausgelassen. Vergleichswert: Trefferquote nach Position und Startelf/Bank.

| | Log-Loss | Brier |
|---|---|---|
| Modell | 0.2297 | 0.06302 |
| Positions-Schnitt | 0.2350 | 0.06423 |

Kalibrierung:

| vorhergesagt (Klasse) | n | Ø vorhergesagt | eingetreten |
|---|---|---|---|
| (0.0, 0.02] | 12291 | 0.9 % | 1.3 % |
| (0.02, 0.05] | 11304 | 3.5 % | 4.0 % |
| (0.05, 0.1] | 10674 | 7.2 % | 6.5 % |
| (0.1, 0.15] | 3843 | 12.0 % | 10.5 % |
| (0.15, 0.2] | 1930 | 17.6 % | 17.9 % |
| (0.2, 0.3] | 3896 | 24.6 % | 22.3 % |
| (0.3, 0.4] | 1154 | 33.6 % | 32.1 % |
| (0.4, 0.6] | 161 | 43.0 % | 47.8 % |

## Kalibrierung ausgewählter Märkte

**Heimsieg**

| Klasse | n | Ø vorhergesagt | eingetreten |
|---|---|---|---|
| (0.1, 0.2] | 14 | 16.4 % | 28.6 % |
| (0.2, 0.3] | 120 | 26.6 % | 35.8 % |
| (0.3, 0.4] | 340 | 35.6 % | 32.6 % |
| (0.4, 0.5] | 485 | 44.9 % | 48.0 % |
| (0.5, 0.6] | 268 | 54.4 % | 51.5 % |
| (0.6, 0.7] | 58 | 63.2 % | 75.9 % |
| (0.7, 0.8] | 11 | 72.5 % | 54.5 % |

**Über 2.5**

| Klasse | n | Ø vorhergesagt | eingetreten |
|---|---|---|---|
| (0.3, 0.4] | 14 | 37.0 % | 50.0 % |
| (0.4, 0.5] | 166 | 46.8 % | 54.8 % |
| (0.5, 0.6] | 610 | 55.4 % | 59.5 % |
| (0.6, 0.7] | 454 | 63.9 % | 59.0 % |
| (0.7, 0.8] | 49 | 72.5 % | 69.4 % |
| (0.8, 0.9] | 3 | 82.0 % | 33.3 % |

**Beide treffen**

| Klasse | n | Ø vorhergesagt | eingetreten |
|---|---|---|---|
| (0.3, 0.4] | 1 | 39.2 % | 100.0 % |
| (0.4, 0.5] | 65 | 47.3 % | 55.4 % |
| (0.5, 0.6] | 622 | 56.0 % | 59.3 % |
| (0.6, 0.7] | 565 | 63.8 % | 57.0 % |
| (0.7, 0.8] | 42 | 71.9 % | 73.8 % |
| (0.8, 0.9] | 1 | 80.5 % | 0.0 % |

**1. HZ Über 0.5**

| Klasse | n | Ø vorhergesagt | eingetreten |
|---|---|---|---|
| (0.6, 0.7] | 193 | 68.2 % | 71.5 % |
| (0.7, 0.8] | 1089 | 74.1 % | 73.6 % |
| (0.8, 0.9] | 14 | 80.8 % | 85.7 % |

## Pattern-Signale außerhalb der Trainingsdaten

Ein Signal *hoch* bzw. *niedrig* entsteht, wenn die Serie (Wilson-Intervall) deutlich über bzw. unter dem Ligaschnitt liegt. *Eingetreten* = tatsächliche Quote des Zielereignisses in diesen Spielen. *Rest ggü. Modell* = eingetreten minus Modellwahrscheinlichkeit: nahe 0 heißt, das Modell kennt die Information bereits; deutlich ≠ 0 heißt, das Pattern liefert Zusatzinformation.

| Gruppe | Pattern | Signal | n | eingetreten | Liga | Modell | Abstand ggü. Liga | Rest ggü. Modell |
|---|---|---|---|---|---|---|---|---|
| 1x2 | `away_draw_rate` | hoch | 89 | 23.6 % | 25.5 % | 25.5 % | -1.9 % | -2.0 % |
| 1x2 | `away_draw_rate` | niedrig | 58 | 25.9 % | 25.6 % | 25.5 % | +0.3 % | +0.3 % |
| 1x2 | `away_win_rate_away` | hoch | 107 | 39.3 % | 31.2 % | 38.6 % | +8.1 % | +0.7 % |
| 1x2 | `away_win_rate_away` | niedrig | 183 | 27.3 % | 31.0 % | 26.6 % | -3.7 % | +0.7 % |
| 1x2 | `home_draw_rate` | hoch | 115 | 27.8 % | 25.5 % | 25.5 % | +2.3 % | +2.4 % |
| 1x2 | `home_draw_rate` | niedrig | 73 | 24.7 % | 25.2 % | 24.0 % | -0.5 % | +0.6 % |
| 1x2 | `home_win_rate_home` | hoch | 155 | 43.2 % | 43.6 % | 48.5 % | -0.4 % | -5.3 % |
| 1x2 | `home_win_rate_home` | niedrig | 146 | 39.0 % | 43.6 % | 36.4 % | -4.5 % | +2.6 % |
| halves | `combined_o05_1h` | hoch | 106 | 78.3 % | 73.7 % | 75.6 % | +4.6 % | +2.7 % |
| halves | `combined_o05_1h` | niedrig | 95 | 70.5 % | 73.4 % | 71.1 % | -2.9 % | -0.6 % |
| halves | `combined_o15_1h` | hoch | 108 | 38.9 % | 38.6 % | 41.3 % | +0.3 % | -2.4 % |
| halves | `combined_o15_1h` | niedrig | 91 | 33.0 % | 38.5 % | 34.7 % | -5.6 % | -1.7 % |
| halves | `combined_o15_2h` | hoch | 84 | 51.2 % | 50.8 % | 53.4 % | +0.4 % | -2.2 % |
| halves | `combined_o15_2h` | niedrig | 108 | 43.5 % | 50.8 % | 47.2 % | -7.3 % | -3.6 % |
| team_totals | `away_2plus` | hoch | 153 | 49.7 % | 39.5 % | 45.6 % | +10.2 % | +4.1 % |
| team_totals | `away_2plus` | niedrig | 117 | 40.2 % | 40.3 % | 33.6 % | -0.1 % | +6.6 % |
| team_totals | `away_clean_sheet` | hoch | 172 | 25.6 % | 19.8 % | 22.8 % | +5.8 % | +2.8 % |
| team_totals | `away_clean_sheet` | niedrig | 160 | 15.6 % | 19.7 % | 18.3 % | -4.0 % | -2.7 % |
| team_totals | `away_conceded_2plus_away` | hoch | 133 | 53.4 % | 49.1 % | 51.2 % | +4.3 % | +2.1 % |
| team_totals | `away_conceded_2plus_away` | niedrig | 81 | 45.7 % | 49.3 % | 43.6 % | -3.7 % | +2.1 % |
| team_totals | `away_conceded_away` | hoch | 160 | 84.4 % | 80.3 % | 81.7 % | +4.0 % | +2.7 % |
| team_totals | `away_conceded_away` | niedrig | 172 | 74.4 % | 80.2 % | 77.2 % | -5.8 % | -2.8 % |
| team_totals | `away_scored` | hoch | 137 | 76.6 % | 72.2 % | 76.5 % | +4.5 % | +0.1 % |
| team_totals | `away_scored` | niedrig | 187 | 62.6 % | 72.3 % | 69.4 % | -9.7 % | -6.9 % |
| team_totals | `home_2plus` | hoch | 164 | 53.7 % | 49.2 % | 53.6 % | +4.5 % | +0.1 % |
| team_totals | `home_2plus` | niedrig | 110 | 44.5 % | 49.2 % | 39.5 % | -4.7 % | +5.0 % |
| team_totals | `home_clean_sheet` | hoch | 151 | 30.5 % | 27.8 % | 28.6 % | +2.6 % | +1.9 % |
| team_totals | `home_clean_sheet` | niedrig | 97 | 21.6 % | 28.0 % | 22.9 % | -6.4 % | -1.2 % |
| team_totals | `home_conceded_home` | hoch | 97 | 78.4 % | 72.0 % | 77.1 % | +6.4 % | +1.2 % |
| team_totals | `home_conceded_home` | niedrig | 151 | 69.5 % | 72.2 % | 71.4 % | -2.6 % | -1.9 % |
| team_totals | `home_scored` | hoch | 194 | 81.4 % | 80.2 % | 82.7 % | +1.2 % | -1.3 % |
| team_totals | `home_scored` | niedrig | 168 | 73.8 % | 80.2 % | 74.7 % | -6.4 % | -0.9 % |
| totals | `away_o15` | hoch | 133 | 77.4 % | 81.1 % | 82.2 % | -3.6 % | -4.8 % |
| totals | `away_o15` | niedrig | 146 | 85.6 % | 80.9 % | 78.8 % | +4.7 % | +6.8 % |
| totals | `away_o25` | hoch | 156 | 55.1 % | 59.2 % | 59.9 % | -4.1 % | -4.7 % |
| totals | `away_o25` | niedrig | 72 | 66.7 % | 59.0 % | 55.4 % | +7.6 % | +11.3 % |
| totals | `away_o35` | hoch | 124 | 29.8 % | 34.5 % | 37.9 % | -4.6 % | -8.1 % |
| totals | `away_o35` | niedrig | 136 | 33.8 % | 34.4 % | 32.6 % | -0.6 % | +1.2 % |
| totals | `combined_btts` | hoch | 140 | 62.1 % | 58.3 % | 63.3 % | +3.8 % | -1.1 % |
| totals | `combined_btts` | niedrig | 109 | 59.6 % | 58.0 % | 56.9 % | +1.6 % | +2.7 % |
| totals | `combined_o15` | hoch | 111 | 81.1 % | 81.2 % | 83.5 % | -0.1 % | -2.4 % |
| totals | `combined_o15` | niedrig | 99 | 81.8 % | 80.8 % | 77.0 % | +1.0 % | +4.8 % |
| totals | `combined_o25` | hoch | 93 | 66.7 % | 59.2 % | 63.2 % | +7.5 % | +3.5 % |
| totals | `combined_o25` | niedrig | 87 | 57.5 % | 59.0 % | 52.5 % | -1.5 % | +5.0 % |
| totals | `combined_o35` | hoch | 126 | 42.1 % | 34.3 % | 41.8 % | +7.7 % | +0.3 % |
| totals | `combined_o35` | niedrig | 97 | 25.8 % | 34.4 % | 31.5 % | -8.6 % | -5.7 % |
| totals | `home_o15` | hoch | 183 | 81.4 % | 81.1 % | 82.7 % | +0.3 % | -1.3 % |
| totals | `home_o15` | niedrig | 140 | 77.9 % | 80.8 % | 78.0 % | -2.9 % | -0.1 % |
| totals | `home_o25` | hoch | 191 | 62.3 % | 59.3 % | 61.8 % | +3.0 % | +0.5 % |
| totals | `home_o25` | niedrig | 109 | 59.6 % | 59.0 % | 53.2 % | +0.7 % | +6.4 % |
| totals | `home_o35` | hoch | 139 | 43.9 % | 34.5 % | 41.2 % | +9.3 % | +2.6 % |
| totals | `home_o35` | niedrig | 140 | 27.9 % | 34.3 % | 32.5 % | -6.5 % | -4.7 % |

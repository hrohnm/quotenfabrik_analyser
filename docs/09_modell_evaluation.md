# 09 – Modell-Evaluation (Phase 2, ohne Quoten)

Automatisch erzeugt von `qf model evaluate` am 19.10.2026 08:23 UTC (Modell `dc-v1`, Lauf `analytics.model_runs.id = 1`).

**Testzeitraum:** Saisons 2022/23, 2023/24, 2024/25, 2025/26, 2026/27 – 1278 Spiele, Walk-Forward je Spieltag (Training nur mit Spielen vor dem Spieltag).

**Vergleichswerte:** *Liga* = Häufigkeit des Ereignisses in den letzten 3 Saisons; *Form* = letzte 10 Heimspiele des Heimteams und letzte 10 Auswärtsspiele des Gastteams (geschrumpft zum Ligaschnitt).

**Kennzahlen:** Brier-Score (mittlerer quadratischer Fehler der Wahrscheinlichkeit, kleiner = besser), *Skill* = relative Verbesserung des Brier-Scores gegenüber dem Vergleichswert, *ECE* = mittlerer Kalibrierungsfehler (|vorhergesagt − eingetreten| über 10 Klassen).

**Parameter:** Zeitgewichtung ξ = 0.0015/Tag, Regularisierung 10.0 (Halbzeiten 25.0), Fenster 1095 Tage, Aufsteiger-Prior -0.3/-0.3; Torschützen: Shrinkage 15.0 × 90 Min., Team-Faktor-Exponent 0.6.

## Überblick

| Markt | Modell | Liga | Form | Bewertung |
|---|---|---|---|---|
| 1X2 (RPS) | 0.2028 | 0.2311 | 0.2177 | +12.2 % ggü. Liga |
| Halbzeit-Ergebnis (RPS) | 0.2028 | 0.2169 | 0.2083 | +6.5 % ggü. Liga |
| 1. Spielausgang (1X2) (Ø Brier, 5 Auswahlen) | 0.1608 | 0.1811 | 0.1721 | Skill +10.7 % ggü. Liga |
| 2. Über/Unter Tore gesamt (Ø Brier, 7 Auswahlen) | 0.1654 | 0.1682 | 0.1697 | Skill +1.6 % ggü. Liga |
| 3. Über/Unter Tore pro Team (Ø Brier, 9 Auswahlen) | 0.1602 | 0.1718 | 0.1677 | Skill +6.7 % ggü. Liga |
| 4. Über/Unter Tore pro Halbzeit (Ø Brier, 18 Auswahlen) | 0.1875 | 0.1923 | 0.1914 | Skill +2.4 % ggü. Liga |
| 5. Torschützen Anytime (Brier, 44847 Spieler-Einsätze) | 0.06603 | 0.06794 | – | Skill +2.8 % ggü. Positions-Schnitt |

## Saison für Saison (1X2-RPS und Über 2.5-Brier)

| Saison | Spiele | RPS Modell | RPS Liga | RPS Form | Brier Ü2.5 Modell | Brier Ü2.5 Liga |
|---|---|---|---|---|---|---|
| 2022/23 | 306 | 0.2061 | 0.2271 | 0.2189 | 0.2411 | 0.2395 |
| 2023/24 | 306 | 0.1963 | 0.2284 | 0.2085 | 0.2287 | 0.2355 |
| 2024/25 | 306 | 0.2102 | 0.2371 | 0.2250 | 0.2281 | 0.2407 |
| 2025/26 | 306 | 0.1965 | 0.2316 | 0.2190 | 0.2318 | 0.2320 |
| 2026/27 | 54 | 0.2151 | 0.2312 | 0.2150 | 0.2115 | 0.2069 |

## 1. Spielausgang (1X2)

| Markt | Auswahl | Linie | n | Quote eingetreten | Brier Modell | Brier Liga | Brier Form | Skill ggü. Liga | Skill ggü. Form | ECE |
|---|---|---|---|---|---|---|---|---|---|---|
| 1X2 | A |  | 1278 | 31.2 % | 0.1906 | 0.2152 | 0.2025 | +11.5 % | +5.9 % | 2.2 % |
| 1X2 | D |  | 1278 | 25.0 % | 0.1874 | 0.1879 | 0.1929 | +0.3 % | +2.8 % | 1.2 % |
| 1X2 | H |  | 1278 | 43.7 % | 0.2150 | 0.2469 | 0.2329 | +12.9 % | +7.7 % | 2.2 % |
| Europ. Handicap (Heim) | A | -2 | 1278 | 73.2 % | 0.1728 | 0.1971 | 0.1877 | +12.3 % | +8.0 % | 1.4 % |
| Europ. Handicap (Heim) | D | -2 | 1278 | 13.6 % | 0.1144 | 0.1180 | 0.1183 | +3.0 % | +3.3 % | 1.3 % |
| Europ. Handicap (Heim) | H | -2 | 1278 | 13.2 % | 0.1045 | 0.1151 | 0.1106 | +9.1 % | +5.5 % | 1.1 % |
| Europ. Handicap (Heim) | A | -1 | 1278 | 56.3 % | 0.2150 | 0.2469 | 0.2329 | +12.9 % | +7.7 % | 2.2 % |
| Europ. Handicap (Heim) | D | -1 | 1278 | 16.9 % | 0.1395 | 0.1408 | 0.1415 | +1.0 % | +1.4 % | 1.8 % |
| Europ. Handicap (Heim) | H | -1 | 1278 | 26.8 % | 0.1728 | 0.1971 | 0.1877 | +12.3 % | +8.0 % | 1.4 % |
| Europ. Handicap (Heim) | A | 1 | 1278 | 15.5 % | 0.1213 | 0.1313 | 0.1268 | +7.6 % | +4.3 % | 1.6 % |
| Europ. Handicap (Heim) | D | 1 | 1278 | 15.7 % | 0.1292 | 0.1326 | 0.1324 | +2.6 % | +2.4 % | 0.7 % |
| Europ. Handicap (Heim) | H | 1 | 1278 | 68.8 % | 0.1906 | 0.2152 | 0.2025 | +11.5 % | +5.9 % | 2.2 % |
| Europ. Handicap (Heim) | A | 2 | 1278 | 6.9 % | 0.0599 | 0.0643 | 0.0632 | +6.9 % | +5.2 % | 0.9 % |
| Europ. Handicap (Heim) | D | 2 | 1278 | 8.6 % | 0.0774 | 0.0788 | 0.0797 | +1.7 % | +2.9 % | 0.9 % |
| Europ. Handicap (Heim) | H | 2 | 1278 | 84.5 % | 0.1213 | 0.1313 | 0.1268 | +7.6 % | +4.3 % | 1.6 % |

## 2. Über/Unter Tore gesamt

| Markt | Auswahl | Linie | n | Quote eingetreten | Brier Modell | Brier Liga | Brier Form | Skill ggü. Liga | Skill ggü. Form | ECE |
|---|---|---|---|---|---|---|---|---|---|---|
| Beide treffen | yes |  | 1278 | 59.9 % | 0.2383 | 0.2403 | 0.2430 | +0.8 % | +1.9 % | 1.5 % |
| Exakte Toranzahl | 0 |  | 1278 | 5.2 % | 0.0490 | 0.0490 | 0.0491 | +0.2 % | +0.4 % | 0.8 % |
| Exakte Toranzahl | 1 |  | 1278 | 11.3 % | 0.1008 | 0.1008 | 0.1031 | -0.0 % | +2.2 % | 1.3 % |
| Exakte Toranzahl | 2 |  | 1278 | 21.4 % | 0.1668 | 0.1681 | 0.1698 | +0.8 % | +1.8 % | 0.9 % |
| Exakte Toranzahl | 3 |  | 1278 | 20.3 % | 0.1623 | 0.1623 | 0.1673 | -0.0 % | +3.0 % | 1.9 % |
| Exakte Toranzahl | 4 |  | 1278 | 20.0 % | 0.1599 | 0.1599 | 0.1630 | +0.0 % | +1.9 % | 3.0 % |
| Exakte Toranzahl | 5 |  | 1278 | 10.6 % | 0.0945 | 0.0946 | 0.0964 | +0.1 % | +1.9 % | 1.2 % |
| Exakte Toranzahl | 6+ |  | 1278 | 11.3 % | 0.0969 | 0.1003 | 0.1003 | +3.3 % | +3.4 % | 1.0 % |
| Tore gesamt | over | 0.5 | 1278 | 94.8 % | 0.0490 | 0.0490 | 0.0491 | +0.2 % | +0.4 % | 0.8 % |
| Tore gesamt | over | 1.5 | 1278 | 83.5 % | 0.1379 | 0.1381 | 0.1392 | +0.2 % | +1.0 % | 1.6 % |
| Tore gesamt | over | 2.5 | 1278 | 62.1 % | 0.2316 | 0.2357 | 0.2381 | +1.7 % | +2.8 % | 2.5 % |
| Tore gesamt | over | 3.5 | 1278 | 41.8 % | 0.2374 | 0.2433 | 0.2448 | +2.4 % | +3.0 % | 3.8 % |
| Tore gesamt | over | 4.5 | 1278 | 21.8 % | 0.1665 | 0.1708 | 0.1734 | +2.5 % | +4.0 % | 1.7 % |
| Tore gesamt | over | 5.5 | 1278 | 11.3 % | 0.0969 | 0.1003 | 0.1003 | +3.3 % | +3.4 % | 1.0 % |

## 3. Über/Unter Tore pro Team

| Markt | Auswahl | Linie | n | Quote eingetreten | Brier Modell | Brier Liga | Brier Form | Skill ggü. Liga | Skill ggü. Form | ECE |
|---|---|---|---|---|---|---|---|---|---|---|
| Zu null | away |  | 1278 | 19.4 % | 0.1487 | 0.1567 | 0.1511 | +5.1 % | +1.6 % | 0.8 % |
| Zu null | home |  | 1278 | 25.8 % | 0.1814 | 0.1919 | 0.1894 | +5.5 % | +4.2 % | 1.5 % |
| Tore Gastteam | over | 0.5 | 1278 | 74.2 % | 0.1814 | 0.1919 | 0.1894 | +5.5 % | +4.2 % | 1.5 % |
| Tore Gastteam | over | 1.5 | 1278 | 40.6 % | 0.2224 | 0.2414 | 0.2347 | +7.9 % | +5.2 % | 2.0 % |
| Tore Gastteam | over | 2.5 | 1278 | 18.5 % | 0.1395 | 0.1509 | 0.1460 | +7.6 % | +4.5 % | 2.7 % |
| Tore Gastteam | over | 3.5 | 1278 | 6.1 % | 0.0545 | 0.0576 | 0.0577 | +5.2 % | +5.4 % | 1.0 % |
| Tore Heimteam | over | 0.5 | 1278 | 80.6 % | 0.1487 | 0.1567 | 0.1511 | +5.1 % | +1.6 % | 0.8 % |
| Tore Heimteam | over | 1.5 | 1278 | 51.7 % | 0.2324 | 0.2507 | 0.2429 | +7.3 % | +4.3 % | 1.8 % |
| Tore Heimteam | over | 2.5 | 1278 | 27.5 % | 0.1841 | 0.1997 | 0.1943 | +7.8 % | +5.2 % | 2.8 % |
| Tore Heimteam | over | 3.5 | 1278 | 12.0 % | 0.0970 | 0.1056 | 0.1035 | +8.2 % | +6.3 % | 0.7 % |

## 4. Über/Unter Tore pro Halbzeit

| Markt | Auswahl | Linie | n | Quote eingetreten | Brier Modell | Brier Liga | Brier Form | Skill ggü. Liga | Skill ggü. Form | ECE |
|---|---|---|---|---|---|---|---|---|---|---|
| Beide treffen 1. HZ | yes |  | 1278 | 23.9 % | 0.1833 | 0.1824 | 0.1853 | -0.5 % | +1.1 % | 2.8 % |
| Beide treffen 2. HZ | yes |  | 1278 | 31.6 % | 0.2160 | 0.2162 | 0.2193 | +0.1 % | +1.5 % | 2.0 % |
| Torreichste Halbzeit | 1H |  | 1278 | 29.7 % | 0.2118 | 0.2090 | 0.2126 | -1.3 % | +0.4 % | 5.3 % |
| Torreichste Halbzeit | 2H |  | 1278 | 43.0 % | 0.2465 | 0.2460 | 0.2473 | -0.2 % | +0.3 % | 2.8 % |
| Torreichste Halbzeit | equal |  | 1278 | 27.3 % | 0.2001 | 0.1989 | 0.2009 | -0.6 % | +0.4 % | 4.0 % |
| Halbzeit-Ergebnis | A |  | 1278 | 27.7 % | 0.1876 | 0.2008 | 0.1937 | +6.5 % | +3.1 % | 4.3 % |
| Halbzeit-Ergebnis | D |  | 1278 | 35.8 % | 0.2277 | 0.2301 | 0.2293 | +1.0 % | +0.7 % | 1.4 % |
| Halbzeit-Ergebnis | H |  | 1278 | 36.5 % | 0.2179 | 0.2330 | 0.2230 | +6.5 % | +2.3 % | 2.8 % |
| Tore 1. HZ | over | 0.5 | 1278 | 77.5 % | 0.1726 | 0.1749 | 0.1741 | +1.3 % | +0.8 % | 0.9 % |
| Tore 1. HZ | over | 1.5 | 1278 | 44.1 % | 0.2433 | 0.2471 | 0.2492 | +1.5 % | +2.4 % | 1.9 % |
| Tore 1. HZ | over | 2.5 | 1278 | 17.8 % | 0.1456 | 0.1465 | 0.1476 | +0.6 % | +1.3 % | 0.7 % |
| Tore 2. HZ | over | 0.5 | 1278 | 83.8 % | 0.1359 | 0.1360 | 0.1371 | +0.1 % | +0.9 % | 2.5 % |
| Tore 2. HZ | over | 1.5 | 1278 | 53.0 % | 0.2476 | 0.2496 | 0.2515 | +0.8 % | +1.5 % | 2.7 % |
| Tore 2. HZ | over | 2.5 | 1278 | 24.5 % | 0.1833 | 0.1852 | 0.1895 | +1.0 % | +3.3 % | 0.3 % |
| Tore 2. HZ | over | 3.5 | 1278 | 9.8 % | 0.0874 | 0.0883 | 0.0897 | +1.1 % | +2.6 % | 0.7 % |
| Gastteam 1. HZ | over | 0.5 | 1278 | 46.9 % | 0.2399 | 0.2495 | 0.2462 | +3.8 % | +2.6 % | 2.3 % |
| Gastteam 1. HZ | over | 1.5 | 1278 | 14.0 % | 0.1160 | 0.1206 | 0.1196 | +3.8 % | +3.0 % | 1.2 % |
| Gastteam 2. HZ | over | 0.5 | 1278 | 53.8 % | 0.2385 | 0.2490 | 0.2434 | +4.2 % | +2.0 % | 4.9 % |
| Gastteam 2. HZ | over | 1.5 | 1278 | 17.6 % | 0.1414 | 0.1454 | 0.1464 | +2.7 % | +3.4 % | 1.6 % |
| Heimteam 1. HZ | over | 0.5 | 1278 | 54.5 % | 0.2373 | 0.2491 | 0.2431 | +4.7 % | +2.4 % | 2.9 % |
| Heimteam 1. HZ | over | 1.5 | 1278 | 20.7 % | 0.1569 | 0.1648 | 0.1596 | +4.8 % | +1.7 % | 1.3 % |
| Heimteam 2. HZ | over | 0.5 | 1278 | 61.7 % | 0.2309 | 0.2368 | 0.2328 | +2.5 % | +0.8 % | 2.1 % |
| Heimteam 2. HZ | over | 1.5 | 1278 | 25.0 % | 0.1809 | 0.1874 | 0.1873 | +3.5 % | +3.4 % | 1.3 % |

## 5. Torschützen (Anytime, mit bekannter Aufstellung)

44847 Spieler-Einsätze (Feldspieler in Startelf oder auf der Bank), 835 ohne Vorgeschichte ausgelassen. Vergleichswert: Trefferquote nach Position und Startelf/Bank.

| | Log-Loss | Brier |
|---|---|---|
| Modell | 0.2379 | 0.06603 |
| Positions-Schnitt | 0.2462 | 0.06794 |

Kalibrierung:

| vorhergesagt (Klasse) | n | Ø vorhergesagt | eingetreten |
|---|---|---|---|
| (0.0, 0.02] | 12212 | 0.9 % | 1.2 % |
| (0.02, 0.05] | 10801 | 3.4 % | 4.4 % |
| (0.05, 0.1] | 10168 | 7.1 % | 6.6 % |
| (0.1, 0.15] | 4079 | 12.1 % | 11.9 % |
| (0.15, 0.2] | 2086 | 17.4 % | 16.6 % |
| (0.2, 0.3] | 3949 | 24.6 % | 21.8 % |
| (0.3, 0.4] | 1224 | 33.7 % | 32.4 % |
| (0.4, 0.6] | 317 | 46.5 % | 49.5 % |
| (0.6, 1.0] | 11 | 61.5 % | 90.9 % |

## Kalibrierung ausgewählter Märkte

**Heimsieg**

| Klasse | n | Ø vorhergesagt | eingetreten |
|---|---|---|---|
| (-0.001, 0.1] | 7 | 8.5 % | 0.0 % |
| (0.1, 0.2] | 68 | 15.9 % | 14.7 % |
| (0.2, 0.3] | 169 | 25.2 % | 24.9 % |
| (0.3, 0.4] | 282 | 35.4 % | 34.0 % |
| (0.4, 0.5] | 301 | 45.2 % | 40.5 % |
| (0.5, 0.6] | 195 | 54.7 % | 54.9 % |
| (0.6, 0.7] | 159 | 64.7 % | 67.3 % |
| (0.7, 0.8] | 66 | 74.6 % | 77.3 % |
| (0.8, 0.9] | 30 | 84.2 % | 76.7 % |
| (0.9, 1.0] | 1 | 90.0 % | 100.0 % |

**Über 2.5**

| Klasse | n | Ø vorhergesagt | eingetreten |
|---|---|---|---|
| (0.2, 0.3] | 1 | 27.2 % | 100.0 % |
| (0.3, 0.4] | 23 | 36.9 % | 43.5 % |
| (0.4, 0.5] | 141 | 46.3 % | 53.2 % |
| (0.5, 0.6] | 459 | 55.7 % | 59.0 % |
| (0.6, 0.7] | 460 | 64.4 % | 64.3 % |
| (0.7, 0.8] | 164 | 73.8 % | 72.6 % |
| (0.8, 0.9] | 29 | 82.6 % | 72.4 % |
| (0.9, 1.0] | 1 | 90.2 % | 100.0 % |

**Beide treffen**

| Klasse | n | Ø vorhergesagt | eingetreten |
|---|---|---|---|
| (0.3, 0.4] | 1 | 36.4 % | 0.0 % |
| (0.4, 0.5] | 67 | 46.8 % | 59.7 % |
| (0.5, 0.6] | 544 | 55.9 % | 55.9 % |
| (0.6, 0.7] | 606 | 63.9 % | 62.4 % |
| (0.7, 0.8] | 60 | 71.8 % | 73.3 % |

**1. HZ Über 0.5**

| Klasse | n | Ø vorhergesagt | eingetreten |
|---|---|---|---|
| (0.6, 0.7] | 49 | 68.6 % | 71.4 % |
| (0.7, 0.8] | 983 | 75.5 % | 75.7 % |
| (0.8, 0.9] | 246 | 82.5 % | 85.8 % |

## Pattern-Signale außerhalb der Trainingsdaten

Ein Signal *hoch* bzw. *niedrig* entsteht, wenn die Serie (Wilson-Intervall) deutlich über bzw. unter dem Ligaschnitt liegt. *Eingetreten* = tatsächliche Quote des Zielereignisses in diesen Spielen. *Rest ggü. Modell* = eingetreten minus Modellwahrscheinlichkeit: nahe 0 heißt, das Modell kennt die Information bereits; deutlich ≠ 0 heißt, das Pattern liefert Zusatzinformation.

| Gruppe | Pattern | Signal | n | eingetreten | Liga | Modell | Abstand ggü. Liga | Rest ggü. Modell |
|---|---|---|---|---|---|---|---|---|
| 1x2 | `away_draw_rate` | hoch | 103 | 27.2 % | 24.8 % | 24.2 % | +2.4 % | +3.0 % |
| 1x2 | `away_draw_rate` | niedrig | 72 | 23.6 % | 24.6 % | 25.1 % | -1.0 % | -1.5 % |
| 1x2 | `away_win_rate_away` | hoch | 194 | 44.3 % | 30.2 % | 43.9 % | +14.1 % | +0.4 % |
| 1x2 | `away_win_rate_away` | niedrig | 298 | 21.1 % | 30.5 % | 22.3 % | -9.4 % | -1.2 % |
| 1x2 | `home_draw_rate` | hoch | 75 | 22.7 % | 24.9 % | 26.2 % | -2.3 % | -3.5 % |
| 1x2 | `home_draw_rate` | niedrig | 67 | 25.4 % | 24.9 % | 21.6 % | +0.4 % | +3.7 % |
| 1x2 | `home_win_rate_home` | hoch | 222 | 61.7 % | 44.5 % | 62.0 % | +17.2 % | -0.3 % |
| 1x2 | `home_win_rate_home` | niedrig | 239 | 34.7 % | 44.2 % | 35.5 % | -9.5 % | -0.8 % |
| halves | `combined_o05_1h` | hoch | 102 | 85.3 % | 75.8 % | 79.2 % | +9.5 % | +6.1 % |
| halves | `combined_o05_1h` | niedrig | 88 | 76.1 % | 76.6 % | 73.9 % | -0.5 % | +2.3 % |
| halves | `combined_o15_1h` | hoch | 131 | 52.7 % | 43.2 % | 48.4 % | +9.5 % | +4.3 % |
| halves | `combined_o15_1h` | niedrig | 108 | 40.7 % | 43.5 % | 38.7 % | -2.8 % | +2.1 % |
| halves | `combined_o15_2h` | hoch | 115 | 56.5 % | 51.9 % | 56.0 % | +4.6 % | +0.6 % |
| halves | `combined_o15_2h` | niedrig | 121 | 52.1 % | 51.8 % | 46.2 % | +0.3 % | +5.8 % |
| team_totals | `away_2plus` | hoch | 235 | 54.5 % | 39.0 % | 53.0 % | +15.5 % | +1.4 % |
| team_totals | `away_2plus` | niedrig | 172 | 30.2 % | 39.6 % | 31.7 % | -9.4 % | -1.4 % |
| team_totals | `away_clean_sheet` | hoch | 178 | 23.6 % | 19.2 % | 22.9 % | +4.4 % | +0.7 % |
| team_totals | `away_clean_sheet` | niedrig | 188 | 15.4 % | 19.1 % | 16.9 % | -3.7 % | -1.5 % |
| team_totals | `away_conceded_2plus_away` | hoch | 122 | 53.3 % | 50.3 % | 57.7 % | +3.0 % | -4.5 % |
| team_totals | `away_conceded_2plus_away` | niedrig | 159 | 48.4 % | 51.4 % | 44.4 % | -3.0 % | +4.1 % |
| team_totals | `away_conceded_away` | hoch | 188 | 84.6 % | 80.9 % | 83.1 % | +3.7 % | +1.5 % |
| team_totals | `away_conceded_away` | niedrig | 178 | 76.4 % | 80.8 % | 77.1 % | -4.4 % | -0.7 % |
| team_totals | `away_scored` | hoch | 125 | 84.0 % | 73.8 % | 83.4 % | +10.2 % | +0.6 % |
| team_totals | `away_scored` | niedrig | 140 | 65.7 % | 73.8 % | 66.2 % | -8.1 % | -0.4 % |
| team_totals | `home_2plus` | hoch | 232 | 72.0 % | 50.5 % | 65.9 % | +21.5 % | +6.1 % |
| team_totals | `home_2plus` | niedrig | 217 | 38.7 % | 51.3 % | 41.5 % | -12.6 % | -2.8 % |
| team_totals | `home_clean_sheet` | hoch | 156 | 28.8 % | 26.2 % | 31.5 % | +2.7 % | -2.7 % |
| team_totals | `home_clean_sheet` | niedrig | 86 | 16.3 % | 26.2 % | 23.9 % | -9.9 % | -7.6 % |
| team_totals | `home_conceded_home` | hoch | 86 | 83.7 % | 73.8 % | 76.1 % | +9.9 % | +7.6 % |
| team_totals | `home_conceded_home` | niedrig | 156 | 71.2 % | 73.8 % | 68.5 % | -2.7 % | +2.7 % |
| team_totals | `home_scored` | hoch | 257 | 90.7 % | 80.7 % | 86.6 % | +10.0 % | +4.1 % |
| team_totals | `home_scored` | niedrig | 217 | 69.6 % | 80.6 % | 74.2 % | -11.0 % | -4.6 % |
| totals | `away_o15` | hoch | 213 | 83.1 % | 83.6 % | 84.1 % | -0.5 % | -1.0 % |
| totals | `away_o15` | niedrig | 93 | 79.6 % | 83.6 % | 80.0 % | -4.0 % | -0.4 % |
| totals | `away_o25` | hoch | 127 | 70.1 % | 60.5 % | 65.3 % | +9.6 % | +4.8 % |
| totals | `away_o25` | niedrig | 112 | 54.5 % | 61.0 % | 53.5 % | -6.5 % | +1.0 % |
| totals | `away_o35` | hoch | 147 | 46.3 % | 39.8 % | 45.2 % | +6.5 % | +1.1 % |
| totals | `away_o35` | niedrig | 115 | 40.9 % | 40.4 % | 31.5 % | +0.5 % | +9.4 % |
| totals | `combined_btts` | hoch | 76 | 61.8 % | 60.0 % | 63.0 % | +1.8 % | -1.2 % |
| totals | `combined_btts` | niedrig | 67 | 59.7 % | 59.8 % | 54.5 % | -0.1 % | +5.2 % |
| totals | `combined_o15` | hoch | 48 | 89.6 % | 83.7 % | 87.9 % | +5.9 % | +1.7 % |
| totals | `combined_o15` | niedrig | 74 | 75.7 % | 83.8 % | 78.6 % | -8.1 % | -2.9 % |
| totals | `combined_o25` | hoch | 108 | 65.7 % | 60.7 % | 69.3 % | +5.1 % | -3.5 % |
| totals | `combined_o25` | niedrig | 93 | 54.8 % | 60.8 % | 53.1 % | -6.0 % | +1.8 % |
| totals | `combined_o35` | hoch | 124 | 43.5 % | 39.7 % | 48.9 % | +3.8 % | -5.3 % |
| totals | `combined_o35` | niedrig | 84 | 38.1 % | 39.6 % | 30.8 % | -1.5 % | +7.3 % |
| totals | `home_o15` | hoch | 234 | 85.0 % | 83.6 % | 85.4 % | +1.5 % | -0.3 % |
| totals | `home_o15` | niedrig | 90 | 83.3 % | 83.6 % | 79.2 % | -0.3 % | +4.1 % |
| totals | `home_o25` | hoch | 122 | 66.4 % | 60.3 % | 66.7 % | +6.1 % | -0.3 % |
| totals | `home_o25` | niedrig | 138 | 55.8 % | 60.9 % | 55.4 % | -5.1 % | +0.4 % |
| totals | `home_o35` | hoch | 165 | 44.8 % | 39.3 % | 46.3 % | +5.5 % | -1.5 % |
| totals | `home_o35` | niedrig | 130 | 36.9 % | 40.1 % | 31.6 % | -3.1 % | +5.3 % |

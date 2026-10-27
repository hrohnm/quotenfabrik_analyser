# Tippschein: 6 Entscheidungen pro Spiel

_Automatisch erzeugt mit `qf model decisions`. Nicht von Hand bearbeiten._

## Methode

Je Entscheidung (Sieger, Über 1,5, Über 2,5, Beide treffen, Tor 1. HZ, Tor 2. HZ) eine logistische Regression über der Wahrscheinlichkeit des Tor-Modells mit allem, was vor Anpfiff bekannt ist: Pattern der Liga-Historie (direkter Vergleich, Heim-/Auswärtsquoten, Tor- und Halbzeitquoten), Form beider Teams, Spielstil beider Teams (Schüsse, Schüsse aufs Tor, Strafraumanteil, Verwertung, Ballbesitz, Ertrag, Gegentore, Paraden), Termine (Ruhetage, Europapokal davor/danach, Spiele in 14 Tagen) und gemeldete Ausfälle (ab 2021/22). Fehlende Werte werden aufgefüllt und markiert, eine L2-Strafe hält nutzlose Merkmale bei null (Stärke auf den Validierungssaisons 2019, 2020 gewählt).

Walk-forward: jede Saison mit einem Fit auf den Saisons davor, getestet ab 2021/22. **Konfidenz** (0–100) = Rang der Wahrscheinlichkeit der getippten Seite unter allen Spielen derselben Entscheidung (70 = sicherer als 70 % der Spiele). Getippt wird ab der Mindest-Konfidenz (Einstellung, derzeit 50), sonst „kein Tipp“.

## Gewinn durch die Zusatzinformationen (Testsaisons)

| Entscheidung | Spiele | Log-Loss Tor-Modell | Log-Loss mit allem | Gewinn (95 %) | Treffer Tor-Modell | Treffer mit allem |
|---|--:|--:|--:|--:|--:|--:|
| Sieger | 3593 | 1.0093 | 1.0081 | +0.0012 [+0.0001; +0.0023] ✓ | 50,0 % | 50,0 % |
| Über 1,5 Tore | 3593 | 0.4684 | 0.4674 | +0.0010 [-0.0011; +0.0031] | 81,9 % | 81,9 % |
| Über 2,5 Tore | 3593 | 0.6635 | 0.6623 | +0.0012 [-0.0012; +0.0035] | 59,9 % | 60,3 % |
| Beide treffen | 3593 | 0.6743 | 0.6739 | +0.0004 [-0.0006; +0.0013] | 58,8 % | 58,9 % |
| Tor in der 1. Halbzeit | 3593 | 0.5591 | 0.5591 | +0.0001 [-0.0014; +0.0014] | 74,8 % | 74,8 % |
| Tor in der 2. Halbzeit | 3593 | 0.4595 | 0.4580 | +0.0014 [-0.0003; +0.0031] | 82,8 % | 82,8 % |

✓ = Verbesserung belastbar (Intervall über 0).

## Trefferquote nach Mindest-Konfidenz (Testsaisons)

Getippt = Anteil der Spiele mit Tipp. Vergleich = immer das Ergebnis, das in den Vorsaisons am häufigsten war, auf denselben Spielen.

### Sieger

| Mindest-Konfidenz | getippt | Spiele | getroffen | erwartet | Vergleich |
|--:|--:|--:|--:|--:|--:|
| 0 | 100 % | 3593 | 50,0 % | 49,7 % | 44,7 % |
| 30 | 72 % | 2596 | 54,5 % | 53,7 % | 48,1 % |
| 50 | 52 % | 1870 | 58,4 % | 57,3 % | 51,2 % |
| 60 | 42 % | 1520 | 59,9 % | 59,4 % | 53,3 % |
| 70 | 32 % | 1138 | 64,1 % | 62,2 % | 55,8 % |
| 80 | 22 % | 775 | 69,8 % | 65,7 % | 60,9 % |
| 90 | 11 % | 383 | 74,4 % | 71,7 % | 64,0 % |

### Über 1,5 Tore

| Mindest-Konfidenz | getippt | Spiele | getroffen | erwartet | Vergleich |
|--:|--:|--:|--:|--:|--:|
| 0 | 100 % | 3593 | 81,9 % | 82,8 % | 81,9 % |
| 30 | 71 % | 2551 | 84,1 % | 85,2 % | 84,1 % |
| 50 | 52 % | 1862 | 85,1 % | 86,4 % | 85,1 % |
| 60 | 42 % | 1499 | 85,5 % | 87,1 % | 85,5 % |
| 70 | 32 % | 1136 | 86,8 % | 87,9 % | 86,8 % |
| 80 | 21 % | 756 | 86,6 % | 89,0 % | 86,6 % |
| 90 | 10 % | 372 | 89,5 % | 90,7 % | 89,5 % |

### Über 2,5 Tore

| Mindest-Konfidenz | getippt | Spiele | getroffen | erwartet | Vergleich |
|--:|--:|--:|--:|--:|--:|
| 0 | 100 % | 3593 | 60,3 % | 60,7 % | 60,0 % |
| 30 | 73 % | 2610 | 63,0 % | 63,5 % | 62,6 % |
| 50 | 53 % | 1920 | 65,6 % | 65,4 % | 65,3 % |
| 60 | 43 % | 1550 | 66,3 % | 66,6 % | 66,1 % |
| 70 | 32 % | 1163 | 67,6 % | 68,0 % | 67,5 % |
| 80 | 22 % | 779 | 70,0 % | 69,9 % | 70,0 % |
| 90 | 11 % | 390 | 73,1 % | 73,1 % | 73,1 % |

### Beide treffen

| Mindest-Konfidenz | getippt | Spiele | getroffen | erwartet | Vergleich |
|--:|--:|--:|--:|--:|--:|
| 0 | 100 % | 3593 | 58,9 % | 60,0 % | 58,6 % |
| 30 | 68 % | 2458 | 60,8 % | 62,4 % | 60,7 % |
| 50 | 50 % | 1794 | 62,3 % | 63,7 % | 62,5 % |
| 60 | 41 % | 1463 | 63,8 % | 64,4 % | 64,0 % |
| 70 | 31 % | 1122 | 64,4 % | 65,2 % | 64,6 % |
| 80 | 21 % | 765 | 63,7 % | 66,2 % | 63,9 % |
| 90 | 11 % | 384 | 67,4 % | 67,8 % | 68,0 % |

### Tor in der 1. Halbzeit

| Mindest-Konfidenz | getippt | Spiele | getroffen | erwartet | Vergleich |
|--:|--:|--:|--:|--:|--:|
| 0 | 100 % | 3593 | 74,8 % | 75,9 % | 74,8 % |
| 30 | 75 % | 2696 | 76,2 % | 77,6 % | 76,2 % |
| 50 | 56 % | 2001 | 78,1 % | 78,8 % | 78,1 % |
| 60 | 45 % | 1624 | 78,9 % | 79,5 % | 78,9 % |
| 70 | 35 % | 1240 | 80,6 % | 80,4 % | 80,6 % |
| 80 | 23 % | 822 | 81,5 % | 81,6 % | 81,5 % |
| 90 | 11 % | 411 | 85,4 % | 83,5 % | 85,4 % |

### Tor in der 2. Halbzeit

| Mindest-Konfidenz | getippt | Spiele | getroffen | erwartet | Vergleich |
|--:|--:|--:|--:|--:|--:|
| 0 | 100 % | 3593 | 82,8 % | 82,9 % | 82,8 % |
| 30 | 70 % | 2520 | 83,5 % | 84,4 % | 83,5 % |
| 50 | 49 % | 1778 | 83,8 % | 85,4 % | 83,8 % |
| 60 | 39 % | 1408 | 84,6 % | 85,9 % | 84,6 % |
| 70 | 29 % | 1035 | 85,1 % | 86,5 % | 85,1 % |
| 80 | 19 % | 670 | 86,4 % | 87,3 % | 86,4 % |
| 90 | 9 % | 319 | 88,1 % | 88,7 % | 88,1 % |

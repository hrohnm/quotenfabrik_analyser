# 20 – Kalibrierung der Prognosen

Automatisch erzeugt von `qf model calibration-eval` am 21.10.2026 11:32 UTC.

**Verfahren:** Je Markt und Linie eine logistische Nachkorrektur p' = σ(a + b · logit p), gelernt aus den abgerechneten rückwirkenden Prognosen **früherer Saisons** (jede Saison wird nur mit den Saisons davor kalibriert, mindestens 300 Prognosen je Markt, zur Identität gezogen). Über/Unter ergeben weiter 100 %, 1X2 ebenso; Doppelte Chance und Draw No Bet folgen aus dem korrigierten 1X2. Torschützen bleiben unverändert.

**Kennzahlen** (kleiner = besser): Log-Loss, Brier-Score und ECE (mittlerer Kalibrierungsfehler: Abstand zwischen vorhergesagter und eingetretener Quote über 10 Klassen). Δ = Log-Loss kalibriert − roh je Spiel, mit 95-%-Bootstrap-Intervall über Spiele.

## Bundesliga (Testsaisons 2018/19–2026/27)

| Marktgruppe | Prognosen | Log-Loss roh | kalibriert | Δ (95 %) | Brier roh | kalibriert | ECE roh | kalibriert |
|---|---:|---:|---:|---|---:|---:|---:|---:|
| Spielausgang (1X2, DC, DNB, Handicap) | 37530 | 0,4603 | 0,4607 | +0,0004 (−0,0002 … +0,0011) | 0,1483 | 0,1485 | 0,20 % | 0,31 % |
| Halbzeiten | 106356 | 0,5593 | 0,5595 | +0,0003 (−0,0001 … +0,0007) | 0,1889 | 0,1890 | 0,47 % | 0,17 % |
| Tore pro Team | 45036 | 0,4800 | 0,4806 | +0,0006 (+0,0002 … +0,0011) ✗ | 0,1573 | 0,1575 | 0,66 % | 0,45 % |
| Tore gesamt | 52542 | 0,4597 | 0,4599 | +0,0002 (−0,0003 … +0,0008) | 0,1482 | 0,1483 | 0,42 % | 0,29 % |

**Heimsieg** – vorhergesagt roh / kalibriert gegen eingetreten

| Klasse (roh) | n | roh | kalibriert | eingetreten |
|---|---:|---:|---:|---:|
| (0.0, 0.1] | 11 | 8,0 % | 7,1 % | 9,1 % |
| (0.1, 0.2] | 139 | 15,6 % | 14,6 % | 15,1 % |
| (0.2, 0.3] | 357 | 25,5 % | 24,8 % | 24,4 % |
| (0.3, 0.4] | 573 | 35,3 % | 35,2 % | 33,5 % |
| (0.4, 0.5] | 560 | 45,0 % | 45,6 % | 42,3 % |
| (0.5, 0.6] | 443 | 54,7 % | 55,8 % | 54,9 % |
| (0.6, 0.7] | 256 | 64,6 % | 66,0 % | 73,4 % |
| (0.7, 0.8] | 120 | 74,4 % | 75,7 % | 72,5 % |
| (0.8, 0.9] | 42 | 83,6 % | 84,6 % | 83,3 % |
| (0.9, 1.0] | 1 | 91,7 % | 92,4 % | 100,0 % |

**Über 2,5** – vorhergesagt roh / kalibriert gegen eingetreten

| Klasse (roh) | n | roh | kalibriert | eingetreten |
|---|---:|---:|---:|---:|
| (0.3, 0.4] | 5 | 38,0 % | 41,8 % | 40,0 % |
| (0.4, 0.5] | 247 | 47,2 % | 49,4 % | 52,2 % |
| (0.5, 0.6] | 1090 | 55,5 % | 56,9 % | 57,4 % |
| (0.6, 0.7] | 914 | 64,3 % | 64,3 % | 65,4 % |
| (0.7, 0.8] | 224 | 73,7 % | 72,6 % | 75,4 % |
| (0.8, 0.9] | 22 | 82,0 % | 80,3 % | 86,4 % |

**Beide treffen** – vorhergesagt roh / kalibriert gegen eingetreten

| Klasse (roh) | n | roh | kalibriert | eingetreten |
|---|---:|---:|---:|---:|
| (0.4, 0.5] | 53 | 48,1 % | 49,4 % | 58,5 % |
| (0.5, 0.6] | 1283 | 56,3 % | 56,5 % | 56,0 % |
| (0.6, 0.7] | 1122 | 63,6 % | 63,0 % | 63,5 % |
| (0.7, 0.8] | 44 | 71,3 % | 69,7 % | 75,0 % |

## 2. Bundesliga (Testsaisons 2018/19–2026/27)

| Marktgruppe | Prognosen | Log-Loss roh | kalibriert | Δ (95 %) | Brier roh | kalibriert | ECE roh | kalibriert |
|---|---:|---:|---:|---|---:|---:|---:|---:|
| Spielausgang (1X2, DC, DNB, Handicap) | 37800 | 0,4692 | 0,4695 | +0,0003 (−0,0002 … +0,0008) | 0,1511 | 0,1512 | 0,43 % | 0,50 % |
| Halbzeiten | 107022 | 0,5672 | 0,5672 | −0,0000 (−0,0005 … +0,0005) | 0,1923 | 0,1923 | 0,52 % | 0,26 % |
| Tore pro Team | 45360 | 0,4861 | 0,4860 | −0,0002 (−0,0008 … +0,0004) | 0,1592 | 0,1592 | 0,54 % | 0,49 % |
| Tore gesamt | 52920 | 0,4615 | 0,4607 | −0,0008 (−0,0016 … −0,0001) ✓ | 0,1486 | 0,1483 | 0,28 % | 0,23 % |

**Heimsieg** – vorhergesagt roh / kalibriert gegen eingetreten

| Klasse (roh) | n | roh | kalibriert | eingetreten |
|---|---:|---:|---:|---:|
| (0.1, 0.2] | 14 | 17,6 % | 19,1 % | 21,4 % |
| (0.2, 0.3] | 205 | 26,6 % | 27,5 % | 26,8 % |
| (0.3, 0.4] | 758 | 35,7 % | 35,5 % | 35,9 % |
| (0.4, 0.5] | 935 | 44,9 % | 43,8 % | 44,7 % |
| (0.5, 0.6] | 494 | 54,1 % | 52,3 % | 53,4 % |
| (0.6, 0.7] | 102 | 63,0 % | 60,7 % | 73,5 % |
| (0.7, 0.8] | 12 | 72,7 % | 70,6 % | 41,7 % |

**Über 2,5** – vorhergesagt roh / kalibriert gegen eingetreten

| Klasse (roh) | n | roh | kalibriert | eingetreten |
|---|---:|---:|---:|---:|
| (0.3, 0.4] | 26 | 37,9 % | 42,7 % | 65,4 % |
| (0.4, 0.5] | 422 | 46,8 % | 50,8 % | 56,2 % |
| (0.5, 0.6] | 1386 | 55,3 % | 57,2 % | 57,1 % |
| (0.6, 0.7] | 657 | 63,4 % | 62,7 % | 61,9 % |
| (0.7, 0.8] | 28 | 71,6 % | 69,3 % | 60,7 % |
| (0.8, 0.9] | 1 | 80,3 % | 72,6 % | 100,0 % |

**Beide treffen** – vorhergesagt roh / kalibriert gegen eingetreten

| Klasse (roh) | n | roh | kalibriert | eingetreten |
|---|---:|---:|---:|---:|
| (0.4, 0.5] | 103 | 47,6 % | 51,5 % | 57,3 % |
| (0.5, 0.6] | 1406 | 56,1 % | 58,1 % | 57,2 % |
| (0.6, 0.7] | 991 | 63,3 % | 63,0 % | 60,2 % |
| (0.7, 0.8] | 20 | 71,6 % | 69,5 % | 60,0 % |

✓ = signifikant besser, ✗ = signifikant schlechter.

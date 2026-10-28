# Value-Tipps

_Automatisch erzeugt mit `qf value tips`. Nicht von Hand bearbeiten._

## Methode

Kandidaten sind die üblichen Märkte (1X2, Doppelte Chance, Tore, Team-Tore, Halbzeiten, Beide treffen, Zu null; nur x,5-Linien). Unsere Wahrscheinlichkeit: Tippschein-Entscheidungsmodell, wo es den Markt abdeckt, sonst das Tor-Modell. Weil Pinnacle ohne Marge auf diesen Spielen genauer ist als unser Modell (Log-Loss 0,6109 gegen 0,6169), wird gemischt: 25 % Modell, Rest Pinnacle (Mischung 0,6112). Value-Tipp = Wahrscheinlichkeit × Betano-Quote − 1 ≥ 2 %, Wahrscheinlichkeit ≥ 30 %, Quote ≤ 4, höchstens 2 je Spiel.

Backtest: Betano- und Pinnacle-Preis zu dem Zeitpunkt, an dem der Tipp gezeigt worden wäre (fixierter Tag, sonst Prognose; Backtest: erster Anpfiff des Spieltags), abgerechnet zu diesem Preis; CLV gegen den Schlusspreis. ROI-Intervall per Bootstrap über Spiele.

Datenbasis: 7212 Auswahlen aus 180 Spielen mit Betano-Verlauf (2026-04-11 bis 2026-10-25).

## Ergebnis

| | Tipps | Ø Quote | Treffer | erwartet | ROI [95 %] | CLV | Quote fiel danach |
|---|--:|--:|--:|--:|--:|--:|--:|
| Backtest (aktuelle Einstellungen) | 40 | 2,24 | 52,5 % | 49,6 % | +10,4 % [-27 %; +48 %] | +0,5 % | 57 % |
| Live (fixierte Value-Tipps) | 0 | – | – | – | – | – | – |

**Einordnung:** Ein Intervall, das 0 einschließt, ist kein Nachweis. Aussagekräftiger ist der CLV: liegt er über 0, waren die Quoten besser als der faire Schlusspreis.

## Je Marktgruppe (Backtest)

| | Tipps | Ø Quote | Treffer | erwartet | ROI [95 %] | CLV | Quote fiel danach |
|---|--:|--:|--:|--:|--:|--:|--:|
| Spielausgang | 12 | 2,53 | 41,7 % | 42,0 % | +8,2 % [-61 %; +78 %] | -0,2 % | 42 % |
| Halbzeiten | 18 | 2,35 | 50,0 % | 47,4 % | +6,7 % [-46 %; +55 %] | -1,3 % | 50 % |
| Tore pro Team | 6 | 1,71 | 66,7 % | 62,6 % | +16,3 % [-71 %; +79 %] | +5,5 % | 83 % |
| Tore gesamt | 4 | 1,67 | 75,0 % | 62,4 % | +24,8 % [-59 %; +70 %] | +2,6 % | 100 % |

## Gewicht des Modells × Mindest-Vorteil (Backtest)

| Gewicht / Vorteil | Tipps | Ø Quote | Treffer | erwartet | ROI [95 %] | CLV | Quote fiel danach |
|---|--:|--:|--:|--:|--:|--:|--:|
| 0 % / 0 % | 36 | 1,75 | 66,7 % | 61,6 % | +7,6 % [-24 %; +36 %] | +1,4 % | 58 % |
| 0 % / 2 % | 8 | 2,06 | 50,0 % | 54,5 % | -8,1 % [-79 %; +59 %] | +5,2 % | 62 % |
| 0 % / 4 % | 2 | 2,61 | 0,0 % | 44,1 % | -100,0 % [-100 %; -100 %] | +6,9 % | 50 % |
| 0 % / 6 % | 0 | – | – | – | – | – | – |
| 0 % / 10 % | 0 | – | – | – | – | – | – |
| 25 % / 0 % | 112 | 2,09 | 56,2 % | 52,9 % | +5,7 % [-15 %; +25 %] | -2,2 % | 55 % |
| 25 % / 2 % | 40 | 2,24 | 52,5 % | 49,6 % | +10,4 % [-27 %; +48 %] | +0,5 % | 57 % |
| 25 % / 4 % | 13 | 2,23 | 61,5 % | 50,4 % | +32,2 % [-37 %; +93 %] | +0,3 % | 31 % |
| 25 % / 6 % | 2 | 2,59 | 0,0 % | 42,4 % | -100,0 % [-100 %; -100 %] | -3,6 % | 0 % |
| 25 % / 10 % | 0 | – | – | – | – | – | – |
| 50 % / 0 % | 266 | 2,20 | 48,5 % | 50,6 % | -0,1 % [-15 %; +14 %] | -3,7 % | 53 % |
| 50 % / 2 % | 172 | 2,33 | 44,8 % | 48,5 % | -3,2 % [-22 %; +16 %] | -3,4 % | 55 % |
| 50 % / 4 % | 103 | 2,47 | 42,7 % | 46,3 % | -4,5 % [-27 %; +18 %] | -2,8 % | 53 % |
| 50 % / 6 % | 58 | 2,66 | 32,8 % | 43,6 % | -22,2 % [-52 %; +9 %] | -2,9 % | 50 % |
| 50 % / 10 % | 26 | 2,78 | 38,5 % | 42,5 % | -1,3 % [-49 %; +49 %] | -2,7 % | 42 % |
| 75 % / 0 % | 316 | 2,28 | 46,5 % | 50,3 % | -0,3 % [-14 %; +14 %] | -5,0 % | 47 % |
| 75 % / 2 % | 268 | 2,35 | 44,8 % | 49,1 % | -0,4 % [-17 %; +16 %] | -4,9 % | 49 % |
| 75 % / 4 % | 211 | 2,41 | 41,2 % | 48,6 % | -6,4 % [-23 %; +11 %] | -5,0 % | 50 % |
| 75 % / 6 % | 157 | 2,48 | 41,4 % | 48,0 % | -3,9 % [-24 %; +17 %] | -4,8 % | 52 % |
| 75 % / 10 % | 89 | 2,68 | 43,8 % | 45,3 % | +7,8 % [-20 %; +36 %] | -4,6 % | 52 % |
| 100 % / 0 % | 331 | 2,42 | 45,0 % | 48,8 % | +2,5 % [-12 %; +17 %] | -5,6 % | 48 % |
| 100 % / 2 % | 305 | 2,46 | 43,3 % | 48,4 % | +0,8 % [-14 %; +16 %] | -5,9 % | 46 % |
| 100 % / 4 % | 272 | 2,49 | 42,3 % | 48,1 % | +0,5 % [-16 %; +17 %] | -5,9 % | 48 % |
| 100 % / 6 % | 240 | 2,53 | 40,8 % | 48,0 % | -1,2 % [-19 %; +15 %] | -5,8 % | 49 % |
| 100 % / 10 % | 159 | 2,64 | 37,7 % | 47,4 % | -6,5 % [-29 %; +16 %] | -6,0 % | 51 % |

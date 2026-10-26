# Closing Line Value der Tipps

_Automatisch erzeugt mit `qf value clv`. Nicht von Hand bearbeiten._

## Methode

- **Zeitpunkt des Tipps:** Live-Tipps beim Fixieren des Tages (`qf picks freeze`, sonst bei der Prognose), Backtest-Tipps zum ersten Anpfiff des Spieltags (das Modell kennt nur Spiele davor). Tipps weniger als 1 h vor Anpfiff zählen nicht.
- **Genommene Quote:** letzter Betano-Preis vor diesem Zeitpunkt (OddsPapi-Verlauf).
- **CLV** = genommene Betano-Quote × Pinnacle-Wahrscheinlichkeit ohne Marge beim Anpfiff − 1. Über 0 heißt: Die Quote war besser als der faire Schlusspreis des schärfsten Marktes.
- **Vergleich\*** = CLV aller Auswahlen derselben Märkte und Spiele zur selben Zeit, gewichtet auf die Quotenverteilung der Tipps (Betano nimmt auf Favoriten weniger Marge als auf Außenseiter). **Abstand** = CLV − Vergleich: Zeigt, ob die Auswahl des Modells Information enthält, die der Markt erst später einpreist.
- **± SE**: Standardfehler, nach Spiel geclustert (die 3 Tipps eines Spiels hängen zusammen). Ein Abstand ab etwa 2 SE gilt als belastbar.
- **Quote fiel danach** = Anteil der Tipps, deren Betano-Quote bis zum Anpfiff gesunken ist.

Datenbasis: 1447 Tipps aus 180 Spielen mit Betano-Verlauf (2026-04-11 bis 2026-10-25). Für neue Ligen werden Verläufe nur für kommende Spiele geladen (`oddspapi.history_days`) – die Live-Zahl wächst mit jedem fixierten Spieltag.

## Ergebnis

**Die Tipps schlagen die Vergleichsgruppe gleicher Quotenhöhe deutlich (Modell erkennt Richtung), liegen aber nach Betano-Marge noch unter dem fairen Schlusspreis: Einzeln ohne Value-Filter kein Gewinn zu erwarten.**

| Quelle | Tipps | Spiele | Ø Quote | CLV | ± SE | Vergleich* | Abstand | Quote fiel danach | Treffer | ROI zur Quote |
|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| Alle Tipps | 1447 | 180 | 1,33 | -3,0 % | 0,2 % | -3,6 % | +0,7 % | 43 % | 75 % | -2,7 % |
| Backtest (Modell zum Spieltagsbeginn) | 1375 | 172 | 1,33 | -3,0 % | 0,3 % | -3,7 % | +0,7 % | 45 % | 75 % | -2,7 % |
| Live (fixierte Tipps) | 72 | 8 | 1,35 | -2,3 % | 0,2 % | -3,0 % | +0,7 % | 0 % | – | – |

## Tipps mit Modell-Value

Tipps, bei denen Modellwahrscheinlichkeit × genommene Quote > 1 war (Vorschau auf ein Value-Profil; nur sinnvoll, wenn der CLV hier höher ist als bei allen Tipps).

| Auswahl | Tipps | Spiele | Ø Quote | CLV | ± SE | Vergleich* | Abstand | Quote fiel danach | Treffer | ROI zur Quote |
|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| Tipps mit Modell-EV > 0 zur genommenen Quote | 456 | 133 | 1,47 | -3,2 % | 0,6 % | -4,1 % | +1,0 % | 46 % | 68 % | -2,2 % |

## Je Profil

| Profil | Tipps | Spiele | Ø Quote | CLV | ± SE | Vergleich* | Abstand | Quote fiel danach | Treffer | ROI zur Quote |
|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| Ausgewogen | 490 | 178 | 1,26 | -2,5 % | 0,2 % | -3,3 % | +0,8 % | 43 % | 78 % | -3,0 % |
| Mutig | 474 | 179 | 1,54 | -3,8 % | 0,3 % | -4,2 % | +0,4 % | 41 % | 65 % | -1,6 % |
| Sicher | 483 | 178 | 1,19 | -2,1 % | 0,2 % | -3,1 % | +1,0 % | 43 % | 82 % | -3,5 % |

## Je Marktgruppe

| Marktgruppe | Tipps | Spiele | Ø Quote | CLV | ± SE | Vergleich* | Abstand | Quote fiel danach | Treffer | ROI zur Quote |
|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| Spielausgang | 272 | 156 | 1,36 | -2,9 % | 0,3 % | -3,5 % | +0,6 % | 40 % | 74 % | -1,0 % |
| Halbzeiten | 336 | 148 | 1,34 | -4,0 % | 0,5 % | -5,4 % | +1,4 % | 42 % | 79 % | +4,5 % |
| Tore pro Team | 446 | 179 | 1,29 | -3,0 % | 0,3 % | -3,6 % | +0,6 % | 43 % | 74 % | -6,4 % |
| Tore gesamt | 393 | 170 | 1,33 | -2,7 % | 0,4 % | -3,1 % | +0,4 % | 44 % | 73 % | -5,8 % |

## Je Vorlauf bis Anpfiff

| Vorlauf | Tipps | Spiele | Ø Quote | CLV | ± SE | Vergleich* | Abstand | Quote fiel danach | Treffer | ROI zur Quote |
|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| unter 6 h | 8 | 1 | 1,21 | -2,4 % | – | -3,1 % | +0,7 % | 12 % | 100 % | +21,4 % |
| 6–24 h | 763 | 94 | 1,32 | -3,1 % | 0,3 % | -3,6 % | +0,5 % | 46 % | 75 % | -2,4 % |
| 1–3 Tage | 604 | 77 | 1,34 | -2,9 % | 0,4 % | -3,8 % | +0,9 % | 43 % | 74 % | -3,4 % |
| über 3 Tage | 72 | 8 | 1,35 | -2,3 % | 0,2 % | -3,0 % | +0,7 % | 0 % | – | – |

## Je Liga

| Liga | Tipps | Spiele | Ø Quote | CLV | ± SE | Vergleich* | Abstand | Quote fiel danach | Treffer | ROI zur Quote |
|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| Bundesliga | 693 | 86 | 1,31 | -3,9 % | 0,5 % | -3,9 % | -0,0 % | 44 % | 74 % | -5,1 % |
| 2. Bundesliga | 754 | 94 | 1,34 | -2,3 % | 0,3 % | -3,5 % | +1,1 % | 41 % | 76 % | -0,4 % |

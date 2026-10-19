# 11 – Betano-Nebenmärkte gegen faire Preise (Phase 3, Weg 1)

Automatisch erzeugt von `qf value betano` am 19.10.2026 13:32 UTC (Modell `mkt-v1`, Lauf `analytics.model_runs.id = 12`).

**Vorgehen:** Für jedes Spiel mit Quotenverläufen (OddsPapi) wird zu einem Zeitpunkt *T* vor Anpfiff das marktbasierte Modell `mkt-v1` an die Pinnacle-Quoten angepasst (1X2, Ü/U, Team-Tore, Beide treffen, jeweils Spiel und 1. Halbzeit; Margenentfernung nach Shin). Parameter: erwartete Tore Heim/Gast, Anteil der Tore in der 1. Halbzeit je Team, Dixon-Coles-ρ. Daraus folgt ein fairer Preis für **jede** Betano-Quote zum selben Zeitpunkt – auch für Märkte, die Pinnacle nicht anbietet (2. Halbzeit, torreichste Halbzeit, exakte Toranzahl …). *Edge* = faire Wahrscheinlichkeit × Betano-Quote − 1.

**Bewertung:** *CLV* = Betano-Quote × faire Wahrscheinlichkeit beim Anpfiff (Pinnacle-Schlusskurs) − 1, *CLV Betano* = Betano-Quote / Betano-Schlussquote − 1. Bei ≈ 100 Spielen ist der ROI reiner Zufall; aussagekräftig sind Edge-Verteilung und CLV. Je Spiel und Marktlinie höchstens eine Wette.

**Nicht enthalten:** Torschützen (Zuordnung OddsPapi-Spieler ↔ API-Football-Spieler fehlt noch) und „exakte Tore Heim/Gast“ – dort sind die Betano-Daten über den ganzen Verlauf widersprüchlich zu Betanos eigenen Team-Tore-Quoten (z. B. „4+“ zu 16,5 bei Ü3,5 = 1,44), vermutlich falsch beschriftete Auswahlen.

## Fazit

- **Faire Preise sind verlässlich:** Das Modell trifft die Pinnacle-Quoten im Mittel auf 0,42 % genau und ist auf 10715 Betano-Auswahlen gut kalibriert (Tabelle unten) und in 3 von 4 Marktfamilien genauer als Betanos eigene margenbereinigte Quoten (sonst gleichauf).
- **Betano liegt fast nie über dem fairen Preis:** 24 h vor Anpfiff sind 0,9 % der 10716 Betano-Quoten positiv (Ø Edge dieser Wetten +0,8 %, CLV −0,6 %). Größere Abweichungen (> 2 %) kommen praktisch nicht vor – auch nicht 48 h oder 1 h vor Anpfiff. Betano leitet seine Nebenmärkte offenbar sauber aus den Hauptmärkten ab und schlägt nur eine Marge auf.
- **Die Marge ist je Markt sehr unterschiedlich:** ≈ 4–7 % bei 1X2, Doppelter Chance, Über/Unter und Team-Toren, ≈ 9–17 % bei Halbzeit-Ergebnis, Handicap, torreichster Halbzeit und exakter Toranzahl. Wer bei Betano wettet, verliert in den letztgenannten Märkten langfristig zwei- bis dreimal so viel.
- **Konsequenz:** Mit Quotenvergleich allein ist bei Betano kein dauerhafter Value zu finden. Realistische Quellen sind Quotenboosts und Aktionen (mit den fairen Preisen sofort bewertbar), Torschützen-Märkte (noch zu prüfen) und Momente, in denen Betano nach Nachrichten (Aufstellung, Ausfall) langsamer reagiert als Pinnacle.

## Value-Wetten je Zeitpunkt

| Zeitpunkt | Spiele | Betano-Quoten | davon Edge > 0 | Schwelle | Wetten | Ø Edge | ROI | CLV | CLV Betano |
|---|---|---|---|---|---|---|---|---|---|
| 48 h vor Anpfiff | 102 | 10396 | 0,7 % | Edge > 0 % | 72 | +0,7 % | −4,9 % | +0,1 % | +1,4 % |
| 48 h vor Anpfiff | 102 | 10396 | 0,7 % | Edge > 2 % | 8 | +2,7 % | +44,2 % | −0,6 % | +3,1 % |
| 48 h vor Anpfiff | 102 | 10396 | 0,7 % | Edge > 5 % | 0 | – | – | – | – |
| 24 h vor Anpfiff | 106 | 10716 | 0,9 % | Edge > 0 % | 93 | +0,8 % | +0,7 % | −0,6 % | +0,9 % |
| 24 h vor Anpfiff | 106 | 10716 | 0,9 % | Edge > 2 % | 9 | +2,9 % | +60,3 % | −1,5 % | +0,1 % |
| 24 h vor Anpfiff | 106 | 10716 | 0,9 % | Edge > 5 % | 0 | – | – | – | – |
| 6 h vor Anpfiff | 109 | 11005 | 0,8 % | Edge > 0 % | 88 | +0,6 % | −3,3 % | +0,3 % | +0,7 % |
| 6 h vor Anpfiff | 109 | 11005 | 0,8 % | Edge > 2 % | 0 | – | – | – | – |
| 6 h vor Anpfiff | 109 | 11005 | 0,8 % | Edge > 5 % | 0 | – | – | – | – |
| 1 h vor Anpfiff | 109 | 11027 | 1,3 % | Edge > 0 % | 138 | +0,8 % | −11,2 % | −0,3 % | +0,9 % |
| 1 h vor Anpfiff | 109 | 11027 | 1,3 % | Edge > 2 % | 12 | +3,5 % | −30,3 % | +2,0 % | +4,1 % |
| 1 h vor Anpfiff | 109 | 11027 | 1,3 % | Edge > 5 % | 2 | +7,1 % | −100,0 % | – | +10,6 % |

## Betano je Markt (24 h vor Anpfiff)

*Typische Edge* = Median über alle Betano-Quoten des Marktes (≈ −Marge). *Nah am fairen Preis* = Edge > −2 %. *Pinnacle direkt* = Anteil der Quoten, deren Markt und Linie Pinnacle selbst anbietet (sonst abgeleitet).

| Markt | Familie | Quoten | Typische Edge | Edge > 0 | Nah am fairen Preis | Pinnacle direkt |
|---|---|---|---|---|---|---|
| Doppelte Chance | 1X2 & Handicap | 315 | −4,3 % | 0,3 % | 8 % | 99 % |
| Über/Unter Tore | Tore gesamt | 1642 | −4,9 % | 1,5 % | 30 % | 29 % |
| 1X2 | 1X2 & Handicap | 316 | −5,0 % | 0,9 % | 8 % | 100 % |
| Über/Unter 1. Halbzeit | Halbzeiten | 1038 | −5,5 % | 3,0 % | 28 % | 23 % |
| Über/Unter 2. Halbzeit | Halbzeiten | 324 | −5,7 % | 2,5 % | 15 % | 0 % |
| Heimteam 1. Halbzeit | Halbzeiten | 384 | −6,5 % | 0,3 % | 20 % | 28 % |
| Heimteam 2. Halbzeit | Halbzeiten | 416 | −6,6 % | 0,5 % | 29 % | 0 % |
| Über/Unter Tore Gastteam | Team-Tore | 1056 | −6,6 % | 0,0 % | 17 % | 42 % |
| Gastteam 2. Halbzeit | Halbzeiten | 398 | −6,6 % | 0,8 % | 28 % | 0 % |
| Beide treffen 2. HZ | Halbzeiten | 108 | −6,6 % | 4,6 % | 27 % | 0 % |
| Gastteam 1. Halbzeit | Halbzeiten | 346 | −6,6 % | 0,6 % | 20 % | 31 % |
| Draw No Bet | 1X2 & Handicap | 212 | −6,6 % | 0,5 % | 3 % | 100 % |
| Beide Teams treffen | Tore gesamt | 210 | −6,7 % | 0,0 % | 0 % | 100 % |
| Über/Unter Tore Heimteam | Team-Tore | 1192 | −6,7 % | 0,0 % | 19 % | 40 % |
| Beide treffen 1. HZ | Halbzeiten | 108 | −7,3 % | 0,9 % | 9 % | 100 % |
| 2. Halbzeit 1X2 | Halbzeiten | 162 | −9,5 % | 0,0 % | 0 % | 0 % |
| Halbzeit-Ergebnis | Halbzeiten | 316 | −9,6 % | 1,6 % | 9 % | 100 % |
| Torreichste Halbzeit | Halbzeiten | 162 | −11,9 % | 2,5 % | 6 % | 0 % |
| Europäisches Handicap | 1X2 & Handicap | 1579 | −12,5 % | 0,2 % | 3 % | 99 % |
| Exakte Toranzahl | Tore gesamt | 432 | −16,7 % | 0,0 % | 0 % | 100 % |

## Kalibrierung der fairen Preise (Schlusskurs)

| Vorhergesagt | Auswahlen | Ø vorhergesagt | Eingetreten |
|---|---|---|---|
| (0.0, 0.1] | 1885 | 5,1 % | 4,6 % |
| (0.1, 0.2] | 1442 | 15,1 % | 15,7 % |
| (0.2, 0.3] | 1140 | 24,4 % | 24,5 % |
| (0.3, 0.4] | 928 | 34,6 % | 33,7 % |
| (0.4, 0.5] | 780 | 45,0 % | 45,8 % |
| (0.5, 0.6] | 703 | 55,1 % | 55,3 % |
| (0.6, 0.7] | 723 | 65,2 % | 65,0 % |
| (0.7, 0.8] | 854 | 75,1 % | 74,7 % |
| (0.8, 0.9] | 948 | 85,1 % | 84,2 % |
| (0.9, 1.0] | 1312 | 95,4 % | 96,6 % |

| Familie | Auswahlen | Brier faire Preise | Brier Betano (margenbereinigt) |
|---|---|---|---|
| 1X2 & Handicap | 2085 | 0,1547 | 0,1544 |
| Halbzeiten | 3686 | 0,1505 | 0,1513 |
| Team-Tore | 2282 | 0,1310 | 0,1325 |
| Tore gesamt | 1890 | 0,1360 | 0,1374 |

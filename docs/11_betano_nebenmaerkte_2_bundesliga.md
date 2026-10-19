# 11 – Betano-Nebenmärkte gegen faire Preise (Phase 3, Weg 1) · 2. Bundesliga

Automatisch erzeugt von `qf value betano` am 19.10.2026 15:26 UTC (Modell `mkt-v1`, Lauf `analytics.model_runs.id = 17`).

**Vorgehen:** Für jedes Spiel mit Quotenverläufen (OddsPapi) wird zu einem Zeitpunkt *T* vor Anpfiff das marktbasierte Modell `mkt-v1` an die Pinnacle-Quoten angepasst (1X2, Ü/U, Team-Tore, Beide treffen, jeweils Spiel und 1. Halbzeit; Margenentfernung nach Shin). Parameter: erwartete Tore Heim/Gast, Anteil der Tore in der 1. Halbzeit je Team, Dixon-Coles-ρ. Daraus folgt ein fairer Preis für **jede** Betano-Quote zum selben Zeitpunkt – auch für Märkte, die Pinnacle nicht anbietet (2. Halbzeit, torreichste Halbzeit, exakte Toranzahl …). *Edge* = faire Wahrscheinlichkeit × Betano-Quote − 1.

**Bewertung:** *CLV* = Betano-Quote × faire Wahrscheinlichkeit beim Anpfiff (Pinnacle-Schlusskurs) − 1, *CLV Betano* = Betano-Quote / Betano-Schlussquote − 1. Bei ≈ 100 Spielen ist der ROI reiner Zufall; aussagekräftig sind Edge-Verteilung und CLV. Je Spiel und Marktlinie höchstens eine Wette.

**Nicht enthalten:** Torschützen (Zuordnung OddsPapi-Spieler ↔ API-Football-Spieler fehlt noch) und „exakte Tore Heim/Gast“ – dort sind die Betano-Daten über den ganzen Verlauf widersprüchlich zu Betanos eigenen Team-Tore-Quoten (z. B. „4+“ zu 16,5 bei Ü3,5 = 1,44), vermutlich falsch beschriftete Auswahlen.

## Fazit

- **Faire Preise sind verlässlich:** Das Modell trifft die Pinnacle-Quoten im Mittel auf 0,47 % genau und ist auf 12042 Betano-Auswahlen gut kalibriert (Tabelle unten) und in 1 von 4 Marktfamilien genauer als Betanos eigene margenbereinigte Quoten (sonst gleichauf).
- **Betano liegt fast nie über dem fairen Preis:** 24 h vor Anpfiff sind 0,6 % der 12137 Betano-Quoten positiv (Ø Edge dieser Wetten +0,7 %, CLV +0,8 %). Größere Abweichungen (> 2 %) kommen praktisch nicht vor – auch nicht 48 h oder 1 h vor Anpfiff. Betano leitet seine Nebenmärkte offenbar sauber aus den Hauptmärkten ab und schlägt nur eine Marge auf.
- **Die Marge ist je Markt sehr unterschiedlich:** ≈ 4–7 % bei 1X2, Doppelter Chance, Über/Unter und Team-Toren, ≈ 9–17 % bei Halbzeit-Ergebnis, Handicap, torreichster Halbzeit und exakter Toranzahl. Wer bei Betano wettet, verliert in den letztgenannten Märkten langfristig zwei- bis dreimal so viel.
- **Konsequenz:** Mit Quotenvergleich allein ist bei Betano kein dauerhafter Value zu finden. Realistische Quellen sind Quotenboosts und Aktionen (mit den fairen Preisen sofort bewertbar), Torschützen-Märkte (noch zu prüfen) und Momente, in denen Betano nach Nachrichten (Aufstellung, Ausfall) langsamer reagiert als Pinnacle.

## Value-Wetten je Zeitpunkt

| Zeitpunkt | Spiele | Betano-Quoten | davon Edge > 0 | Schwelle | Wetten | Ø Edge | ROI | CLV | CLV Betano |
|---|---|---|---|---|---|---|---|---|---|
| 48 h vor Anpfiff | 120 | 12011 | 0,7 % | Edge > 0 % | 85 | +0,8 % | +6,3 % | +1,9 % | +2,6 % |
| 48 h vor Anpfiff | 120 | 12011 | 0,7 % | Edge > 2 % | 3 | +4,0 % | −100,0 % | +8,6 % | +5,3 % |
| 48 h vor Anpfiff | 120 | 12011 | 0,7 % | Edge > 5 % | 0 | – | – | – | – |
| 24 h vor Anpfiff | 122 | 12137 | 0,6 % | Edge > 0 % | 78 | +0,7 % | +10,6 % | +0,8 % | +1,9 % |
| 24 h vor Anpfiff | 122 | 12137 | 0,6 % | Edge > 2 % | 5 | +2,8 % | −2,0 % | +0,7 % | +1,8 % |
| 24 h vor Anpfiff | 122 | 12137 | 0,6 % | Edge > 5 % | 0 | – | – | – | – |
| 6 h vor Anpfiff | 127 | 12449 | 0,9 % | Edge > 0 % | 115 | +1,4 % | −9,0 % | +1,8 % | +2,8 % |
| 6 h vor Anpfiff | 127 | 12449 | 0,9 % | Edge > 2 % | 22 | +4,9 % | −31,2 % | +4,9 % | +5,5 % |
| 6 h vor Anpfiff | 127 | 12449 | 0,9 % | Edge > 5 % | 7 | +9,5 % | −48,3 % | +6,3 % | +7,8 % |
| 1 h vor Anpfiff | 128 | 12599 | 1,1 % | Edge > 0 % | 136 | +1,7 % | −13,1 % | +1,9 % | +3,3 % |
| 1 h vor Anpfiff | 128 | 12599 | 1,1 % | Edge > 2 % | 29 | +5,4 % | −38,1 % | +4,5 % | +8,0 % |
| 1 h vor Anpfiff | 128 | 12599 | 1,1 % | Edge > 5 % | 10 | +9,2 % | −79,0 % | +8,6 % | +9,9 % |

## Betano je Markt (24 h vor Anpfiff)

*Typische Edge* = Median über alle Betano-Quoten des Marktes (≈ −Marge). *Nah am fairen Preis* = Edge > −2 %. *Pinnacle direkt* = Anteil der Quoten, deren Markt und Linie Pinnacle selbst anbietet (sonst abgeleitet).

| Markt | Familie | Quoten | Typische Edge | Edge > 0 | Nah am fairen Preis | Pinnacle direkt |
|---|---|---|---|---|---|---|
| Doppelte Chance | 1X2 & Handicap | 338 | −4,3 % | 0,6 % | 5 % | 90 % |
| Über/Unter Tore | Tore gesamt | 1858 | −4,8 % | 0,9 % | 32 % | 57 % |
| 1X2 | 1X2 & Handicap | 366 | −5,2 % | 2,5 % | 8 % | 100 % |
| Über/Unter 1. Halbzeit | Halbzeiten | 1057 | −5,3 % | 1,7 % | 25 % | 24 % |
| Über/Unter 2. Halbzeit | Halbzeiten | 432 | −5,6 % | 1,4 % | 16 % | 0 % |
| Heimteam 1. Halbzeit | Halbzeiten | 442 | −6,4 % | 0,0 % | 15 % | 33 % |
| Heimteam 2. Halbzeit | Halbzeiten | 520 | −6,5 % | 0,6 % | 31 % | 0 % |
| Über/Unter Tore Heimteam | Team-Tore | 1241 | −6,5 % | 0,0 % | 14 % | 59 % |
| Gastteam 2. Halbzeit | Halbzeiten | 470 | −6,5 % | 0,0 % | 24 % | 0 % |
| Gastteam 1. Halbzeit | Halbzeiten | 410 | −6,5 % | 0,0 % | 18 % | 35 % |
| Beide treffen 2. HZ | Halbzeiten | 144 | −6,5 % | 5,6 % | 33 % | 0 % |
| Über/Unter Tore Gastteam | Team-Tore | 1073 | −6,6 % | 0,0 % | 14 % | 64 % |
| Draw No Bet | 1X2 & Handicap | 244 | −6,6 % | 0,0 % | 1 % | 98 % |
| Beide Teams treffen | Tore gesamt | 224 | −6,7 % | 0,4 % | 0 % | 98 % |
| Beide treffen 1. HZ | Halbzeiten | 144 | −7,7 % | 0,0 % | 4 % | 99 % |
| Halbzeit-Ergebnis | Halbzeiten | 366 | −8,9 % | 1,6 % | 5 % | 100 % |
| 2. Halbzeit 1X2 | Halbzeiten | 216 | −9,2 % | 0,0 % | 0 % | 0 % |
| Torreichste Halbzeit | Halbzeiten | 162 | −12,1 % | 0,0 % | 0 % | 0 % |
| Europäisches Handicap | 1X2 & Handicap | 1854 | −13,7 % | 0,4 % | 3 % | 98 % |
| Exakte Toranzahl | Tore gesamt | 576 | −18,5 % | 0,0 % | 0 % | 99 % |

## Kalibrierung der fairen Preise (Schlusskurs)

| Vorhergesagt | Auswahlen | Ø vorhergesagt | Eingetreten |
|---|---|---|---|
| (0.0, 0.1] | 2025 | 5,3 % | 6,4 % |
| (0.1, 0.2] | 1588 | 15,3 % | 14,7 % |
| (0.2, 0.3] | 1381 | 24,4 % | 23,5 % |
| (0.3, 0.4] | 1117 | 35,2 % | 36,3 % |
| (0.4, 0.5] | 915 | 45,0 % | 45,0 % |
| (0.5, 0.6] | 830 | 55,0 % | 53,9 % |
| (0.6, 0.7] | 805 | 64,6 % | 65,1 % |
| (0.7, 0.8] | 1021 | 75,3 % | 75,8 % |
| (0.8, 0.9] | 1044 | 84,6 % | 85,3 % |
| (0.9, 1.0] | 1316 | 95,0 % | 93,5 % |

| Familie | Auswahlen | Brier faire Preise | Brier Betano (margenbereinigt) |
|---|---|---|---|
| 1X2 & Handicap | 2430 | 0,1470 | 0,1467 |
| Halbzeiten | 4227 | 0,1644 | 0,1653 |
| Team-Tore | 2350 | 0,1442 | 0,1441 |
| Tore gesamt | 2112 | 0,1495 | 0,1484 |

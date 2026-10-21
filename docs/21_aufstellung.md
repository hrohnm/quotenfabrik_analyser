# 21 – Voraussichtliche Aufstellung

Automatisch erzeugt von `qf model lineup-eval` am 21.10.2026 14:35 UTC. Ligen: Bundesliga, 2. Bundesliga, Saisons 2021/22–2026/27, 6405 Startelfen.

**Idee:** API-Football liefert keine voraussichtlichen Aufstellungen, die bestätigte kommt erst 20–40 Minuten vor Anpfiff. Bis dahin zeigt die Detailseite eine eigene Schätzung: die Startelf des letzten Spiels (alle Wettbewerbe, Formation und Positionen übernommen); gemeldete Ausfälle (verletzt, gesperrt) werden durch den verfügbaren Spieler derselben Position mit den meisten Einsätzen in den letzten 5 Spielen ersetzt. Gemessen wird, wie viele der 11 geschätzten Spieler tatsächlich begonnen haben.

| Variante | Startelfen | richtig im Schnitt | mind. 10 richtig | alle 11 richtig | Torwart richtig |
|---|---:|---:|---:|---:|---:|
| letzte Startelf | 6405 | 8,68 von 11 | 33 % | 11 % | 91 % |
| letzte Startelf, Ausfälle ersetzt | 6405 | 8,81 von 11 | 36 % | 12 % | 92 % |

## Je Liga und Saison (Variante mit ersetzten Ausfällen)

| Liga | Saison | Startelfen | richtig im Schnitt | mind. 10 richtig |
|---|---|---:|---:|---:|
| Bundesliga | 2021/22 | 616 | 8,73 | 33 % |
| Bundesliga | 2022/23 | 616 | 8,89 | 35 % |
| Bundesliga | 2023/24 | 616 | 8,88 | 36 % |
| Bundesliga | 2024/25 | 616 | 8,92 | 39 % |
| Bundesliga | 2025/26 | 616 | 8,66 | 32 % |
| Bundesliga | 2026/27 | 108 | 8,47 | 35 % |
| 2. Bundesliga | 2021/22 | 615 | 8,71 | 37 % |
| 2. Bundesliga | 2022/23 | 616 | 8,85 | 39 % |
| 2. Bundesliga | 2023/24 | 615 | 8,79 | 36 % |
| 2. Bundesliga | 2024/25 | 613 | 8,88 | 37 % |
| 2. Bundesliga | 2025/26 | 615 | 8,87 | 38 % |
| 2. Bundesliga | 2026/27 | 143 | 8,71 | 40 % |

## Bewertung

- Mit gemeldeten Ausfällen (3169 Startelfen) bringt das Ersetzen 0,27 richtige Spieler mehr.
- Die Schätzung ist eine Orientierung bis zur offiziellen Aufstellung, kein Modell-Input: Prognosen und Torschützen-Wahrscheinlichkeiten verwenden sie nicht.
- Einschränkung: Die Ausfall-Liste der API wird bis kurz vor Anpfiff ergänzt; im Backtest steht der letzte Stand, live kann er unvollständiger sein (Abruf täglich).

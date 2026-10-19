# 12 – 3 Tipps pro Spiel: Trefferquote einzeln und als Kombi · 2. Bundesliga

Automatisch erzeugt von `qf picks report` am 19.10.2026 15:26 UTC (Modell `dc-v1`, Saisons 2016/17 – 2026/27, 3132 Spiele).

## So werden die Tipps gewählt

1. **Kandidaten:** alle Modell-Prognosen eines Spiels in gängigen Märkten mit üblichen Linien (`1x2, btts, btts_1h, clean_sheet, dc, ht_1x2, ou_1h, ou_2h, ou_away, ou_away_1h, ou_away_2h, ou_ft, ou_home, ou_home_1h, ou_home_2h`) – keine Torschützen, Handicaps oder exotischen Linien.
2. **Stärke:** Wahrscheinlichkeit im Fenster des Profils, bewertet mit *Wahrscheinlichkeit + Gewicht × (Wahrscheinlichkeit − Ligaschnitt)*. Der Ligaschnitt ist die Häufigkeit der letzten drei Saisons; Tipps, bei denen das Modell für *dieses* Spiel etwas Besonderes sieht, werden bevorzugt.
3. **Streuung:** je Marktgruppe (Spielausgang, Tore gesamt, Team-Tore, Halbzeiten) nur der beste Kandidat, davon die 3 besten – nie zwei Tipps aus derselben Gruppe. Welche Gruppen zum Zug kommen, wechselt von Spiel zu Spiel.
4. **Begründung:** Pattern mit auffälligem Signal, die denselben Tipp stützen, werden angehängt.

Alles nur mit Informationen vor dem Spieltag (Walk-Forward-Prognosen, Ligaschnitt und Pattern vor dem Spieltag). Profile und Gewichte wurden auf den Saisons bis 2021/22 festgelegt; die Testsaisons danach zeigen, ob die Quoten stabil bleiben.

| Profil | Wahrscheinlichkeit je Tipp | Gewicht Ligaschnitt-Abstand |
|---|---|---|
| Sicher | 70 % – 92 % | 0,5 |
| Ausgewogen | 58 % – 85 % | 1 |
| Mutig | 45 % – 72 % | 1 |

## Ergebnis

| Profil | Zeitraum | Tipps | Trefferquote | erwartet | Kombis | Kombi getroffen | Kombi rechnerisch* | faire Kombi-Quote (Median) |
|---|---|---|---|---|---|---|---|---|
| Sicher | Validierung | 5508 | **80,2 %** | 81,9 % | 1836 | **57,2 %** | 54,9 % | 1,84 |
| Sicher | Test | 3888 | **81,6 %** | 82,5 % | 1296 | **59,6 %** | 56,1 % | 1,79 |
| Ausgewogen | Validierung | 5508 | **76,2 %** | 78,3 % | 1836 | **53,5 %** | 48,1 % | 2,04 |
| Ausgewogen | Test | 3888 | **77,3 %** | 78,9 % | 1296 | **53,5 %** | 49,2 % | 2,00 |
| Mutig | Validierung | 5508 | **64,1 %** | 66,0 % | 1836 | **34,0 %** | 28,8 % | 3,47 |
| Mutig | Test | 3888 | **61,7 %** | 64,6 % | 1296 | **32,6 %** | 27,0 % | 3,74 |

\* Produkt der drei Einzelwahrscheinlichkeiten – so rechnet eine gewöhnliche Kombiwette. Die Kombi trifft **deutlich öfter**, weil die Tipps eines Spiels zusammenhängen (z. B. Heimsieg und „Gastteam unter 1,5 Tore“). Faire Kombi-Quote = 1 / rechnerische Wahrscheinlichkeit.

## Einordnung

- **Die Einzeltipps sind verlässlich:** Die Trefferquote entspricht in Validierung und Test fast genau der vorhergesagten Wahrscheinlichkeit (Profil Ausgewogen, Test: 77,3 % getroffen bei 78,9 % erwartet). Das Modell ist kalibriert – die Prozentwerte kann man wörtlich nehmen.
- **Die Kombi trifft öfter als gedacht:** 53,5 % statt rechnerisch 49,2 %. Bei einer normalen Kombiwette (Quoten werden multipliziert) wäre das ein Vorteil. Innerhalb *eines* Spiels bieten Buchmacher Kombis aber meist nur als „Bet Builder“ an – dort wird der Zusammenhang eingepreist, die Quote liegt unter dem Produkt der Einzelquoten.
- **Trefferquote ist nicht Gewinn:** Bei Betano liegt auf jedem Tipp eine Marge von ≈ 6 % (siehe `11_betano_nebenmaerkte.md`). Ein Tipp mit 80 % Wahrscheinlichkeit wird also nicht zu 1,25, sondern eher zu ≈ 1,18 angeboten. Die Tipps sind eine gut begründete Vorauswahl, keine Value-Wetten.
- **Pattern-Begründung:** Tipps mit stützendem Pattern trafen 75,3 % (erwartet 77,8 %, n = 1391), ohne 76,9 % (erwartet 78,7 %). Pattern erklären den Tipp, verbessern ihn aber nicht messbar – das Modell kennt die Information bereits.

## Details Profil „Ausgewogen“ (alle Saisons)

### Wie viele der drei Tipps treffen?

| Treffer | 0 von 3 | 1 von 3 | 2 von 3 | 3 von 3 (Kombi) |
|---|---|---|---|---|
| Anteil der Spiele | 4,5 % | 14,6 % | 27,4 % | 53,5 % |

### Je Saison

| Saison | Tipps | Trefferquote | erwartet | Kombi getroffen | Kombi rechnerisch |
|---|---|---|---|---|---|
| 2016/17 | 918 | 75,6 % | 77,5 % | 52,9 % | 46,5 % |
| 2017/18 | 918 | 78,5 % | 77,8 % | 57,5 % | 47,0 % |
| 2018/19 | 918 | 72,5 % | 77,8 % | 48,7 % | 47,2 % |
| 2019/20 | 918 | 73,0 % | 78,4 % | 48,4 % | 48,4 % |
| 2020/21 | 918 | 77,8 % | 79,1 % | 56,5 % | 49,5 % |
| 2021/22 | 918 | 79,8 % | 79,2 % | 57,2 % | 49,7 % |
| 2022/23 | 918 | 76,9 % | 79,0 % | 51,0 % | 49,4 % |
| 2023/24 | 918 | 77,8 % | 78,5 % | 58,2 % | 48,4 % |
| 2024/25 | 918 | 76,8 % | 78,6 % | 52,3 % | 48,5 % |
| 2025/26 | 918 | 77,6 % | 79,3 % | 52,9 % | 50,0 % |
| 2026/27 | 216 | 77,8 % | 79,3 % | 52,8 % | 49,8 % |

### Je Tipp-Rang (1 = stärkster Tipp des Spiels)

| Rang | Tipps | Trefferquote | erwartet |
|---|---|---|---|
| 1 | 3132 | 79,1 % | 80,9 % |
| 2 | 3132 | 75,8 % | 78,0 % |
| 3 | 3132 | 75,1 % | 76,7 % |

### Kalibrierung

| Wahrscheinlichkeit | Tipps | Trefferquote | erwartet |
|---|---|---|---|
| 50–60 % | 3 | 0,0 % | 59,5 % |
| 60–70 % | 626 | 60,9 % | 67,2 % |
| 70–80 % | 4317 | 73,2 % | 76,2 % |
| 80–90 % | 4450 | 82,3 % | 82,4 % |

### Häufigste Tipps

| Tipp | Anzahl | Trefferquote | erwartet |
|---|---|---|---|
| 2. HZ: Über 0,5 Tore | 1807 | 81,9 % | 81,3 % |
| Über 1,5 Tore | 1576 | 79,3 % | 80,7 % |
| Unter 3,5 Tore | 811 | 70,0 % | 76,0 % |
| Heimteam oder Remis | 805 | 76,9 % | 78,2 % |
| Heimteam trifft | 714 | 84,0 % | 82,3 % |
| Heimteam: Unter 2,5 Tore | 703 | 80,4 % | 82,2 % |
| Gastteam trifft | 641 | 77,4 % | 79,2 % |
| Gastteam oder Remis | 445 | 67,2 % | 71,6 % |
| Gastteam: Unter 1,5 Tore | 378 | 72,2 % | 75,2 % |
| 1. HZ: Über 0,5 Tore | 301 | 73,4 % | 75,7 % |
| Kein Remis | 255 | 74,1 % | 76,0 % |
| Heimteam: Unter 1,5 Tore | 217 | 61,3 % | 69,1 % |
| 1. HZ: Unter 1,5 Tore | 166 | 69,9 % | 73,5 % |
| Gastteam: Unter 2,5 Tore | 154 | 86,4 % | 83,9 % |
| Über 2,5 Tore | 102 | 55,9 % | 71,7 % |

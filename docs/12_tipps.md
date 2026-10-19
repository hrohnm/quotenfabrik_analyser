# 12 – 3 Tipps pro Spiel: Trefferquote einzeln und als Kombi

Automatisch erzeugt von `qf picks report` am 19.10.2026 13:46 UTC (Modell `dc-v1`, Saisons 2016/17 – 2026/27, 3114 Spiele).

## So werden die Tipps gewählt

1. **Kandidaten:** alle Modell-Prognosen eines Spiels in gängigen Märkten mit üblichen Linien (`1x2, btts, btts_1h, clean_sheet, dc, ht_1x2, ou_1h, ou_2h, ou_away, ou_away_1h, ou_away_2h, ou_ft, ou_home, ou_home_1h, ou_home_2h`) – keine Torschützen, Handicaps oder exotischen Linien.
2. **Stärke:** Wahrscheinlichkeit im Fenster des Profils, bewertet mit *Wahrscheinlichkeit + Gewicht × (Wahrscheinlichkeit − Ligaschnitt)*. Der Ligaschnitt ist die Häufigkeit der letzten drei Saisons; Tipps, bei denen das Modell für *dieses* Spiel etwas Besonderes sieht, werden bevorzugt.
3. **Streuung:** je Marktgruppe (Spielausgang, Tore gesamt, Team-Tore, Halbzeiten) nur der beste Kandidat, davon die 3 besten – nie zwei Tipps aus derselben Gruppe. Welche Gruppen zum Zug kommen, wechselt von Spiel zu Spiel.
4. **Begründung:** Pattern mit auffälligem Signal, die denselben Tipp stützen, werden angehängt.

Alles nur mit Informationen vor dem Spieltag (Walk-Forward-Prognosen, Ligaschnitt und Pattern vor dem Spieltag). Profile und Gewichte wurden auf den Saisons bis 2021/22 festgelegt; die Testsaisons danach zeigen, ob die Quoten stabil bleiben.

| Profil | Wahrscheinlichkeit je Tipp | Gewicht Ligaschnitt-Abstand |
|---|---|---|
| Sicher | 70 % – 92 % | 0.5 |
| Ausgewogen | 58 % – 85 % | 1 |
| Mutig | 45 % – 72 % | 1 |

## Ergebnis

| Profil | Zeitraum | Tipps | Trefferquote | erwartet | Kombis | Kombi getroffen | Kombi rechnerisch* | faire Kombi-Quote (Median) |
|---|---|---|---|---|---|---|---|---|
| Sicher | Validierung | 5508 | **82,9 %** | 83,0 % | 1836 | **63,1 %** | 57,3 % | 1,77 |
| Sicher | Test | 3834 | **83,1 %** | 83,4 % | 1278 | **63,7 %** | 58,1 % | 1,74 |
| Ausgewogen | Validierung | 5508 | **77,4 %** | 77,7 % | 1836 | **56,4 %** | 47,0 % | 2,12 |
| Ausgewogen | Test | 3834 | **78,2 %** | 77,7 % | 1278 | **57,6 %** | 46,9 % | 2,13 |
| Mutig | Validierung | 5508 | **64,7 %** | 64,8 % | 1836 | **37,9 %** | 27,3 % | 3,66 |
| Mutig | Test | 3834 | **63,5 %** | 64,4 % | 1278 | **37,7 %** | 26,7 % | 3,77 |

\* Produkt der drei Einzelwahrscheinlichkeiten – so rechnet eine gewöhnliche Kombiwette. Die Kombi trifft **deutlich öfter**, weil die Tipps eines Spiels zusammenhängen (z. B. Heimsieg und „Gastteam unter 1,5 Tore“). Faire Kombi-Quote = 1 / rechnerische Wahrscheinlichkeit.

## Einordnung

- **Die Einzeltipps sind verlässlich:** Die Trefferquote entspricht in Validierung und Test fast genau der vorhergesagten Wahrscheinlichkeit (Profil Ausgewogen, Test: 78,2 % getroffen bei 77,7 % erwartet). Das Modell ist kalibriert – die Prozentwerte kann man wörtlich nehmen.
- **Die Kombi trifft öfter als gedacht:** 57,6 % statt rechnerisch 46,9 %. Bei einer normalen Kombiwette (Quoten werden multipliziert) wäre das ein Vorteil. Innerhalb *eines* Spiels bieten Buchmacher Kombis aber meist nur als „Bet Builder“ an – dort wird der Zusammenhang eingepreist, die Quote liegt unter dem Produkt der Einzelquoten.
- **Trefferquote ist nicht Gewinn:** Bei Betano liegt auf jedem Tipp eine Marge von ≈ 6 % (siehe `11_betano_nebenmaerkte.md`). Ein Tipp mit 80 % Wahrscheinlichkeit wird also nicht zu 1,25, sondern eher zu ≈ 1,18 angeboten. Die Tipps sind eine gut begründete Vorauswahl, keine Value-Wetten.
- **Pattern-Begründung:** Tipps mit stützendem Pattern trafen 75,7 % (erwartet 76,3 %, n = 1997), ohne 78,3 % (erwartet 78,1 %). Pattern erklären den Tipp, verbessern ihn aber nicht messbar – das Modell kennt die Information bereits.

## Details Profil „Ausgewogen“ (alle Saisons)

### Wie viele der drei Tipps treffen?

| Treffer | 0 von 3 | 1 von 3 | 2 von 3 | 3 von 3 (Kombi) |
|---|---|---|---|---|
| Anteil der Spiele | 4,2 % | 15,4 % | 23,6 % | 56,9 % |

### Je Saison

| Saison | Tipps | Trefferquote | erwartet | Kombi getroffen | Kombi rechnerisch |
|---|---|---|---|---|---|
| 2016/17 | 918 | 75,7 % | 77,4 % | 51,3 % | 46,4 % |
| 2017/18 | 918 | 76,9 % | 77,9 % | 59,5 % | 47,2 % |
| 2018/19 | 918 | 78,5 % | 77,9 % | 59,2 % | 47,3 % |
| 2019/20 | 918 | 78,4 % | 78,1 % | 55,6 % | 47,7 % |
| 2020/21 | 918 | 78,6 % | 77,7 % | 58,2 % | 46,8 % |
| 2021/22 | 918 | 76,1 % | 77,4 % | 54,9 % | 46,3 % |
| 2022/23 | 918 | 74,3 % | 77,6 % | 52,3 % | 46,6 % |
| 2023/24 | 918 | 82,0 % | 77,9 % | 63,7 % | 47,2 % |
| 2024/25 | 918 | 77,7 % | 77,7 % | 55,9 % | 46,9 % |
| 2025/26 | 918 | 79,1 % | 77,5 % | 59,2 % | 46,5 % |
| 2026/27 | 162 | 77,2 % | 78,4 % | 53,7 % | 48,2 % |

### Je Tipp-Rang (1 = stärkster Tipp des Spiels)

| Rang | Tipps | Trefferquote | erwartet |
|---|---|---|---|
| 1 | 3114 | 79,3 % | 80,0 % |
| 2 | 3114 | 77,4 % | 76,8 % |
| 3 | 3114 | 76,5 % | 76,2 % |

### Kalibrierung

| Wahrscheinlichkeit | Tipps | Trefferquote | erwartet |
|---|---|---|---|
| 50–60 % | 7 | 57,1 % | 59,2 % |
| 60–70 % | 1190 | 67,7 % | 67,0 % |
| 70–80 % | 3927 | 75,5 % | 75,7 % |
| 80–90 % | 4218 | 82,7 % | 82,6 % |

### Häufigste Tipps

| Tipp | Anzahl | Trefferquote | erwartet |
|---|---|---|---|
| 2. HZ: Über 0,5 Tore | 1307 | 82,6 % | 81,8 % |
| Heimteam oder Remis | 959 | 80,7 % | 78,7 % |
| Über 1,5 Tore | 950 | 83,9 % | 82,2 % |
| Unter 3,5 Tore | 798 | 71,2 % | 74,6 % |
| Gastteam oder Remis | 719 | 73,0 % | 73,6 % |
| Heimteam: Unter 2,5 Tore | 625 | 81,6 % | 82,0 % |
| Gastteam trifft | 449 | 78,4 % | 80,6 % |
| Gastteam: Unter 1,5 Tore | 419 | 73,7 % | 76,4 % |
| Heimteam trifft | 415 | 81,9 % | 82,9 % |
| 1. HZ: Über 0,5 Tore | 408 | 78,7 % | 79,1 % |
| Heimteam: Über 1,5 Tore | 401 | 68,8 % | 72,2 % |
| Sieg Heimteam | 378 | 74,1 % | 72,2 % |
| Heimteam: Unter 1,5 Tore | 279 | 68,5 % | 71,0 % |
| Heimteam trifft in der 2. HZ | 207 | 78,3 % | 74,5 % |
| Gastteam: Unter 2,5 Tore | 177 | 88,7 % | 83,6 % |

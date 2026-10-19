# 14 – Gemeinsames Modell über Ligen

Automatisch erzeugt von `qf model joint-eval` am 19.10.2026 22:25 UTC. Ligen: Bundesliga, 2. Bundesliga.

**Frage:** Werden Prognosen besser, wenn verbundene Ligen gemeinsam gerechnet werden – mit einer Stärkeskala über alle Ligen und einer Ebene (Angriff/Abwehr) pro Liga – statt jede Liga getrennt?

**Methode:** Walk-Forward pro Spieltag (nur Spiele vor dem ersten Anpfiff, kein Data Leakage), Vollzeitmodell Dixon-Coles mit den Standardparametern. *Getrennt* = bisheriges Vorgehen (Liga allein, Teams ohne Spiel im letzten Jahr starten mit dem Aufsteiger-Prior). *Gemeinsam* = alle Ligen in einem Fit, die Stärke eines Teams wird zur zeitgewichteten Mischung der Ligaebenen gezogen, in denen es gespielt hat; verbunden sind die Ligen über Auf- und Absteiger. Kennzahlen: Log-Loss und RPS (1X2), Log-Loss Über/Unter 2,5 und Beide treffen – jeweils **kleiner ist besser**. Varianten wurden nur auf den Validierungssaisons verglichen (2018/19–2020/21); die Testsaisons (2021/22–2026/27) dienen allein der Bestätigung.

## Validierung: 2018/19–2020/21

### Bundesliga

| Spiele | n | Modell | Log-Loss 1X2 | RPS 1X2 | Log-Loss Ü/U 2,5 | Log-Loss BTTS |
|---|---:|---|---:|---:|---:|---:|
| alle | 918 | getrennt | 0,9926 | 0,2046 | 0,6629 | 0,6733 |
| alle | 918 | gemeinsam | 0,9919 | 0,2044 | 0,6625 | 0,6746 |
| mit Auf-/Absteiger | 228 | getrennt | 0,9702 | 0,2009 | 0,6663 | 0,6682 |
| mit Auf-/Absteiger | 228 | gemeinsam | 0,9700 | 0,2010 | 0,6665 | 0,6714 |
| Spieltag 1–10 | 270 | getrennt | 1,0167 | 0,2014 | 0,6521 | 0,6470 |
| Spieltag 1–10 | 270 | gemeinsam | 1,0130 | 0,2002 | 0,6479 | 0,6500 |
| Auf-/Absteiger, Spieltag 1–10 | 68 | getrennt | 0,9227 | 0,1872 | 0,6544 | 0,6640 |
| Auf-/Absteiger, Spieltag 1–10 | 68 | gemeinsam | 0,9092 | 0,1833 | 0,6388 | 0,6647 |

Differenz Log-Loss 1X2 (gemeinsam − getrennt, alle Spiele): **-0,0008**, 95-%-Intervall [-0,0059; 0,0046] (Bootstrap über Spiele) → gemeinsames Modell: **kein signifikanter Unterschied**.

### 2. Bundesliga

| Spiele | n | Modell | Log-Loss 1X2 | RPS 1X2 | Log-Loss Ü/U 2,5 | Log-Loss BTTS |
|---|---:|---|---:|---:|---:|---:|
| alle | 918 | getrennt | 1,0675 | 0,2212 | 0,6966 | 0,6825 |
| alle | 918 | gemeinsam | 1,0627 | 0,2197 | 0,6963 | 0,6819 |
| mit Auf-/Absteiger | 422 | getrennt | 1,0526 | 0,2176 | 0,6933 | 0,6919 |
| mit Auf-/Absteiger | 422 | gemeinsam | 1,0456 | 0,2153 | 0,6937 | 0,6902 |
| Spieltag 1–10 | 270 | getrennt | 1,0865 | 0,2253 | 0,6938 | 0,6854 |
| Spieltag 1–10 | 270 | gemeinsam | 1,0810 | 0,2236 | 0,6944 | 0,6845 |
| Auf-/Absteiger, Spieltag 1–10 | 127 | getrennt | 1,0604 | 0,2185 | 0,6912 | 0,6983 |
| Auf-/Absteiger, Spieltag 1–10 | 127 | gemeinsam | 1,0510 | 0,2154 | 0,6932 | 0,6977 |

Differenz Log-Loss 1X2 (gemeinsam − getrennt, alle Spiele): **-0,0048**, 95-%-Intervall [-0,0092; 0,0001] (Bootstrap über Spiele) → gemeinsames Modell: **kein signifikanter Unterschied**.

## Test: 2021/22–2026/27

### Bundesliga

| Spiele | n | Modell | Log-Loss 1X2 | RPS 1X2 | Log-Loss Ü/U 2,5 | Log-Loss BTTS |
|---|---:|---|---:|---:|---:|---:|
| alle | 1584 | getrennt | 0,9938 | 0,2037 | 0,6555 | 0,6669 |
| alle | 1584 | gemeinsam | 0,9896 | 0,2022 | 0,6550 | 0,6679 |
| mit Auf-/Absteiger | 347 | getrennt | 0,9916 | 0,2001 | 0,6520 | 0,6673 |
| mit Auf-/Absteiger | 347 | gemeinsam | 0,9760 | 0,1948 | 0,6512 | 0,6723 |
| Spieltag 1–10 | 504 | getrennt | 0,9791 | 0,2019 | 0,6493 | 0,6690 |
| Spieltag 1–10 | 504 | gemeinsam | 0,9677 | 0,1981 | 0,6467 | 0,6712 |
| Auf-/Absteiger, Spieltag 1–10 | 115 | getrennt | 0,9779 | 0,2090 | 0,6483 | 0,6718 |
| Auf-/Absteiger, Spieltag 1–10 | 115 | gemeinsam | 0,9416 | 0,1974 | 0,6416 | 0,6805 |

Differenz Log-Loss 1X2 (gemeinsam − getrennt, alle Spiele): **-0,0042**, 95-%-Intervall [-0,0078; -0,0003] (Bootstrap über Spiele) → gemeinsames Modell: **besser**.

### 2. Bundesliga

| Spiele | n | Modell | Log-Loss 1X2 | RPS 1X2 | Log-Loss Ü/U 2,5 | Log-Loss BTTS |
|---|---:|---|---:|---:|---:|---:|
| alle | 1602 | getrennt | 1,0523 | 0,2218 | 0,6809 | 0,6818 |
| alle | 1602 | gemeinsam | 1,0529 | 0,2219 | 0,6816 | 0,6833 |
| mit Auf-/Absteiger | 759 | getrennt | 1,0622 | 0,2219 | 0,6865 | 0,6788 |
| mit Auf-/Absteiger | 759 | gemeinsam | 1,0628 | 0,2221 | 0,6879 | 0,6816 |
| Spieltag 1–10 | 522 | getrennt | 1,0583 | 0,2239 | 0,6846 | 0,6870 |
| Spieltag 1–10 | 522 | gemeinsam | 1,0625 | 0,2253 | 0,6863 | 0,6903 |
| Auf-/Absteiger, Spieltag 1–10 | 249 | getrennt | 1,0791 | 0,2289 | 0,6813 | 0,6704 |
| Auf-/Absteiger, Spieltag 1–10 | 249 | gemeinsam | 1,0890 | 0,2322 | 0,6849 | 0,6753 |

Differenz Log-Loss 1X2 (gemeinsam − getrennt, alle Spiele): **0,0005**, 95-%-Intervall [-0,0035; 0,0049] (Bootstrap über Spiele) → gemeinsames Modell: **kein signifikanter Unterschied**.

## Teams neu in der Liga (Testsaisons, Spieltag 1–10)

Tatsächliche gegen erwartete Tordifferenz pro Spiel. Positive Abweichung = Team stärker als vom Modell erwartet.

| Liga | Herkunft | Modell | n | Tordifferenz | erwartet | Abweichung |
|---|---|---|---:|---:|---:|---:|
| Bundesliga | aus 2. Bundesliga | gemeinsam | 118 | -0,7966 | -0,8594 | 0,0628 |
| Bundesliga | aus 2. Bundesliga | getrennt | 118 | -0,7966 | -1,0191 | 0,2225 |
| 2. Bundesliga | aus Bundesliga | gemeinsam | 124 | -0,0806 | 0,4786 | -0,5592 |
| 2. Bundesliga | aus Bundesliga | getrennt | 124 | -0,0806 | -0,2680 | 0,1873 |
| 2. Bundesliga | ohne Daten (z. B. aus 3. Liga) | gemeinsam | 156 | -0,5769 | -0,8095 | 0,2326 |
| 2. Bundesliga | ohne Daten (z. B. aus 3. Liga) | getrennt | 156 | -0,5769 | -0,6004 | 0,0235 |

## Bewertung

- Das gemeinsame Modell nutzt für Aufsteiger deren Leistung in der unteren Liga statt eines pauschalen Startwerts; davon profitiert vor allem der Saisonbeginn der höheren Liga.
- Bekannte Schwäche: Absteiger werden in der unteren Liga zu Saisonbeginn überschätzt (Kaderumbruch nach dem Abstieg ist im Modell nicht abgebildet). Eine Korrektur dafür wurde auf den Validierungssaisons geprüft (Startwert nach aktueller Liga, milderer Aufsteiger-Prior) und brachte keine Verbesserung.
- Einstellung: `model.joint` auf der Einstellungsseite (Standard 1). Verbunden werden nur Ligen, die sich Teams teilen; andere Ligen werden weiterhin allein gerechnet.
- Grundlage für den nächsten Schritt: weitere Ligen und Europapokal auf derselben Skala.

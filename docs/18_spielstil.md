# 18 – Spielstil: Weiß er mehr als das Modell?

Automatisch erzeugt von `qf model style-eval` am 21.10.2026 09:04 UTC. Ligen: Bundesliga, 2. Bundesliga; 11876 Team-Spiele mit rückwirkender Prognose.

**Spielstil** = Profil aus den Statistiken der letzten 12 Ligaspiele vor dem Spiel (mindestens 5). **Ziel:** Tore eines Teams minus die vom Modell erwarteten Tore (Walk-Forward). Korrelation nahe 0 heißt: das Modell kennt die Information schon.

## 1. Zusammenhang mit den Toren über/unter Modell-Erwartung

| Merkmal vor dem Spiel | Spiele | Korrelation | 95-%-Intervall | auffällig |
|---|---:|---:|---|---|
| Schüsse pro Spiel | 11729 | +0,049 | +0,031 … +0,067 | ja |
| Schüsse aufs Tor pro Spiel | 11729 | +0,041 | +0,023 … +0,059 | ja |
| Anteil Schüsse aus dem Strafraum | 11729 | +0,005 | −0,013 … +0,024 |  |
| Ballbesitz | 11729 | +0,049 | +0,030 … +0,067 | ja |
| Anteil an allen Schüssen | 11729 | +0,052 | +0,034 … +0,070 | ja |
| Ertrag des Ballbesitzes | 11729 | +0,025 | +0,007 … +0,043 | ja |
| Tore pro Spiel | 11729 | +0,010 | −0,009 … +0,028 |  |
| Tore pro Schuss aufs Tor (Abschlussglück?) | 11729 | −0,028 | −0,046 … −0,010 | ja |
| xG pro Spiel | 2976 | +0,071 | +0,035 … +0,106 | ja |
| Tore minus xG | 2976 | −0,032 | −0,068 … +0,004 |  |
| Gegner: zugelassene Schüsse | 11729 | +0,033 | +0,015 … +0,051 | ja |
| Gegner: zugelassene Schüsse aufs Tor | 11729 | +0,005 | −0,014 … +0,023 |  |
| Gegner: Gegentore pro Spiel | 11729 | −0,042 | −0,060 … −0,024 | ja |
| Gegner: Paradenquote | 11729 | +0,058 | +0,040 … +0,076 | ja |
| Gegner: zugelassene xG | 2976 | +0,038 | +0,002 … +0,074 | ja |

## 2. Test auf späteren Saisons (Training bis 2021/22)

Lineare Korrektur der erwarteten Tore aus 7 Spielstil-Merkmalen (ohne xG, da erst ab 2022 vorhanden). Training 6530 Team-Spiele, Test 5060.

| | mittlerer quadratischer Fehler der Tore |
|---|---:|
| nur Modell | 1,5433 |
| Modell + Niveau-Korrektur (mittlere Abweichung im Training) | 1,5435 |
| Modell + Spielstil-Korrektur | 1,5333 |
| Verbesserung durch den Spielstil (ggü. Niveau-Korrektur) | +0,66 % (95 %: +0,0036 … +0,0176 absolut) |

Korrelation Korrektur ↔ tatsächlicher Rest im Test: +0,083 (+0,056 … +0,111).

Gewichte (Training): const −1,086, shots_on −0,002, shots +0,026, inside_share +0,405, conversion_on −0,470, possession_yield +0,121, opp_shots_on_against −0,007, opp_save_rate +1,060

## 3. Stil-Duelle: Ballbesitz Heim gegen Gast

Drittel nach Ballbesitz vor dem Spiel. Tore und Über 2,5 tatsächlich gegen Modell.

| Heim gegen Gast | Spiele | Tore | Modell | Differenz | Über 2,5 | Modell |
|---|---:|---:|---:|---:|---:|---:|
| viel gegen viel | 660 | 3,36 | 3,22 | +0,14 (± 0,07) | 65,0 % | 61,9 % |
| viel gegen mittel | 659 | 3,21 | 3,13 | +0,07 (± 0,07) | 65,4 % | 59,9 % |
| viel gegen wenig | 624 | 3,25 | 3,15 | +0,10 (± 0,07) | 63,5 % | 60,2 % |
| mittel gegen viel | 672 | 3,03 | 3,03 | −0,00 (± 0,07) | 59,2 % | 57,9 % |
| mittel gegen mittel | 617 | 2,93 | 2,89 | +0,04 (± 0,07) | 57,9 % | 54,9 % |
| mittel gegen wenig | 609 | 2,86 | 2,86 | +0,00 (± 0,07) | 56,0 % | 54,0 % |
| wenig gegen viel | 628 | 3,09 | 3,00 | +0,09 (± 0,07) | 57,6 % | 57,1 % |
| wenig gegen mittel | 620 | 2,79 | 2,81 | −0,02 (± 0,07) | 53,1 % | 53,0 % |
| wenig gegen wenig | 706 | 2,71 | 2,75 | −0,04 (± 0,06) | 51,4 % | 51,4 % |

## Bewertung

- Der Spielstil verbessert die Tor-Erwartung im Test messbar (+0,66 %). Kandidat für das Modell (nächster Schritt: als Merkmal einbauen und erneut prüfen).
- Auffällig (Intervall ohne 0, bei vielen getesteten Merkmalen mit Vorsicht): Schüsse pro Spiel (+0,049), Schüsse aufs Tor pro Spiel (+0,041), Ballbesitz (+0,049), Anteil an allen Schüssen (+0,052), Ertrag des Ballbesitzes (+0,025), Tore pro Schuss aufs Tor (Abschlussglück?) (−0,028), xG pro Spiel (+0,071), Gegner: zugelassene Schüsse (+0,033), Gegner: Gegentore pro Spiel (−0,042), Gegner: Paradenquote (+0,058), Gegner: zugelassene xG (+0,038).
- Der Spielstil wird auf der Detailseite angezeigt (Tab „Spielstil“) – als Beschreibung der Teams.

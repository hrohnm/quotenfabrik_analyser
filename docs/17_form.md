# 17 – Form-Pattern: Punkte über oder unter der Modell-Erwartung

Automatisch erzeugt von `qf model form-eval` am 20.10.2026 10:36 UTC.

**Form** = Mittel aus (Punkte − erwartete Punkte) der letzten 6 Pflichtspiele in allen Wettbewerben; erwartete Punkte = 3 × P(Sieg) + P(Remis) aus der rückwirkenden Prognose vor dem jeweiligen Spiel (Walk-Forward). Mindestens 4 Spiele mit Prognose. Signal ab ±0,5 Punkten pro Spiel.

**Frage:** Holt eine Mannschaft, die zuletzt mehr Punkte geholt hat als erwartet, auch im nächsten Spiel mehr als das Modell erwartet? Dann wüsste die Form etwas, das das Modell noch nicht weiß.

## Zusammenhang mit dem nächsten Spiel

| Merkmal vor dem Spiel | Spiele | Korrelation mit (Punkte − Erwartung) im Spiel | 95-%-Intervall |
|---|---:|---:|---|
| Form über/unter Erwartung (letzte 6) | 11638 | +0,005 | −0,014 … +0,023 |
| Punkte pro Spiel (letzte 6, roh) | 11618 | +0,010 | −0,008 … +0,028 |

## Nach Form-Gruppe

| Form vor dem Spiel | Spiele | Punkte | Modell erwartet | Differenz | Siegquote | Modell |
|---|---:|---:|---:|---:|---:|---:|
| deutlich unter Erwartung | 1962 | 1,30 | 1,32 | −0,01 (± 0,03) | 35,0 % | 35,3 % |
| leicht darunter | 2204 | 1,35 | 1,34 | +0,00 (± 0,03) | 36,9 % | 36,3 % |
| wie erwartet | 3445 | 1,36 | 1,36 | +0,01 (± 0,02) | 36,9 % | 36,7 % |
| leicht darüber | 2016 | 1,38 | 1,40 | −0,02 (± 0,03) | 36,5 % | 38,1 % |
| deutlich über Erwartung | 2011 | 1,46 | 1,43 | +0,03 (± 0,03) | 40,1 % | 39,3 % |

## Je Wettbewerb

| Wettbewerb | Spiele | Korrelation | 95-%-Intervall |
|---|---:|---:|---|
| 2. Bundesliga | 5540 | −0,011 | −0,038 … +0,015 |
| Bundesliga | 5988 | +0,015 | −0,011 … +0,040 |

## Bewertung

- Kein messbarer Zusatznutzen: Ob ein Team zuletzt über oder unter Erwartung lag, sagt nichts über das nächste Spiel, das das Modell nicht schon weiß. Das Modell gewichtet jüngere Spiele bereits stärker (Zeitgewichtung).
- Die Form wird auf der Detailseite als Pattern angezeigt (mit den letzten 10 Spielen). Sie fließt nicht in Prognosen oder Tipps ein, solange sie hier keinen klaren Zusatznutzen zeigt.

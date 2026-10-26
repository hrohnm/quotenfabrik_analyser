# 22 – Ausfälle, Aufstellung und Belastung

Automatisch erzeugt von `qf model availability-eval` am 26.10.2026 09:32 UTC. Ligen: Bundesliga, 2. Bundesliga. Basis: Produktionsmodell (gemeinsames Modell, Tore + Schüsse), Walk-Forward je Spieltag.

**Frage:** Kennt das Modell zu wenig über den Spieltag? Rotation vor/nach Europapokalspielen, wenige Ruhetage, fehlende Stammspieler und eine rotierte Startelf sind ihm bisher unbekannt.

## Situationen gegen die Modell-Erwartung

Verhältnis > 1 = mehr als erwartet. Punkte: Ø Differenz zu den erwarteten Punkten je Spiel.

| Situation | Spiele | Tore / erwartet | Gegentore / erwartet | Punkte vs. erwartet | Ø rotierte Stammspieler |
|---|---:|---:|---:|---:|---:|
| alle Ligaspiele | 12492 | 1,011 | 1,011 | −0,002 | 1,11 |
| Europapokalspiel folgt in ≤ 4 Tagen | 468 | 1,068 | 1,064 | −0,035 | 1,19 |
| Europapokalspiel ≤ 4 Tage zuvor | 639 | 0,997 | 0,998 | −0,075 | 1,14 |
| höchstens 3,5 Tage Pause | 1100 | 0,992 | 0,939 | +0,009 | 0,70 |
| mind. 2 Stammspieler fehlen | 352 | 0,984 | 1,075 | −0,075 | 1,16 |
| Topscorer fehlt (≥ 25 % der Tore + Vorlagen) | 277 | 0,996 | 1,019 | −0,044 | 1,39 |
| mind. 2 Stammspieler rotiert (Elf) | 3341 | 0,990 | 1,018 | −0,029 | 3,10 |

## Korrektur des Modells (Validierung → Test)

Korrekturfaktor je Team: exp(β · eigene Merkmale + γ · Merkmale des Gegners), auf den Validierungssaisons geschätzt.

| Variante | Saisons (Validierung → Test) | Spiele | Log-Loss 1X2 vorher → nachher | Δ (95 %) | Log-Loss Ü/U 2,5 | Log-Loss Beide treffen |
|---|---|---:|---|---|---|---|
| Termine (Ruhetage, Europapokal davor/danach) | 2016/17–2020/21 → 2021/22–2026/27 | 3186 | 1,0197 → 1,0197 | −0,0001 (−0,0008 … +0,0006) | 0,6668 → 0,6662 | 0,6750 → 0,6756 |
| Ausfälle (gemeldete Ausfälle, gewichtet) | 2021/22–2023/24 → 2024/25–2026/27 | 1350 | 1,0235 → 1,0233 | −0,0002 (−0,0037 … +0,0035) | 0,6626 → 0,6634 | 0,6784 → 0,6782 |
| Termine + Ausfälle | 2021/22–2023/24 → 2024/25–2026/27 | 1350 | 1,0235 → 1,0228 | −0,0007 (−0,0043 … +0,0032) | 0,6626 → 0,6628 | 0,6784 → 0,6784 |
| Termine + Ausfälle + Rotation (bestätigte Elf) | 2021/22–2023/24 → 2024/25–2026/27 | 1350 | 1,0235 → 1,0255 | +0,0020 (−0,0028 … +0,0069) | 0,6626 → 0,6630 | 0,6784 → 0,6781 |

### Koeffizienten (log-Faktor auf die erwarteten Tore)

- Termine (Ruhetage, Europapokal davor/danach): own_short_rest −0,031, own_prev_cup +0,021, own_next_cup +0,034, own_games_14d +0,007, opp_short_rest −0,114, opp_prev_cup +0,039, opp_next_cup +0,074, opp_games_14d +0,009
- Ausfälle (gemeldete Ausfälle, gewichtet): own_miss_starters −0,029, own_miss_attack −0,263, own_miss_defense +0,001, own_doubtful −0,035, opp_miss_starters +0,148, opp_miss_attack −0,665, opp_miss_defense −0,083, opp_doubtful +0,039
- Termine + Ausfälle: own_short_rest +0,074, own_prev_cup −0,045, own_next_cup +0,023, own_games_14d +0,007, own_miss_starters −0,033, own_miss_attack −0,250, own_miss_defense +0,005, own_doubtful −0,035, opp_short_rest −0,065, opp_prev_cup +0,018, opp_next_cup +0,058, opp_games_14d −0,006, opp_miss_starters +0,146, opp_miss_attack −0,681, opp_miss_defense −0,086, opp_doubtful +0,035
- Termine + Ausfälle + Rotation (bestätigte Elf): own_short_rest +0,073, own_prev_cup −0,036, own_next_cup +0,028, own_games_14d +0,008, own_miss_starters −0,042, own_miss_attack −0,254, own_miss_defense +0,004, own_doubtful −0,016, own_rotated −0,026, opp_short_rest −0,061, opp_prev_cup +0,009, opp_next_cup +0,054, opp_games_14d −0,008, opp_miss_starters +0,158, opp_miss_attack −0,684, opp_miss_defense −0,086, opp_doubtful +0,016, opp_rotated +0,027

## Bewertung

- Termine (Ruhetage, Europapokal davor/danach): tendenziell besser, aber nicht belastbar.
- Ausfälle (gemeldete Ausfälle, gewichtet): tendenziell besser, aber nicht belastbar.
- Termine + Ausfälle: tendenziell besser, aber nicht belastbar.
- Termine + Ausfälle + Rotation (bestätigte Elf): kein Gewinn.
- Rotation ist erst mit der bestätigten Aufstellung bekannt (20–40 Minuten vor Anpfiff); nutzbar nur mit einer Prognose kurz vor Anpfiff.
- Nicht abgedeckt: nationale Pokale (DFB-Pokal ist nicht in der Datenbank), Ausfall-Meldungen vor 2021.

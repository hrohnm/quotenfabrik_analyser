# 19 – Schüsse im Modell

Automatisch erzeugt von `qf model shots-eval` am 21.10.2026 09:10 UTC. Ligen: Bundesliga, 2. Bundesliga (gemeinsames Modell wie in der Produktion), Walk-Forward je Spieltag.

**Idee:** Das Modell schätzt die Teamstärke bisher nur aus Toren. Tore sind stark vom Zufall geprägt; Schüsse zeigen stabiler, wie gut ein Team ist (Nachweis: `18_spielstil.md`). Deshalb rechnet das Modell mit einer Mischung aus Toren und einer Schuss-Erwartung (Schüsse × Torquote pro Schuss der Trainingsspiele).

## Auswahl auf den Validierungssaisons 2018/19–2020/21

| Variante | Spiele | Log-Loss 1X2 | RPS 1X2 | Log-Loss Ü/U 2,5 | Log-Loss Beide treffen |
|---|---:|---:|---:|---:|---:|
| nur Tore (bisher) | 1836 | 1,0273 | 0,2121 | 0,6794 | 0,6783 |
| Schüsse aufs Tor, Gewicht 0,25 **← gewählt** | 1836 | 1,0265 | 0,2119 | 0,6765 | 0,6767 |
| Schüsse aufs Tor, Gewicht 0,50 | 1836 | 1,0273 | 0,2122 | 0,6743 | 0,6755 |
| Schüsse aufs Tor, Gewicht 0,75 | 1836 | 1,0294 | 0,2129 | 0,6729 | 0,6747 |
| alle Schüsse, Gewicht 0,25 | 1836 | 1,0266 | 0,2120 | 0,6764 | 0,6766 |
| alle Schüsse, Gewicht 0,50 | 1836 | 1,0285 | 0,2126 | 0,6750 | 0,6758 |
| alle Schüsse, Gewicht 0,75 | 1836 | 1,0329 | 0,2140 | 0,6753 | 0,6758 |

## Test auf 2021/22–2026/27 (kleiner = besser)

| Modell | Spiele | Log-Loss 1X2 | RPS 1X2 | Log-Loss Ü/U 2,5 | Log-Loss Beide treffen |
|---|---:|---:|---:|---:|---:|
| nur Tore (bisher) | 3186 | 1,0214 | 0,2121 | 0,6684 | 0,6757 |
| Schüsse aufs Tor, Gewicht 0,25 | 3186 | 1,0197 | 0,2116 | 0,6668 | 0,6750 |

Differenz Log-Loss 1X2 (gewählt − bisher): −0,0017 (95 %: −0,0029 … −0,0005).

| Liga | Modell | Log-Loss 1X2 | Log-Loss Ü/U 2,5 | Log-Loss Beide treffen |
|---|---|---:|---:|---:|
| Bundesliga | nur Tore (bisher) | 0,9896 | 0,6550 | 0,6679 |
| Bundesliga | Schüsse aufs Tor, Gewicht 0,25 | 0,9889 | 0,6541 | 0,6674 |
| 2. Bundesliga | nur Tore (bisher) | 1,0529 | 0,6816 | 0,6833 |
| 2. Bundesliga | Schüsse aufs Tor, Gewicht 0,25 | 1,0502 | 0,6794 | 0,6824 |

## Bewertung

- **Übernehmen:** „Schüsse aufs Tor, Gewicht 0,25“ ist im Test signifikant besser als das reine Tor-Modell (1X2-Log-Loss −0,0017, Intervall ohne 0).
- Tor-Märkte (Ü/U 2,5, Beide treffen) im Test: ebenfalls besser.

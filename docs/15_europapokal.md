# 15 – Europapokal: gemeinsame Stärkeskala über Ländergrenzen

Automatisch erzeugt von `qf model cup-eval` am 20.10.2026 05:58 UTC.

**Frage:** Lassen sich Spiele zwischen Teams aus verschiedenen Ländern (Champions League, Europa League, Conference League) vorhersagen, wenn alle Ligen und die Pokalspiele in einem gemeinsamen Modell gerechnet werden?

**Methode:** Walk-Forward pro Woche: Jede Woche mit Pokalspielen wird nur aus Spielen vor ihrem ersten Anpfiff vorhergesagt (kein Data Leakage). Grundlage sind die Ergebnisse von 1./2. Bundesliga, den Stärke-Ligen (erste Ligen Europas, inkl. Meister-/Abstiegsrunden) und der drei Europapokale. Pokalspiele gehen in die Teamstärken ein, bilden aber keine eigene Ligaebene; Endspiele zählen als neutraler Platz; abgerechnet wird nach 90 Minuten. Kennzahlen jeweils **kleiner ist besser**. Varianten wurden nur auf der Validierung (2019/20–2021/22) verglichen, der Test (2022/23–2026/27) bestätigt.

| Variante | Beschreibung |
|---|---|
| Basisrate | Häufigkeit von Heimsieg/Remis/Auswärtssieg, Über 2,5 und BTTS in Pokalspielen der letzten 3 Jahre |
| ohne Pokalspiele | gemeinsames Modell nur aus den Ligen – ohne Verbindung zwischen den Ländern gilt jede Liga als gleich stark (naiver Ansatz) |
| gemeinsam | Ligen und Pokalspiele in einem Modell: alle Teams auf einer Skala |
| gemeinsam + Heimvorteil | wie „gemeinsam“, mit eigenem Heimvorteil für Europapokalspiele |

## Validierung: 2019/20–2021/22

| Spiele | n | Modell | Log-Loss 1X2 | RPS 1X2 | Log-Loss Ü/U 2,5 | Log-Loss BTTS |
|---|---:|---|---:|---:|---:|---:|
| alle | 2070 | Basisrate | 1,0562 | 0,2333 | 0,6911 | 0,6935 |
| alle | 2070 | ohne Pokalspiele | 1,0478 | 0,2262 | 0,6930 | 0,6925 |
| alle | 2070 | gemeinsam | 0,9407 | 0,1927 | 0,6815 | 0,6908 |
| alle | 2070 | gemeinsam + Heimvorteil | 0,9404 | 0,1926 | 0,6811 | 0,6913 |
| Champions League | 604 | Basisrate | 1,0563 | 0,2379 | 0,6881 | 0,6945 |
| Champions League | 604 | ohne Pokalspiele | 1,0339 | 0,2240 | 0,6892 | 0,6907 |
| Champions League | 604 | gemeinsam | 0,9153 | 0,1873 | 0,6765 | 0,6899 |
| Champions League | 604 | gemeinsam + Heimvorteil | 0,9158 | 0,1876 | 0,6761 | 0,6901 |
| Europa League | 1044 | Basisrate | 1,0593 | 0,2332 | 0,6911 | 0,6932 |
| Europa League | 1044 | ohne Pokalspiele | 1,0509 | 0,2262 | 0,6958 | 0,6956 |
| Europa League | 1044 | gemeinsam | 0,9521 | 0,1955 | 0,6883 | 0,6923 |
| Europa League | 1044 | gemeinsam + Heimvorteil | 0,9522 | 0,1955 | 0,6880 | 0,6929 |
| Conference League | 422 | Basisrate | 1,0485 | 0,2272 | 0,6953 | 0,6930 |
| Conference League | 422 | ohne Pokalspiele | 1,0599 | 0,2290 | 0,6916 | 0,6876 |
| Conference League | 422 | gemeinsam | 0,9488 | 0,1934 | 0,6715 | 0,6886 |
| Conference League | 422 | gemeinsam + Heimvorteil | 0,9466 | 0,1928 | 0,6715 | 0,6890 |
| Qualifikation | 859 | Basisrate | 1,0557 | 0,2331 | 0,6950 | 0,6917 |
| Qualifikation | 859 | ohne Pokalspiele | 0,9928 | 0,2081 | 0,7048 | 0,6855 |
| Qualifikation | 859 | gemeinsam | 0,9323 | 0,1902 | 0,6844 | 0,6845 |
| Qualifikation | 859 | gemeinsam + Heimvorteil | 0,9317 | 0,1901 | 0,6835 | 0,6851 |
| Play-offs | 163 | Basisrate | 1,0229 | 0,2246 | 0,6823 | 0,6941 |
| Play-offs | 163 | ohne Pokalspiele | 1,0527 | 0,2282 | 0,6985 | 0,7025 |
| Play-offs | 163 | gemeinsam | 0,9499 | 0,1979 | 0,6959 | 0,6971 |
| Play-offs | 163 | gemeinsam + Heimvorteil | 0,9445 | 0,1963 | 0,6942 | 0,6971 |
| Gruppen-/Ligaphase | 766 | Basisrate | 1,0665 | 0,2334 | 0,6881 | 0,6949 |
| Gruppen-/Ligaphase | 766 | ohne Pokalspiele | 1,0916 | 0,2374 | 0,6806 | 0,7015 |
| Gruppen-/Ligaphase | 766 | gemeinsam | 0,9278 | 0,1852 | 0,6721 | 0,7000 |
| Gruppen-/Ligaphase | 766 | gemeinsam + Heimvorteil | 0,9284 | 0,1855 | 0,6722 | 0,7005 |
| K.-o.-Runde | 282 | Basisrate | 1,0492 | 0,2389 | 0,6923 | 0,6949 |
| K.-o.-Runde | 282 | ohne Pokalspiele | 1,0933 | 0,2495 | 0,6874 | 0,6839 |
| K.-o.-Runde | 282 | gemeinsam | 0,9961 | 0,2173 | 0,6896 | 0,6815 |
| K.-o.-Runde | 282 | gemeinsam + Heimvorteil | 0,9970 | 0,2177 | 0,6908 | 0,6815 |
| Rückspiele | 541 | Basisrate | 1,0257 | 0,2326 | 0,6929 | 0,6929 |
| Rückspiele | 541 | ohne Pokalspiele | 1,0335 | 0,2281 | 0,7104 | 0,6928 |
| Rückspiele | 541 | gemeinsam | 0,9516 | 0,2038 | 0,6942 | 0,6933 |
| Rückspiele | 541 | gemeinsam + Heimvorteil | 0,9495 | 0,2032 | 0,6928 | 0,6935 |
| beide Teams aus geladenen Ligen | 1258 | Basisrate | 1,0538 | 0,2312 | 0,6887 | 0,6946 |
| beide Teams aus geladenen Ligen | 1258 | ohne Pokalspiele | 1,0969 | 0,2424 | 0,6792 | 0,6944 |
| beide Teams aus geladenen Ligen | 1258 | gemeinsam | 0,9573 | 0,1972 | 0,6727 | 0,6907 |
| beide Teams aus geladenen Ligen | 1258 | gemeinsam + Heimvorteil | 0,9565 | 0,1971 | 0,6724 | 0,6912 |

- gemeinsam gegen „ohne Pokalspiele“ (Log-Loss 1X2, alle): **-0,1071** [-0,1248; -0,0900] → **besser**
- gemeinsam + Heimvorteil gegen „ohne Pokalspiele“ (Log-Loss 1X2, alle): **-0,1074** [-0,1252; -0,0905] → **besser**

## Test: 2022/23–2026/27

| Spiele | n | Modell | Log-Loss 1X2 | RPS 1X2 | Log-Loss Ü/U 2,5 | Log-Loss BTTS |
|---|---:|---|---:|---:|---:|---:|
| alle | 4044 | Basisrate | 1,0440 | 0,2302 | 0,6909 | 0,6938 |
| alle | 4044 | ohne Pokalspiele | 1,0418 | 0,2273 | 0,6860 | 0,6933 |
| alle | 4044 | gemeinsam | 0,9501 | 0,1974 | 0,6826 | 0,6911 |
| alle | 4044 | gemeinsam + Heimvorteil | 0,9481 | 0,1969 | 0,6824 | 0,6916 |
| Champions League | 1114 | Basisrate | 1,0373 | 0,2317 | 0,6865 | 0,6928 |
| Champions League | 1114 | ohne Pokalspiele | 1,0440 | 0,2309 | 0,6753 | 0,6873 |
| Champions League | 1114 | gemeinsam | 0,9258 | 0,1926 | 0,6587 | 0,6837 |
| Champions League | 1114 | gemeinsam + Heimvorteil | 0,9236 | 0,1920 | 0,6584 | 0,6845 |
| Europa League | 1006 | Basisrate | 1,0393 | 0,2298 | 0,6901 | 0,6940 |
| Europa League | 1006 | ohne Pokalspiele | 1,0933 | 0,2456 | 0,6952 | 0,7049 |
| Europa League | 1006 | gemeinsam | 0,9544 | 0,1996 | 0,6957 | 0,7016 |
| Europa League | 1006 | gemeinsam + Heimvorteil | 0,9523 | 0,1991 | 0,6960 | 0,7027 |
| Conference League | 1924 | Basisrate | 1,0503 | 0,2295 | 0,6938 | 0,6943 |
| Conference League | 1924 | ohne Pokalspiele | 1,0135 | 0,2157 | 0,6874 | 0,6907 |
| Conference League | 1924 | gemeinsam | 0,9620 | 0,1991 | 0,6896 | 0,6898 |
| Conference League | 1924 | gemeinsam + Heimvorteil | 0,9600 | 0,1985 | 0,6892 | 0,6900 |
| Qualifikation | 1668 | Basisrate | 1,0523 | 0,2294 | 0,6955 | 0,6947 |
| Qualifikation | 1668 | ohne Pokalspiele | 0,9975 | 0,2093 | 0,6877 | 0,6914 |
| Qualifikation | 1668 | gemeinsam | 0,9572 | 0,1965 | 0,6885 | 0,6900 |
| Qualifikation | 1668 | gemeinsam + Heimvorteil | 0,9554 | 0,1960 | 0,6885 | 0,6904 |
| Play-offs | 314 | Basisrate | 1,0423 | 0,2240 | 0,6897 | 0,6936 |
| Play-offs | 314 | ohne Pokalspiele | 1,0719 | 0,2307 | 0,6837 | 0,6908 |
| Play-offs | 314 | gemeinsam | 0,9650 | 0,1982 | 0,6905 | 0,6863 |
| Play-offs | 314 | gemeinsam + Heimvorteil | 0,9615 | 0,1971 | 0,6902 | 0,6878 |
| Gruppen-/Ligaphase | 1458 | Basisrate | 1,0257 | 0,2321 | 0,6862 | 0,6935 |
| Gruppen-/Ligaphase | 1458 | ohne Pokalspiele | 1,0560 | 0,2392 | 0,6826 | 0,6939 |
| Gruppen-/Ligaphase | 1458 | gemeinsam | 0,9105 | 0,1911 | 0,6734 | 0,6920 |
| Gruppen-/Ligaphase | 1458 | gemeinsam + Heimvorteil | 0,9076 | 0,1904 | 0,6729 | 0,6926 |
| K.-o.-Runde | 604 | Basisrate | 1,0659 | 0,2308 | 0,6901 | 0,6922 |
| K.-o.-Runde | 604 | ohne Pokalspiele | 1,1140 | 0,2465 | 0,6906 | 0,6982 |
| K.-o.-Runde | 604 | gemeinsam | 1,0187 | 0,2150 | 0,6847 | 0,6942 |
| K.-o.-Runde | 604 | gemeinsam + Heimvorteil | 1,0187 | 0,2149 | 0,6846 | 0,6945 |
| Rückspiele | 1284 | Basisrate | 1,0458 | 0,2280 | 0,6889 | 0,6939 |
| Rückspiele | 1284 | ohne Pokalspiele | 1,0295 | 0,2206 | 0,6884 | 0,6909 |
| Rückspiele | 1284 | gemeinsam | 0,9722 | 0,2023 | 0,6936 | 0,6880 |
| Rückspiele | 1284 | gemeinsam + Heimvorteil | 0,9699 | 0,2016 | 0,6928 | 0,6883 |
| beide Teams aus geladenen Ligen | 2419 | Basisrate | 1,0470 | 0,2306 | 0,6882 | 0,6936 |
| beide Teams aus geladenen Ligen | 2419 | ohne Pokalspiele | 1,0904 | 0,2444 | 0,6845 | 0,6938 |
| beide Teams aus geladenen Ligen | 2419 | gemeinsam | 0,9678 | 0,2027 | 0,6779 | 0,6905 |
| beide Teams aus geladenen Ligen | 2419 | gemeinsam + Heimvorteil | 0,9663 | 0,2023 | 0,6779 | 0,6914 |

- gemeinsam gegen „ohne Pokalspiele“ (Log-Loss 1X2, alle): **-0,0916** [-0,1040; -0,0790] → **besser**
- gemeinsam + Heimvorteil gegen „ohne Pokalspiele“ (Log-Loss 1X2, alle): **-0,0937** [-0,1062; -0,0812] → **besser**

## Stärke der Ligen (Ebene Angriff + Abwehr, letzter Stand)

Höher = stärker. Die Ebene ist der Ausgangswert der Teams einer Liga; einzelne Teams weichen davon ab.

| Liga | Ebene |
|---|---:|
| Premier League (England) | +1,27 |
| Bundesliga | +0,87 |
| La Liga (Spain) | +0,76 |
| Serie A (Italy) | +0,69 |
| Ligue 1 (France) | +0,66 |
| Primeira Liga (Portugal) | +0,39 |
| Jupiler Pro League (Belgium) | +0,32 |
| Superliga (Denmark) | +0,29 |
| Eliteserien (Norway) | +0,21 |
| Eredivisie (Netherlands) | +0,20 |
| Ekstraklasa (Poland) | +0,14 |
| Süper Lig (Turkey) | +0,12 |
| Super League 1 (Greece) | +0,08 |
| 2, Bundesliga | +0,06 |
| Super League (Switzerland) | +0,05 |
| Bundesliga (Austria) | +0,00 |
| Czech Liga (Czech-Republic) | -0,01 |
| Allsvenskan (Sweden) | -0,06 |
| NB I (Hungary) | -0,15 |
| HNL (Croatia) | -0,16 |
| 1, Division (Cyprus) | -0,19 |
| Premiership (Scotland) | -0,23 |
| Liga I (Romania) | -0,27 |
| Ligat Ha'al (Israel) | -0,28 |
| Premier League (Ukraine) | -0,36 |
| Super Liga (Serbia) | -0,43 |
| First League (Bulgaria) | -0,43 |
| Super Liga (Slovakia) | -0,46 |
| 1, SNL (Slovenia) | -0,53 |

## Auswirkung auf die Bundesliga-Prognosen

Test der eigenen Ligen (gleiche Saisons wie in `docs/14_gemeinsames_modell.md`): Modell aus den eigenen Ligen allein gegen Modell mit allen europäischen Ligen und Pokalspielen.

| Liga | n | Log-Loss 1X2 nur eigene Ligen | mit Europa | Differenz | 95-%-Intervall |
|---|---:|---:|---:|---:|---:|
| Bundesliga | 1584 | 0,9896 | 0,9886 | -0,0011 | [-0,0037; 0,0016] |
| 2. Bundesliga | 1602 | 1,0529 | 1,0530 | 0,0001 | [-0,0018; 0,0022] |

## Bewertung

- Ohne Verbindung zwischen den Ländern ist ein Modell aus Ligadaten bei Europapokalspielen nicht besser als die Basisrate – die Teamstärken der Ligen sind nicht vergleichbar. Erst die Pokalspiele legen alle Teams auf eine Skala; das senkt den Log-Loss 1X2 deutlich und in jedem Wettbewerb und jeder Runde.
- K.-o.-Runden bleiben am schwersten vorherzusagen (ausgeglichenere Paarungen); Rückspiele hängen zusätzlich vom Hinspiel ab, das im Modell noch nicht berücksichtigt ist.
- Ein eigener Heimvorteil für Europapokalspiele ist minimal besser und ist Standard (`cup_home_adv`).
- Für die eigenen Ligen bringt der Europa-Pool keinen messbaren Vorteil, kostet aber ein Vielfaches an Rechenzeit – sie werden weiterhin nur mit verbundenen Ligen (1./2. Bundesliga) gerechnet. Der Europa-Pool wird für Prognosen von Europapokalspielen verwendet.

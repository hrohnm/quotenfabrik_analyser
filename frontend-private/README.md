# Privates Frontend (Next.js)

Analyse-Oberfläche für den eigenen Gebrauch. Spricht nur mit der Backend-API (`backend/quotenfabrik/api`).
Kopfzeile: Navigation und Ligen-Auswahl als Dropdown (öffnet die Spieltage der Liga). Tipps zeigen beim Überfahren
(am Handy: Antippen) eine Karte, warum der Tipp gewählt wurde und warum er als wahrscheinlich gilt.

| Seite | Inhalt |
|---|---|
| `/spieltage` | Spiele pro Tag (Tagesleiste), Modellwahrscheinlichkeiten 1X2 / Über 2,5 / Beide treffen, Ergebnis und ob der Tipp eingetreten ist |
| `/team/[id]` | Mannschaft: Kopf mit Logo, Wettbewerben und Tabellenplatz, Trainer- und Stadionbild, Form, Kennzahlen; Tabs Übersicht (nächstes Spiel mit Prognose, letzte/nächste Spiele, Serien), Spiele (alle Wettbewerbe, Filter, Prognose und Tipp-Treffer), Statistik (Heim/Auswärts, Tore nach Minute, Spielstatistik gegen den Ligaschnitt, Punkte gegen das Modell), Kader (häufigste Startelf, Rotation, Spielerwerte mit Foto, Ausfälle). Teamnamen auf Detailseite, Tabelle, Form, Spielstil und Aufstellung verlinken hierher; Suche in der Kopfzeile |
| `/spiel/[id]` | Detail: Kopfbereich (Logos, Ergebnis, Torschützen, nach Abpfiff Zeitstrahl der Ereignisse: Tore, Karten, VAR, Wechsel ein-/ausblendbar, Details als Tooltip-Karte beim Überfahren bzw. Antippen), „Einschätzung“ (automatischer Text: Favorit, erwartete Tore, Form, Termine & Personal, Spielstil, Auffälliges, Spielverlauf, Torschützen, Markt, Tipps, nach Abpfiff Abgleich) Karte „Termine & Personal“ (letztes/nächstes Spiel mit Europapokal-Hinweis, fehlende Stammspieler und fragliche Spieler), „Auf einen Blick“ (1X2, Kernmärkte, Top-Torschützen, auffällige Pattern) und Tabs: Märkte (je Marktgruppe, Ü/U als kompakte Linientabellen, Betano-Quoten), Aufstellung (Spielfeld mit Formation und Trikotfarben, bestätigt oder voraussichtlich aus der letzten Startelf mit ersetzten Ausfällen, Bank, Ausfälle mit Grund), Letzte Spiele (10 je Team, alle Wettbewerbe, Form über/unter Modell-Erwartung), Spielstil (Ballbesitz, Offensivdruck, Verwertung, Defensive, Intensität mit Rang im Wettbewerb und Stil-Etiketten), Torschützen (mit Spielerfotos), Pattern (mit Ligaschnitt, Tor-Timing), Statistik, Liga (Tabelle gesamt/Heim/Auswärts/vor dem Spiel, Torjäger, Vorlagen, Torschützen beider Teams, Ligazahlen) |
| `/tipps` | Ein Spieltag (Pfeile springen zum vorigen/nächsten Tag mit Spielen, Start: heute bzw. nächster Spieltag): Tageskombis (morgens fixiert, danach unverändert; Tore Über, Team-Tore Über, Doppelte Chance, Quote 5–10) mit „Als Wette erfassen“, 3 Tipps pro Spiel (Profile Sicher / Ausgewogen / Mutig), Trefferquote einzeln und als Kombi |
| `/wetten` | Wett-Tracking: erfasste Wetten (Tageskombis, 3 Tipps, frei), automatische Abrechnung, Korrektur von Einsatz, Quote, Status und Auszahlung (Cashout, Boost), Einsatz, Gewinn, ROI, Trefferquote gegen Modell-Erwartung, Gewinnverlauf; Bankroll (Startkapital, Ein-/Auszahlungen, Kontostand, verfügbar, Rendite); Auswertung zurücksetzen (neuer Zeitraum) |
| `/explorer` | Daten-Explorer: ein Markt über alle Spiele (Saison, Team, Heim/Auswärts, Wahrscheinlichkeitsbereich, Ergebnis), inkl. vergangener Spiele (Backtest) |
| `/auswertung` | Trefferquoten pro Liga, Saison, Marktgruppe und Markt; Trefferquote nach Konfidenz, je Saison, Kalibrierung, Torschützen |
| `/einstellungen` | API-Kontingent, Backups (Download, „Backup jetzt“), Ligen (aktiv schalten, hinzufügen mit Request-Schätzung), Stärke-Ligen (27 erste Ligen Europas, nur Ergebnisse), Einstellungen (Schwellen der Tipp-Profile, Modellparameter, Reserven), Fortschritt der Hintergrund-Jobs |

Vergangene Spiele zeigen die **rückwirkende Walk-Forward-Prognose** (`qf model backtest`): Das Modell wurde für jeden
Spieltag nur mit Spielen davor trainiert. Kommende Spiele zeigen die letzte Prognose vor Anpfiff (`qf model forecast`).

## Start

```bash
# Backend (Terminal 1)
cd backend && uvicorn quotenfabrik.api.main:app --port 8000

# Frontend (Terminal 2)
cd frontend-private
npm install
npm run dev            # http://localhost:3000
```

Umgebungsvariable `API_URL` (Standard `http://127.0.0.1:8000`): Adresse der Backend-API. Der Browser ruft `/api/*`
auf, Next.js leitet an die API weiter (siehe `next.config.ts`).

Stack: Next.js 15 (App Router), React 19, TypeScript, Tailwind CSS 4, Recharts.

Logos und Spielerfotos kommen von `media.api-sports.io` (kostet keine API-Quota, über `next/image` gecacht); fehlt ein Bild, werden Initialen angezeigt.

# Privates Frontend (Next.js)

Analyse-Oberfläche für den eigenen Gebrauch. Spricht nur mit der Backend-API (`backend/quotenfabrik/api`).

| Seite | Inhalt |
|---|---|
| `/spieltage` | Spiele pro Tag (Tagesleiste), Modellwahrscheinlichkeiten 1X2 / Über 2,5 / Beide treffen, Ergebnis und ob der Tipp eingetreten ist |
| `/spiel/[id]` | Detail: Kopfbereich (Logos, Ergebnis, Torschützen), „Einschätzung“ (automatischer Text: Favorit, erwartete Tore, Form, Spielstil, Auffälliges, Spielverlauf, Torschützen, Markt, Tipps, nach Abpfiff Abgleich) „Auf einen Blick“ (1X2, Kernmärkte, Top-Torschützen, auffällige Pattern) und Tabs: Märkte (je Marktgruppe, Ü/U als kompakte Linientabellen, Betano-Quoten), Letzte Spiele (10 je Team, alle Wettbewerbe, Form über/unter Modell-Erwartung), Spielstil (Ballbesitz, Offensivdruck, Verwertung, Defensive, Intensität mit Rang im Wettbewerb und Stil-Etiketten), Torschützen (mit Spielerfotos), Pattern (mit Ligaschnitt, Tor-Timing), Statistik |
| `/tipps` | Ein Spieltag (Pfeile springen zum vorigen/nächsten Tag mit Spielen, Start: heute bzw. nächster Spieltag): Tageskombis (Tore Über, Team-Tore Über, Doppelte Chance, Quote 5–10) mit „Als Wette erfassen“, 3 Tipps pro Spiel (Profile Sicher / Ausgewogen / Mutig), Trefferquote einzeln und als Kombi |
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

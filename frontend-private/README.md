# Privates Frontend (Next.js)

Analyse-Oberfläche für den eigenen Gebrauch. Spricht nur mit der Backend-API (`backend/quotenfabrik/api`).

| Seite | Inhalt |
|---|---|
| `/spieltage` | Spiele pro Tag (Tagesleiste), Modellwahrscheinlichkeiten 1X2 / Über 2,5 / Beide treffen, Ergebnis und ob der Tipp eingetreten ist |
| `/spiel/[id]` | Detail: alle Märkte je Marktgruppe mit Wahrscheinlichkeit, fairer Quote und Ergebnis, Torschützen, Pattern, Tor-Timing, Spielstatistik |
| `/explorer` | Daten-Explorer: ein Markt über alle Spiele (Saison, Team, Heim/Auswärts, Wahrscheinlichkeitsbereich, Ergebnis), inkl. vergangener Spiele (Backtest) |
| `/auswertung` | Trefferquoten pro Liga, Saison, Marktgruppe und Markt; Trefferquote nach Konfidenz, je Saison, Kalibrierung, Torschützen |

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

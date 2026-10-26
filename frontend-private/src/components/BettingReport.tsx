"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Card } from "@/components/ui";
import { api } from "@/lib/api";
import { dateShort, odd, pct, signedPct } from "@/lib/format";
import type { BettingReport as Report, BetsSummary } from "@/lib/types";

/** Tab "Wetten & Modell" of the competition and team pages (``path``: API endpoint of the report). */
export function BettingReport({ path, season, scope }: { path: string; season: number; scope: string }) {
  const [r, setR] = useState<Report | null>(null);
  const [error, setError] = useState(false);
  useEffect(() => {
    let current = true;
    setR(null);
    setError(false);
    api<Report>(path, { season }).then((x) => current && setR(x)).catch(() => current && setError(true));
    return () => { current = false; };
  }, [path, season]);
  if (error) return <Card><p className="text-sm text-rose-700">Auswertung konnte nicht geladen werden.</p></Card>;
  if (!r) return <Card><p className="text-sm text-slate-400">Wird geladen …</p></Card>;
  return (
    <div className="space-y-4">
      <p className="text-xs text-slate-500">
        Rückblick auf die beendeten Spiele {scope} in dieser Saison: Prognosen und Tipps so, wie sie vor Anpfiff galten (fixierter bzw. letzter Lauf
        vor Anpfiff). Kleine Stichproben schwanken stark – das ist eine Bilanz, kein Wettsignal.
      </p>
      <div className="grid gap-4 lg:grid-cols-2">
        <ModelCard r={r} />
        <PicksCard r={r} />
        <MarketCard r={r} />
        <BetsCard bets={r.bets} />
      </div>
    </div>
  );
}

function Rate({ hit, expected }: { hit: number | null | undefined; expected: number | null | undefined }) {
  if (hit == null) return <span className="text-slate-400">–</span>;
  const diff = expected != null ? hit - expected : 0;
  return (
    <span className="whitespace-nowrap tabular-nums">
      <b>{pct(hit, 0)}</b>
      {expected != null && <span className={`ml-1 text-xs ${diff >= 0.02 ? "text-emerald-700" : diff <= -0.02 ? "text-rose-700" : "text-slate-400"}`}>(erw. {pct(expected, 0)})</span>}
    </span>
  );
}

function ModelCard({ r }: { r: Report }) {
  const m = r.model;
  if (m.fixtures === 0) return <Card title="Modell"><p className="text-sm text-slate-500">Noch keine abgerechneten Prognosen.</p></Card>;
  return (
    <Card title={`Modell · ${m.fixtures} Spiele`}>
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
        {m.groups.map((g) => (
          <div key={g.group} className="rounded-lg bg-slate-50 p-2 text-center" title={`${g.n} Auswahlen`}>
            <div className="text-[11px] uppercase tracking-wide text-slate-500">{g.label}</div>
            <div className="text-lg font-semibold tabular-nums">{pct(g.hit_rate, 0)}</div>
            <div className="text-[11px] text-slate-400">erwartet {pct(g.expected, 0)}</div>
          </div>
        ))}
      </div>
      <table className="mt-3 w-full text-sm">
        <thead>
          <tr className="text-[11px] uppercase tracking-wide text-slate-400">
            <th className="py-1 text-left font-medium">Markt</th>
            <th className="py-1 text-left font-medium">meist gewählt</th>
            <th className="py-1 text-right font-medium">Treffer</th>
          </tr>
        </thead>
        <tbody>
          {m.markets.map((x) => (
            <tr key={`${x.market}${x.line}`} className="border-t border-slate-50">
              <td className="py-1.5 text-slate-700">{x.label}</td>
              <td className="py-1.5 text-slate-500">{x.most_picked}</td>
              <td className="py-1.5 text-right"><Rate hit={x.hit_rate} expected={x.expected} /></td>
            </tr>
          ))}
        </tbody>
      </table>
      {m.calibration.length > 0 && (
        <div className="mt-4">
          <h3 className="mb-1.5 text-[11px] font-semibold uppercase tracking-wide text-slate-500">Kalibrierung (alle Märkte)</h3>
          <div className="grid grid-cols-10 items-end gap-1">
            {m.calibration.map((c) => (
              <div key={c.bin} className="flex flex-col items-center" title={`${c.bin}: vorhergesagt ${pct(c.predicted, 0)}, eingetreten ${pct(c.observed, 0)} (${c.n})`}>
                <div className="relative h-20 w-full rounded bg-slate-50">
                  <div className="absolute bottom-0 left-0 right-0 rounded bg-emerald-500/80" style={{ height: `${c.observed * 100}%` }} />
                  <div className="absolute left-0 right-0 h-0.5 bg-slate-900" style={{ bottom: `${c.predicted * 100}%` }} />
                </div>
                <span className="mt-0.5 text-[9px] text-slate-400">{c.bin.split("–")[0]}</span>
              </div>
            ))}
          </div>
          <p className="mt-1 text-[11px] text-slate-400">Balken: eingetreten, Strich: vorhergesagt – je Wahrscheinlichkeitsstufe.</p>
        </div>
      )}
    </Card>
  );
}

function PicksCard({ r }: { r: Report }) {
  if (r.picks.length === 0) return <Card title="Unsere 3 Tipps"><p className="text-sm text-slate-500">Noch keine abgerechneten Tipps.</p></Card>;
  const main = r.picks.find((p) => p.profile === "ausgewogen") ?? r.picks[0];
  return (
    <Card title="Unsere 3 Tipps">
      <div className="grid grid-cols-3 gap-2">
        {r.picks.map((p) => (
          <div key={p.profile} className="rounded-lg bg-slate-50 p-2 text-center">
            <div className="text-[11px] uppercase tracking-wide text-slate-500">{p.label}</div>
            <div className="text-lg font-semibold tabular-nums">{p.singles.hit_rate != null ? pct(p.singles.hit_rate, 0) : "–"}</div>
            <div className="text-[11px] text-slate-400">erw. {p.singles.expected != null ? pct(p.singles.expected, 0) : "–"} · Kombi {p.combo.hit_rate != null ? pct(p.combo.hit_rate, 0) : "–"}</div>
          </div>
        ))}
      </div>
      {main.markets.length > 0 && (
        <>
          <h3 className="mb-1 mt-3 text-[11px] font-semibold uppercase tracking-wide text-slate-500">Tipp-Arten im Profil {main.label}</h3>
          <ul className="space-y-1 text-sm">
            {main.markets.map((m) => (
              <li key={m.label} className="flex justify-between gap-2">
                <span className="truncate text-slate-700">{m.label} <span className="text-xs text-slate-400">({m.n})</span></span>
                <Rate hit={m.hit_rate} expected={m.expected} />
              </li>
            ))}
          </ul>
        </>
      )}
      <p className="mt-2 text-[11px] text-slate-400">Einzeltipps: Trefferquote gegen die mittlere Modell-Wahrscheinlichkeit. Kombi: alle 3 Tipps eines Spiels getroffen.</p>
    </Card>
  );
}

function MarketCard({ r }: { r: Report }) {
  const m = r.market;
  if (m.selections === 0) return <Card title="Betano gegen Pinnacle und Modell"><p className="text-sm text-slate-500">Keine Betano-Quoten zu den beendeten Spielen.</p></Card>;
  return (
    <Card title={`Betano gegen Pinnacle und Modell · ${m.fixtures} Spiele`}>
      <div className="-mx-4 overflow-x-auto">
        <table className="w-full min-w-[30rem] text-sm tabular-nums">
          <thead>
            <tr className="text-[11px] uppercase tracking-wide text-slate-400">
              <th className="px-4 py-1 text-left font-medium">Markt</th>
              <th className="px-2 py-1 text-right font-medium" title="Betano-Quote × faire Pinnacle-Wahrscheinlichkeit: erwartete Auszahlung je Euro, wenn Pinnacle recht hat">Auszahlung</th>
              <th className="px-2 py-1 text-right font-medium" title="Anteil der Auswahlen, bei denen Betano mehr zahlt als der faire Pinnacle-Preis">über Pinnacle</th>
              <th className="px-2 py-1 text-right font-medium" title="Anteil mit Modell-Vorteil (Wahrscheinlichkeit × Betano-Quote > 1)">Modell-Vorteil</th>
              <th className="px-4 py-1 text-right font-medium" title="Ergebnis, wenn man alle Auswahlen mit Modell-Vorteil zu 1 Einheit gespielt hätte">Rendite</th>
            </tr>
          </thead>
          <tbody>
            {m.groups.map((g) => (
              <tr key={g.group} className="border-t border-slate-50">
                <td className="px-4 py-1.5 text-slate-700">{g.label}</td>
                <td className="px-2 py-1.5 text-right">{g.payback != null ? pct(g.payback, 1) : "–"}</td>
                <td className="px-2 py-1.5 text-right">{g.above_pinnacle != null ? pct(g.above_pinnacle, 0) : "–"}</td>
                <td className="px-2 py-1.5 text-right">{pct(g.edge_share, 0)}</td>
                <td className={`px-4 py-1.5 text-right ${g.value_roi == null ? "" : g.value_roi >= 0 ? "text-emerald-700" : "text-rose-700"}`}>
                  {g.value_roi != null ? `${signedPct(g.value_roi)} (${g.value_bets})` : "–"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="mt-2 text-[11px] text-slate-400">Letzte Betano-Quote vor Anpfiff (OddsPapi). Auszahlung unter 100 % = Marge des Buchmachers gegenüber dem fairen Pinnacle-Preis.</p>
    </Card>
  );
}

const STATUS: Record<string, string> = { open: "offen", won: "gewonnen", lost: "verloren", void: "storniert" };

export function BetsCard({ bets, title = "Eigene Wetten" }: { bets: BetsSummary; title?: string }) {
  if (bets.bets === 0) {
    return <Card title={title}><p className="text-sm text-slate-500">Keine erfassten Wetten. <Link href="/wetten" className="text-emerald-700 hover:underline">Zu den Wetten</Link></p></Card>;
  }
  return (
    <Card title={title}>
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
        <Tile label="Wetten" value={`${bets.bets}`} hint={`${bets.won} gewonnen · ${bets.lost} verloren · ${bets.open} offen`} />
        <Tile label="Einsatz" value={`${odd(bets.stake)} €`} />
        <Tile label="Gewinn" value={`${bets.profit >= 0 ? "+" : "−"}${odd(Math.abs(bets.profit))} €`} tone={bets.profit >= 0 ? "text-emerald-700" : "text-rose-700"} />
        <Tile label="Rendite" value={bets.roi != null ? signedPct(bets.roi) : "–"} tone={bets.roi != null && bets.roi >= 0 ? "text-emerald-700" : "text-rose-700"} />
      </div>
      <p className="mt-2 text-xs text-slate-500">Tipps aus diesen Wetten: {bets.legs_won} von {bets.legs_settled} abgerechneten getroffen.</p>
      <ul className="mt-2 divide-y divide-slate-100 text-sm">
        {bets.recent.map((b) => (
          <li key={b.id} className="flex items-center gap-2 py-1.5">
            <span className="w-16 text-xs tabular-nums text-slate-500">{dateShort(b.placed_at)}</span>
            <span className="min-w-0 flex-1 truncate">{b.label}</span>
            <span className="text-xs tabular-nums text-slate-500">{odd(b.odds)}</span>
            <span className={`rounded px-1.5 text-[10px] font-semibold ${b.status === "won" ? "bg-emerald-100 text-emerald-800" : b.status === "lost" ? "bg-rose-100 text-rose-700" : "bg-slate-100 text-slate-600"}`}>{STATUS[b.status] ?? b.status}</span>
          </li>
        ))}
      </ul>
    </Card>
  );
}

function Tile({ label, value, hint, tone = "" }: { label: string; value: string; hint?: string; tone?: string }) {
  return (
    <div className="rounded-lg bg-slate-50 p-2 text-center" title={hint}>
      <div className="text-[11px] uppercase tracking-wide text-slate-500">{label}</div>
      <div className={`text-lg font-semibold tabular-nums ${tone}`}>{value}</div>
    </div>
  );
}

"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { api, apiSend } from "@/lib/api";
import { dateShort, odd, pct, signedPct, time } from "@/lib/format";
import type { BetBlock, BetItem, BetStats, BetStatus } from "@/lib/types";
import { Card, OutcomeBadge, StatTile } from "@/components/ui";
import { BetDialog, type BetDraft } from "@/components/bets/BetDialog";

const euro = (v: number | null | undefined) =>
  v === null || v === undefined ? "–" : `${v.toLocaleString("de-DE", { minimumFractionDigits: 2, maximumFractionDigits: 2 })} €`;

const SOURCE_LABEL: Record<string, string> = { tageskombi: "Tageskombis", tipps: "3 Tipps pro Spiel", manuell: "Manuell" };
const STATUS_LABEL: Record<BetStatus, string> = { open: "offen", won: "gewonnen", lost: "verloren", void: "storniert" };
const STATUS_CLASS: Record<BetStatus, string> = {
  open: "bg-slate-100 text-slate-600",
  won: "bg-emerald-100 text-emerald-700",
  lost: "bg-rose-100 text-rose-700",
  void: "bg-amber-100 text-amber-700",
};

export default function BetsPage() {
  const [data, setData] = useState<{ bets: BetItem[]; stats: BetStats } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [manual, setManual] = useState<BetDraft | null>(null);
  const [manualLabel, setManualLabel] = useState("");
  const [manualOdds, setManualOdds] = useState("");

  const load = useCallback(() => {
    api<{ bets: BetItem[]; stats: BetStats }>("/bets").then(setData).catch((e) => setError(String(e instanceof Error ? e.message : e)));
  }, []);
  useEffect(load, [load]);

  const act = async (fn: () => Promise<unknown>) => {
    try {
      await fn();
      load();
    } catch (e) {
      setError(String(e instanceof Error ? e.message : e));
    }
  };

  const openManual = () => {
    const o = Number(manualOdds.replace(",", "."));
    if (!manualLabel.trim() || !(o > 1)) return;
    setManual({ label: manualLabel.trim(), source: "manuell", odds: o, probability: null, legs: [] });
  };

  const t = data?.stats.total;
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Wetten</h1>
        <p className="max-w-3xl text-sm text-slate-500">
          Erfasste Wetten mit Einsatz und tatsächlicher Quote. Wetten mit Modell-Tipps werden nach Spielende automatisch abgerechnet
          (90 Minuten); freie Wetten setzt du selbst auf gewonnen oder verloren. Erfassen: auf der Seite <Link href="/tipps" className="text-emerald-700 hover:underline">Tipps</Link> oder unten.
        </p>
      </div>
      {error && <p className="rounded-md bg-rose-50 p-3 text-sm text-rose-700">{error}</p>}

      {t && (
        <div className="grid grid-cols-2 gap-3 sm:gap-4 lg:grid-cols-5">
          <StatTile label="Einsatz" value={euro(t.stake ?? 0)} hint={`${t.n} abgerechnet · ${data.stats.open} offen`} />
          <StatTile label="Rückfluss" value={euro(t.return ?? 0)} />
          <StatTile label="Gewinn" value={euro(t.profit ?? 0)} tone={(t.profit ?? 0) > 0 ? "good" : (t.profit ?? 0) < 0 ? "bad" : undefined}
            hint={t.expected_profit != null ? `Modell erwartet ${euro(t.expected_profit)}` : undefined} />
          <StatTile label="ROI" value={t.roi != null ? signedPct(t.roi) : "–"} tone={(t.roi ?? 0) > 0 ? "good" : (t.roi ?? 0) < 0 ? "bad" : undefined} />
          <StatTile label="Trefferquote" value={t.n ? pct(t.hit_rate ?? null) : "–"}
            hint={t.expected_hit_rate != null ? `Modell erwartet ${pct(t.expected_hit_rate)} · Ø Quote ${odd(t.avg_odds ?? null)}` : undefined} />
        </div>
      )}

      {data && data.stats.curve.length > 1 && (
        <div className="grid gap-4 lg:grid-cols-3">
          <Card title="Gewinnverlauf" className="lg:col-span-2"><ProfitCurve curve={data.stats.curve} /></Card>
          <Card title="Nach Herkunft"><SourceTable bySource={data.stats.by_source} /></Card>
        </div>
      )}

      <Card title="Freie Wette erfassen">
        <div className="flex flex-wrap items-end gap-3">
          <label className="min-w-64 flex-1 text-xs font-medium text-slate-500">
            Beschreibung
            <input value={manualLabel} onChange={(e) => setManualLabel(e.target.value)} placeholder="z. B. Bayern gewinnt + Über 2,5" className="mt-1 w-full rounded-md border border-slate-300 px-2 py-1.5 text-sm text-slate-900" />
          </label>
          <label className="w-28 text-xs font-medium text-slate-500">
            Quote
            <input inputMode="decimal" value={manualOdds} onChange={(e) => setManualOdds(e.target.value)} className="mt-1 w-full rounded-md border border-slate-300 px-2 py-1.5 text-sm text-slate-900" />
          </label>
          <button type="button" onClick={openManual} className="rounded-md bg-slate-900 px-4 py-2 text-sm text-white">weiter</button>
        </div>
      </Card>

      <section className="space-y-3">
        <h2 className="text-lg font-semibold">Alle Wetten</h2>
        {data && data.bets.length === 0 && <Card><p className="text-sm text-slate-500">Noch keine Wetten erfasst.</p></Card>}
        {data?.bets.map((b) => (
          <BetRow
            key={b.id}
            bet={b}
            onStatus={(s) => act(() => apiSend("PATCH", `/bets/${b.id}`, { status: s }))}
            onDelete={() => window.confirm(`Wette „${b.label}“ löschen?`) && act(() => apiSend("DELETE", `/bets/${b.id}`))}
          />
        ))}
      </section>

      {manual && <BetDialog draft={manual} onClose={() => { setManual(null); setManualLabel(""); setManualOdds(""); }} onSaved={load} />}
    </div>
  );
}

function BetRow({ bet, onStatus, onDelete }: { bet: BetItem; onStatus: (s: BetStatus) => void; onDelete: () => void }) {
  const auto = bet.legs.length > 0 && bet.legs.every((l) => l.market);
  return (
    <Card>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <span className={`rounded px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wide ${STATUS_CLASS[bet.status]}`}>{STATUS_LABEL[bet.status]}</span>
            <span className="font-medium">{bet.label}</span>
          </div>
          <div className="mt-0.5 text-xs text-slate-500">
            {SOURCE_LABEL[bet.source] ?? bet.source} · {bet.bookmaker} · erfasst {dateShort(bet.placed_at)} {time(bet.placed_at)}
            {bet.probability != null && <> · Modell {pct(bet.probability)}</>}
            {bet.notes && <> · {bet.notes}</>}
          </div>
        </div>
        <div className="text-right text-sm tabular-nums">
          <div>{euro(bet.stake)} × {odd(bet.odds)}</div>
          {bet.payout != null && <div className={`font-semibold ${bet.payout > bet.stake ? "text-emerald-700" : bet.payout < bet.stake ? "text-rose-700" : ""}`}>{euro(bet.payout - bet.stake)}</div>}
        </div>
      </div>
      {bet.legs.length > 0 && (
        <ul className="mt-3 space-y-1 text-sm">
          {bet.legs.map((l, i) => (
            <li key={i} className="flex items-center justify-between gap-3 border-t border-slate-100 pt-1">
              {l.fixture_id ? <Link href={`/spiel/${l.fixture_id}`} className="min-w-0 hover:opacity-80">{l.label}</Link> : <span>{l.label}</span>}
              <span className="flex shrink-0 items-center gap-2 text-xs tabular-nums text-slate-500">
                {l.ft_home != null && <span>{l.ft_home}:{l.ft_away}</span>}
                {l.ft_home == null && l.kickoff && <span>{dateShort(l.kickoff)} {time(l.kickoff)}</span>}
                <OutcomeBadge outcome={l.outcome} small />
              </span>
            </li>
          ))}
        </ul>
      )}
      <div className="mt-3 flex flex-wrap gap-3 text-xs">
        {bet.status === "open" && !auto && (
          <>
            <button type="button" onClick={() => onStatus("won")} className="text-emerald-700 hover:underline">gewonnen</button>
            <button type="button" onClick={() => onStatus("lost")} className="text-rose-700 hover:underline">verloren</button>
          </>
        )}
        {bet.status === "open" && <button type="button" onClick={() => onStatus("void")} className="text-amber-700 hover:underline">stornieren</button>}
        {bet.status !== "open" && !auto && <button type="button" onClick={() => onStatus("open")} className="text-slate-500 hover:underline">wieder öffnen</button>}
        <button type="button" onClick={onDelete} className="text-slate-400 hover:text-rose-700 hover:underline">löschen</button>
      </div>
    </Card>
  );
}

function SourceTable({ bySource }: { bySource: Record<string, BetBlock> }) {
  return (
    <table className="w-full text-sm">
      <thead><tr className="text-left text-xs text-slate-400"><th className="pb-2 font-medium" /><th className="pb-2 text-right font-medium">Wetten</th><th className="pb-2 text-right font-medium">Treffer</th><th className="pb-2 text-right font-medium">ROI</th></tr></thead>
      <tbody className="divide-y divide-slate-100">
        {Object.entries(bySource).map(([k, b]) => (
          <tr key={k}>
            <td className="py-1.5">{SOURCE_LABEL[k] ?? k}</td>
            <td className="py-1.5 text-right tabular-nums">{b.n}</td>
            <td className="py-1.5 text-right tabular-nums">{pct(b.hit_rate ?? null, 0)}</td>
            <td className={`py-1.5 text-right font-semibold tabular-nums ${(b.roi ?? 0) >= 0 ? "text-emerald-700" : "text-rose-700"}`}>{b.roi != null ? signedPct(b.roi) : "–"}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

/** Cumulative profit after each settled bet (simple SVG line, zero line dashed). */
function ProfitCurve({ curve }: { curve: { at: string; profit: number }[] }) {
  const W = 600, H = 180, P = 8;
  const values = [0, ...curve.map((c) => c.profit)];
  const lo = Math.min(...values), hi = Math.max(...values);
  const span = hi - lo || 1;
  const x = (i: number) => P + (i / (values.length - 1)) * (W - 2 * P);
  const y = (v: number) => P + (1 - (v - lo) / span) * (H - 2 * P);
  const path = values.map((v, i) => `${i ? "L" : "M"}${x(i).toFixed(1)},${y(v).toFixed(1)}`).join(" ");
  const last = values[values.length - 1];
  return (
    <div>
      <svg viewBox={`0 0 ${W} ${H}`} className="h-44 w-full" preserveAspectRatio="none" role="img" aria-label="Gewinnverlauf">
        <line x1={P} x2={W - P} y1={y(0)} y2={y(0)} stroke="#cbd5e1" strokeDasharray="4 4" vectorEffect="non-scaling-stroke" />
        <path d={path} fill="none" stroke={last >= 0 ? "#059669" : "#e11d48"} strokeWidth={2} vectorEffect="non-scaling-stroke" />
      </svg>
      <div className="mt-1 flex justify-between text-xs text-slate-500">
        <span>{dateShort(curve[0].at)}</span>
        <span>{euro(last)} nach {curve.length} Wetten</span>
        <span>{dateShort(curve[curve.length - 1].at)}</span>
      </div>
    </div>
  );
}

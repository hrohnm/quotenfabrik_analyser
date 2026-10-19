"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { api, getMeta } from "@/lib/api";
import { dateShort, num, odd, pct, seasonLabel } from "@/lib/format";
import type { Meta } from "@/lib/types";
import { Card, OutcomeBadge, ProbabilityBar, Select, SourceBadge, StatTile, TeamLogo } from "@/components/ui";

type Row = {
  id: number;
  season: number;
  matchday: number | null;
  kickoff: string;
  finished: boolean;
  home: { id: number; name: string };
  away: { id: number; name: string };
  score: { ft: [number | null, number | null]; ht: [number | null, number | null] };
  probability: number;
  fair_odd: number | null;
  outcome: boolean | null;
  source: string;
};
type Result = {
  summary: { n: number; settled: number; avg_probability: number | null; observed_rate: number | null; expected_rate: number | null; brier: number | null };
  rows: Row[];
};

const PAGE = 50;

export default function ExplorerPage() {
  const [meta, setMeta] = useState<Meta | null>(null);
  const [filters, setFilters] = useState({
    market: "1x2", line: "", selection: "H", season: "", team: "", venue: "any",
    status: "finished", outcome: "all", min_p: "0", max_p: "1", sort: "kickoff_desc",
  });
  const [offset, setOffset] = useState(0);
  const [data, setData] = useState<Result | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => { getMeta().then(setMeta).catch((e) => setError(String(e))); }, []);

  const marketOptions = useMemo(() => {
    const seen = new Map<string, { group: string; market: string }>();
    meta?.markets.forEach((m) => seen.set(m.market, { group: m.group, market: m.market }));
    return [...seen.values()];
  }, [meta]);
  const lines = useMemo(() => meta?.markets.filter((m) => m.market === filters.market && m.line !== null).map((m) => m.line as number) ?? [], [meta, filters.market]);
  const selections = useMemo(() => {
    const m = meta?.markets.find((x) => x.market === filters.market && (filters.line === "" ? x.line === null : x.line === Number(filters.line)));
    return m?.selections ?? [];
  }, [meta, filters.market, filters.line]);

  const set = (patch: Partial<typeof filters>) => { setOffset(0); setFilters((f) => ({ ...f, ...patch })); };

  const changeMarket = (market: string) => {
    const options = meta?.markets.filter((m) => m.market === market) ?? [];
    const first = options.find((m) => m.line === 2.5) ?? options.find((m) => m.line === 1.5) ?? options[0];
    const sel = first?.selections.includes("over") ? "over" : first?.selections.includes("H") ? "H" : first?.selections.includes("yes") ? "yes" : first?.selections[0] ?? "";
    set({ market, line: first?.line === null || first?.line === undefined ? "" : String(first.line), selection: sel });
  };

  useEffect(() => {
    if (!meta || !filters.selection) return;
    setLoading(true);
    setError(null);
    api<Result>("/explorer", { ...filters, line: filters.line || undefined, limit: PAGE, offset })
      .then(setData)
      .catch((e) => setError(String(e)))
      .finally(() => setLoading(false));
  }, [meta, filters, offset]);

  const label = (m: string) => meta?.market_labels[m] ?? m;
  const selLabel = (s: string) => meta?.selection_labels[s] ?? s;
  const s = data?.summary;
  const diff = s && s.observed_rate !== null && s.expected_rate !== null ? s.observed_rate - s.expected_rate : null;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Daten-Explorer</h1>
        <p className="text-sm text-slate-500">
          Modellwahrscheinlichkeiten für einen Markt über alle Spiele – vergangene Spiele mit rückwirkender Walk-Forward-Prognose und Ergebnis, kommende mit aktueller Prognose.
        </p>
      </div>

      <Card>
        <div className="grid grid-cols-2 gap-3 md:grid-cols-4 lg:grid-cols-6">
          <Select label="Markt" value={filters.market} onChange={changeMarket} className="col-span-2">
            {Object.entries(meta?.groups ?? {}).filter(([g]) => g !== "scorers").map(([g, gl]) => (
              <optgroup key={g} label={gl}>
                {marketOptions.filter((m) => m.group === g).map((m) => <option key={m.market} value={m.market}>{label(m.market)}</option>)}
              </optgroup>
            ))}
          </Select>
          {lines.length > 0 && (
            <Select label="Linie" value={filters.line} onChange={(v) => set({ line: v })}>
              {lines.map((l) => <option key={l} value={String(l)}>{num(l, l % 1 ? 1 : 0)}</option>)}
            </Select>
          )}
          <Select label="Auswahl" value={filters.selection} onChange={(v) => set({ selection: v })}>
            {selections.map((x) => <option key={x} value={x}>{selLabel(x)}</option>)}
          </Select>
          <Select label="Saison" value={filters.season} onChange={(v) => set({ season: v })}>
            <option value="">alle</option>
            {meta?.seasons.map((x) => <option key={x} value={x}>{seasonLabel(x)}</option>)}
          </Select>
          <Select label="Team" value={filters.team} onChange={(v) => set({ team: v })}>
            <option value="">alle</option>
            {meta?.teams.map((t) => <option key={t.id} value={t.id}>{t.name}</option>)}
          </Select>
          {filters.team && (
            <Select label="Heim/Auswärts" value={filters.venue} onChange={(v) => set({ venue: v })}>
              <option value="any">beides</option><option value="home">nur Heimspiele</option><option value="away">nur Auswärtsspiele</option>
            </Select>
          )}
          <Select label="Status" value={filters.status} onChange={(v) => set({ status: v })}>
            <option value="all">alle</option><option value="finished">beendet</option><option value="upcoming">kommend</option>
          </Select>
          <Select label="Ergebnis" value={filters.outcome} onChange={(v) => set({ outcome: v })}>
            <option value="all">alle</option><option value="hit">eingetreten</option><option value="miss">nicht eingetreten</option>
          </Select>
          <label className="flex flex-col gap-1 text-xs font-medium text-slate-500">
            Wahrscheinlichkeit von (%)
            <input type="number" min={0} max={100} step={5} value={Math.round(Number(filters.min_p) * 100)} onChange={(e) => set({ min_p: String(Number(e.target.value) / 100) })} className="rounded-md border border-slate-300 px-2 py-1.5 text-sm text-slate-900" />
          </label>
          <label className="flex flex-col gap-1 text-xs font-medium text-slate-500">
            bis (%)
            <input type="number" min={0} max={100} step={5} value={Math.round(Number(filters.max_p) * 100)} onChange={(e) => set({ max_p: String(Number(e.target.value) / 100) })} className="rounded-md border border-slate-300 px-2 py-1.5 text-sm text-slate-900" />
          </label>
          <Select label="Sortierung" value={filters.sort} onChange={(v) => set({ sort: v })}>
            <option value="kickoff_desc">neueste zuerst</option><option value="kickoff_asc">älteste zuerst</option>
            <option value="probability_desc">höchste Wahrscheinlichkeit</option><option value="probability_asc">niedrigste Wahrscheinlichkeit</option>
          </Select>
        </div>
      </Card>

      {error && <p className="rounded-md bg-rose-50 p-3 text-sm text-rose-700">{error}</p>}

      {s && (
        <div className="grid grid-cols-2 gap-4 md:grid-cols-5">
          <StatTile label="Spiele" value={s.n.toLocaleString("de-DE")} hint={`${s.settled.toLocaleString("de-DE")} abgerechnet`} />
          <StatTile label="Ø Wahrscheinlichkeit" value={pct(s.avg_probability)} hint="Modell, alle gefilterten Spiele" />
          <StatTile label="Tatsächlich eingetreten" value={pct(s.observed_rate)} hint={`erwartet laut Modell: ${pct(s.expected_rate)}`} />
          <StatTile label="Abweichung" value={diff === null ? "–" : `${diff >= 0 ? "+" : "−"}${Math.abs(diff * 100).toFixed(1).replace(".", ",")} Pp.`} hint="eingetreten minus erwartet" tone={diff === null ? undefined : Math.abs(diff) < 0.03 ? "good" : undefined} />
          <StatTile label="Brier-Score" value={num(s.brier, 4)} hint="kleiner = besser" />
        </div>
      )}

      <Card
        title={`${label(filters.market)}${filters.line ? ` ${num(Number(filters.line), Number(filters.line) % 1 ? 1 : 0)}` : ""} · ${selLabel(filters.selection)}`}
        actions={loading ? <span className="text-xs text-slate-400">lädt …</span> : null}
      >
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-xs text-slate-400">
                <th className="pb-2 font-medium">Datum</th><th className="pb-2 font-medium">Saison</th><th className="pb-2 font-medium">Begegnung</th>
                <th className="pb-2 text-center font-medium">Ergebnis</th><th className="pb-2 font-medium">Wahrscheinlichkeit</th>
                <th className="pb-2 text-right font-medium">Faire Quote</th><th className="pb-2 text-right font-medium">Eingetreten</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {data?.rows.map((r) => (
                <tr key={r.id} className="hover:bg-slate-50">
                  <td className="py-1.5 tabular-nums text-slate-600">{dateShort(r.kickoff)}</td>
                  <td className="py-1.5 text-slate-500">{seasonLabel(r.season)}{r.matchday ? ` · ${r.matchday}.` : ""}</td>
                  <td className="py-1.5"><Link href={`/spiel/${r.id}`} className="inline-flex items-center gap-1.5 font-medium hover:underline"><TeamLogo team={r.home} size={16} />{r.home.name} – {r.away.name}<TeamLogo team={r.away} size={16} /></Link> <SourceBadge kind={r.source === "forecast" ? "forecast" : null} /></td>
                  <td className="py-1.5 text-center tabular-nums">{r.finished ? `${r.score.ft[0]}:${r.score.ft[1]} (${r.score.ht[0]}:${r.score.ht[1]})` : "–"}</td>
                  <td className="py-1.5"><div className="flex items-center gap-2"><span className="w-14 shrink-0 whitespace-nowrap tabular-nums">{pct(r.probability)}</span><div className="w-28"><ProbabilityBar value={r.probability} /></div></div></td>
                  <td className="py-1.5 text-right tabular-nums">{odd(r.fair_odd)}</td>
                  <td className="py-1.5 text-right"><OutcomeBadge outcome={r.outcome} small /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {s && s.n > PAGE && (
          <div className="mt-4 flex items-center justify-between text-sm">
            <button disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - PAGE))} className="rounded-md border border-slate-300 px-3 py-1 disabled:opacity-40">← zurück</button>
            <span className="text-slate-500">{offset + 1}–{Math.min(offset + PAGE, s.n)} von {s.n.toLocaleString("de-DE")}</span>
            <button disabled={offset + PAGE >= s.n} onClick={() => setOffset(offset + PAGE)} className="rounded-md border border-slate-300 px-3 py-1 disabled:opacity-40">weiter →</button>
          </div>
        )}
      </Card>
    </div>
  );
}

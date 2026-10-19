"use client";

import { useState } from "react";
import { Card, TeamLogo } from "@/components/ui";
import { num } from "@/lib/format";
import type { FixtureDetail } from "@/lib/types";
import { Segmented } from "./Segmented";

const ROWS: [string, string][] = [
  ["xg", "Expected Goals (xG)"], ["possession", "Ballbesitz %"], ["shots_total", "Schüsse"], ["shots_on", "Schüsse aufs Tor"],
  ["shots_inside", "Schüsse im Strafraum"], ["corners", "Ecken"], ["passes_total", "Pässe"], ["fouls", "Fouls"],
  ["offsides", "Abseits"], ["yellow", "Gelbe Karten"], ["red", "Rote Karten"], ["gk_saves", "Paraden"],
];
const PERIODS = [
  { key: "FT", label: "Gesamt" },
  { key: "1H", label: "1. HZ" },
  { key: "2H", label: "2. HZ" },
];

export function StatsPanel({ data }: { data: FixtureDetail }) {
  const { stats, fixture: f } = data;
  const periods = PERIODS.filter((p) => stats.home[p.key] || stats.away[p.key]);
  const [period, setPeriod] = useState(periods[0]?.key ?? "FT");
  if (periods.length === 0) return <Card><p className="text-sm text-slate-500">Noch keine Spielstatistik vorhanden.</p></Card>;
  const home = stats.home[period] ?? {};
  const away = stats.away[period] ?? {};
  const rows = ROWS.filter(([k]) => home[k] != null || away[k] != null);
  return (
    <Card
      title={
        <span className="flex items-center gap-2">
          <TeamLogo team={f.home} size={18} />{f.home.name}<span className="text-slate-300">vs.</span>{f.away.name}<TeamLogo team={f.away} size={18} />
        </span>
      }
      actions={periods.length > 1 ? <Segmented options={periods} value={period} onChange={setPeriod} size="sm" /> : undefined}
    >
      <ul className="mx-auto max-w-2xl space-y-3">
        {rows.map(([k, label]) => {
          const h = home[k] ?? 0;
          const a = away[k] ?? 0;
          const share = h + a > 0 ? h / (h + a) : 0.5;
          return (
            <li key={k}>
              <div className="mb-1 flex items-center justify-between text-sm">
                <span className={`w-12 font-semibold tabular-nums ${h > a ? "text-emerald-700" : ""}`}>{fmt(home[k])}</span>
                <span className="text-xs text-slate-500">{label}</span>
                <span className={`w-12 text-right font-semibold tabular-nums ${a > h ? "text-sky-700" : ""}`}>{fmt(away[k])}</span>
              </div>
              <div className="flex h-1.5 gap-1">
                <div className="flex flex-1 justify-end overflow-hidden rounded-full bg-slate-100"><div className="bg-emerald-500" style={{ width: `${share * 100}%` }} /></div>
                <div className="flex-1 overflow-hidden rounded-full bg-slate-100"><div className="h-full bg-sky-500" style={{ width: `${(1 - share) * 100}%` }} /></div>
              </div>
            </li>
          );
        })}
      </ul>
    </Card>
  );
}

const fmt = (v: number | null | undefined) => (v == null ? "–" : Number.isInteger(v) ? String(v) : num(v));

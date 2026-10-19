"use client";

import { Card, TeamLogo } from "@/components/ui";
import { pct } from "@/lib/format";
import { isRate, patternValue, signals } from "@/lib/patterns";
import type { Fixture, Pattern, Team } from "@/lib/types";

const GROUPS = [
  { key: "1x2", label: "Spielausgang" },
  { key: "totals", label: "Tore gesamt" },
  { key: "team_totals", label: "Tore pro Team" },
  { key: "halves", label: "Halbzeiten" },
];

export function PatternsPanel({ patterns, fixture: f }: { patterns: Pattern[]; fixture: Fixture }) {
  if (patterns.length === 0) return <Card><p className="text-sm text-slate-500">Keine Pattern vorhanden.</p></Card>;
  const teamOf = (p: Pattern) => (p.scope === "home" ? f.home : p.scope === "away" ? f.away : undefined);
  const sig = signals(patterns);
  return (
    <div className="space-y-4">
      <p className="text-xs text-slate-500">
        Alle Werte nur aus Spielen vor Anpfiff. Der Balken zeigt den Wert, die Markierung den Ligaschnitt. „Hoch“ / „niedrig“ = statistisch auffällige Abweichung (Wilson-Intervall).
      </p>
      {sig.length > 0 && (
        <Card title={`Auffällig (${sig.length})`}>
          <PatternList patterns={sig} teamOf={teamOf} />
        </Card>
      )}
      <div className="grid gap-4 lg:grid-cols-2">
        {GROUPS.map((g) => {
          const ps = patterns.filter((p) => p.group === g.key && !p.key.endsWith("goal_timing"));
          if (ps.length === 0) return null;
          return (
            <details key={g.key} className="group rounded-xl border border-slate-200 bg-white shadow-sm" open={g.key === "1x2" || g.key === "totals"}>
              <summary className="flex cursor-pointer list-none items-center justify-between px-4 py-3 text-sm font-semibold text-slate-800">
                {g.label}
                <span className="text-xs font-normal text-slate-400">{ps.length} Pattern <span className="inline-block transition group-open:rotate-180">▾</span></span>
              </summary>
              <div className="border-t border-slate-100 px-4 py-2"><PatternList patterns={ps} teamOf={teamOf} /></div>
            </details>
          );
        })}
      </div>
      <GoalTiming patterns={patterns} teamOf={teamOf} />
    </div>
  );
}

function PatternList({ patterns, teamOf }: { patterns: Pattern[]; teamOf: (p: Pattern) => Team | undefined }) {
  return (
    <ul className="divide-y divide-slate-100">
      {patterns.map((p) => {
        const t = teamOf(p);
        const rate = isRate(p);
        return (
          <li key={p.key} className="flex items-center gap-3 py-2 text-sm">
            {t ? <TeamLogo team={t} size={18} /> : <span className="grid h-[18px] w-[18px] shrink-0 place-items-center text-[10px] text-slate-400">⚔</span>}
            <div className="min-w-0 flex-1">
              <div className="text-slate-700">{p.label}</div>
              {rate && p.value !== null && p.baseline !== null && <BaselineBar value={p.value} baseline={p.baseline} signal={p.signal} />}
            </div>
            <div className="w-16 shrink-0 text-right">
              <div className={`font-semibold tabular-nums ${p.signal === "high" ? "text-emerald-700" : p.signal === "low" ? "text-rose-700" : ""}`}>{patternValue(p)}</div>
              <div className="text-[11px] text-slate-400">
                {p.baseline !== null && p.baseline <= 1 && rate ? `Liga ${pct(p.baseline, 0)}` : p.n !== null ? `n=${p.n}` : ""}
              </div>
            </div>
          </li>
        );
      })}
    </ul>
  );
}

function BaselineBar({ value, baseline, signal }: { value: number; baseline: number; signal: Pattern["signal"] }) {
  const color = signal === "high" ? "bg-emerald-500" : signal === "low" ? "bg-rose-500" : "bg-slate-400";
  return (
    <div className="relative mt-1 h-1.5 max-w-64 rounded-full bg-slate-100">
      <div className={`h-full rounded-full ${color}`} style={{ width: `${value * 100}%` }} />
      <div className="absolute -top-0.5 h-2.5 w-0.5 bg-slate-800" style={{ left: `${baseline * 100}%` }} title={`Ligaschnitt ${pct(baseline, 0)}`} />
    </div>
  );
}

function GoalTiming({ patterns, teamOf }: { patterns: Pattern[]; teamOf: (p: Pattern) => Team | undefined }) {
  const timing = patterns.filter((p) => p.key.endsWith("goal_timing") && p.details);
  if (timing.length === 0) return null;
  return (
    <Card title="Tor-Timing (eigene Tore der letzten 10 Heim- bzw. Auswärtsspiele)">
      <div className="grid gap-6 sm:grid-cols-2">
        {timing.map((p) => {
          const values = Object.entries(p.details ?? {});
          const max = Math.max(1, ...values.map(([, v]) => v));
          const t = teamOf(p);
          return (
            <div key={p.key}>
              <div className="mb-2 flex items-center gap-2 text-xs text-slate-500">
                {t && <TeamLogo team={t} size={16} />}{t?.name} · {p.n} Tore
              </div>
              <div className="flex items-end gap-1.5">
                {values.map(([k, v]) => (
                  <div key={k} className="flex flex-1 flex-col items-center gap-1">
                    <span className="text-[10px] tabular-nums text-slate-500">{v}</span>
                    <div className="w-full rounded-t bg-emerald-400" style={{ height: `${(v / max) * 56 + 2}px` }} />
                    <span className="text-[10px] text-slate-400">{k}</span>
                  </div>
                ))}
              </div>
            </div>
          );
        })}
      </div>
    </Card>
  );
}

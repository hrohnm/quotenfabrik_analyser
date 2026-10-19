import type { ReactNode } from "react";
import type { Team } from "@/lib/types";
import { pct } from "@/lib/format";

export function Card({ title, children, className = "", actions }: { title?: ReactNode; children: ReactNode; className?: string; actions?: ReactNode }) {
  return (
    <section className={`rounded-xl border border-slate-200 bg-white shadow-sm ${className}`}>
      {title && (
        <div className="flex items-center justify-between border-b border-slate-100 px-4 py-3">
          <h2 className="text-sm font-semibold text-slate-800">{title}</h2>
          {actions}
        </div>
      )}
      <div className="p-4">{children}</div>
    </section>
  );
}

export function TeamLogo({ team, size = 24 }: { team: Team; size?: number }) {
  if (!team.logo) return <span className="inline-block rounded-full bg-slate-200" style={{ width: size, height: size }} />;
  // eslint-disable-next-line @next/next/no-img-element
  return <img src={team.logo} alt="" width={size} height={size} className="object-contain" style={{ width: size, height: size }} />;
}

export function OutcomeBadge({ outcome, small = false }: { outcome: boolean | null | undefined; small?: boolean }) {
  const size = small ? "h-5 w-5 text-[11px]" : "h-6 w-6 text-xs";
  if (outcome === true) return <span title="eingetreten" className={`inline-grid ${size} place-items-center rounded-full bg-emerald-100 font-bold text-emerald-700`}>✓</span>;
  if (outcome === false) return <span title="nicht eingetreten" className={`inline-grid ${size} place-items-center rounded-full bg-rose-100 font-bold text-rose-700`}>✗</span>;
  return <span title="offen" className={`inline-grid ${size} place-items-center rounded-full bg-slate-100 text-slate-400`}>·</span>;
}

export function ProbabilityBar({ value, tone = "emerald" }: { value: number; tone?: "emerald" | "slate" | "amber" }) {
  const color = { emerald: "bg-emerald-500", slate: "bg-slate-400", amber: "bg-amber-500" }[tone];
  return (
    <div className="h-2 w-full overflow-hidden rounded-full bg-slate-100">
      <div className={`h-full ${color}`} style={{ width: `${Math.max(0, Math.min(1, value)) * 100}%` }} />
    </div>
  );
}

/** Stacked home / draw / away bar. */
export function ThreeWayBar({ home, draw, away }: { home?: number; draw?: number; away?: number }) {
  if (home === undefined || draw === undefined || away === undefined) return <div className="h-2 rounded-full bg-slate-100" />;
  return (
    <div className="flex h-2 w-full overflow-hidden rounded-full" title={`Heim ${pct(home)} · X ${pct(draw)} · Gast ${pct(away)}`}>
      <div className="bg-emerald-500" style={{ width: `${home * 100}%` }} />
      <div className="bg-slate-300" style={{ width: `${draw * 100}%` }} />
      <div className="bg-sky-500" style={{ width: `${away * 100}%` }} />
    </div>
  );
}

export function StatTile({ label, value, hint, tone }: { label: string; value: ReactNode; hint?: ReactNode; tone?: "good" | "bad" }) {
  const toneClass = tone === "good" ? "text-emerald-700" : tone === "bad" ? "text-rose-700" : "text-slate-900";
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="text-xs font-medium uppercase tracking-wide text-slate-500">{label}</div>
      <div className={`mt-1 text-2xl font-semibold ${toneClass}`}>{value}</div>
      {hint && <div className="mt-1 text-xs text-slate-500">{hint}</div>}
    </div>
  );
}

export function SourceBadge({ kind }: { kind?: string | null }) {
  if (!kind) return null;
  const forecast = kind === "forecast";
  return (
    <span
      title={forecast ? "Prognose vor Anpfiff" : "Rückwirkende Walk-Forward-Prognose (nur Daten vor dem Spieltag)"}
      className={`rounded px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wide ${forecast ? "bg-emerald-50 text-emerald-700" : "bg-slate-100 text-slate-600"}`}
    >
      {forecast ? "Prognose" : "Backtest"}
    </span>
  );
}

export function Select({ label, value, onChange, children, className = "" }: { label: string; value: string; onChange: (v: string) => void; children: ReactNode; className?: string }) {
  return (
    <label className={`flex flex-col gap-1 text-xs font-medium text-slate-500 ${className}`}>
      {label}
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="rounded-md border border-slate-300 bg-white px-2 py-1.5 text-sm text-slate-900 shadow-sm focus:border-emerald-500 focus:outline-none"
      >
        {children}
      </select>
    </label>
  );
}

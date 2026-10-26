import type { ReactNode } from "react";
import { dateShort, odd, pct, signedPct, time } from "@/lib/format";
import type { Pick } from "@/lib/types";

/** Hover card (tap on mobile) explaining why a pick was chosen and why it is considered likely. */
export function PickInfo({ pick, children, className = "" }: { pick: Pick; children: ReactNode; className?: string }) {
  if (!pick.explain) return <>{children}</>;
  return (
    <span tabIndex={0} className={`group/pick relative inline-flex cursor-help outline-none ${className}`}>
      {children}
      <span
        role="tooltip"
        className="pointer-events-none invisible absolute left-0 top-full z-30 mt-1.5 w-80 max-w-[calc(100vw-2rem)] overflow-hidden rounded-xl border border-slate-200 bg-white text-left text-xs font-normal text-slate-600 opacity-0 shadow-lg ring-1 ring-black/5 transition duration-150 group-hover/pick:visible group-hover/pick:opacity-100 group-focus/pick:visible group-focus/pick:opacity-100"
      >
        <span className="flex items-center justify-between gap-2 bg-slate-900 px-3 py-2 text-white">
          <span className="font-semibold">{pick.label}</span>
          <span className="tabular-nums">{pct(pick.probability, 0)}</span>
        </span>
        <Section title="Warum dieser Tipp?" lines={pick.explain.why} tone="text-slate-900" />
        <Section title="Warum wahrscheinlich?" lines={pick.explain.likely} tone="text-emerald-800" />
        <OddsMove pick={pick} />
      </span>
    </span>
  );
}

function Section({ title, lines, tone }: { title: string; lines: string[]; tone: string }) {
  if (lines.length === 0) return null;
  return (
    <span className="block border-t border-slate-100 px-3 py-2 first:border-t-0">
      <span className={`mb-1 block text-[11px] font-semibold uppercase tracking-wide ${tone}`}>{title}</span>
      <span className="block space-y-1">
        {lines.map((l) => (
          <span key={l} className="flex gap-1.5 leading-snug">
            <span className="mt-[5px] h-1 w-1 shrink-0 rounded-full bg-slate-400" />
            <span>{l}</span>
          </span>
        ))}
      </span>
    </span>
  );
}

/** Betano odds when the pick was published against the latest price (closing price once the match started). */
function OddsMove({ pick }: { pick: Pick }) {
  const taken = pick.betano_taken;
  if (taken == null) return null;
  const last = pick.betano;
  const moved = last != null && Math.abs(last - taken) >= 0.005;
  return (
    <span className="block border-t border-slate-100 px-3 py-2">
      <span className="mb-1 block text-[11px] font-semibold uppercase tracking-wide text-slate-900">Quote seit dem Tipp</span>
      <span className="flex items-baseline justify-between gap-2">
        <span>
          Betano beim Tipp{pick.taken_at && <span className="text-slate-400"> ({dateShort(pick.taken_at)} {time(pick.taken_at)})</span>}
        </span>
        <span className="tabular-nums font-semibold text-slate-900">{odd(taken)}</span>
      </span>
      {last != null && (
        <span className="flex items-baseline justify-between gap-2">
          <span>zuletzt (bis Anpfiff)</span>
          <span className={`tabular-nums font-semibold ${moved ? (last < taken ? "text-emerald-700" : "text-rose-700") : "text-slate-900"}`}>
            {odd(last)}{moved && (last < taken ? " ↓" : " ↑")}
          </span>
        </span>
      )}
      {pick.clv != null && (
        <span className="flex items-baseline justify-between gap-2">
          <span title="Quote beim Tipp × Pinnacle-Wahrscheinlichkeit ohne Marge − 1">CLV gegen Pinnacle</span>
          <span className={`tabular-nums font-semibold ${pick.clv > 0 ? "text-emerald-700" : "text-rose-700"}`}>{signedPct(pick.clv)}</span>
        </span>
      )}
      {moved && (
        <span className="mt-1 block leading-snug text-slate-500">
          {last! < taken ? "Die Quote ist gefallen: Der Markt hat sich in Richtung des Tipps bewegt." : "Die Quote ist gestiegen: Der Markt hat sich gegen den Tipp bewegt."}
        </span>
      )}
    </span>
  );
}

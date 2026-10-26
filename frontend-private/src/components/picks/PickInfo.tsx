import type { ReactNode } from "react";
import { pct } from "@/lib/format";
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

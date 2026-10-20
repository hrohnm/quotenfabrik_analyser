import { OutcomeBadge, ProbabilityBar } from "@/components/ui";
import { odd, pct } from "@/lib/format";
import type { Pick } from "@/lib/types";
import { BetanoOdd } from "@/components/BetanoOdd";

/** Combined outcome: true if all picks came true, false as soon as one failed, null while open. */
export function comboOutcome(picks: Pick[]): boolean | null {
  if (picks.some((p) => p.outcome === false)) return false;
  return picks.length > 0 && picks.every((p) => p.outcome === true) ? true : null;
}

export const comboProbability = (picks: Pick[]) => picks.reduce((prod, p) => prod * p.probability, 1);

export function PickList({ picks, finished, reasons = true }: { picks: Pick[]; finished: boolean; reasons?: boolean }) {
  if (picks.length === 0) return <p className="text-sm text-slate-500">Keine Tipps in diesem Profil – kein Markt liegt im Wahrscheinlichkeitsbereich.</p>;
  const combo = comboProbability(picks);
  return (
    <div>
      <ol className="space-y-3">
        {picks.map((p) => (
          <li key={p.rank} className="flex gap-3">
            <span className="mt-0.5 grid h-6 w-6 shrink-0 place-items-center rounded-full bg-slate-900 text-xs font-bold text-white">{p.rank}</span>
            <div className="min-w-0 flex-1">
              <div className="flex items-center justify-between gap-2">
                <span className="font-medium">{p.label}</span>
                <span className="flex shrink-0 items-center gap-2 tabular-nums">
                  <span className="font-semibold">{pct(p.probability, 0)}</span>
                  <span className="w-10 text-right text-xs text-slate-400" title="faire Quote">{odd(p.fair_odd)}</span>
                  <span className="w-11 text-right"><BetanoOdd prices={p} /></span>
                  {finished && <OutcomeBadge outcome={p.outcome} small />}
                </span>
              </div>
              <div className="mt-1"><ProbabilityBar value={p.probability} /></div>
              {reasons && (
                <div className="mt-1 space-y-0.5 text-xs text-slate-500">
                  {p.base_rate !== null && <div>Ligaschnitt {pct(p.base_rate, 0)} – Modell {p.probability >= p.base_rate ? "+" : "−"}{Math.abs((p.probability - p.base_rate) * 100).toFixed(0)} Punkte</div>}
                  {p.reasons.map((r) => (
                    <div key={r.label} className="text-emerald-700">✓ {r.label}: {r.value !== null && r.value <= 1 ? pct(r.value, 0) : r.value}{r.baseline !== null && r.baseline <= 1 ? ` (Liga ${pct(r.baseline, 0)})` : ""}</div>
                  ))}
                </div>
              )}
            </div>
          </li>
        ))}
      </ol>
      {picks.length > 1 && (
        <div className="mt-4 flex items-center justify-between rounded-lg bg-slate-50 px-3 py-2 text-sm">
          <span className="text-slate-600">Kombi aus {picks.length} Tipps</span>
          <span className="flex items-center gap-3 tabular-nums">
            <span title="Produkt der Einzelwahrscheinlichkeiten">rechnerisch {pct(combo, 0)}</span>
            <span className="text-xs text-slate-400" title="faire Kombi-Quote">{odd(1 / combo)}</span>
            {picks.every((p) => p.betano != null) && (
              <span className="rounded bg-orange-50 px-1 text-xs font-medium text-orange-700" title="Produkt der Betano-Einzelquoten (als Bet Builder im selben Spiel meist niedriger)">
                {odd(picks.reduce((o, p) => o * (p.betano ?? 1), 1))}
              </span>
            )}
            {finished && <OutcomeBadge outcome={comboOutcome(picks)} small />}
          </span>
        </div>
      )}
    </div>
  );
}

/** Compact chips for lists (matchday overview). */
export function PickChips({ picks, finished }: { picks: Pick[]; finished: boolean }) {
  return (
    <div className="flex flex-wrap gap-1.5">
      {picks.map((p) => {
        const tone = !finished || p.outcome === null ? "border-slate-200 bg-white text-slate-700" : p.outcome ? "border-emerald-200 bg-emerald-50 text-emerald-800" : "border-rose-200 bg-rose-50 text-rose-800";
        return (
          <span key={p.rank} className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-xs ${tone}`}>
            {p.label} <span className="font-semibold tabular-nums">{pct(p.probability, 0)}</span>
          </span>
        );
      })}
    </div>
  );
}

import { OutcomeBadge, ProbabilityBar } from "@/components/ui";
import { odd, pct, signedPct } from "@/lib/format";
import type { Pick, PickCombo } from "@/lib/types";
import { BetanoOdd } from "@/components/BetanoOdd";
import { PickInfo } from "./PickInfo";

/** Combined outcome: true if all picks came true, false as soon as one failed, null while open. */
export function comboOutcome(picks: Pick[]): boolean | null {
  if (picks.some((p) => p.outcome === false)) return false;
  return picks.length > 0 && picks.every((p) => p.outcome === true) ? true : null;
}

export const comboProbability = (picks: Pick[]) => picks.reduce((prod, p) => prod * p.probability, 1);

type ListProps = { picks: Pick[]; finished: boolean; reasons?: boolean; combo?: PickCombo | null };

export function PickList({ picks, finished, reasons = true, combo }: ListProps) {
  if (picks.length === 0) return <p className="text-sm text-slate-500">Keine Tipps in diesem Profil – kein Markt liegt im Wahrscheinlichkeitsbereich.</p>;
  return (
    <div>
      <ol className="space-y-3">
        {picks.map((p) => (
          <li key={p.rank} className="flex gap-3">
            <span className="mt-0.5 grid h-6 w-6 shrink-0 place-items-center rounded-full bg-slate-900 text-xs font-bold text-white">{p.rank}</span>
            <div className="min-w-0 flex-1">
              <div className="flex items-center justify-between gap-2">
                <PickInfo pick={p} className="min-w-0">
                  <span className="font-medium underline decoration-slate-300 decoration-dotted underline-offset-4">{p.label}</span>
                </PickInfo>
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
      {picks.length > 1 && <ComboRow picks={picks} combo={combo} finished={finished} />}
    </div>
  );
}

/** Same-game combo of the picks: joint model chance (correlated picks) and estimated Bet Builder odds. */
function ComboRow({ picks, combo, finished }: { picks: Pick[]; combo?: PickCombo | null; finished: boolean }) {
  const naive = combo?.naive ?? comboProbability(picks);
  const p = combo?.probability ?? null;
  const product = combo?.betano_product ?? (picks.every((x) => x.betano != null) ? picks.reduce((o, x) => o * (x.betano ?? 1), 1) : null);
  const builder = combo?.builder_odds ?? null;
  return (
    <div className="mt-4 rounded-lg bg-slate-50 px-3 py-2 text-sm">
      <div className="flex items-center justify-between gap-2">
        <span className="text-slate-600">Kombi aus {picks.length} Tipps <span className="text-xs text-slate-400">(Bet Builder)</span></span>
        <span className="flex items-center gap-3 tabular-nums">
          <span className="font-semibold" title={p != null ? `Modell-Chance, dass alle ${picks.length} Tipps zusammen treffen (die Tipps eines Spiels hängen zusammen; einzeln multipliziert ${pct(naive, 0)})` : "Produkt der Einzelwahrscheinlichkeiten"}>
            {pct(p ?? naive, 0)}
          </span>
          <span className="text-xs text-slate-400" title="faire Kombi-Quote laut Modell">{odd(combo?.fair_odd ?? 1 / naive)}</span>
          {builder != null ? (
            <span
              className="rounded bg-orange-50 px-1 text-xs font-medium text-orange-700"
              title={`Geschätzte Bet-Builder-Quote: die Betano-Einzelquoten so verbunden, wie Betano es im Bet Builder tut (Torverteilung an Betanos eigene Quoten angepasst). Einzelquoten multipliziert ${odd(product)}. Die echte Quote auf dem Wettschein kann leicht abweichen.`}
            >
              ≈ {odd(builder)}
            </span>
          ) : product != null && (
            <span className="rounded bg-orange-50 px-1 text-xs font-medium text-orange-700" title="Produkt der Betano-Einzelquoten (als Bet Builder im selben Spiel niedriger)">{odd(product)}</span>
          )}
          {finished && <OutcomeBadge outcome={comboOutcome(picks)} small />}
        </span>
      </div>
      {p != null && (
        <div className="mt-0.5 text-xs text-slate-400">
          einzeln multipliziert {pct(naive, 0)}{product != null && builder != null && <> · Einzelquoten multipliziert {odd(product)}</>}
          {combo?.edge != null && (
            <> · <span className={combo.edge > 0 ? "text-emerald-700" : ""} title="Modell-Chance × geschätzte Bet-Builder-Quote − 1">Modell-EV {signedPct(combo.edge)}</span></>
          )}
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
          <PickInfo key={p.rank} pick={p}>
            <span className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-xs ${tone}`}>
              {p.label} <span className="font-semibold tabular-nums">{pct(p.probability, 0)}</span>
              <BetanoOdd prices={p} />
            </span>
          </PickInfo>
        );
      })}
    </div>
  );
}

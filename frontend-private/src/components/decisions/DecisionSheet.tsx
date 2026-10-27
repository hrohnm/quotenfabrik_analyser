import { OutcomeBadge } from "@/components/ui";
import { BetanoOdd } from "@/components/BetanoOdd";
import { pct } from "@/lib/format";
import type { Decision, Team } from "@/lib/types";

/** Readable pick: winner with the team name, yes/no decisions as they are. */
function pickText(d: Decision, home?: Team, away?: Team): string {
  if (d.key !== "winner") return d.pick_label;
  if (d.pick === "H") return home?.name ?? "Heim";
  if (d.pick === "A") return away?.name ?? "Gast";
  return "Unentschieden";
}

const SHORT: Record<string, string> = { winner: "Sieger", o15: "Über 1,5", o25: "Über 2,5", btts: "Beide treffen", goal_1h: "Tor 1. HZ", goal_2h: "Tor 2. HZ" };

/** Confidence 0-100 as a small meter (rank among past fixtures of the same decision). */
function Confidence({ value, tipped }: { value: number | null | undefined; tipped: boolean }) {
  if (value == null) return null;
  const color = !tipped ? "bg-slate-300" : value >= 80 ? "bg-emerald-600" : value >= 65 ? "bg-emerald-500" : "bg-emerald-400";
  return (
    <span className="inline-flex items-center gap-1" title={`Konfidenz ${value}: sicherer als ${value} % der früheren Spiele bei dieser Entscheidung`}>
      <span className="h-1.5 w-7 overflow-hidden rounded-full bg-slate-100"><span className={`block h-full ${color}`} style={{ width: `${value}%` }} /></span>
      <span className={`w-5 text-right text-[11px] tabular-nums ${tipped ? "text-slate-600" : "text-slate-400"}`}>{value}</span>
    </span>
  );
}

/** Tippschein: the six decisions of a fixture; below the minimum confidence "kein Tipp". */
export function DecisionSheet({ decisions, home, away, finished }: { decisions: Decision[]; home?: Team; away?: Team; finished: boolean }) {
  if (decisions.length === 0) return <p className="text-sm text-slate-500">Keine Prognose für dieses Spiel.</p>;
  const tips = decisions.filter((d) => d.tipped !== false);
  const settled = tips.filter((d) => d.hit !== null);
  const correct = settled.filter((d) => d.hit).length;
  return (
    <div>
      <table className="w-full text-sm">
        <tbody className="divide-y divide-slate-100">
          {decisions.map((d) => {
            const tipped = d.tipped !== false;
            const yes = d.pick === "over" || d.pick === "yes";
            const tone = !tipped ? "bg-white text-slate-400 ring-1 ring-inset ring-slate-200" : d.key === "winner" ? "bg-sky-50 text-sky-800" : yes ? "bg-emerald-50 text-emerald-800" : "bg-slate-100 text-slate-700";
            return (
              <tr key={d.key} className={tipped ? "" : "text-slate-400"}>
                <td className={`whitespace-nowrap py-1.5 pr-2 ${tipped ? "text-slate-600" : ""}`} title={d.label}>{SHORT[d.key] ?? d.label}</td>
                <td className="py-1.5 pr-2">
                  <span className={`inline-block max-w-[8rem] truncate rounded px-1.5 py-0.5 align-middle text-xs font-semibold ${tone}`} title={tipped ? undefined : `kein Tipp – Modell tendiert zu „${pickText(d, home, away)}“`}>
                    {tipped ? pickText(d, home, away) : "kein Tipp"}
                  </span>
                </td>
                <td className="w-16 whitespace-nowrap py-1.5"><Confidence value={d.confidence} tipped={tipped} /></td>
                <td className={`w-12 whitespace-nowrap py-1.5 text-right tabular-nums ${tipped ? "font-semibold" : ""}`} title={d.model_probability != null ? `Wahrscheinlichkeit (Tor-Modell allein ${pct(d.model_probability, 0)})` : "Wahrscheinlichkeit laut Modell"}>
                  {pct(d.probability, 0)}
                </td>
                <td className="w-12 py-1.5 text-right">{tipped && <BetanoOdd prices={d} />}</td>
                {finished && <td className="w-7 py-1.5 text-right">{tipped ? <OutcomeBadge outcome={d.hit} small /> : null}</td>}
              </tr>
            );
          })}
        </tbody>
      </table>
      <div className="mt-3 flex items-center justify-between rounded-lg bg-slate-50 px-3 py-2 text-sm">
        <span className="text-slate-600">{tips.length} von {decisions.length} getippt</span>
        {finished && settled.length > 0 ? (
          <span className={`font-semibold tabular-nums ${correct === settled.length ? "text-emerald-700" : ""}`}>{correct} von {settled.length} richtig</span>
        ) : (
          <span className="text-xs text-slate-400">Konfidenz 0–100</span>
        )}
      </div>
    </div>
  );
}

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

/** Tippschein: the six fixed decisions of a fixture (always the selection the model considers more likely). */
export function DecisionSheet({ decisions, home, away, finished }: { decisions: Decision[]; home?: Team; away?: Team; finished: boolean }) {
  if (decisions.length === 0) return <p className="text-sm text-slate-500">Keine Prognose für dieses Spiel.</p>;
  const settled = decisions.filter((d) => d.hit !== null);
  const correct = settled.filter((d) => d.hit).length;
  return (
    <div>
      <table className="w-full text-sm">
        <tbody className="divide-y divide-slate-100">
          {decisions.map((d) => {
            const yesNo = d.key !== "winner";
            const tone = yesNo ? (d.pick === "over" || d.pick === "yes" ? "bg-emerald-50 text-emerald-800" : "bg-slate-100 text-slate-700") : "bg-sky-50 text-sky-800";
            return (
              <tr key={d.key}>
                <td className="whitespace-nowrap py-1.5 pr-2 text-slate-600">{d.label}</td>
                <td className="py-1.5 pr-2">
                  <span className={`inline-block max-w-[9rem] truncate rounded px-1.5 py-0.5 text-xs font-semibold align-middle ${tone}`}>{pickText(d, home, away)}</span>
                </td>
                <td className="w-12 py-1.5 text-right font-semibold tabular-nums" title="Wahrscheinlichkeit laut Modell">{pct(d.probability, 0)}</td>
                <td className="w-12 py-1.5 text-right"><BetanoOdd prices={d} /></td>
                {finished && <td className="w-7 py-1.5 text-right"><OutcomeBadge outcome={d.hit} small /></td>}
              </tr>
            );
          })}
        </tbody>
      </table>
      {finished && settled.length > 0 && (
        <div className="mt-3 flex items-center justify-between rounded-lg bg-slate-50 px-3 py-2 text-sm">
          <span className="text-slate-600">Richtig</span>
          <span className={`font-semibold tabular-nums ${correct === decisions.length ? "text-emerald-700" : ""}`}>{correct} von {settled.length}</span>
        </div>
      )}
    </div>
  );
}

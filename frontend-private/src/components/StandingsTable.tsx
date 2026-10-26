import { TeamLink } from "@/components/TeamLink";
import { TeamLogo } from "@/components/ui";
import { FormChips } from "@/components/match/FormPanel";
import type { TableRow, Team } from "@/lib/types";

type Tone = "home" | "away" | "selected";
const TONE: Record<Tone, string> = { home: "bg-emerald-50 font-semibold", away: "bg-sky-50 font-semibold", selected: "bg-amber-50" };

/** League table (rank, team, played, W/D/L, goals, difference, points, form). ``highlight`` colours rows;
 * ``onToggle`` makes rows selectable (e.g. lines of the position chart). */
export function StandingsTable({ rows, teams, highlight = {}, onToggle }: {
  rows: TableRow[];
  teams: Record<number, Team>;
  highlight?: Record<number, Tone>;
  onToggle?: (teamId: number) => void;
}) {
  return (
    <div className="-mx-4 overflow-x-auto">
      <table className="w-full min-w-[22rem] text-sm tabular-nums">
        <thead>
          <tr className="border-b border-slate-100 text-[11px] uppercase tracking-wide text-slate-400">
            <th className="w-8 px-2 py-1.5 text-right font-medium">#</th>
            <th className="w-full px-2 py-1.5 text-left font-medium">Team</th>
            <th className="px-1.5 py-1.5 text-right font-medium">Sp</th>
            <th className="hidden px-1.5 py-1.5 text-right font-medium sm:table-cell">S</th>
            <th className="hidden px-1.5 py-1.5 text-right font-medium sm:table-cell">U</th>
            <th className="hidden px-1.5 py-1.5 text-right font-medium sm:table-cell">N</th>
            <th className="px-1.5 py-1.5 text-right font-medium">Tore</th>
            <th className="px-1.5 py-1.5 text-right font-medium">Diff</th>
            <th className="px-2 py-1.5 text-right font-medium">Pkt</th>
            <th className="hidden px-2 py-1.5 text-left font-medium md:table-cell">Form</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => {
            const team = teams[r.team_id];
            const tone = highlight[r.team_id];
            return (
              <tr
                key={r.team_id}
                onClick={onToggle ? () => onToggle(r.team_id) : undefined}
                className={`border-b border-slate-50 last:border-0 ${tone ? TONE[tone] : ""} ${onToggle ? "cursor-pointer hover:bg-slate-50" : ""}`}
              >
                <td className="px-2 py-1.5 text-right text-slate-500">{r.rank}</td>
                <td className="max-w-0 px-2 py-1.5">
                  <span className="flex min-w-0 items-center gap-2">
                    {team && <TeamLogo team={team} size={16} />}
                    <TeamLink id={r.team_id} className="truncate">{team?.name ?? r.team_id}</TeamLink>
                  </span>
                </td>
                <td className="px-1.5 py-1.5 text-right">{r.played}</td>
                <td className="hidden px-1.5 py-1.5 text-right sm:table-cell">{r.won}</td>
                <td className="hidden px-1.5 py-1.5 text-right sm:table-cell">{r.drawn}</td>
                <td className="hidden px-1.5 py-1.5 text-right sm:table-cell">{r.lost}</td>
                <td className="whitespace-nowrap px-1.5 py-1.5 text-right">{r.gf}:{r.ga}</td>
                <td className="px-1.5 py-1.5 text-right">{r.gd > 0 ? `+${r.gd}` : r.gd < 0 ? `−${-r.gd}` : "0"}</td>
                <td className="px-2 py-1.5 text-right font-semibold">{r.points}</td>
                <td className="hidden px-2 py-1.5 md:table-cell">{r.form && <FormChips sequence={r.form} size="h-4 w-4" />}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

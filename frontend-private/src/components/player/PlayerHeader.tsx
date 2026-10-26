import Link from "next/link";
import { Logo } from "@/components/Logo";
import { TeamLink } from "@/components/TeamLink";
import { SeasonSelect } from "@/components/team/SeasonSelect";
import { TeamLogo } from "@/components/ui";
import { dateShort, num, pct, time } from "@/lib/format";
import type { PlayerOverview } from "@/lib/types";

const POSITION: Record<string, string> = { G: "Torwart", D: "Abwehr", M: "Mittelfeld", F: "Sturm" };

/** Player header: photo, team, number, position, status, next match with scorer forecast, key values. */
export function PlayerHeader({ data }: { data: PlayerOverview }) {
  const team = data.teams[data.team_id];
  const s = data.summary;
  const next = data.next;
  const opponent = next ? data.teams[next.opponent_id] : null;
  return (
    <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
      <div className="flex flex-col gap-4 bg-gradient-to-br from-slate-50 to-white px-5 py-6 sm:flex-row sm:items-center sm:gap-6 sm:px-6">
        <div className="relative w-fit shrink-0">
          <Logo src={data.player.photo} alt={data.player.name} size={96} shape="round" />
          {data.number != null && (
            <span className="absolute -bottom-1 -right-1 grid h-8 w-8 place-items-center rounded-full border-2 border-white bg-slate-900 text-sm font-bold text-white">{data.number}</span>
          )}
        </div>
        <div className="min-w-0 flex-1">
          <h1 className="text-2xl font-semibold tracking-tight sm:text-3xl">{data.player.name}</h1>
          <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-slate-600">
            {team && <span className="flex items-center gap-1.5"><TeamLogo team={team} size={18} /><TeamLink id={team.id}>{team.name}</TeamLink></span>}
            {data.position && <span className="text-slate-400">· {POSITION[data.position] ?? data.position}</span>}
            {data.penalties.taker && <span className="rounded bg-slate-100 px-1.5 text-xs" title={`${data.penalties.scored} Elfmeter verwandelt, ${data.penalties.missed} verschossen (alle Daten)`}>Elfmeterschütze</span>}
          </div>
          <div className="mt-2">
            {data.status ? (
              <span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${data.status.type === "missing" ? "bg-rose-100 text-rose-700" : "bg-amber-100 text-amber-800"}`}>
                {data.status.type === "missing" ? "Fällt aus" : "Fraglich"}: {data.status.reason}
              </span>
            ) : next ? (
              <span className="rounded-full bg-emerald-100 px-2 py-0.5 text-xs font-semibold text-emerald-800">Kein Ausfall gemeldet</span>
            ) : null}
          </div>
        </div>
        <div className="flex flex-col items-start gap-3 sm:items-end">
          <SeasonSelect basePath={`/spieler/${data.player.id}`} season={data.season} seasons={data.seasons} />
          {next && (
            <Link href={`/spiel/${next.fixture_id}`} className="rounded-lg border border-emerald-200 bg-emerald-50/60 px-3 py-2 text-sm hover:border-emerald-300">
              <div className="text-[11px] font-medium uppercase tracking-wide text-emerald-700">Nächstes Spiel</div>
              <div className="flex items-center gap-1.5">
                {opponent && <TeamLogo team={opponent} size={16} />}
                {next.home ? "gegen" : "bei"} {opponent?.name ?? "?"} · {dateShort(next.kickoff)} {time(next.kickoff)}
              </div>
              {next.p_anytime != null && (
                <div className="text-xs text-slate-600">Trifft: <b>{pct(next.p_anytime, 0)}</b>{next.p_first != null && <> · erstes Tor {pct(next.p_first, 0)}</>}</div>
              )}
            </Link>
          )}
        </div>
      </div>
      {s.apps > 0 && (
        <div className="grid grid-cols-3 divide-x divide-slate-100 border-t border-slate-100 text-center sm:grid-cols-6">
          <Kpi label="Einsätze" value={`${s.apps}`} hint={`${s.starts} in der Startelf`} />
          <Kpi label="Minuten" value={`${s.minutes}`} />
          <Kpi label="Tore" value={`${s.goals}`} hint={s.minutes_per_goal ? `alle ${Math.round(s.minutes_per_goal)} Minuten` : undefined} />
          <Kpi label="Vorlagen" value={`${s.assists}`} />
          <Kpi label="Tore / 90" value={s.per90 ? num(s.per90.goals) : "–"} />
          <Kpi label="Note" value={s.rating ? num(s.rating, 1) : "–"} />
        </div>
      )}
    </section>
  );
}

function Kpi({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return (
    <div className="px-2 py-3" title={hint}>
      <div className="text-[11px] uppercase tracking-wide text-slate-500">{label}</div>
      <div className="text-lg font-semibold tabular-nums">{value}</div>
    </div>
  );
}

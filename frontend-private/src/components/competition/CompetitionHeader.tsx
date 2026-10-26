import { Logo } from "@/components/Logo";
import { SeasonSelect } from "@/components/team/SeasonSelect";
import { dateShort, num, pct, time } from "@/lib/format";
import type { CompetitionOverview } from "@/lib/types";

/** Competition header: logo, flag, season, progress and key figures of the season. */
export function CompetitionHeader({ data }: { data: CompetitionOverview }) {
  const { league, progress: p, figures: f } = data;
  return (
    <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
      <div className="flex flex-col gap-4 bg-gradient-to-br from-slate-50 to-white px-5 py-6 sm:flex-row sm:items-center sm:gap-6 sm:px-6">
        <Logo src={league.logo} alt={league.name} size={72} />
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2 text-sm text-slate-500">
            {league.flag && <Logo src={league.flag} alt={league.country ?? "Land"} size={16} />}
            {league.country === "World" ? "International" : league.country}
            {league.cup && <span className="rounded bg-slate-100 px-1.5 text-xs">Europapokal</span>}
          </div>
          <h1 className="text-2xl font-semibold tracking-tight sm:text-3xl">{league.name}</h1>
          <p className="mt-1 text-sm text-slate-600">
            {p.matchday && p.matchdays ? `${p.matchday}. von ${p.matchdays} Spieltagen · ` : ""}
            {p.finished} von {p.matches} Spielen gespielt
            {p.next_kickoff && ` · nächstes Spiel ${dateShort(p.next_kickoff)}, ${time(p.next_kickoff)} Uhr`}
          </p>
        </div>
        <SeasonSelect basePath={`/wettbewerb/${league.id}`} season={data.season} seasons={data.seasons} />
      </div>
      {f && (
        <div className="grid grid-cols-3 divide-x divide-slate-100 border-t border-slate-100 text-center sm:grid-cols-6">
          <Kpi label="Tore pro Spiel" value={num(f.goals_per_match, 2)} />
          <Kpi label="Heimsiege" value={pct(f.home_win, 0)} />
          <Kpi label="Remis" value={pct(f.draw, 0)} />
          <Kpi label="Auswärtssiege" value={pct(f.away_win, 0)} />
          <Kpi label="Über 2,5" value={pct(f.over_2_5, 0)} />
          <Kpi label="Beide treffen" value={pct(f.btts, 0)} />
        </div>
      )}
    </section>
  );
}

function Kpi({ label, value }: { label: string; value: string }) {
  return (
    <div className="px-2 py-3">
      <div className="text-[11px] uppercase tracking-wide text-slate-500">{label}</div>
      <div className="text-lg font-semibold tabular-nums">{value}</div>
    </div>
  );
}

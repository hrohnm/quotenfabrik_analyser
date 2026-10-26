import Link from "next/link";
import { Logo } from "@/components/Logo";
import { TeamLogo } from "@/components/ui";
import { num } from "@/lib/format";
import type { TeamOverview } from "@/lib/types";
import { FormChips } from "@/components/match/FormPanel";
import { SeasonSelect } from "./SeasonSelect";

/** Team page header: logo, competitions with table position, venue (image), coach (photo), form, season. */
export function TeamHeader({ data }: { data: TeamOverview }) {
  const { team, venue, coach } = data;
  const t = data.totals;
  return (
    <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
      <div className="relative">
        {venue && (
          <div className="absolute inset-0 opacity-15">
            {/* stadium image as a soft background (falls back to plain white without image) */}
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src={venue.image} alt="" className="h-full w-full object-cover" />
          </div>
        )}
        <div className="relative flex flex-col gap-4 px-5 py-6 sm:flex-row sm:items-center sm:gap-6 sm:px-6">
          <TeamLogo team={team} size={72} />
          <div className="min-w-0 flex-1">
            <h1 className="text-2xl font-semibold tracking-tight sm:text-3xl">{team.name}</h1>
            <div className="mt-2 flex flex-wrap gap-2">
              {data.competitions.map((c) => (
                <span key={c.league.id} className="inline-flex items-center gap-1.5 rounded-full border border-slate-200 bg-white/90 px-2.5 py-1 text-xs text-slate-700">
                  {c.league.flag && <Logo src={c.league.flag} alt="Flagge" size={14} />}
                  <Logo src={c.league.logo} alt={c.league.name} size={16} />
                  <span className="font-medium">{c.league.name}</span>
                  {c.rank !== null && <span className="text-slate-500">· Platz {c.rank}{c.teams ? `/${c.teams}` : ""} · {c.points} Pkt.</span>}
                </span>
              ))}
            </div>
            <div className="mt-3 flex flex-wrap items-center gap-x-5 gap-y-2 text-sm text-slate-600">
              {coach && (
                <span className="flex items-center gap-2">
                  <Logo src={coach.photo} alt={coach.name} size={28} shape="round" />
                  <span><span className="text-slate-400">Trainer</span> {coach.name}</span>
                </span>
              )}
              {venue && (
                <span className="flex items-center gap-2">
                  <Logo src={venue.image} alt={venue.name} size={28} shape="round" />
                  <span><span className="text-slate-400">Stadion</span> {venue.name}{venue.city ? `, ${venue.city}` : ""}</span>
                </span>
              )}
            </div>
          </div>
          <div className="flex flex-col items-start gap-2 sm:items-end">
            <SeasonSelect teamId={data.team.id} season={data.season} seasons={data.seasons} />
            {data.form.length > 0 && (
              <div className="flex items-center gap-2 text-xs text-slate-500">
                Form
                <span className="flex gap-0.5">
                  {data.form.map((f) => (
                    <Link key={f.fixture_id} href={`/spiel/${f.fixture_id}`} title={`${f.home ? "gegen" : "bei"} ${f.opponent?.name ?? "?"} ${f.score[0]}:${f.score[1]}`}>
                      <FormChips sequence={f.result} />
                    </Link>
                  ))}
                </span>
              </div>
            )}
          </div>
        </div>
      </div>
      {t.played > 0 && (
        <div className="grid grid-cols-3 divide-x divide-slate-100 border-t border-slate-100 text-center sm:grid-cols-6">
          <Kpi label="Spiele" value={String(t.played)} />
          <Kpi label="S – U – N" value={`${t.won}–${t.drawn}–${t.lost}`} />
          <Kpi label="Tore" value={`${num((t.gf_per_game ?? 0) * t.played, 0)}:${num((t.ga_per_game ?? 0) * t.played, 0)}`} />
          <Kpi label="Punkte/Spiel" value={num(t.points_per_game ?? 0)} />
          <Kpi
            label="vs. Modell"
            value={data.expected_points ? `${data.expected_points.diff_per_game >= 0 ? "+" : "−"}${num(Math.abs(data.expected_points.diff_per_game))}` : "–"}
            hint={data.expected_points ? `${data.expected_points.points} Punkte, erwartet ${num(data.expected_points.expected, 1)} (${data.expected_points.matches} Spiele)` : undefined}
          />
          <Kpi label="Zu Null" value={t.clean_sheet != null ? `${Math.round(t.clean_sheet * 100)} %` : "–"} />
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

import { Logo } from "@/components/Logo";
import { SourceBadge, TeamLogo } from "@/components/ui";
import { dateLong, seasonLabel, time } from "@/lib/format";
import { leagueLogo } from "@/lib/media";
import type { FixtureDetail, Team } from "@/lib/types";

type Goal = FixtureDetail["goals"][number];

const GOAL_NOTE: Record<string, string> = { Penalty: "Elfm.", "Own Goal": "ET", "Missed Penalty": "Elfm. verschossen" };

export function Hero({ data }: { data: FixtureDetail }) {
  const { fixture: f, prediction } = data;
  const league = f.league ?? { id: f.league_id, name: "Liga" };
  const goals = data.goals.filter((g) => g.detail !== "Missed Penalty");
  return (
    <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-100 bg-slate-50 px-5 py-2.5 text-xs text-slate-500">
        <div className="flex items-center gap-2">
          <Logo src={league.logo ?? leagueLogo(league.id)} alt={league.name} size={20} />
          <span className="font-medium text-slate-700">{league.name}</span>
          <span>· Saison {seasonLabel(f.season)}{f.round_label ? ` · ${f.round_label}` : f.matchday ? ` · ${f.matchday}. Spieltag` : ""}</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="capitalize">{dateLong(f.kickoff)}</span>
          <SourceBadge kind={prediction?.kind} />
        </div>
      </div>

      <div className="grid grid-cols-[1fr_auto_1fr] items-start gap-3 px-4 py-6 sm:gap-6 sm:px-6">
        <TeamSide team={f.home} goals={goals.filter((g) => g.team_id === f.home.id)} align="end" />
        <div className="pt-4 text-center">
          {f.finished ? (
            <>
              <div className="text-4xl font-bold tabular-nums sm:text-5xl">{f.score.ft[0]}<span className="mx-1 text-slate-300">:</span>{f.score.ft[1]}</div>
              <div className="mt-1 text-xs text-slate-500">HZ {f.score.ht[0]}:{f.score.ht[1]}{f.cup ? " · nach 90 Min." : ""}</div>
              {f.first_leg?.finished && f.first_leg.score && <div className="mt-1 text-xs text-slate-500">Hinspiel {f.first_leg.score[0]}:{f.first_leg.score[1]}</div>}
            </>
          ) : (
            <>
              <div className="text-3xl font-bold tabular-nums sm:text-4xl">{time(f.kickoff)}</div>
              <div className="mt-1 text-xs text-slate-500">Anstoß</div>
              {f.first_leg?.finished && f.first_leg.score && <div className="mt-1 text-xs text-slate-500">Hinspiel {f.first_leg.score[0]}:{f.first_leg.score[1]}</div>}
            </>
          )}
        </div>
        <TeamSide team={f.away} goals={goals.filter((g) => g.team_id === f.away.id)} align="start" />
      </div>

      {(f.venue || f.referee) && (
        <div className="flex flex-wrap justify-center gap-x-4 gap-y-1 border-t border-slate-100 px-5 py-2 text-xs text-slate-400">
          {f.venue && <span>Stadion: {f.venue}</span>}
          {f.referee && <span>Schiedsrichter: {f.referee.replace(/,.*$/, "")}</span>}
        </div>
      )}
    </section>
  );
}

function TeamSide({ team, goals, align }: { team: Team; goals: Goal[]; align: "start" | "end" }) {
  const right = align === "end";
  return (
    <div className={`flex flex-col items-center gap-2 text-center ${right ? "sm:items-end sm:text-right" : "sm:items-start sm:text-left"}`}>
      <div className={`flex flex-col items-center gap-2 sm:flex-row ${right ? "sm:flex-row-reverse" : ""}`}>
        <TeamLogo team={team} size={64} />
        <span className="text-base font-semibold leading-tight sm:text-xl">{team.name}</span>
      </div>
      {goals.length > 0 && (
        <ul className="space-y-0.5 text-xs text-slate-600">
          {goals.map((g, i) => (
            <li key={i}>
              <span className="tabular-nums text-slate-400">{g.minute}{g.extra_minute ? `+${g.extra_minute}` : ""}&apos;</span>{" "}
              {g.player_name}
              {GOAL_NOTE[g.detail] && <span className="text-slate-400"> ({GOAL_NOTE[g.detail]})</span>}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

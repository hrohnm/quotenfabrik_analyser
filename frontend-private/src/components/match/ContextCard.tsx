import Link from "next/link";
import { Logo } from "@/components/Logo";
import { Card, TeamLogo } from "@/components/ui";
import { dateShort } from "@/lib/format";
import { leagueLogo } from "@/lib/media";
import type { ContextAbsence, FixtureDetail, NeighbourMatch, Team, TeamContext } from "@/lib/types";

const CUP_DAYS = 4.5;
const competition = (name: string) => name.replace("UEFA ", "").replace("Europa Conference League", "Conference League");

/** "Termine & Personal": previous / next match of both teams and reported absences (facts, not in the model). */
export function ContextCard({ data }: { data: FixtureDetail }) {
  const ctx = data.context;
  if (!ctx) return null;
  return (
    <Card title="Termine & Personal">
      <div className="grid gap-5 md:grid-cols-2">
        <TeamColumn team={data.fixture.home} ctx={ctx.home} />
        <TeamColumn team={data.fixture.away} ctx={ctx.away} />
      </div>
      <p className="mt-4 text-xs text-slate-400">
        Spiele aller Wettbewerbe in der Datenbank (ohne nationale Pokale), Ausfälle laut API-Football. Stammspieler = in mindestens 5 der
        letzten 10 Spiele in der Startelf. Das Modell berücksichtigt das nicht: im Backtest kein messbarer Gewinn (docs/22).
      </p>
    </Card>
  );
}

function TeamColumn({ team, ctx }: { team: Team; ctx: TeamContext }) {
  const regulars = ctx.absences.filter((a) => a.type === "missing" && a.regular);
  const others = ctx.absences.filter((a) => a.type === "missing" && !a.regular);
  const doubtful = ctx.absences.filter((a) => a.type === "doubtful");
  return (
    <div className="min-w-0 space-y-3">
      <div className="flex items-center gap-2 font-medium"><TeamLogo team={team} size={18} />{team.name}</div>
      <div className="space-y-1.5 text-sm">
        <MatchRow label="Zuletzt" m={ctx.prev} />
        <MatchRow label="Danach" m={ctx.next} />
      </div>
      <div>
        <div className="mb-1 text-[11px] font-semibold uppercase tracking-wide text-slate-500">
          Ausfälle{regulars.length > 0 && <span className="ml-1 rounded-full bg-rose-100 px-1.5 text-rose-700">{regulars.length} Stammspieler</span>}
        </div>
        {ctx.absences.length === 0 ? (
          <p className="text-xs text-slate-400">Keine Ausfälle gemeldet.</p>
        ) : (
          <div className="flex flex-wrap gap-1.5">
            {[...regulars, ...doubtful, ...others].map((a) => <AbsenceChip key={a.player_id} a={a} />)}
          </div>
        )}
      </div>
    </div>
  );
}

function MatchRow({ label, m }: { label: string; m: NeighbourMatch | null }) {
  if (!m) return <div className="flex gap-2 text-slate-400"><span className="w-14 shrink-0 text-xs uppercase tracking-wide">{label}</span>–</div>;
  const close = m.days <= CUP_DAYS;
  const warn = close && m.cup;
  const days = Math.round(m.days);
  return (
    <div className="flex items-center gap-2">
      <span className="w-14 shrink-0 text-xs uppercase tracking-wide text-slate-500">{label}</span>
      <Link href={`/spiel/${m.fixture_id}`} className="flex min-w-0 flex-1 items-center gap-1.5 hover:opacity-80">
        <Logo src={leagueLogo(m.league_id)} alt={m.league} size={14} />
        <span className="truncate">
          {m.home ? "gegen" : "bei"} {m.opponent}
          {m.score && <b className="ml-1 tabular-nums">{m.score[0]}:{m.score[1]}</b>}
        </span>
      </Link>
      <span
        className={`shrink-0 rounded px-1.5 py-0.5 text-[11px] tabular-nums ${warn ? "bg-amber-100 font-semibold text-amber-800" : close ? "bg-slate-100 text-slate-700" : "text-slate-400"}`}
        title={`${competition(m.league)}, ${dateShort(m.kickoff)}`}
      >
        {label === "Zuletzt" ? `vor ${days} Tg.` : `in ${days} Tg.`}
        {warn && <span className="hidden sm:inline"> · {competition(m.league)}</span>}
      </span>
    </div>
  );
}

function AbsenceChip({ a }: { a: ContextAbsence }) {
  const tone = a.type === "doubtful" ? "border-amber-200 bg-amber-50 text-amber-800" : a.regular ? "border-rose-200 bg-rose-50 font-medium text-rose-800" : "border-slate-200 bg-white text-slate-600";
  const role = a.start_share > 0 ? `Startelf in ${Math.round(a.start_share * 10)} der letzten 10 Spiele` : "zuletzt nicht in der Startelf";
  const attack = a.attack_share >= 0.05 ? `, ${Math.round(a.attack_share * 100)} % der Tore + Vorlagen` : "";
  return (
    <span className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-xs ${tone}`} title={`${a.reason_label} · ${role}${attack}`}>
      {a.type === "doubtful" && <span aria-hidden>?</span>}
      {a.name ?? "?"}
      <span className="opacity-60">{a.reason_label}</span>
    </span>
  );
}

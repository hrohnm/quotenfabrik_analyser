import Link from "next/link";
import { notFound } from "next/navigation";
import { getFixture } from "@/lib/api";
import { dateLong, num, odd, pct, seasonLabel, time } from "@/lib/format";
import { Card, OutcomeBadge, ProbabilityBar, SourceBadge, TeamLogo } from "@/components/ui";
import type { FixtureDetail, Market, Pattern, Scorer } from "@/lib/types";

export const dynamic = "force-dynamic";

const GROUP_ORDER = ["1x2", "totals", "team_totals", "halves"] as const;
const GROUP_TITLES: Record<string, string> = {
  "1x2": "Spielausgang",
  totals: "Tore gesamt",
  team_totals: "Tore pro Team",
  halves: "Halbzeiten",
  scorers: "Torschützen",
};

export default async function FixturePage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  let data: FixtureDetail;
  try {
    data = await getFixture(id);
  } catch {
    notFound();
  }
  const { fixture: f, prediction, markets } = data;
  const day = new Date(f.kickoff).toLocaleDateString("en-CA", { timeZone: "Europe/Berlin" });

  return (
    <div className="space-y-6">
      <Link href={`/spieltage?datum=${day}`} className="text-sm text-slate-500 hover:text-slate-900">← zurück zum Spieltag</Link>

      <Card>
        <div className="grid items-center gap-6 md:grid-cols-[1fr_auto_1fr]">
          <div className="flex items-center gap-3 md:justify-end">
            <span className="text-xl font-semibold">{f.home.name}</span>
            <TeamLogo team={f.home} size={48} />
          </div>
          <div className="text-center">
            <div className="text-4xl font-bold tabular-nums">{f.finished ? `${f.score.ft[0]} : ${f.score.ft[1]}` : "– : –"}</div>
            {f.finished && <div className="text-sm text-slate-500">Halbzeit {f.score.ht[0]} : {f.score.ht[1]}</div>}
          </div>
          <div className="flex items-center gap-3">
            <TeamLogo team={f.away} size={48} />
            <span className="text-xl font-semibold">{f.away.name}</span>
          </div>
        </div>
        <div className="mt-4 flex flex-wrap justify-center gap-x-4 gap-y-1 text-sm text-slate-500">
          <span className="capitalize">{dateLong(f.kickoff)}, {time(f.kickoff)} Uhr</span>
          <span>Saison {seasonLabel(f.season)}{f.matchday ? ` · ${f.matchday}. Spieltag` : ""}</span>
          {f.venue && <span>{f.venue}</span>}
          {f.referee && <span>Schiedsrichter: {f.referee}</span>}
          <SourceBadge kind={prediction?.kind} />
        </div>
        {prediction?.kind === "backtest" && (
          <p className="mt-3 text-center text-xs text-slate-400">
            Rückwirkende Prognose: Modell nur mit Spielen vor diesem Spieltag trainiert (Walk-Forward), Torschützen mit bekannter Aufstellung.
          </p>
        )}
      </Card>

      {data.goals.length > 0 && <Goals data={data} />}

      <nav className="flex flex-wrap gap-2 text-sm">
        {[...GROUP_ORDER, "scorers", "pattern", "statistik"].map((g) => (
          <a key={g} href={`#${g}`} className="rounded-full border border-slate-200 bg-white px-3 py-1 hover:border-slate-400">
            {GROUP_TITLES[g] ?? (g === "pattern" ? "Pattern" : "Statistik")}
          </a>
        ))}
      </nav>

      {markets.length === 0 && <Card><p className="text-sm text-slate-500">Für dieses Spiel liegt noch keine Prognose vor.</p></Card>}

      {GROUP_ORDER.map((g) => {
        const ms = markets.filter((m) => m.group === g);
        if (ms.length === 0) return null;
        return (
          <section key={g} id={g} className="scroll-mt-20 space-y-3">
            <h2 className="text-lg font-semibold">{GROUP_TITLES[g]}</h2>
            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
              {ms.map((m) => <MarketCard key={`${m.market}-${m.line}`} m={m} />)}
            </div>
          </section>
        );
      })}

      <section id="scorers" className="scroll-mt-20">
        <Scorers data={data} />
      </section>
      <section id="pattern" className="scroll-mt-20">
        <Patterns patterns={data.patterns} home={f.home.name} away={f.away.name} />
      </section>
      <section id="statistik" className="scroll-mt-20">
        <MatchStats data={data} />
      </section>
    </div>
  );
}

function MarketCard({ m }: { m: Market }) {
  const best = Math.max(...m.selections.map((s) => s.probability));
  return (
    <Card title={<>{m.label}{m.line !== null && <span className="ml-1 text-slate-500">{num(m.line, m.line % 1 ? 1 : 0)}</span>}</>}>
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-xs text-slate-400">
            <th className="pb-1 font-medium">Auswahl</th>
            <th className="pb-1 font-medium">Wahrscheinlichkeit</th>
            <th className="pb-1 text-right font-medium">Faire Quote</th>
            <th className="pb-1" />
          </tr>
        </thead>
        <tbody>
          {m.selections.map((s) => (
            <tr key={s.selection} className={s.probability === best ? "font-semibold" : ""}>
              <td className="py-1 pr-2">{s.label}</td>
              <td className="py-1 pr-2">
                <div className="flex items-center gap-2">
                  <span className="w-14 shrink-0 whitespace-nowrap tabular-nums">{pct(s.probability)}</span>
                  <div className="flex-1"><ProbabilityBar value={s.probability} tone={s.probability === best ? "emerald" : "slate"} /></div>
                </div>
              </td>
              <td className="py-1 text-right tabular-nums">{odd(s.fair_odd)}</td>
              <td className="py-1 pl-2 text-right"><OutcomeBadge outcome={s.outcome} small /></td>
            </tr>
          ))}
        </tbody>
      </table>
    </Card>
  );
}

function Scorers({ data }: { data: FixtureDetail }) {
  const { fixture: f } = data;
  const team = (s: Scorer) => (s.team_id === f.home.id ? f.home.name : s.team_id === f.away.id ? f.away.name : "–");
  const rows = data.scorers.filter((s) => (s.anytime ?? 0) >= 0.03).slice(0, 24);
  return (
    <Card title="Torschützen">
      {rows.length === 0 ? (
        <p className="text-sm text-slate-500">Keine Torschützen-Prognose vorhanden.</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-xs text-slate-400">
                <th className="pb-2 font-medium">Spieler</th><th className="pb-2 font-medium">Team</th><th className="pb-2 font-medium">Pos.</th>
                <th className="pb-2 font-medium">Anytime</th><th className="pb-2 text-right font-medium">Faire Quote</th>
                <th className="pb-2 text-right font-medium">Erster Torschütze</th><th className="pb-2 text-right font-medium">Tore</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {rows.map((s) => (
                <tr key={s.player_id}>
                  <td className="py-1.5 font-medium">{s.name ?? s.player_id}{s.is_starter === false && <span className="ml-1 text-xs text-slate-400">(Bank)</span>}</td>
                  <td className="py-1.5 text-slate-600">{team(s)}</td>
                  <td className="py-1.5 text-slate-500">{s.position ?? "–"}</td>
                  <td className="py-1.5">
                    <div className="flex items-center gap-2"><span className="w-14 shrink-0 whitespace-nowrap tabular-nums">{pct(s.anytime)}</span><div className="w-24"><ProbabilityBar value={s.anytime ?? 0} /></div></div>
                  </td>
                  <td className="py-1.5 text-right tabular-nums">{s.anytime ? odd(1 / s.anytime) : "–"}</td>
                  <td className="py-1.5 text-right tabular-nums">{pct(s.first)}</td>
                  <td className="py-1.5 text-right">
                    {f.finished ? <span className="inline-flex items-center gap-2">{s.goals ?? 0}<OutcomeBadge outcome={s.anytime_outcome} small /></span> : "–"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Card>
  );
}

function Patterns({ patterns, home, away }: { patterns: Pattern[]; home: string; away: string }) {
  const groups = ["1x2", "totals", "team_totals", "halves"];
  const fmt = (p: Pattern) => {
    if (p.value === null) return "–";
    const isRate = p.baseline !== null && p.baseline <= 1 && p.value <= 1 && !p.key.includes("goals") && !p.key.includes("xg") && !p.key.includes("ppg") && !p.key.includes("diff");
    return isRate ? pct(p.value, 0) : num(p.value);
  };
  return (
    <Card title={`Pattern (vor Anpfiff): ${home} – ${away}`}>
      <div className="grid gap-6 lg:grid-cols-2">
        {groups.map((g) => (
          <div key={g}>
            <h3 className="mb-2 text-sm font-semibold text-slate-700">{GROUP_TITLES[g]}</h3>
            <table className="w-full text-sm">
              <tbody className="divide-y divide-slate-100">
                {patterns.filter((p) => p.group === g && !p.key.endsWith("goal_timing")).map((p) => (
                  <tr key={p.key}>
                    <td className="py-1 pr-2 text-slate-700">{p.label}</td>
                    <td className="py-1 text-right font-medium tabular-nums">{fmt(p)}</td>
                    <td className="py-1 pl-2 text-right text-xs text-slate-400">{p.n !== null ? `n=${p.n}` : ""}{p.baseline !== null && p.baseline <= 1 ? ` · Liga ${pct(p.baseline, 0)}` : ""}</td>
                    <td className="py-1 pl-2 text-right">
                      {p.signal === "high" && <span className="rounded bg-emerald-100 px-1.5 py-0.5 text-xs font-medium text-emerald-700">hoch</span>}
                      {p.signal === "low" && <span className="rounded bg-rose-100 px-1.5 py-0.5 text-xs font-medium text-rose-700">niedrig</span>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ))}
        <GoalTiming patterns={patterns} />
      </div>
    </Card>
  );
}

function GoalTiming({ patterns }: { patterns: Pattern[] }) {
  const timing = patterns.filter((p) => p.key.endsWith("goal_timing") && p.details);
  if (timing.length === 0) return null;
  return (
    <div>
      <h3 className="mb-2 text-sm font-semibold text-slate-700">Tor-Timing (eigene Tore, letzte 10 Heim-/Auswärtsspiele)</h3>
      {timing.map((p) => {
        const values = Object.entries(p.details ?? {});
        const max = Math.max(1, ...values.map(([, v]) => v));
        return (
          <div key={p.key} className="mb-3">
            <div className="mb-1 text-xs text-slate-500">{p.scope === "home" ? "Heimteam" : "Gastteam"} · {p.n} Tore</div>
            <div className="flex items-end gap-1">
              {values.map(([k, v]) => (
                <div key={k} className="flex flex-1 flex-col items-center gap-1">
                  <div className="w-full rounded-t bg-emerald-400" style={{ height: `${(v / max) * 48 + 2}px` }} title={`${v} Tore`} />
                  <span className="text-[10px] text-slate-400">{k}</span>
                </div>
              ))}
            </div>
          </div>
        );
      })}
    </div>
  );
}

const STAT_ROWS: [string, string][] = [
  ["xg", "Expected Goals (xG)"], ["shots_total", "Schüsse"], ["shots_on", "Schüsse aufs Tor"], ["possession", "Ballbesitz %"],
  ["corners", "Ecken"], ["fouls", "Fouls"], ["yellow", "Gelbe Karten"], ["passes_total", "Pässe"],
];

function MatchStats({ data }: { data: FixtureDetail }) {
  const { stats, fixture: f } = data;
  const periods = ["FT", "1H", "2H"].filter((p) => stats.home[p] || stats.away[p]);
  if (periods.length === 0) return <Card title="Statistik"><p className="text-sm text-slate-500">Noch keine Spielstatistik vorhanden.</p></Card>;
  return (
    <Card title="Statistik">
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-xs text-slate-400">
              <th className="pb-2 text-left font-medium">Wert</th>
              {periods.map((p) => <th key={p} className="pb-2 text-center font-medium" colSpan={2}>{p === "FT" ? "Gesamt" : p === "1H" ? "1. HZ" : "2. HZ"}</th>)}
            </tr>
            <tr className="text-xs text-slate-400">
              <th />
              {periods.map((p) => [<th key={`${p}h`} className="pb-1 text-right font-normal">{f.home.name}</th>, <th key={`${p}a`} className="pb-1 pl-3 text-right font-normal">{f.away.name}</th>])}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {STAT_ROWS.map(([k, label]) => (
              <tr key={k}>
                <td className="py-1.5 text-slate-600">{label}</td>
                {periods.map((p) => [
                  <td key={`${p}h`} className="py-1.5 text-right tabular-nums">{fmtStat(stats.home[p]?.[k])}</td>,
                  <td key={`${p}a`} className="py-1.5 pl-3 text-right tabular-nums">{fmtStat(stats.away[p]?.[k])}</td>,
                ])}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  );
}

const fmtStat = (v: number | null | undefined) => (v === null || v === undefined ? "–" : Number.isInteger(v) ? String(v) : num(v));

function Goals({ data }: { data: FixtureDetail }) {
  const { fixture: f } = data;
  const column = (teamId: number) => (
    <ol className="space-y-1">
      {data.goals.filter((g) => g.team_id === teamId).map((g, i) => (
        <li key={i} className="flex items-center gap-2">
          <span className="w-12 tabular-nums text-slate-500">{g.minute}{g.extra_minute ? `+${g.extra_minute}` : ""}&apos;</span>
          <span className="font-medium">{g.player_name}</span>
          {g.detail !== "Normal Goal" && <span className="text-xs text-slate-400">({g.detail === "Penalty" ? "Elfmeter" : g.detail === "Own Goal" ? "Eigentor" : g.detail})</span>}
        </li>
      ))}
    </ol>
  );
  return (
    <Card title="Tore">
      <div className="grid gap-4 text-sm sm:grid-cols-2">
        <div><div className="mb-1 text-xs font-medium text-slate-400">{f.home.name}</div>{column(f.home.id)}</div>
        <div><div className="mb-1 text-xs font-medium text-slate-400">{f.away.name}</div>{column(f.away.id)}</div>
      </div>
    </Card>
  );
}

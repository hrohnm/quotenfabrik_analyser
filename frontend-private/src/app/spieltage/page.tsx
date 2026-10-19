import Link from "next/link";
import { getDays, getFixtures } from "@/lib/api";
import { addDays, berlinToday, dateLong, dayMonth, pct, time, weekday } from "@/lib/format";
import { Card, OutcomeBadge, SourceBadge, TeamLogo, ThreeWayBar } from "@/components/ui";
import type { Day, Fixture } from "@/lib/types";
import { ScrollToActive } from "@/components/ScrollToActive";

export const dynamic = "force-dynamic";

function pickDefaultDay(days: Day[], today: string): string | undefined {
  return days.find((d) => d.date >= today)?.date ?? days.at(-1)?.date;
}

export default async function MatchdaysPage({ searchParams }: { searchParams: Promise<{ datum?: string }> }) {
  const { datum } = await searchParams;
  const today = berlinToday();
  const center = datum ?? today;
  const days = await getDays(addDays(center, -45), addDays(center, 45));
  const selected = datum ?? pickDefaultDay(days, today);
  const fixtures = selected ? await getFixtures(selected) : [];
  const idx = days.findIndex((d) => d.date === selected);
  const prev = idx > 0 ? days[idx - 1] : undefined;
  const next = idx >= 0 && idx < days.length - 1 ? days[idx + 1] : undefined;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Spieltagsübersicht</h1>
          <p className="text-sm text-slate-500">Spiele pro Tag mit Modellwahrscheinlichkeiten. Vergangene Spiele zeigen die rückwirkende Prognose und ob sie eingetreten ist.</p>
        </div>
        <form className="flex items-end gap-2" action="/spieltage">
          <label className="flex flex-col gap-1 text-xs font-medium text-slate-500">
            Datum
            <input type="date" name="datum" defaultValue={selected} className="rounded-md border border-slate-300 bg-white px-2 py-1.5 text-sm text-slate-900" />
          </label>
          <button className="rounded-md bg-slate-900 px-3 py-1.5 text-sm text-white">Anzeigen</button>
          <Link href={`/spieltage?datum=${pickDefaultDay(days, today) ?? today}`} className="rounded-md border border-slate-300 bg-white px-3 py-1.5 text-sm">
            Heute
          </Link>
        </form>
      </div>

      <ScrollToActive id="aktiver-tag" />
      <div className="flex gap-2 overflow-x-auto pb-2">
        {days.map((d) => {
          const active = d.date === selected;
          const past = d.date < today;
          return (
            <Link
              key={d.date}
              id={active ? "aktiver-tag" : undefined}
              href={`/spieltage?datum=${d.date}`}
              className={`flex min-w-16 flex-col items-center rounded-lg border px-3 py-2 text-xs transition ${
                active ? "border-slate-900 bg-slate-900 text-white" : past ? "border-slate-200 bg-white text-slate-500 hover:border-slate-400" : "border-emerald-200 bg-emerald-50 text-emerald-900 hover:border-emerald-400"
              }`}
            >
              <span className="font-medium">{weekday(d.date)}</span>
              <span className="text-sm font-semibold">{dayMonth(d.date)}</span>
              <span className={active ? "text-slate-300" : "text-slate-500"}>{d.fixtures} {d.fixtures === 1 ? "Spiel" : "Spiele"}</span>
            </Link>
          );
        })}
      </div>

      {selected ? (
        <Card
          title={<span className="capitalize">{dateLong(`${selected}T12:00:00Z`)} · {fixtures.length} {fixtures.length === 1 ? "Spiel" : "Spiele"}</span>}
          actions={
            <div className="flex gap-2 text-sm">
              {prev && <Link className="rounded-md border border-slate-200 px-2 py-1 hover:bg-slate-50" href={`/spieltage?datum=${prev.date}`}>← {dayMonth(prev.date)}</Link>}
              {next && <Link className="rounded-md border border-slate-200 px-2 py-1 hover:bg-slate-50" href={`/spieltage?datum=${next.date}`}>{dayMonth(next.date)} →</Link>}
            </div>
          }
        >
          {fixtures.length === 0 ? (
            <p className="text-sm text-slate-500">Keine Spiele an diesem Tag.</p>
          ) : (
            <div className="divide-y divide-slate-100">
              <div className="hidden grid-cols-[60px_1fr_70px_200px_90px_90px_40px] gap-4 pb-2 text-xs font-medium uppercase tracking-wide text-slate-400 md:grid">
                <span>Anstoß</span><span>Begegnung</span><span className="text-center">Ergebnis</span><span>1 · X · 2</span><span className="text-right">Über 2,5</span><span className="text-right">Beide tr.</span><span />
              </div>
              {fixtures.map((f) => <FixtureRow key={f.id} f={f} />)}
            </div>
          )}
        </Card>
      ) : (
        <p className="text-sm text-slate-500">Keine Spiele im Zeitraum gefunden.</p>
      )}
    </div>
  );
}

function FixtureRow({ f }: { f: Fixture }) {
  const p = f.prediction?.probabilities ?? {};
  const o = f.prediction?.outcomes ?? {};
  const pick = f.prediction?.pick_1x2;
  const labels = { home: "1", draw: "X", away: "2" } as const;
  return (
    <Link href={`/spiel/${f.id}`} className="grid grid-cols-1 items-center gap-2 py-3 hover:bg-slate-50 md:grid-cols-[60px_1fr_70px_200px_90px_90px_40px] md:gap-4">
      <span className="text-sm font-medium text-slate-600">{time(f.kickoff)}</span>
      <div className="space-y-1">
        <div className="flex items-center gap-2 font-medium"><TeamLogo team={f.home} size={20} />{f.home.name}</div>
        <div className="flex items-center gap-2 font-medium"><TeamLogo team={f.away} size={20} />{f.away.name}</div>
      </div>
      <div className="text-center text-lg font-semibold tabular-nums">
        {f.finished ? `${f.score.ft[0]}:${f.score.ft[1]}` : <span className="text-slate-300">–:–</span>}
        {f.finished && <div className="text-xs font-normal text-slate-400">({f.score.ht[0]}:{f.score.ht[1]})</div>}
      </div>
      <div className="space-y-1">
        <ThreeWayBar home={p.home} draw={p.draw} away={p.away} />
        <div className="flex justify-between text-xs tabular-nums text-slate-600">
          {(["home", "draw", "away"] as const).map((k) => (
            <span key={k} className={pick === k ? "font-semibold text-slate-900" : ""}>
              {labels[k]} {pct(p[k], 0)}
            </span>
          ))}
        </div>
      </div>
      <div className="flex items-center justify-end gap-2 text-sm tabular-nums">{pct(p.over25, 0)} <OutcomeBadge outcome={o.over25} small /></div>
      <div className="flex items-center justify-end gap-2 text-sm tabular-nums">{pct(p.btts, 0)} <OutcomeBadge outcome={o.btts} small /></div>
      <div className="flex justify-end" title="Hat der 1X2-Favorit des Modells getroffen?">
        {f.prediction ? <OutcomeBadge outcome={f.prediction.pick_1x2_hit} /> : <SourceBadge kind={null} />}
      </div>
    </Link>
  );
}

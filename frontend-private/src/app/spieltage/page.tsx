import Link from "next/link";
import { getDays, getFixtures, getMeta } from "@/lib/api";
import { addDays, berlinToday, dateLong, dayMonth, pct, time, weekday } from "@/lib/format";
import { Card, TeamLogo, ThreeWayBar } from "@/components/ui";
import { BetanoOdd } from "@/components/BetanoOdd";
import type { Day, Fixture } from "@/lib/types";
import { ScrollToActive } from "@/components/ScrollToActive";
import { Logo } from "@/components/Logo";
import { leagueLogo } from "@/lib/media";
import { PickChips } from "@/components/picks/PickList";

export const dynamic = "force-dynamic";

function pickDefaultDay(days: Day[], today: string): string | undefined {
  return days.find((d) => d.date >= today)?.date ?? days.at(-1)?.date;
}

export default async function MatchdaysPage({ searchParams }: { searchParams: Promise<{ datum?: string; liga?: string }> }) {
  const { datum, liga } = await searchParams;
  const today = berlinToday();
  const center = datum ?? today;
  const [days, meta] = await Promise.all([getDays(addDays(center, -45), addDays(center, 45), liga), getMeta()]);
  const selected = datum ?? pickDefaultDay(days, today);
  const fixtures = selected ? await getFixtures(selected, liga) : [];
  const leagues = meta.leagues.filter((l) => fixtures.some((f) => f.league_id === l.id));
  const link = (patch: { datum?: string; liga?: string | null }) => {
    const q = new URLSearchParams();
    const d = patch.datum ?? selected;
    const l = patch.liga === undefined ? liga : patch.liga;
    if (d) q.set("datum", d);
    if (l) q.set("liga", l);
    return `/spieltage?${q}`;
  };
  const idx = days.findIndex((d) => d.date === selected);
  const prev = idx > 0 ? days[idx - 1] : undefined;
  const next = idx >= 0 && idx < days.length - 1 ? days[idx + 1] : undefined;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="flex items-center gap-2 text-2xl font-semibold tracking-tight">
            {liga && <Logo src={leagueLogo(Number(liga))} alt="Liga" size={32} />}Spieltagsübersicht
          </h1>
          <p className="text-sm text-slate-500">Spiele pro Tag mit Modellwahrscheinlichkeiten. Vergangene Spiele zeigen die rückwirkende Prognose und ob sie eingetreten ist.</p>
        </div>
        <form className="flex items-end gap-2" action="/spieltage">
          {liga && <input type="hidden" name="liga" value={liga} />}
          <label className="flex flex-col gap-1 text-xs font-medium text-slate-500">
            Datum
            <input type="date" name="datum" defaultValue={selected} className="rounded-md border border-slate-300 bg-white px-2 py-1.5 text-sm text-slate-900" />
          </label>
          <button className="rounded-md bg-slate-900 px-3 py-1.5 text-sm text-white">Anzeigen</button>
          <Link href={link({ datum: pickDefaultDay(days, today) ?? today })} className="rounded-md border border-slate-300 bg-white px-3 py-1.5 text-sm">
            Heute
          </Link>
        </form>
      </div>

      <div className="flex flex-wrap gap-2 text-sm">
        {[{ id: "", name: "Alle Ligen" }, ...meta.leagues.map((l) => ({ id: String(l.id), name: l.name }))].map((l) => (
          <Link
            key={l.id}
            href={link({ liga: l.id || null })}
            className={`flex items-center gap-2 rounded-full border px-3 py-1 ${(liga ?? "") === l.id ? "border-slate-900 bg-slate-900 text-white" : "border-slate-200 bg-white text-slate-600 hover:border-slate-400"}`}
          >
            {l.id && <Logo src={leagueLogo(Number(l.id))} alt={l.name} size={16} />}
            {l.name}
          </Link>
        ))}
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
              href={link({ datum: d.date })}
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
              {prev && <Link className="rounded-md border border-slate-200 px-2 py-1 hover:bg-slate-50" href={link({ datum: prev.date })}>← {dayMonth(prev.date)}</Link>}
              {next && <Link className="rounded-md border border-slate-200 px-2 py-1 hover:bg-slate-50" href={link({ datum: next.date })}>{dayMonth(next.date)} →</Link>}
            </div>
          }
        >
          {fixtures.length === 0 ? (
            <p className="text-sm text-slate-500">Keine Spiele an diesem Tag.</p>
          ) : (
            <div className="divide-y divide-slate-100">
              <div className="hidden grid-cols-[60px_1fr_70px_240px] gap-4 pb-2 text-xs font-medium uppercase tracking-wide text-slate-400 md:grid">
                <span>Anstoß</span><span>Begegnung</span><span className="text-center">Ergebnis</span><span>1 · X · 2 <span className="normal-case tracking-normal">(Betano-Quote)</span></span>
              </div>
              {leagues.map((l) => (
                <div key={l.id}>
                  {leagues.length > 1 && (
                    <div className="flex items-center gap-2 bg-slate-50 px-2 py-1.5 text-xs font-semibold uppercase tracking-wide text-slate-500">
                      <Logo src={leagueLogo(l.id)} alt={l.name} size={16} />
                      <Link href={`/wettbewerb/${l.id}`} className="hover:text-slate-900 hover:underline">{l.name}</Link>
                    </div>
                  )}
                  <div className="divide-y divide-slate-100">
                    {fixtures.filter((f) => f.league_id === l.id).map((f) => <FixtureRow key={f.id} f={f} />)}
                  </div>
                </div>
              ))}
            </div>
          )}
        </Card>
      ) : (
        <p className="text-sm text-slate-500">Keine Spiele im Zeitraum gefunden.</p>
      )}
    </div>
  );
}

/** Round and, for second legs, the first-leg score (goals of today's home team first). */
function CupInfo({ f }: { f: Fixture }) {
  const leg = f.first_leg;
  return (
    <div className="flex flex-wrap gap-x-2 text-xs text-slate-500">
      {f.round_label && <span>{f.round_label}</span>}
      {leg && (
        <span title="Ergebnis des Hinspiels aus Sicht der heutigen Paarung (Heim:Gast); abgerechnet wird nur dieses Spiel nach 90 Minuten">
          · Hinspiel {leg.finished && leg.score ? `${leg.score[0]}:${leg.score[1]}` : "noch offen"}
        </span>
      )}
    </div>
  );
}

function FixtureRow({ f }: { f: Fixture }) {
  const p = f.prediction?.probabilities ?? {};
  const o = f.prediction?.outcomes ?? {};
  const betano = f.prediction?.betano ?? {};
  const pick = f.prediction?.pick_1x2;
  const labels = { home: "1", draw: "X", away: "2" } as const;
  return (
    <Link href={`/spiel/${f.id}`} className="grid grid-cols-1 items-center gap-2 py-3 hover:bg-slate-50 md:grid-cols-[60px_1fr_70px_240px] md:gap-4">
      <span className="text-sm font-medium text-slate-600">{time(f.kickoff)}</span>
      <div className="space-y-1">
        <div className="flex items-center gap-2 font-medium"><TeamLogo team={f.home} size={20} />{f.home.name}</div>
        <div className="flex items-center gap-2 font-medium"><TeamLogo team={f.away} size={20} />{f.away.name}</div>
        {f.cup && <CupInfo f={f} />}
      </div>
      <div className="text-center text-lg font-semibold tabular-nums">
        {f.finished ? `${f.score.ft[0]}:${f.score.ft[1]}` : <span className="text-slate-300">–:–</span>}
        {f.finished && <div className="text-xs font-normal text-slate-400">({f.score.ht[0]}:{f.score.ht[1]})</div>}
      </div>
      <div className="space-y-1">
        <ThreeWayBar home={p.home} draw={p.draw} away={p.away} />
        <div className="flex justify-between text-xs tabular-nums text-slate-600">
          {(["home", "draw", "away"] as const).map((k) => (
            <span
              key={k}
              className={`flex flex-col items-center gap-0.5 ${pick === k ? "font-semibold text-slate-900" : ""} ${f.finished && o[k] ? "rounded bg-emerald-50 px-1" : ""}`}
              title={f.finished && o[k] ? "eingetreten" : undefined}
            >
              <span>{labels[k]} {pct(p[k], 0)}</span>
              {betano[k] && <BetanoOdd prices={betano[k]} />}
            </span>
          ))}
        </div>
      </div>
      {f.picks && f.picks.length > 0 && (
        <div className="flex items-center gap-2 md:col-start-2 md:col-end-5">
          <span className="text-xs font-medium text-slate-400">Tipps</span>
          <PickChips picks={f.picks} finished={f.finished} />
        </div>
      )}
    </Link>
  );
}

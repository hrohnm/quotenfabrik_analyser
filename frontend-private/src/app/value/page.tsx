"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { api, getDays, getMeta } from "@/lib/api";
import { addDays, berlinToday, dateLong, dateShort, odd, pct, signedPct, time, weekday } from "@/lib/format";
import type { Day, Meta, ValueDay, ValueResult, ValueStats } from "@/lib/types";
import { Card, OutcomeBadge, StatTile, TeamLogo } from "@/components/ui";
import { Segmented } from "@/components/match/Segmented";
import { Logo } from "@/components/Logo";
import { leagueLogo } from "@/lib/media";
import { AddToSlip } from "@/components/bets/BetSlip";
import { CompetitionBadge } from "@/components/CompetitionBadge";

const SOURCE: Record<string, { label: string; tone: string; title: string }> = {
  fixiert: { label: "fixiert", tone: "bg-slate-900 text-white", title: "So am Spieltag gezeigt (mit der Quote von damals)" },
  aktuell: { label: "aktuell", tone: "bg-emerald-100 text-emerald-800", title: "Mit den aktuellen Betano- und Pinnacle-Preisen" },
  "rückwirkend": { label: "rückwirkend", tone: "bg-amber-100 text-amber-800", title: "Nachträglich berechnet mit den Preisen zum Zeitpunkt der Prognose" },
};

export default function ValuePage() {
  const [meta, setMeta] = useState<Meta | null>(null);
  const [league, setLeague] = useState("");
  const [days, setDays] = useState<Day[]>([]);
  const [day, setDay] = useState<string | null>(null);
  const [data, setData] = useState<ValueDay | null>(null);
  const [stats, setStats] = useState<ValueStats | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => { getMeta().then(setMeta).catch((e) => setError(String(e))); }, []);
  useEffect(() => { api<ValueStats>("/stats/value").then(setStats).catch((e) => setError(String(e))); }, []);
  useEffect(() => {
    const today = berlinToday();
    getDays(addDays(today, -60), addDays(today, 30), league || undefined)
      .then((list) => { setDays(list); setDay((cur) => cur ?? list.find((d) => d.date >= today)?.date ?? list.at(-1)?.date ?? today); })
      .catch((e) => setError(String(e)));
  }, [league]);
  useEffect(() => {
    if (!day) return;
    let current = true;
    setData(null);
    api<ValueDay>("/value", { date: day, league: league || undefined }).then((d) => current && setData(d)).catch((e) => current && setError(String(e)));
    return () => { current = false; };
  }, [day, league]);

  const idx = days.findIndex((d) => d.date === day);
  const prev = idx > 0 ? days[idx - 1].date : undefined;
  const next = idx >= 0 ? days[idx + 1]?.date : undefined;
  const s = data?.settings ?? stats?.backtest.settings;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Value-Tipps</h1>
          <p className="max-w-3xl text-sm text-slate-500">
            Unabhängig von den 3 Tipps pro Spiel: Auswahlen, bei denen unsere Wahrscheinlichkeit × Betano-Quote klar über 1 liegt. Weil Pinnacle ohne Marge
            genauer ist als unser Modell allein, wird gemischt{s && ` (${pct(s.model_weight, 0)} Modell, Rest Pinnacle)`}. Mit „+“ kommen Tipps auf den Wettschein –
            zusammen mit Tipps von der Tipps-Seite.
          </p>
        </div>
        {meta && meta.leagues.length > 1 && (
          <Segmented options={[{ key: "", label: "Alle Ligen" }, ...meta.leagues.map((l) => ({ key: String(l.id), label: l.name }))]} value={league} onChange={setLeague} />
        )}
      </div>
      <p className="rounded-lg bg-amber-50 px-3 py-2 text-sm text-amber-800">
        Noch kein Nachweis: Im Backtest sind es wenige Tipps, die Rendite schwankt stark (siehe Auswertung unten). Die Tipps werden täglich fixiert, damit
        eine ehrliche Live-Bilanz entsteht.
      </p>
      {error && <p className="rounded-md bg-rose-50 p-3 text-sm text-rose-700">{error}</p>}

      {day && (
        <div className="sticky top-[57px] z-10 -mx-4 flex flex-wrap items-center justify-between gap-2 border-b border-slate-200 bg-background/95 px-4 py-2 backdrop-blur">
          <div className="flex items-center gap-1 text-sm">
            <button type="button" disabled={!prev} onClick={() => prev && setDay(prev)} className="rounded-md border border-slate-300 bg-white px-2 py-1 disabled:opacity-30" aria-label="voriger Spieltag">‹</button>
            <span className="min-w-56 text-center font-semibold capitalize">{dateLong(`${day}T12:00:00Z`)}</span>
            <button type="button" disabled={!next} onClick={() => next && setDay(next)} className="rounded-md border border-slate-300 bg-white px-2 py-1 disabled:opacity-30" aria-label="nächster Spieltag">›</button>
          </div>
          {data && <span className="text-xs text-slate-500">{data.fixtures.reduce((n, f) => n + f.tips.length, 0)} Value-Tipps in {data.fixtures.length} von {data.fixtures_checked} Spielen</span>}
        </div>
      )}

      <section className="space-y-3">
        {data === null ? (
          <Card><p className="text-sm text-slate-400">Value-Tipps werden berechnet …</p></Card>
        ) : data.fixtures.length === 0 ? (
          <Card><p className="text-sm text-slate-500">An diesem Tag gibt es keine Value-Tipps{data.fixtures_checked ? ` (${data.fixtures_checked} Spiele geprüft)` : ""}. Ohne Betano- und Pinnacle-Preise wird kein Spiel bewertet.</p></Card>
        ) : (
          <div className="grid gap-4 md:grid-cols-2">{data.fixtures.map((f) => <ValueCard key={f.fixture.id} item={f} />)}</div>
        )}
      </section>

      <section className="space-y-3">
        <h2 className="text-lg font-semibold">Auswertung</h2>
        {stats ? <ValueStatsView stats={stats} /> : <Card><p className="text-sm text-slate-400">Backtest wird berechnet …</p></Card>}
      </section>
    </div>
  );
}

function ValueCard({ item }: { item: ValueDay["fixtures"][number] }) {
  const f = item.fixture;
  const src = SOURCE[item.source];
  const cup = !!f.cup || f.league?.type === "cup";
  return (
    <Card>
      <Link href={`/spiel/${f.id}`} className="mb-3 flex items-center justify-between gap-2 hover:opacity-80">
        <div className="min-w-0 space-y-1">
          <div className="flex items-center gap-2 text-sm font-medium"><TeamLogo team={f.home} size={18} /><span className="truncate">{f.home.name}</span></div>
          <div className="flex items-center gap-2 text-sm font-medium"><TeamLogo team={f.away} size={18} /><span className="truncate">{f.away.name}</span></div>
        </div>
        <div className="flex shrink-0 flex-col items-end gap-1 text-right text-xs text-slate-500">
          <span className="flex items-center gap-1.5">
            {cup && <CompetitionBadge cup international={!!f.cup} />}
            <Logo src={f.league?.logo ?? leagueLogo(f.league_id)} alt={f.league?.name ?? "Liga"} size={16} />
          </span>
          {f.finished ? <span className="text-lg font-semibold tabular-nums text-slate-900">{f.score.ft[0]}:{f.score.ft[1]}</span> : <span>{weekday(f.kickoff.slice(0, 10))} {dateShort(f.kickoff)} · {time(f.kickoff)}</span>}
          <span className={`rounded px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide ${src.tone}`} title={src.title}>{src.label}</span>
        </div>
      </Link>
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-[11px] text-slate-400">
            <th className="pb-1 font-medium">Tipp</th>
            <th className="pb-1 text-right font-medium" title="Unser Modell / Pinnacle ohne Marge">Modell / Markt</th>
            <th className="pb-1 text-right font-medium" title="Gemischte Wahrscheinlichkeit und faire Quote">Fair</th>
            <th className="pb-1 text-right font-medium">Betano</th>
            <th className="pb-1 text-right font-medium" title="Wahrscheinlichkeit × Betano-Quote − 1">Vorteil</th>
            <th className="pb-1" />
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {item.tips.map((t) => (
            <tr key={`${t.market}${t.selection}${t.line}`}>
              <td className="py-1.5 pr-2">
                <div className="font-medium">{t.label}</div>
                {t.group_label && <div className="text-[11px] text-slate-400">{t.group_label}</div>}
              </td>
              <td className="whitespace-nowrap py-1.5 text-right tabular-nums text-slate-500">{pct(t.p_model, 0)} / {pct(t.p_market, 0)}</td>
              <td className="whitespace-nowrap py-1.5 text-right tabular-nums text-slate-500" title={`Wahrscheinlichkeit ${pct(t.probability)}`}>{odd(t.fair_odd)}</td>
              <td className="py-1.5 text-right"><span className="rounded bg-emerald-100 px-1 text-xs font-semibold tabular-nums text-emerald-800">{odd(t.odds)}</span></td>
              <td className="whitespace-nowrap py-1.5 text-right font-semibold tabular-nums text-emerald-700">{signedPct(t.edge)}</td>
              <td className="py-1.5 pl-2 text-right">
                {f.finished ? (
                  <OutcomeBadge outcome={t.outcome} small />
                ) : (
                  <AddToSlip leg={{ fixture_id: f.id, market: t.market, selection: t.selection, line: t.line, label: t.label,
                    match: `${f.home.name} – ${f.away.name}`, kickoff: f.kickoff, probability: t.probability, odds: t.odds, origin: "value" }} />
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </Card>
  );
}

function ResultRow({ label, r }: { label: string; r: ValueResult | undefined }) {
  if (!r || !r.n) {
    return <tr><td className="py-1.5">{label}</td><td className="py-1.5 text-right tabular-nums text-slate-400" colSpan={6}>noch keine abgerechneten Tipps</td></tr>;
  }
  return (
    <tr>
      <td className="py-1.5">{label}</td>
      <td className="py-1.5 text-right tabular-nums">{r.n}</td>
      <td className="py-1.5 text-right tabular-nums">{odd(r.odds)}</td>
      <td className="py-1.5 text-right tabular-nums">{pct(r.hit_rate ?? null)} <span className="text-slate-400">/ {pct(r.expected ?? null)}</span></td>
      <td className={`whitespace-nowrap py-1.5 text-right font-semibold tabular-nums ${(r.roi ?? 0) > 0 ? "text-emerald-700" : "text-rose-700"}`}>
        {signedPct(r.roi ?? null)}
        {r.roi_ci && <span className="ml-1 text-xs font-normal text-slate-400">[{signedPct(r.roi_ci[0])}; {signedPct(r.roi_ci[1])}]</span>}
      </td>
      <td className={`py-1.5 text-right tabular-nums ${(r.clv ?? 0) > 0 ? "text-emerald-700" : "text-rose-700"}`}>{signedPct(r.clv ?? null)}</td>
      <td className="py-1.5 text-right tabular-nums text-slate-500">{pct(r.beat_close ?? null, 0)}</td>
    </tr>
  );
}

function ValueStatsView({ stats }: { stats: ValueStats }) {
  const b = stats.backtest;
  if (!b.candidates) return <Card><p className="text-sm text-slate-500">Noch keine Spiele mit Betano-Verlauf für einen Backtest.</p></Card>;
  const r = b.result;
  return (
    <div className="space-y-4">
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatTile label="Backtest: Value-Tipps" value={`${r?.n ?? 0}`} hint={`${b.fixtures} Spiele mit Betano-Verlauf · ${b.from ? dateShort(b.from) : ""} – ${b.to ? dateShort(b.to) : ""}`} />
        <StatTile label="Rendite zur Quote" value={<span className={(r?.roi ?? 0) > 0 ? "text-emerald-700" : "text-rose-700"}>{signedPct(r?.roi ?? null)}</span>} hint={r?.roi_ci ? `95 %: ${signedPct(r.roi_ci[0])} bis ${signedPct(r.roi_ci[1])}` : undefined} />
        <StatTile label="CLV" value={<span className={(r?.clv ?? 0) > 0 ? "text-emerald-700" : "text-rose-700"}>{signedPct(r?.clv ?? null)}</span>} hint={`Quote fiel danach bei ${pct(r?.beat_close ?? null, 0)}`} />
        <StatTile label="Live (fixiert)" value={`${stats.live.n} Tipps`} hint={stats.live.n ? `Rendite ${signedPct(stats.live.roi ?? null)} · Treffer ${pct(stats.live.hit_rate ?? null, 0)}` : "Bilanz entsteht ab jetzt"} />
      </div>
      <Card title="Ergebnis">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-xs text-slate-400">
                <th className="pb-2 font-medium" />
                <th className="pb-2 text-right font-medium">Tipps</th>
                <th className="pb-2 text-right font-medium">Ø Quote</th>
                <th className="pb-2 text-right font-medium">Treffer / erwartet</th>
                <th className="pb-2 text-right font-medium">Rendite [95 %]</th>
                <th className="pb-2 text-right font-medium" title="Quote beim Tipp × Pinnacle-Wahrscheinlichkeit beim Anpfiff − 1">CLV</th>
                <th className="pb-2 text-right font-medium">Quote fiel</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              <ResultRow label="Backtest (aktuelle Einstellungen)" r={r} />
              <ResultRow label="Live (fixierte Value-Tipps)" r={stats.live} />
              {(b.groups ?? []).map((g) => <ResultRow key={g.group} label={`· ${g.label}`} r={g} />)}
            </tbody>
          </table>
        </div>
        {b.log_loss && (
          <p className="mt-3 text-xs text-slate-500">
            Genauigkeit auf diesen Spielen (Log-Loss, kleiner = besser): Pinnacle {b.log_loss.market.toFixed(4).replace(".", ",")}, unser Modell {b.log_loss.model.toFixed(4).replace(".", ",")},
            Mischung {b.log_loss.blend.toFixed(4).replace(".", ",")}. Ein Rendite-Intervall, das 0 einschließt, ist kein Nachweis; ein CLV über 0 spricht für echten Vorteil.
            Einstellungen: Einstellungen → Value-Tipps · Bericht: docs/25_value_tipps.md.
          </p>
        )}
      </Card>
    </div>
  );
}

"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { api, getDays, getMeta } from "@/lib/api";
import { addDays, berlinToday, dateLong, dateShort, pct, seasonLabel, time, weekday } from "@/lib/format";
import type { ComboRate, Day, Fixture, Meta, PickRate, PickStats } from "@/lib/types";
import { Card, Select, StatTile, TeamLogo } from "@/components/ui";
import { Segmented } from "@/components/match/Segmented";
import { PickList, comboOutcome } from "@/components/picks/PickList";
import { Logo } from "@/components/Logo";
import { leagueLogo } from "@/lib/media";
import { DayCombos } from "@/components/bets/DayCombos";
import { BetDialog, type BetDraft } from "@/components/bets/BetDialog";
import { ClvView } from "@/components/picks/ClvView";
import { CompetitionBadge } from "@/components/CompetitionBadge";
import { DecisionSheet } from "@/components/decisions/DecisionSheet";
import { DecisionStatsView } from "@/components/decisions/DecisionStatsView";

export default function TipsPage() {
  const [meta, setMeta] = useState<Meta | null>(null);
  const [profile, setProfile] = useState("ausgewogen");
  const [season, setSeason] = useState("");
  const [league, setLeague] = useState("");
  const [days, setDays] = useState<Day[]>([]);
  const [day, setDay] = useState<string | null>(null);
  const [fixtures, setFixtures] = useState<Fixture[] | null>(null);
  const [stats, setStats] = useState<PickStats | null>(null);
  const [mode, setMode] = useState<"tipps" | "schein">("tipps");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getMeta()
      .then((m) => { setMeta(m); setProfile(m.pick_profiles.find((p) => p.default)?.key ?? "ausgewogen"); })
      .catch((e) => setError(String(e)));
  }, []);

  // days with fixtures around today; default: today or the next day with fixtures
  useEffect(() => {
    const today = berlinToday();
    getDays(addDays(today, -60), addDays(today, 60), league || undefined)
      .then((list) => {
        setDays(list);
        setDay((cur) => cur ?? list.find((d) => d.date >= today)?.date ?? list.at(-1)?.date ?? today);
      })
      .catch((e) => setError(String(e)));
  }, [league]);

  // only the fixtures (with picks) of the selected day
  useEffect(() => {
    if (!day) return;
    let current = true;
    setFixtures(null);
    api<Fixture[]>("/fixtures", { date: day, profile, league: league || undefined })
      .then((list) => current && setFixtures(list))
      .catch((e) => current && setError(String(e)));
    return () => { current = false; };
  }, [day, profile, league]);

  useEffect(() => {
    api<PickStats>("/stats/picks", { profile, season: season || undefined, league: league || undefined }).then(setStats).catch((e) => setError(String(e)));
  }, [profile, season, league]);

  const profiles = meta?.pick_profiles ?? [];
  const current = profiles.find((p) => p.key === profile);
  const idx = days.findIndex((d) => d.date === day);
  const prev = idx > 0 ? days[idx - 1].date : days.filter((d) => day && d.date < day).at(-1)?.date;
  const next = idx >= 0 ? days[idx + 1]?.date : days.find((d) => day && d.date > day)?.date;
  const finished = (fixtures ?? []).filter((f) => f.finished && (f.picks?.length ?? 0) === 3);
  const hits = finished.filter((f) => comboOutcome(f.picks ?? []) === true).length;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Tipps</h1>
          <p className="max-w-3xl text-sm text-slate-500">
            Pro Spiel drei Tipps aus den stärksten Modell-Prognosen, gestreut über Spielausgang, Tore, Team-Tore und Halbzeiten
            (je Gruppe höchstens einer). Bevorzugt werden Tipps, bei denen das Modell deutlich vom Ligaschnitt abweicht.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {meta && meta.leagues.length > 1 && (
            <Segmented options={[{ key: "", label: "Alle Ligen" }, ...meta.leagues.map((l) => ({ key: String(l.id), label: l.name }))]} value={league} onChange={setLeague} />
          )}
          {profiles.length > 0 && <Segmented options={profiles.map((p) => ({ key: p.key, label: p.label }))} value={profile} onChange={setProfile} />}
        </div>
      </div>
      {current && <p className="-mt-3 text-xs text-slate-400">Profil {current.label}: Tipps mit {pct(current.min_p, 0)} – {pct(current.max_p, 0)} Wahrscheinlichkeit.</p>}

      {error && <p className="rounded-md bg-rose-50 p-3 text-sm text-rose-700">{error}</p>}

      {day && (
        <div className="sticky top-[57px] z-10 -mx-4 flex flex-wrap items-center justify-between gap-2 border-b border-slate-200 bg-background/95 px-4 py-2 backdrop-blur">
          <div className="flex items-center gap-1 text-sm">
            <button type="button" disabled={!prev} onClick={() => prev && setDay(prev)} className="rounded-md border border-slate-300 bg-white px-2 py-1 disabled:opacity-30" aria-label="voriger Spieltag">‹</button>
            <span className="min-w-56 text-center font-semibold capitalize">{dateLong(`${day}T12:00:00Z`)}</span>
            <button type="button" disabled={!next} onClick={() => next && setDay(next)} className="rounded-md border border-slate-300 bg-white px-2 py-1 disabled:opacity-30" aria-label="nächster Spieltag">›</button>
          </div>
          <div className="flex items-center gap-3 text-xs text-slate-500">
            {fixtures && <span>{fixtures.length} {fixtures.length === 1 ? "Spiel" : "Spiele"}{finished.length > 0 && ` · Kombi aus 3 Tipps ${hits} von ${finished.length} getroffen`}</span>}
            {day !== (days.find((d) => d.date >= berlinToday())?.date ?? berlinToday()) && (
              <button type="button" onClick={() => setDay(days.find((d) => d.date >= berlinToday())?.date ?? berlinToday())} className="text-emerald-700 hover:underline">
                nächster Spieltag ab heute
              </button>
            )}
          </div>
        </div>
      )}

      {day && <DayCombos day={day} />}

      <section className="space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h2 className="text-lg font-semibold">{mode === "tipps" ? "Tipps pro Spiel" : "Tippschein: 6 Entscheidungen pro Spiel"}</h2>
          <Segmented options={[{ key: "tipps", label: "3 Tipps" }, { key: "schein", label: "Tippschein" }]} value={mode} onChange={(v) => setMode(v as "tipps" | "schein")} />
        </div>
        {mode === "schein" && (
          <p className="-mt-1 max-w-3xl text-sm text-slate-500">
            Sieger, Über 1,5 Tore, Über 2,5 Tore, Beide treffen, Tor in der 1. und in der 2. Halbzeit – jeweils die wahrscheinlichere Seite laut
            Entscheidungsmodell (Tor-Modell plus Form, Spielstil, Termine, Ausfälle und Historie). Die Konfidenz (0–100) zeigt, wie sicher die
            Entscheidung im Vergleich zu früheren Spielen ist; unter der Mindest-Konfidenz (Einstellungen) steht „kein Tipp“.
          </p>
        )}
        {fixtures === null ? (
          <Card><p className="text-sm text-slate-400">Tipps werden geladen …</p></Card>
        ) : fixtures.length === 0 ? (
          <Card><p className="text-sm text-slate-500">An diesem Tag gibt es keine Spiele mit Prognose.</p></Card>
        ) : (
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {fixtures.map((f) => (mode === "tipps" ? <FixturePicks key={f.id} f={f} /> : <FixtureSheet key={f.id} f={f} />))}
          </div>
        )}
      </section>

      {mode === "schein" && (
        <section className="space-y-3">
          <h2 className="text-lg font-semibold">Tippschein-Auswertung (rückwirkend, nur Daten vor dem Spieltag)</h2>
          <DecisionStatsView league={league} />
        </section>
      )}

      {mode === "tipps" && <section className="space-y-3">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <h2 className="text-lg font-semibold">Trefferquote (rückwirkend, nur Daten vor dem Spieltag)</h2>
          <Select label="Saison" value={season} onChange={setSeason}>
            <option value="">alle</option>
            {meta?.seasons.filter((s) => s >= 2016).map((s) => <option key={s} value={s}>{seasonLabel(s)}</option>)}
          </Select>
        </div>
        {stats && <StatsView stats={stats} />}
      </section>}

      <section className="space-y-3">
        <div>
          <h2 className="text-lg font-semibold">Closing Line Value (Quote beim Tipp gegen den fairen Schlusspreis)</h2>
          <p className="max-w-3xl text-sm text-slate-500">
            Sinkt die Betano-Quote nach dem Tipp, hatte das Modell Informationen, die der Markt erst später einpreist – der
            verlässlichste Hinweis auf einen echten Vorteil, lange bevor Gewinn und Verlust aussagekräftig sind.
          </p>
        </div>
        <ClvView />
      </section>
    </div>
  );
}

/** Bookmaker odds of a pick: Betano if known, else fair odds minus a typical margin of 5 %. */
const MARGIN = 0.05;
const legOdds = (p: { betano?: number | null; probability: number }) => p.betano ?? (1 / p.probability) * (1 - MARGIN);

function picksDraft(f: Fixture): BetDraft {
  const picks = f.picks ?? [];
  return {
    label: `${f.home.name} – ${f.away.name}: 3 Tipps`,
    source: "tipps",
    // same-game combo: estimated Bet Builder odds and joint model chance (the picks are correlated)
    odds: f.pick_combo?.builder_odds ?? picks.reduce((o, p) => o * legOdds(p), 1) / (f.pick_combo?.factor ?? 1),
    realOdds: false,
    probability: f.pick_combo?.probability ?? null,
    legs: picks.map((p) => ({ fixture_id: f.id, market: p.market, selection: p.selection, line: p.line, label: p.label, probability: p.probability, odds: Math.round(legOdds(p) * 100) / 100 })),
  };
}

function FixtureHeader({ f }: { f: Fixture }) {
  return (
    <Link href={`/spiel/${f.id}`} className="mb-3 flex items-center justify-between gap-2 hover:opacity-80">
      <div className="min-w-0 space-y-1">
        <div className="flex items-center gap-2 text-sm font-medium"><TeamLogo team={f.home} size={18} /><span className="truncate">{f.home.name}</span></div>
        <div className="flex items-center gap-2 text-sm font-medium"><TeamLogo team={f.away} size={18} /><span className="truncate">{f.away.name}</span></div>
      </div>
      <div className="flex shrink-0 flex-col items-end text-right text-xs text-slate-500">
        <span className="mb-1 flex items-center gap-1.5">
          {(f.cup || f.league?.type === "cup") && <CompetitionBadge cup international={!!f.cup} />}
          <Logo src={f.league?.logo ?? leagueLogo(f.league_id)} alt={f.league?.name ?? "Liga"} size={16} />
        </span>
        {f.finished ? <span className="text-lg font-semibold tabular-nums text-slate-900">{f.score.ft[0]}:{f.score.ft[1]}</span> : <span>{weekday(f.kickoff.slice(0, 10))} {dateShort(f.kickoff)}</span>}
        <div>{f.finished ? dateShort(f.kickoff) : `${time(f.kickoff)} Uhr`}</div>
      </div>
    </Link>
  );
}

function FixtureSheet({ f }: { f: Fixture }) {
  return (
    <Card>
      <FixtureHeader f={f} />
      <DecisionSheet decisions={f.prediction?.decisions ?? []} home={f.home} away={f.away} finished={f.finished} />
    </Card>
  );
}

function FixturePicks({ f }: { f: Fixture }) {
  const [draft, setDraft] = useState<BetDraft | null>(null);
  return (
    <Card>
      <FixtureHeader f={f} />
      <PickList picks={f.picks ?? []} combo={f.pick_combo} finished={f.finished} reasons={false} />
      {!f.finished && (f.picks?.length ?? 0) > 0 && (
        <button type="button" onClick={() => setDraft(picksDraft(f))} className="mt-3 text-xs text-emerald-700 hover:underline">Als Kombi-Wette erfassen</button>
      )}
      {draft && <BetDialog draft={draft} onClose={() => setDraft(null)} />}
    </Card>
  );
}

const rate = (r: { hit_rate?: number | null }) => pct(r.hit_rate ?? null);

function StatsView({ stats }: { stats: PickStats }) {
  const d = stats.detail;
  const dist = d.hits_distribution;
  return (
    <div className="space-y-4">
      <div className="grid gap-4 md:grid-cols-3">
        {stats.profiles.map((p) => (
          <ProfileTile key={p.profile} label={p.label} singles={p.singles} combo={p.combo} active={p.profile === stats.profile} />
        ))}
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card title="Wie viele der drei Tipps treffen?">
          <div className="flex h-8 overflow-hidden rounded-lg text-xs font-medium text-white">
            {["0", "1", "2", "3"].map((k, i) => (
              <div key={k} className={["bg-rose-500", "bg-orange-400", "bg-sky-500", "bg-emerald-600"][i]} style={{ width: `${(dist[k] ?? 0) * 100}%` }} title={`${k} von 3: ${pct(dist[k] ?? null)}`}>
                {(dist[k] ?? 0) > 0.07 && <span className="grid h-full place-items-center">{pct(dist[k] ?? null, 0)}</span>}
              </div>
            ))}
          </div>
          <div className="mt-2 flex justify-between text-xs text-slate-500"><span>0 von 3</span><span>1</span><span>2</span><span>3 von 3 = Kombi</span></div>
          <p className="mt-3 text-xs text-slate-500">
            Die Kombi trifft öfter als das Produkt der Einzelwahrscheinlichkeiten ({pct(d.combo.expected_naive ?? null, 0)}), weil die Tipps eines Spiels zusammenhängen.
            Die Kombi-Chance je Spiel rechnet diesen Zusammenhang deshalb aus dem Modell ein (im Backtest kalibriert). Buchmacher preisen ihn im Bet Builder
            ebenfalls ein – die Bet-Builder-Quote liegt darum unter dem Produkt der Einzelquoten.
          </p>
        </Card>
        <Card title="Nach Tipp-Rang und Pattern-Begründung">
          <table className="w-full text-sm">
            <thead><tr className="text-left text-xs text-slate-400"><th className="pb-2 font-medium" /><th className="pb-2 text-right font-medium">Tipps</th><th className="pb-2 text-right font-medium">Getroffen</th><th className="pb-2 text-right font-medium">Erwartet</th></tr></thead>
            <tbody className="divide-y divide-slate-100">
              {d.per_rank.map((r) => <RateRow key={r.rank} label={`Tipp ${r.rank}${r.rank === 1 ? " (stärkster)" : ""}`} r={r} />)}
              <RateRow label="mit Pattern-Begründung" r={d.reasons.with} />
              <RateRow label="ohne Pattern-Begründung" r={d.reasons.without} />
            </tbody>
          </table>
        </Card>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card title="Saison für Saison">
          <table className="w-full text-sm">
            <thead><tr className="text-left text-xs text-slate-400"><th className="pb-2 font-medium">Saison</th><th className="pb-2 text-right font-medium">Tipps</th><th className="pb-2 text-right font-medium">Einzeln</th><th className="pb-2 text-right font-medium">Kombi</th><th className="pb-2 text-right font-medium">Kombi rechnerisch</th></tr></thead>
            <tbody className="divide-y divide-slate-100">
              {d.per_season.map((s) => (
                <tr key={s.season}>
                  <td className="py-1.5">{seasonLabel(s.season)}</td>
                  <td className="py-1.5 text-right tabular-nums">{s.n}</td>
                  <td className="py-1.5 text-right font-semibold tabular-nums">{rate(s)}</td>
                  <td className="py-1.5 text-right font-semibold tabular-nums">{rate(s.combo)}</td>
                  <td className="py-1.5 text-right tabular-nums text-slate-500">{pct(s.combo.expected_naive ?? null)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
        <Card title="Häufigste Tipps">
          <table className="w-full text-sm">
            <thead><tr className="text-left text-xs text-slate-400"><th className="pb-2 font-medium">Tipp</th><th className="pb-2 text-right font-medium">Anzahl</th><th className="pb-2 text-right font-medium">Getroffen</th><th className="pb-2 text-right font-medium">Erwartet</th></tr></thead>
            <tbody className="divide-y divide-slate-100">
              {d.per_market.slice(0, 12).map((m) => <RateRow key={`${m.market}${m.selection}${m.line}`} label={m.label} r={m} />)}
            </tbody>
          </table>
        </Card>
      </div>
    </div>
  );
}

function ProfileTile({ label, singles, combo, active }: { label: string; singles: PickRate; combo: ComboRate; active: boolean }) {
  return (
    <div className={active ? "rounded-xl ring-2 ring-emerald-500" : ""}>
      <StatTile
        label={`${label} · Einzeltipp / Kombi`}
        value={<span>{rate(singles)} <span className="text-slate-300">/</span> {rate(combo)}</span>}
        hint={`erwartet ${pct(singles.expected)} je Tipp · Kombi rechnerisch ${pct(combo.expected_naive ?? null)} · ${combo.n.toLocaleString("de-DE")} Spiele`}
      />
    </div>
  );
}

function RateRow({ label, r }: { label: string; r: PickRate }) {
  return (
    <tr>
      <td className="py-1.5">{label}</td>
      <td className="py-1.5 text-right tabular-nums">{r.n.toLocaleString("de-DE")}</td>
      <td className="py-1.5 text-right font-semibold tabular-nums">{rate(r)}</td>
      <td className="py-1.5 text-right tabular-nums text-slate-500">{pct(r.expected)}</td>
    </tr>
  );
}


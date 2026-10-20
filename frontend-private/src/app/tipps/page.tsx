"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { api, getMeta } from "@/lib/api";
import { addDays, berlinToday, dateShort, pct, seasonLabel, time, weekday } from "@/lib/format";
import type { ComboRate, Fixture, Meta, PickRate, PickStats } from "@/lib/types";
import { Card, Select, StatTile, TeamLogo } from "@/components/ui";
import { Segmented } from "@/components/match/Segmented";
import { PickList, comboOutcome } from "@/components/picks/PickList";
import { Logo } from "@/components/Logo";
import { leagueLogo } from "@/lib/media";
import { DayCombos } from "@/components/bets/DayCombos";
import { BetDialog, type BetDraft } from "@/components/bets/BetDialog";

export default function TipsPage() {
  const [meta, setMeta] = useState<Meta | null>(null);
  const [profile, setProfile] = useState("ausgewogen");
  const [season, setSeason] = useState("");
  const [league, setLeague] = useState("");
  const [upcoming, setUpcoming] = useState<Fixture[]>([]);
  const [recent, setRecent] = useState<Fixture[]>([]);
  const [stats, setStats] = useState<PickStats | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getMeta()
      .then((m) => { setMeta(m); setProfile(m.pick_profiles.find((p) => p.default)?.key ?? "ausgewogen"); })
      .catch((e) => setError(String(e)));
  }, []);

  useEffect(() => {
    const today = berlinToday();
    Promise.all([
      api<Fixture[]>("/fixtures", { from: today, to: addDays(today, 10), profile, league: league || undefined }),
      api<Fixture[]>("/fixtures", { from: addDays(today, -10), to: addDays(today, -1), profile, league: league || undefined }),
    ])
      .then(([u, r]) => { setUpcoming(u.filter((f) => !f.finished)); setRecent(r.filter((f) => f.finished).reverse()); })
      .catch((e) => setError(String(e)));
  }, [profile, league]);

  useEffect(() => {
    api<PickStats>("/stats/picks", { profile, season: season || undefined, league: league || undefined }).then(setStats).catch((e) => setError(String(e)));
  }, [profile, season, league]);

  const profiles = meta?.pick_profiles ?? [];
  const current = profiles.find((p) => p.key === profile);
  const recentCombos = recent.filter((f) => (f.picks?.length ?? 0) === 3);
  const recentHits = recentCombos.filter((f) => comboOutcome(f.picks ?? []) === true).length;

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

      <DayCombos />

      <section className="space-y-3">
        <h2 className="text-lg font-semibold">Nächste Spiele</h2>
        {upcoming.length === 0 ? (
          <Card><p className="text-sm text-slate-500">Keine Spiele mit Prognose in den nächsten 10 Tagen.</p></Card>
        ) : (
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">{upcoming.map((f) => <FixturePicks key={f.id} f={f} />)}</div>
        )}
      </section>

      {recent.length > 0 && (
        <section className="space-y-3">
          <h2 className="text-lg font-semibold">
            Zuletzt <span className="text-sm font-normal text-slate-500">· Kombi {recentHits} von {recentCombos.length} getroffen</span>
          </h2>
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">{recent.map((f) => <FixturePicks key={f.id} f={f} />)}</div>
        </section>
      )}

      <section className="space-y-3">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <h2 className="text-lg font-semibold">Trefferquote (rückwirkend, nur Daten vor dem Spieltag)</h2>
          <Select label="Saison" value={season} onChange={setSeason}>
            <option value="">alle</option>
            {meta?.seasons.filter((s) => s >= 2016).map((s) => <option key={s} value={s}>{seasonLabel(s)}</option>)}
          </Select>
        </div>
        {stats && <StatsView stats={stats} />}
      </section>
    </div>
  );
}

/** Estimated bookmaker odds of a pick: fair odds minus a typical margin of 5 %. */
const MARGIN = 0.05;

function picksDraft(f: Fixture): BetDraft {
  const picks = f.picks ?? [];
  return {
    label: `${f.home.name} – ${f.away.name}: 3 Tipps`,
    source: "tipps",
    odds: picks.reduce((o, p) => o * (1 / p.probability) * (1 - MARGIN), 1),
    probability: null,  // the picks of one fixture are correlated: the product would understate the chance
    legs: picks.map((p) => ({ fixture_id: f.id, market: p.market, selection: p.selection, line: p.line, label: p.label, probability: p.probability, odds: Math.round((1 / p.probability) * (1 - MARGIN) * 100) / 100 })),
  };
}

function FixturePicks({ f }: { f: Fixture }) {
  const [draft, setDraft] = useState<BetDraft | null>(null);
  return (
    <Card>
      <Link href={`/spiel/${f.id}`} className="mb-3 flex items-center justify-between gap-2 hover:opacity-80">
        <div className="min-w-0 space-y-1">
          <div className="flex items-center gap-2 text-sm font-medium"><TeamLogo team={f.home} size={18} /><span className="truncate">{f.home.name}</span></div>
          <div className="flex items-center gap-2 text-sm font-medium"><TeamLogo team={f.away} size={18} /><span className="truncate">{f.away.name}</span></div>
        </div>
        <div className="flex shrink-0 flex-col items-end text-right text-xs text-slate-500">
          <Logo src={f.league?.logo ?? leagueLogo(f.league_id)} alt={f.league?.name ?? "Liga"} size={16} className="mb-1" />
          {f.finished ? <span className="text-lg font-semibold tabular-nums text-slate-900">{f.score.ft[0]}:{f.score.ft[1]}</span> : <span>{weekday(f.kickoff.slice(0, 10))} {dateShort(f.kickoff)}</span>}
          <div>{f.finished ? dateShort(f.kickoff) : `${time(f.kickoff)} Uhr`}</div>
        </div>
      </Link>
      <PickList picks={f.picks ?? []} finished={f.finished} reasons={false} />
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
            Buchmacher preisen das bei Kombis innerhalb eines Spiels („Bet Builder“) ein.
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


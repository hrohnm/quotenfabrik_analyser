"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Logo } from "@/components/Logo";
import { TeamLink } from "@/components/TeamLink";
import { Card, TeamLogo } from "@/components/ui";
import { api } from "@/lib/api";
import { dateShort, num, pct, seasonLabel } from "@/lib/format";
import type { BetsSummary, PlayerAbsences, PlayerMatches, PlayerOverview } from "@/lib/types";
import { BetsCard } from "@/components/BettingReport";

const TABS = [
  { key: "uebersicht", label: "Übersicht" },
  { key: "spiele", label: "Spiele" },
  { key: "torschuetze", label: "Torschützen-Prognose" },
  { key: "ausfaelle", label: "Ausfälle" },
];

/** Tabs of the player page. */
export function PlayerTabs({ data }: { data: PlayerOverview }) {
  const [tab, setTab] = useState("uebersicht");
  const [matches, setMatches] = useState<PlayerMatches | null>(null);
  useEffect(() => {
    const hash = window.location.hash.slice(1);
    if (TABS.some((t) => t.key === hash)) setTab(hash);
  }, []);
  useEffect(() => {
    let current = true;
    setMatches(null);
    api<PlayerMatches>(`/players/${data.player.id}/matches`, { season: data.season })
      .then((m) => current && setMatches(m))
      .catch(() => current && setMatches({ season: data.season, matches: [], scoring: null, teams: {}, leagues: {} }));
    return () => { current = false; };
  }, [data.player.id, data.season]);
  const select = (key: string) => {
    setTab(key);
    window.history.replaceState(null, "", `#${key}`);
  };
  return (
    <div className="space-y-4">
      <nav className="flex gap-1 overflow-x-auto border-b border-slate-200">
        {TABS.map((t) => (
          <button
            key={t.key}
            type="button"
            onClick={() => select(t.key)}
            className={`-mb-px whitespace-nowrap border-b-2 px-3 py-2.5 text-sm transition ${tab === t.key ? "border-slate-900 font-semibold text-slate-900" : "border-transparent text-slate-500 hover:text-slate-800"}`}
          >
            {t.label}
          </button>
        ))}
      </nav>
      {tab === "uebersicht" && <Overview data={data} />}
      {tab === "spiele" && <Matches matches={matches} />}
      {tab === "torschuetze" && <Scoring data={data} matches={matches} />}
      {tab === "ausfaelle" && <Absences data={data} />}
    </div>
  );
}

// --------------------------------------------------------------------------- overview

function Overview({ data }: { data: PlayerOverview }) {
  const s = data.summary;
  const share = data.team_share;
  if (s.apps === 0) return <Card><Empty text="Keine Einsätze in dieser Saison." /></Card>;
  const tiles = [
    { label: "Startelf", value: `${s.starts} von ${s.apps}` },
    { label: "Schüsse (aufs Tor)", value: `${s.shots_total} (${s.shots_on})` },
    { label: "Schlüsselpässe", value: `${s.key_passes}` },
    { label: "Verwertung", value: s.conversion != null ? pct(s.conversion, 0) : "–", hint: "Tore pro Schuss" },
    { label: "Elfmeter", value: `${s.penalties_scored}/${(s.penalties_scored ?? 0) + (s.penalties_missed ?? 0)}`, hint: "verwandelt / geschossen" },
    { label: "Karten", value: `${s.yellow} Gelb · ${s.red} Rot` },
  ];
  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <Card title={`Saison ${seasonLabel(data.season)}`}>
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
          {tiles.map((t) => (
            <div key={t.label} className="rounded-lg bg-slate-50 p-2 text-center" title={t.hint}>
              <div className="text-[11px] uppercase tracking-wide text-slate-500">{t.label}</div>
              <div className="font-semibold tabular-nums">{t.value}</div>
            </div>
          ))}
        </div>
        {s.per90 && (
          <div className="mt-4">
            <h3 className="mb-2 text-[11px] font-semibold uppercase tracking-wide text-slate-500">Pro 90 Minuten</h3>
            <div className="grid grid-cols-4 gap-2 text-center text-sm">
              <Per90 label="Tore" v={s.per90.goals} />
              <Per90 label="Vorlagen" v={s.per90.assists} />
              <Per90 label="Schüsse" v={s.per90.shots} />
              <Per90 label="Schlüsselp." v={s.per90.key_passes} />
            </div>
          </div>
        )}
      </Card>
      <div className="space-y-4">
        {share && (
          <Card title="Anteil an der Mannschaft">
            <div className="space-y-2.5">
              <ShareBar label="Tore der Mannschaft" v={share.goals} />
              <ShareBar label="Vorlagen der Mannschaft" v={share.assists} />
              <ShareBar label="Schüsse der Mannschaft" v={share.shots} />
              <ShareBar label="Spielminuten (seiner Einsätze)" v={share.minutes} />
            </div>
            <p className="mt-2 text-xs text-slate-400">Bezogen auf die Spiele, in denen er eingesetzt wurde.</p>
          </Card>
        )}
        {data.competitions.length > 0 && (
          <Card title="Nach Wettbewerb">
            <table className="w-full text-sm tabular-nums">
              <thead>
                <tr className="text-[11px] uppercase tracking-wide text-slate-400">
                  <th className="py-1 text-left font-medium">Wettbewerb</th>
                  <th className="py-1 text-right font-medium">Sp.</th>
                  <th className="py-1 text-right font-medium">Min.</th>
                  <th className="py-1 text-right font-medium">Tore</th>
                  <th className="py-1 text-right font-medium">Vorl.</th>
                  <th className="py-1 text-right font-medium">Note</th>
                </tr>
              </thead>
              <tbody>
                {data.competitions.map((c) => {
                  const l = data.leagues[c.league_id];
                  return (
                    <tr key={c.league_id} className="border-t border-slate-50">
                      <td className="py-1.5"><Link href={`/wettbewerb/${c.league_id}?saison=${data.season}`} className="flex items-center gap-1.5 hover:underline"><Logo src={l?.logo} alt={l?.name ?? "Wettbewerb"} size={16} />{l?.name}</Link></td>
                      <td className="py-1.5 text-right">{c.apps}</td>
                      <td className="py-1.5 text-right">{c.minutes}</td>
                      <td className="py-1.5 text-right font-semibold">{c.goals}</td>
                      <td className="py-1.5 text-right">{c.assists}</td>
                      <td className="py-1.5 text-right">{c.rating ? num(c.rating, 1) : "–"}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </Card>
        )}
      </div>
      {data.career.length > 1 && (
        <Card title="Saisons in der Datenbank" className="lg:col-span-2">
          <table className="w-full text-sm tabular-nums">
            <thead>
              <tr className="text-[11px] uppercase tracking-wide text-slate-400">
                <th className="py-1 text-left font-medium">Saison</th>
                <th className="py-1 text-left font-medium">Mannschaft</th>
                <th className="py-1 text-right font-medium">Sp.</th>
                <th className="py-1 text-right font-medium">Min.</th>
                <th className="py-1 text-right font-medium">Tore</th>
                <th className="py-1 text-right font-medium">Vorl.</th>
                <th className="py-1 text-right font-medium">Note</th>
              </tr>
            </thead>
            <tbody>
              {data.career.map((c) => {
                const team = data.teams[c.team_id];
                return (
                  <tr key={c.season} className={`border-t border-slate-50 ${c.season === data.season ? "font-semibold" : ""}`}>
                    <td className="py-1.5"><Link href={`/spieler/${data.player.id}?saison=${c.season}`} className="hover:underline">{seasonLabel(c.season)}</Link></td>
                    <td className="py-1.5"><span className="flex items-center gap-1.5">{team && <TeamLogo team={team} size={16} />}<TeamLink id={c.team_id}>{team?.name ?? c.team_id}</TeamLink></span></td>
                    <td className="py-1.5 text-right">{c.apps}</td>
                    <td className="py-1.5 text-right">{c.minutes}</td>
                    <td className="py-1.5 text-right">{c.goals}</td>
                    <td className="py-1.5 text-right">{c.assists}</td>
                    <td className="py-1.5 text-right">{c.rating ? num(c.rating, 1) : "–"}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          <p className="mt-2 text-xs text-slate-400">Nur Wettbewerbe mit Spielerdaten (volle Ligen, Europapokal der letzten 2 Saisons).</p>
        </Card>
      )}
    </div>
  );
}

function Per90({ label, v }: { label: string; v: number }) {
  return (
    <div className="rounded-lg bg-slate-50 p-2">
      <div className="text-[11px] text-slate-500">{label}</div>
      <div className="font-semibold tabular-nums">{num(v, 2)}</div>
    </div>
  );
}

function ShareBar({ label, v }: { label: string; v: number | null }) {
  return (
    <div>
      <div className="mb-1 flex justify-between text-sm"><span className="text-slate-600">{label}</span><b className="tabular-nums">{v == null ? "–" : pct(v, 0)}</b></div>
      <div className="h-2 rounded-full bg-slate-100"><div className="h-2 rounded-full bg-emerald-500" style={{ width: `${Math.min(100, (v ?? 0) * 100)}%` }} /></div>
    </div>
  );
}

// --------------------------------------------------------------------------- matches

function Matches({ matches }: { matches: PlayerMatches | null }) {
  if (!matches) return <Card><Loading /></Card>;
  if (matches.matches.length === 0) return <Card><Empty text="Keine Spiele in dieser Saison." /></Card>;
  return (
    <Card title={`Spiele ${matches.matches.length}`}>
      <div className="-mx-4 overflow-x-auto">
        <table className="w-full min-w-[40rem] text-sm tabular-nums">
          <thead>
            <tr className="text-[11px] uppercase tracking-wide text-slate-400">
              <th className="px-4 py-1.5 text-left font-medium">Spiel</th>
              <th className="px-2 py-1.5 text-right font-medium">Erg.</th>
              <th className="px-2 py-1.5 text-right font-medium">Min.</th>
              <th className="px-2 py-1.5 text-right font-medium">Tore</th>
              <th className="px-2 py-1.5 text-right font-medium">Vorl.</th>
              <th className="px-2 py-1.5 text-right font-medium" title="Schüsse (aufs Tor)">Schüsse</th>
              <th className="px-2 py-1.5 text-right font-medium">Karten</th>
              <th className="px-2 py-1.5 text-right font-medium">Note</th>
              <th className="px-4 py-1.5 text-right font-medium" title="Modell vor dem Spiel: trifft">Prognose</th>
            </tr>
          </thead>
          <tbody>
            {matches.matches.map((m) => {
              const opp = matches.teams[m.opponent_id];
              const l = matches.leagues[m.league_id];
              const played = (m.minutes ?? 0) > 0;
              return (
                <tr key={m.fixture_id} className={`border-t border-slate-50 ${played ? "" : "text-slate-400"}`}>
                  <td className="px-4 py-1.5">
                    <Link href={`/spiel/${m.fixture_id}`} className="flex items-center gap-1.5 hover:underline">
                      <span className="w-14 text-xs text-slate-500">{dateShort(m.kickoff)}</span>
                      <Logo src={l?.logo} alt={l?.name ?? "Wettbewerb"} size={14} />
                      <span className="w-3 text-xs text-slate-400">{m.home ? "H" : "A"}</span>
                      {opp && <TeamLogo team={opp} size={16} />}
                      <span className="truncate">{opp?.name ?? m.opponent_id}</span>
                    </Link>
                  </td>
                  <td className="px-2 py-1.5 text-right">{m.score ? `${m.score[0]}:${m.score[1]}` : "–"}</td>
                  <td className="px-2 py-1.5 text-right">{played ? <>{m.minutes}{m.starter === false && <span className="text-xs text-slate-400"> (E)</span>}</> : "–"}</td>
                  <td className="px-2 py-1.5 text-right font-semibold">{m.goals || ""}</td>
                  <td className="px-2 py-1.5 text-right">{m.assists || ""}</td>
                  <td className="px-2 py-1.5 text-right text-slate-500">{played ? `${m.shots ?? 0} (${m.shots_on ?? 0})` : ""}</td>
                  <td className="px-2 py-1.5 text-right">
                    {(m.yellow ?? 0) > 0 && <span className="inline-block h-3 w-2 rounded-[1px] bg-yellow-400" />}
                    {(m.red ?? 0) > 0 && <span className="ml-0.5 inline-block h-3 w-2 rounded-[1px] bg-rose-600" />}
                  </td>
                  <td className="px-2 py-1.5 text-right">{m.rating ? num(m.rating, 1) : ""}</td>
                  <td className={`px-4 py-1.5 text-right ${m.p_anytime != null && (m.goals ?? 0) > 0 ? "font-semibold text-emerald-700" : ""}`}>{m.p_anytime != null ? pct(m.p_anytime, 0) : ""}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <p className="mt-2 text-xs text-slate-400">(E) eingewechselt. Prognose: Modell-Wahrscheinlichkeit „trifft“ vor dem Spiel, grün wenn er getroffen hat.</p>
    </Card>
  );
}

// --------------------------------------------------------------------------- scoring forecast

function Scoring({ data, matches }: { data: PlayerOverview; matches: PlayerMatches | null }) {
  if (!matches) return <Card><Loading /></Card>;
  const sc = matches.scoring;
  return (
    <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_minmax(0,2fr)]">
      <div className="space-y-4">
        {data.next && data.next.p_anytime != null && (
          <Card title="Nächstes Spiel">
            <div className="grid grid-cols-2 gap-2 text-center">
              <div className="rounded-lg bg-emerald-50 p-3"><div className="text-[11px] uppercase tracking-wide text-emerald-700">Trifft</div><div className="text-2xl font-semibold tabular-nums">{pct(data.next.p_anytime, 0)}</div></div>
              <div className="rounded-lg bg-slate-50 p-3"><div className="text-[11px] uppercase tracking-wide text-slate-500">Erstes Tor</div><div className="text-2xl font-semibold tabular-nums">{data.next.p_first != null ? pct(data.next.p_first, 0) : "–"}</div></div>
            </div>
          </Card>
        )}
        <Card title="Prognose gegen Ergebnis">
          {!sc ? <Empty text="Keine Torschützen-Prognosen für diese Saison." /> : (
            <>
              <p className="text-sm text-slate-600">
                In <b>{sc.matches}</b> Einsätzen mit Prognose erwartete das Modell <b>{num(sc.expected, 1)}</b> Spiele mit Tor – getroffen hat er in <b>{sc.actual}</b>.
              </p>
              <p className={`mt-2 text-sm font-semibold ${sc.actual >= sc.expected ? "text-emerald-700" : "text-rose-700"}`}>
                {sc.actual >= sc.expected ? "Über" : "Unter"} der Erwartung ({sc.actual - sc.expected >= 0 ? "+" : "−"}{num(Math.abs(sc.actual - sc.expected), 1)})
              </p>
              <p className="mt-2 text-xs text-slate-400">Rückblick auf die Prognosen vor jedem Spiel (Einsätze mit Spielminuten). Wenige Spiele schwanken stark – kein Wettsignal.</p>
            </>
          )}
        </Card>
        <Card title="Elfmeter">
          <p className="text-sm text-slate-600">{data.penalties.scored} verwandelt, {data.penalties.missed} verschossen (alle Spiele in der Datenbank){data.penalties.taker ? " · hat in den letzten 12 Monaten Elfmeter geschossen." : "."}</p>
        </Card>
        <PlayerBets playerId={data.player.id} />
      </div>
      {sc && sc.series.length > 1 && (
        <Card title="Spiele mit Tor: erwartet und tatsächlich (kumuliert)">
          <ScoringChart series={sc.series} />
          <p className="mt-2 flex gap-3 text-xs text-slate-500">
            <span className="flex items-center gap-1"><span className="h-0.5 w-4 bg-emerald-600" />tatsächlich</span>
            <span className="flex items-center gap-1"><span className="h-0.5 w-4 border-t-2 border-dashed border-slate-400" />Erwartung des Modells</span>
          </p>
        </Card>
      )}
    </div>
  );
}

function ScoringChart({ series }: { series: { expected: number; actual: number }[] }) {
  const W = 600, H = 240, L = 28, R = 10, T = 10, B = 20;
  const max = Math.max(1, ...series.map((p) => Math.max(p.expected, p.actual)));
  const x = (i: number) => L + (i / Math.max(1, series.length - 1)) * (W - L - R);
  const y = (v: number) => H - B - (v / max) * (H - T - B);
  const line = (key: "expected" | "actual") => series.map((p, i) => `${i ? "L" : "M"}${x(i).toFixed(1)},${y(p[key]).toFixed(1)}`).join(" ");
  const ticks = Array.from({ length: Math.min(5, Math.floor(max)) + 1 }, (_, i) => Math.round((i * max) / Math.min(5, Math.floor(max) || 1)));
  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="w-full" role="img" aria-label="Spiele mit Tor kumuliert">
      {[...new Set(ticks)].map((t) => (
        <g key={t}>
          <line x1={L} x2={W - R} y1={y(t)} y2={y(t)} stroke="#e2e8f0" />
          <text x={L - 6} y={y(t) + 3} fontSize={10} textAnchor="end" fill="#94a3b8">{t}</text>
        </g>
      ))}
      <path d={line("expected")} fill="none" stroke="#94a3b8" strokeWidth={2} strokeDasharray="5 4" />
      <path d={line("actual")} fill="none" stroke="#059669" strokeWidth={2.5} strokeLinejoin="round" />
      <text x={W - R} y={H - 4} fontSize={10} textAnchor="end" fill="#94a3b8">{series.length} Spiele</text>
    </svg>
  );
}

function PlayerBets({ playerId }: { playerId: number }) {
  const [bets, setBets] = useState<BetsSummary | null>(null);
  useEffect(() => {
    let current = true;
    api<BetsSummary>(`/players/${playerId}/bets`).then((b) => current && setBets(b)).catch(() => current && setBets(null));
    return () => { current = false; };
  }, [playerId]);
  return bets ? <BetsCard bets={bets} title="Eigene Torschützen-Wetten" /> : null;
}

// --------------------------------------------------------------------------- absences

function Absences({ data }: { data: PlayerOverview }) {
  const [a, setA] = useState<PlayerAbsences | null>(null);
  useEffect(() => {
    let current = true;
    api<PlayerAbsences>(`/players/${data.player.id}/absences`).then((x) => current && setA(x)).catch(() => current && setA(null));
    return () => { current = false; };
  }, [data.player.id]);
  if (!a) return <Card><Loading /></Card>;
  if (a.absences.length === 0) return <Card><Empty text="Keine Ausfälle gemeldet (Meldungen ab 2021)." /></Card>;
  return (
    <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_minmax(0,2fr)]">
      <Card title="Zusammenfassung">
        <div className="grid grid-cols-2 gap-2 text-center">
          <div className="rounded-lg bg-rose-50 p-2"><div className="text-[11px] uppercase tracking-wide text-rose-700">Verpasst</div><div className="text-xl font-semibold tabular-nums">{a.summary.missed}</div></div>
          <div className="rounded-lg bg-amber-50 p-2"><div className="text-[11px] uppercase tracking-wide text-amber-800">Fraglich</div><div className="text-xl font-semibold tabular-nums">{a.summary.doubtful}</div></div>
        </div>
        <ul className="mt-3 space-y-1 text-sm">
          {a.summary.reasons.map((r) => (
            <li key={r.reason} className="flex justify-between"><span className="text-slate-600">{r.reason}</span><span className="tabular-nums">{r.matches} Spiele</span></li>
          ))}
        </ul>
      </Card>
      <Card title="Gemeldete Ausfälle">
        <ul className="divide-y divide-slate-100 text-sm">
          {a.absences.map((x) => {
            const opp = a.teams[x.opponent_id];
            const l = a.leagues[x.league_id];
            return (
              <li key={x.fixture_id} className="flex items-center gap-2 py-1.5">
                <span className="w-16 text-xs tabular-nums text-slate-500">{dateShort(x.kickoff)}</span>
                <Logo src={l?.logo} alt={l?.name ?? "Wettbewerb"} size={14} />
                <Link href={`/spiel/${x.fixture_id}`} className="flex min-w-0 flex-1 items-center gap-1.5 hover:underline">
                  {opp && <TeamLogo team={opp} size={16} />}<span className="truncate">{opp?.name ?? x.opponent_id}</span>
                </Link>
                <span className={`rounded px-1.5 text-[10px] font-semibold ${x.type === "missing" ? "bg-rose-100 text-rose-700" : "bg-amber-100 text-amber-800"}`}>{x.type === "missing" ? "fehlte" : "fraglich"}</span>
                <span className="w-40 truncate text-right text-xs text-slate-500">{x.reason}</span>
              </li>
            );
          })}
        </ul>
      </Card>
    </div>
  );
}

function Loading() {
  return <p className="text-sm text-slate-400">Wird geladen …</p>;
}

function Empty({ text }: { text: string }) {
  return <p className="text-sm text-slate-500">{text}</p>;
}

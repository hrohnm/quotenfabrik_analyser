"use client";

import Link from "next/link";
import { PlayerLink } from "@/components/PlayerLink";
import { useEffect, useMemo, useState } from "react";
import { Logo } from "@/components/Logo";
import { StandingsTable } from "@/components/StandingsTable";
import { TeamLink } from "@/components/TeamLink";
import { Card, OutcomeBadge, TeamLogo } from "@/components/ui";
import { Segmented } from "@/components/match/Segmented";
import { api } from "@/lib/api";
import { dateShort, num, pct, seasonLabel, time } from "@/lib/format";
import { playerPhoto } from "@/lib/media";
import type {
  CompetitionOverview,
  CompetitionPlayers,
  CompetitionStats,
  CompetitionTables,
  ExpectedRow,
  Fixture,
  KnockoutRound,
  RankedPlayer,
  Team,
  TeamRanking,
} from "@/lib/types";

const TABS = [
  { key: "uebersicht", label: "Übersicht" },
  { key: "tabelle", label: "Tabelle" },
  { key: "statistik", label: "Statistik" },
  { key: "spieler", label: "Spieler" },
  { key: "spielplan", label: "Spielplan" },
];

/** Tabs of the competition page; every tab loads its own data. */
export function CompetitionTabs({ data }: { data: CompetitionOverview }) {
  const [tab, setTab] = useState("uebersicht");
  const [fixtures, setFixtures] = useState<Fixture[] | null>(null);
  useEffect(() => {
    const hash = window.location.hash.slice(1);
    if (TABS.some((t) => t.key === hash)) setTab(hash);
  }, []);
  useEffect(() => {
    let current = true;
    setFixtures(null);
    api<Fixture[]>("/fixtures", { league: data.league.id, season: data.season, limit: 1000 })
      .then((f) => current && setFixtures(f))
      .catch(() => current && setFixtures([]));
    return () => { current = false; };
  }, [data.league.id, data.season]);
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
      {tab === "uebersicht" && <Overview data={data} fixtures={fixtures} />}
      {tab === "tabelle" && <Tables data={data} />}
      {tab === "statistik" && <Statistics data={data} />}
      {tab === "spieler" && <Players data={data} />}
      {tab === "spielplan" && <Schedule data={data} fixtures={fixtures} />}
    </div>
  );
}

// --------------------------------------------------------------------------- overview

function groupLabel(group: string | null, cup: boolean) {
  if (!group) return cup ? "Ligaphase" : "Tabelle";
  return group.replace("Group", "Gruppe");
}

function Overview({ data, fixtures }: { data: CompetitionOverview; fixtures: Fixture[] | null }) {
  const upcoming = (fixtures ?? []).filter((f) => !f.finished && !["PST", "CANC", "ABD"].includes(f.status)).slice(0, 9);
  const recent = (fixtures ?? []).filter((f) => f.finished).slice(-9).reverse();
  return (
    <div className="grid gap-4 lg:grid-cols-[minmax(0,3fr)_minmax(0,2fr)]">
      <div className="space-y-4">
        {data.tables.length === 0 && <Card><p className="text-sm text-slate-500">Keine Tabelle in dieser Saison.</p></Card>}
        {data.tables.map((t) => (
          <Card key={t.group ?? "main"} title={groupLabel(t.group, data.league.cup)}>
            <StandingsTable rows={t.rows} teams={data.teams} />
          </Card>
        ))}
        {data.knockout.length > 0 && <Knockout rounds={data.knockout} teams={data.teams} />}
      </div>
      <div className="space-y-4">
        <Card title="Nächste Spiele">{fixtures === null ? <Loading /> : upcoming.length === 0 ? <Empty text="Keine anstehenden Spiele." /> : <FixtureList items={upcoming} />}</Card>
        <Card title="Letzte Ergebnisse">{fixtures === null ? <Loading /> : recent.length === 0 ? <Empty text="Noch keine Ergebnisse." /> : <FixtureList items={recent} />}</Card>
      </div>
    </div>
  );
}

function Knockout({ rounds, teams }: { rounds: KnockoutRound[]; teams: Record<number, Team> }) {
  return (
    <Card title="K.-o.-Runden und Qualifikation">
      <div className="space-y-4">
        {[...rounds].reverse().map((r) => (
          <div key={r.round}>
            <h3 className="mb-1.5 text-[11px] font-semibold uppercase tracking-wide text-slate-500">{r.label ?? r.round}</h3>
            <ul className="grid gap-x-6 gap-y-1 text-sm sm:grid-cols-2">
              {r.ties.map((t) => {
                const a = teams[t.team_a];
                const b = teams[t.team_b];
                const winner = t.aggregate && t.legs.every((l) => l.score) ? (t.aggregate[0] > t.aggregate[1] ? t.team_a : t.aggregate[1] > t.aggregate[0] ? t.team_b : null) : null;
                return (
                  <li key={`${t.team_a}-${t.team_b}`} className="flex items-center gap-2">
                    <span className={`flex min-w-0 flex-1 items-center gap-1.5 ${winner === t.team_a ? "font-semibold" : ""}`}>
                      {a && <TeamLogo team={a} size={16} />}<TeamLink id={t.team_a} className="truncate">{a?.name ?? t.team_a}</TeamLink>
                    </span>
                    <Link href={`/spiel/${t.legs[t.legs.length - 1].fixture_id}`} className="shrink-0 rounded bg-slate-50 px-1.5 tabular-nums hover:bg-slate-100" title={t.legs.map((l) => (l.score ? `${l.score[0]}:${l.score[1]}` : dateShort(l.kickoff))).join(" · ")}>
                      {t.aggregate ? `${t.aggregate[0]}:${t.aggregate[1]}` : "–:–"}
                    </Link>
                    <span className={`flex min-w-0 flex-1 items-center justify-end gap-1.5 text-right ${winner === t.team_b ? "font-semibold" : ""}`}>
                      <TeamLink id={t.team_b} className="truncate">{b?.name ?? t.team_b}</TeamLink>{b && <TeamLogo team={b} size={16} />}
                    </span>
                  </li>
                );
              })}
            </ul>
          </div>
        ))}
      </div>
      <p className="mt-3 text-xs text-slate-400">Gesamtergebnis nach 90 Minuten je Spiel (ohne Verlängerung und Elfmeterschießen).</p>
    </Card>
  );
}

function FixtureList({ items }: { items: Fixture[] }) {
  return (
    <ul className="divide-y divide-slate-100">
      {items.map((f) => (
        <li key={f.id}>
          <Link href={`/spiel/${f.id}`} className="grid grid-cols-[64px_1fr_auto] items-center gap-2 py-2 text-sm hover:bg-slate-50">
            <span className="text-xs tabular-nums text-slate-500">{dateShort(f.kickoff).slice(0, 6)} {f.finished ? "" : time(f.kickoff)}</span>
            <span className="min-w-0 space-y-0.5">
              <span className="flex items-center gap-1.5"><TeamLogo team={f.home} size={16} /><span className="truncate">{f.home.name}</span></span>
              <span className="flex items-center gap-1.5"><TeamLogo team={f.away} size={16} /><span className="truncate">{f.away.name}</span></span>
            </span>
            <span className="text-right tabular-nums">
              {f.finished ? (
                <span className="font-semibold">{f.score.ft[0]}:{f.score.ft[1]}</span>
              ) : f.prediction?.probabilities?.home != null ? (
                <span className="text-xs text-slate-500" title="Modell: 1 · X · 2">
                  {pct(f.prediction.probabilities.home, 0)} · {pct(f.prediction.probabilities.draw, 0)} · {pct(f.prediction.probabilities.away, 0)}
                </span>
              ) : null}
            </span>
          </Link>
        </li>
      ))}
    </ul>
  );
}

// --------------------------------------------------------------------------- tables

const SCOPES = [
  { key: "total", label: "Gesamt" },
  { key: "home", label: "Heim" },
  { key: "away", label: "Auswärts" },
  { key: "first_half", label: "1. HZ" },
  { key: "second_half", label: "2. HZ" },
  { key: "form", label: "Letzte 5" },
  { key: "expected", label: "Erwartet (Modell)" },
];
const LINE_COLORS = ["#059669", "#2563eb", "#d97706", "#db2777", "#7c3aed", "#0891b2"];

function Tables({ data }: { data: CompetitionOverview }) {
  const [group, setGroup] = useState<string | null>(null);
  const [scope, setScope] = useState("total");
  const [t, setT] = useState<CompetitionTables | null>(null);
  const [selected, setSelected] = useState<number[]>([]);
  useEffect(() => {
    let current = true;
    setT(null);
    api<CompetitionTables>(`/competitions/${data.league.id}/table`, { season: data.season, group: group ?? undefined })
      .then((x) => {
        if (!current) return;
        setT(x);
        setSelected((x.tables?.total ?? []).slice(0, 3).map((r) => r.team_id));
      })
      .catch(() => current && setT({ season: data.season, group: null, groups: [], tables: null }));
    return () => { current = false; };
  }, [data.league.id, data.season, group]);
  if (!t) return <Card><Loading /></Card>;
  if (!t.tables) return <Card><Empty text="Keine Tabelle in dieser Saison." /></Card>;
  const teams = t.teams ?? data.teams;
  const toggle = (id: number) => setSelected((s) => (s.includes(id) ? s.filter((x) => x !== id) : [...s, id].slice(-LINE_COLORS.length)));
  const highlight = Object.fromEntries(selected.map((id) => [id, "selected" as const]));
  return (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-2">
        {t.groups.length > 1 && (
          <Segmented size="sm" options={t.groups.map((g) => ({ key: g, label: groupLabel(g || null, data.league.cup) }))} value={t.group ?? ""} onChange={(g) => setGroup(g)} />
        )}
        <Segmented size="sm" options={SCOPES} value={scope} onChange={setScope} />
      </div>
      <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
        <Card title={SCOPES.find((s) => s.key === scope)?.label}>
          {scope === "expected" ? (
            <ExpectedTable rows={t.expected ?? []} teams={teams} />
          ) : (
            <StandingsTable rows={t.tables[scope as keyof NonNullable<CompetitionTables["tables"]>]} teams={teams} highlight={highlight} onToggle={toggle} />
          )}
          {scope === "form" && <p className="mt-2 text-xs text-slate-400">Nur die letzten 5 Spiele jeder Mannschaft.</p>}
          {(scope === "first_half" || scope === "second_half") && <p className="mt-2 text-xs text-slate-400">Tabelle nur aus den Toren der jeweiligen Halbzeit.</p>}
          {scope !== "expected" && <p className="mt-2 text-xs text-slate-400">Zeile anklicken: Mannschaft im Verlauf ein- oder ausblenden.</p>}
        </Card>
        {t.history && t.history.matchdays.length > 1 && (
          <Card title="Tabellenplatz nach Spieltag">
            <PositionChart history={t.history} teams={teams} selected={selected} />
            <div className="mt-3 flex flex-wrap gap-2 text-xs">
              {selected.map((id, i) => (
                <button key={id} type="button" onClick={() => toggle(id)} className="flex items-center gap-1.5 rounded-full border border-slate-200 px-2 py-0.5">
                  <span className="h-2 w-2 rounded-full" style={{ background: LINE_COLORS[i % LINE_COLORS.length] }} />
                  {teams[id]?.name ?? id} ×
                </button>
              ))}
            </div>
          </Card>
        )}
      </div>
    </div>
  );
}

function PositionChart({ history, teams, selected }: { history: NonNullable<CompetitionTables["history"]>; teams: Record<number, Team>; selected: number[] }) {
  const { matchdays, positions } = history;
  const n = Object.keys(positions).length;
  const W = 600, H = 320, L = 28, R = 10, T = 10, B = 24;
  const x = (i: number) => L + (i / Math.max(1, matchdays.length - 1)) * (W - L - R);
  const y = (rank: number) => T + ((rank - 1) / Math.max(1, n - 1)) * (H - T - B);
  const path = (ranks: (number | null)[]) =>
    ranks.map((r, i) => (r == null ? "" : `${i === 0 || ranks[i - 1] == null ? "M" : "L"}${x(i).toFixed(1)},${y(r).toFixed(1)}`)).join(" ");
  const ticks = [1, ...Array.from({ length: Math.floor((n - 1) / 3) }, (_, i) => (i + 1) * 3 + 1).filter((v) => v < n), n];
  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="w-full" role="img" aria-label="Tabellenplatz je Spieltag">
      {ticks.map((r) => (
        <g key={r}>
          <line x1={L} x2={W - R} y1={y(r)} y2={y(r)} stroke="#e2e8f0" strokeWidth={1} />
          <text x={L - 6} y={y(r) + 3} fontSize={10} textAnchor="end" fill="#94a3b8">{r}</text>
        </g>
      ))}
      {matchdays.map((d, i) => (i % Math.ceil(matchdays.length / 12) === 0 || i === matchdays.length - 1) && (
        <text key={d} x={x(i)} y={H - 6} fontSize={10} textAnchor="middle" fill="#94a3b8">{d}</text>
      ))}
      {Object.entries(positions).filter(([id]) => !selected.includes(Number(id))).map(([id, ranks]) => (
        <path key={id} d={path(ranks)} fill="none" stroke="#cbd5e1" strokeWidth={1} />
      ))}
      {selected.map((id, i) => positions[id] && (
        <g key={id}>
          <path d={path(positions[id])} fill="none" stroke={LINE_COLORS[i % LINE_COLORS.length]} strokeWidth={2.5} strokeLinejoin="round" />
          <title>{teams[id]?.name}</title>
        </g>
      ))}
    </svg>
  );
}

function ExpectedTable({ rows, teams }: { rows: ExpectedRow[]; teams: Record<number, Team> }) {
  return (
    <div className="-mx-4 overflow-x-auto">
      <table className="w-full min-w-[22rem] text-sm tabular-nums">
        <thead>
          <tr className="border-b border-slate-100 text-[11px] uppercase tracking-wide text-slate-400">
            <th className="w-8 px-2 py-1.5 text-right font-medium">#</th>
            <th className="w-full px-2 py-1.5 text-left font-medium">Team</th>
            <th className="px-2 py-1.5 text-right font-medium">Sp</th>
            <th className="px-2 py-1.5 text-right font-medium" title="erwartete Punkte laut Prognose vor jedem Spiel">xPkt</th>
            <th className="px-2 py-1.5 text-right font-medium">Pkt</th>
            <th className="px-2 py-1.5 text-right font-medium">Diff</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => {
            const team = teams[r.team_id];
            return (
              <tr key={r.team_id} className="border-b border-slate-50 last:border-0">
                <td className="px-2 py-1.5 text-right text-slate-500">{r.rank}</td>
                <td className="max-w-0 px-2 py-1.5">
                  <span className="flex min-w-0 items-center gap-2">{team && <TeamLogo team={team} size={16} />}<TeamLink id={r.team_id} className="truncate">{team?.name ?? r.team_id}</TeamLink></span>
                </td>
                <td className="px-2 py-1.5 text-right">{r.matches}</td>
                <td className="px-2 py-1.5 text-right font-semibold">{num(r.expected, 1)}</td>
                <td className="px-2 py-1.5 text-right">{r.points}</td>
                <td className={`px-2 py-1.5 text-right ${r.diff >= 1 ? "text-emerald-700" : r.diff <= -1 ? "text-rose-700" : "text-slate-500"}`}>
                  {r.diff >= 0 ? "+" : "−"}{num(Math.abs(r.diff), 1)}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
      <p className="mt-2 px-4 text-xs text-slate-400">Sortiert nach erwarteten Punkten aus der Prognose vor jedem Spiel (3 × Siegchance + Remischance). Positive Differenz: mehr Punkte geholt, als die Leistung laut Modell erwarten ließ. Rückblick, kein Wettsignal.</p>
    </div>
  );
}

// --------------------------------------------------------------------------- statistics

const RANK_COLUMNS: { key: keyof TeamRanking; label: string; digits: number; pct?: boolean; asc?: boolean }[] = [
  { key: "goals", label: "Tore", digits: 2 },
  { key: "conceded", label: "Gegentore", digits: 2, asc: true },
  { key: "shots", label: "Schüsse", digits: 1 },
  { key: "shots_on", label: "aufs Tor", digits: 1 },
  { key: "xg", label: "xG", digits: 2 },
  { key: "conversion", label: "Verwertung", digits: 0, pct: true },
  { key: "possession", label: "Ballbesitz", digits: 0 },
  { key: "shots_against", label: "Schüsse gegen", digits: 1, asc: true },
];

function Statistics({ data }: { data: CompetitionOverview }) {
  const [s, setS] = useState<CompetitionStats | null>(null);
  const [sort, setSort] = useState<keyof TeamRanking>("goals");
  useEffect(() => {
    let current = true;
    setS(null);
    api<CompetitionStats>(`/competitions/${data.league.id}/stats`, { season: data.season }).then((x) => current && setS(x)).catch(() => current && setS(null));
    return () => { current = false; };
  }, [data.league.id, data.season]);
  const ranked = useMemo(() => {
    if (!s) return [];
    const col = RANK_COLUMNS.find((c) => c.key === sort);
    return [...s.teams_ranked].sort((a, b) => ((col?.asc ? 1 : -1) * (((a[sort] as number) ?? 0) - ((b[sort] as number) ?? 0))));
  }, [s, sort]);
  if (!s) return <Card><Loading /></Card>;
  if (!s.figures) return <Card><Empty text="Noch keine beendeten Spiele." /></Card>;
  const seasons = [...s.history, { season: s.season, ...s.figures }];
  const rows: { key: keyof typeof s.figures; label: string; kind: "num" | "pct" | "int" }[] = [
    { key: "matches", label: "Spiele", kind: "int" },
    { key: "goals_per_match", label: "Tore pro Spiel", kind: "num" },
    { key: "home_win", label: "Heimsiege", kind: "pct" },
    { key: "draw", label: "Remis", kind: "pct" },
    { key: "away_win", label: "Auswärtssiege", kind: "pct" },
    { key: "over_2_5", label: "Über 2,5 Tore", kind: "pct" },
    { key: "btts", label: "Beide treffen", kind: "pct" },
    { key: "nil_nil", label: "0:0", kind: "pct" },
  ];
  const fmt = (v: number, kind: string) => (kind === "pct" ? pct(v, 0) : kind === "int" ? String(v) : num(v, 2));
  const pm = s.per_match;
  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <Card title="Ligazahlen im Vergleich">
        <table className="w-full text-sm tabular-nums">
          <thead>
            <tr className="text-[11px] uppercase tracking-wide text-slate-400">
              <th className="py-1 text-left font-medium" />
              {seasons.map((x) => <th key={x.season} className={`py-1 text-right font-medium ${x.season === s.season ? "text-slate-700" : ""}`}>{seasonLabel(x.season)}</th>)}
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.key} className="border-t border-slate-50">
                <td className="py-1.5 text-slate-600">{r.label}</td>
                {seasons.map((x) => <td key={x.season} className={`py-1.5 text-right ${x.season === s.season ? "font-semibold" : "text-slate-500"}`}>{fmt(x[r.key] as number, r.kind)}</td>)}
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
      <div className="space-y-4">
        {s.segments.length > 0 && <GoalTiming segments={s.segments} halves={s.halves} />}
        <Card title="Pro Spiel und Ereignisse">
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
            <Tile label="Gelbe Karten" value={pm.yellow != null ? num(pm.yellow, 1) : "–"} />
            <Tile label="Ecken" value={pm.corners != null ? num(pm.corners, 1) : "–"} />
            <Tile label="Fouls" value={pm.fouls != null ? num(pm.fouls, 1) : "–"} />
            <Tile label="Schüsse" value={pm.shots_total != null ? num(pm.shots_total, 1) : "–"} />
            <Tile label="Rote Karten" value={String(s.events.red_cards)} />
            <Tile label="Elfmeter verwandelt" value={String(s.events.penalties_scored)} />
            <Tile label="Elfmeter verschossen" value={String(s.events.penalties_missed)} />
            <Tile label="Eigentore" value={String(s.events.own_goals)} />
          </div>
          <p className="mt-2 text-xs text-slate-400">Pro Spiel: beide Teams zusammen. Ereignisse aus {s.events.matches} Spielen mit Ereignisdaten.</p>
        </Card>
      </div>
      {ranked.length > 0 && (
        <Card title="Teams im Vergleich (pro Spiel)" className="lg:col-span-2">
          <div className="-mx-4 overflow-x-auto">
            <table className="w-full min-w-[44rem] text-sm tabular-nums">
              <thead>
                <tr className="text-[11px] uppercase tracking-wide text-slate-400">
                  <th className="px-4 py-1.5 text-left font-medium">Team</th>
                  {RANK_COLUMNS.map((c) => (
                    <th key={c.key} className="px-2 py-1.5 text-right font-medium">
                      <button type="button" onClick={() => setSort(c.key)} className={`uppercase ${sort === c.key ? "text-slate-900" : "hover:text-slate-700"}`}>{c.label}{sort === c.key ? (c.asc ? " ↑" : " ↓") : ""}</button>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {ranked.map((r) => {
                  const team = s.teams[r.team_id];
                  return (
                    <tr key={r.team_id} className="border-t border-slate-50">
                      <td className="px-4 py-1.5"><span className="flex items-center gap-2">{team && <TeamLogo team={team} size={16} />}<TeamLink id={r.team_id} className="truncate">{team?.name ?? r.team_id}</TeamLink></span></td>
                      {RANK_COLUMNS.map((c) => {
                        const v = r[c.key] as number | null;
                        return <td key={c.key} className={`px-2 py-1.5 text-right ${sort === c.key ? "font-semibold" : ""}`}>{v == null ? "–" : c.pct ? pct(v, 0) : num(v, c.digits)}</td>;
                      })}
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
          <p className="mt-2 text-xs text-slate-400">Spaltenkopf anklicken zum Sortieren. Verwertung: Tore pro Schuss aufs Tor.</p>
        </Card>
      )}
    </div>
  );
}

function GoalTiming({ segments, halves }: { segments: CompetitionStats["segments"]; halves: CompetitionStats["halves"] }) {
  const max = Math.max(1, ...segments.map((s) => s.goals));
  return (
    <Card title="Tore nach Spielminute">
      <div className="grid grid-cols-6 items-end gap-2">
        {segments.map((s) => (
          <div key={s.label} className="flex flex-col items-center gap-1">
            <div className="flex h-24 w-full items-end justify-center">
              <div className="w-2/3 rounded-t bg-emerald-500" style={{ height: `${(s.goals / max) * 100}%` }} title={`${s.goals} Tore`} />
            </div>
            <div className="text-[11px] tabular-nums text-slate-600">{num(s.goals / Math.max(1, s.matches), 2)}</div>
            <div className="text-[10px] text-slate-400">{s.label}′</div>
          </div>
        ))}
      </div>
      <p className="mt-2 text-xs text-slate-500">
        Tore pro Spiel je Abschnitt{halves ? ` · 1. HZ ${num(halves.first, 2)}, 2. HZ ${num(halves.second, 2)} Tore pro Spiel` : ""}.
      </p>
    </Card>
  );
}

function Tile({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg bg-slate-50 p-2 text-center">
      <div className="text-[11px] uppercase tracking-wide text-slate-500">{label}</div>
      <div className="text-lg font-semibold tabular-nums">{value}</div>
    </div>
  );
}

// --------------------------------------------------------------------------- players

const PLAYER_LISTS: { key: keyof CompetitionPlayers["rankings"]; title: string; value: (p: RankedPlayer) => string; detail: (p: RankedPlayer) => string }[] = [
  { key: "goals", title: "Torjäger", value: (p) => String(p.value), detail: (p) => `${p.assists} Vorl.${p.penalties ? ` · ${p.penalties} Elfm.` : ""}` },
  { key: "assists", title: "Vorlagen", value: (p) => String(p.value), detail: (p) => `${p.goals} Tore` },
  { key: "points", title: "Scorerpunkte", value: (p) => String(p.value), detail: (p) => `${p.goals} T · ${p.assists} V` },
  { key: "goals_per_90", title: "Tore pro 90 Min.", value: (p) => num(p.value, 2), detail: (p) => `${p.goals} Tore in ${p.minutes} Min.` },
  { key: "points_per_90", title: "Scorer pro 90 Min.", value: (p) => num(p.value, 2), detail: (p) => `${p.goals} T · ${p.assists} V` },
  { key: "rating", title: "Beste Note", value: (p) => num(p.value, 2), detail: (p) => `${p.apps} Spiele` },
  { key: "cards", title: "Karten", value: (p) => String(p.value), detail: (p) => `${p.yellow} Gelb · ${p.red} Rot` },
];

function Players({ data }: { data: CompetitionOverview }) {
  const [p, setP] = useState<CompetitionPlayers | null>(null);
  useEffect(() => {
    let current = true;
    setP(null);
    api<CompetitionPlayers>(`/competitions/${data.league.id}/players`, { season: data.season }).then((x) => current && setP(x)).catch(() => current && setP(null));
    return () => { current = false; };
  }, [data.league.id, data.season]);
  if (!p) return <Card><Loading /></Card>;
  if (!p.rankings.goals) return <Card><Empty text="Keine Spielerdaten für diese Saison." /></Card>;
  return (
    <div className="space-y-2">
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {PLAYER_LISTS.map((l) => {
          const list = (p.rankings[l.key] as RankedPlayer[] | undefined) ?? [];
          return (
            <Card key={l.key} title={l.title}>
              {list.length === 0 ? <Empty text="Keine Daten." /> : (
                <ol className="space-y-1.5 text-sm">
                  {list.slice(0, 10).map((pl, i) => {
                    const team = p.teams[pl.team_id];
                    return (
                      <li key={pl.player_id} className="flex items-center gap-2">
                        <span className="w-5 text-right text-xs tabular-nums text-slate-400">{i + 1}.</span>
                        <Logo src={playerPhoto(pl.player_id)} alt={pl.name} size={26} shape="round" />
                        <span className="min-w-0 flex-1">
                          <PlayerLink id={pl.player_id} className="block truncate font-medium">{pl.name}</PlayerLink>
                          <span className="flex items-center gap-1 text-[11px] text-slate-500">
                            {team && <TeamLogo team={team} size={12} />}<span className="truncate">{team?.name}</span><span className="text-slate-400">· {l.detail(pl)}</span>
                          </span>
                        </span>
                        <span className="w-10 text-right font-semibold tabular-nums">{l.value(pl)}</span>
                      </li>
                    );
                  })}
                </ol>
              )}
            </Card>
          );
        })}
      </div>
      <p className="text-xs text-slate-400">Pro 90 Minuten und Note: nur Spieler mit mindestens {p.rankings.min_minutes ?? 0} Minuten (30 % des meisteingesetzten Spielers).</p>
    </div>
  );
}

// --------------------------------------------------------------------------- schedule

function roundKey(f: Fixture) {
  return f.matchday != null ? `${f.matchday}` : f.round_label ?? f.round ?? "–";
}

function Schedule({ data, fixtures }: { data: CompetitionOverview; fixtures: Fixture[] | null }) {
  const rounds = useMemo(() => {
    const map = new Map<string, Fixture[]>();
    for (const f of fixtures ?? []) map.set(roundKey(f), [...(map.get(roundKey(f)) ?? []), f]);
    return [...map.entries()];
  }, [fixtures]);
  const current = rounds.findIndex(([, fs]) => fs.some((f) => !f.finished));
  const [index, setIndex] = useState<number | null>(null);
  if (fixtures === null) return <Card><Loading /></Card>;
  if (rounds.length === 0) return <Card><Empty text="Keine Spiele." /></Card>;
  const i = index ?? (current >= 0 ? current : rounds.length - 1);
  const [key, items] = rounds[i];
  const label = items[0].matchday != null ? `${key}. Spieltag` : key;
  return (
    <Card
      title={label}
      actions={
        <span className="flex items-center gap-2">
          <button type="button" disabled={i === 0} onClick={() => setIndex(i - 1)} className="rounded-md border border-slate-200 px-2 py-0.5 text-sm disabled:opacity-30">‹</button>
          <select value={i} onChange={(e) => setIndex(Number(e.target.value))} className="rounded-md border border-slate-300 bg-white px-2 py-1 text-sm">
            {rounds.map(([k, fs], j) => <option key={k} value={j}>{fs[0].matchday != null ? `${k}. Spieltag` : k}</option>)}
          </select>
          <button type="button" disabled={i === rounds.length - 1} onClick={() => setIndex(i + 1)} className="rounded-md border border-slate-200 px-2 py-0.5 text-sm disabled:opacity-30">›</button>
        </span>
      }
    >
      <ul className="divide-y divide-slate-100">
        {items.map((f) => {
          const p = f.prediction?.probabilities ?? {};
          const hits = (f.picks ?? []).filter((pk) => pk.outcome === true).length;
          return (
            <li key={f.id}>
              <Link href={`/spiel/${f.id}`} className="grid grid-cols-[80px_1fr_auto] items-center gap-3 py-2 text-sm hover:bg-slate-50 md:grid-cols-[100px_1fr_70px_150px_70px]">
                <span className="text-xs tabular-nums text-slate-500">{dateShort(f.kickoff)}<br />{time(f.kickoff)} Uhr</span>
                <span className="min-w-0 space-y-0.5">
                  <span className="flex items-center gap-1.5"><TeamLogo team={f.home} size={18} /><span className="truncate">{f.home.name}</span></span>
                  <span className="flex items-center gap-1.5"><TeamLogo team={f.away} size={18} /><span className="truncate">{f.away.name}</span></span>
                </span>
                <span className="text-center font-semibold tabular-nums">{f.finished ? `${f.score.ft[0]}:${f.score.ft[1]}` : <span className="text-slate-300">–:–</span>}</span>
                <span className="hidden text-right text-xs tabular-nums text-slate-500 md:block" title="Modell: 1 · X · 2">
                  {p.home != null && <>{pct(p.home, 0)} · {pct(p.draw, 0)} · {pct(p.away, 0)}</>}
                  {f.finished && f.prediction?.pick_1x2 && <span className="ml-1 inline-block align-middle"><OutcomeBadge outcome={f.prediction.pick_1x2_hit ?? null} small /></span>}
                </span>
                <span className="hidden text-right text-xs text-slate-500 md:block">{f.finished && (f.picks?.length ?? 0) > 0 ? `${hits}/${f.picks!.length} Tipps` : ""}</span>
              </Link>
            </li>
          );
        })}
      </ul>
      {data.league.cup && <p className="mt-2 text-xs text-slate-400">Europapokal: Runden statt Spieltage, Ergebnis nach 90 Minuten.</p>}
    </Card>
  );
}

function Loading() {
  return <p className="text-sm text-slate-400">Wird geladen …</p>;
}

function Empty({ text }: { text: string }) {
  return <p className="text-sm text-slate-500">{text}</p>;
}

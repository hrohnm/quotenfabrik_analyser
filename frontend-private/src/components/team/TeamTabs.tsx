"use client";

import Link from "next/link";
import { PlayerLink } from "@/components/PlayerLink";
import { useEffect, useState } from "react";
import { Logo } from "@/components/Logo";
import { OutcomeBadge, Card, TeamLogo } from "@/components/ui";
import { TeamLink } from "@/components/TeamLink";
import { BettingReport } from "@/components/BettingReport";
import { api } from "@/lib/api";
import { dateShort, num, pct, time } from "@/lib/format";
import { leagueLogo } from "@/lib/media";
import type { Fixture, SquadPlayer, TeamOverview, TeamSeasonStats, TeamSplit, TeamSquad } from "@/lib/types";
import { Segmented } from "@/components/match/Segmented";

const TABS = [
  { key: "uebersicht", label: "Übersicht" },
  { key: "spiele", label: "Spiele" },
  { key: "statistik", label: "Statistik" },
  { key: "kader", label: "Kader" },
  { key: "wetten", label: "Wetten & Modell" },
];

/** Tabs of the team page; every tab loads its own data. */
export function TeamTabs({ data }: { data: TeamOverview }) {
  const [tab, setTab] = useState("uebersicht");
  const [matches, setMatches] = useState<Fixture[] | null>(null);
  useEffect(() => {
    const hash = window.location.hash.slice(1);
    if (TABS.some((t) => t.key === hash)) setTab(hash);
  }, []);
  useEffect(() => {
    let current = true;
    setMatches(null);
    api<Fixture[]>("/fixtures", { team: data.team.id, season: data.season, limit: 300 }).then((m) => current && setMatches(m)).catch(() => current && setMatches([]));
    return () => { current = false; };
  }, [data.team.id, data.season]);
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
      {tab === "uebersicht" && <Overview data={data} matches={matches} />}
      {tab === "spiele" && <Matches data={data} matches={matches} />}
      {tab === "statistik" && <Statistics data={data} />}
      {tab === "kader" && <Squad data={data} />}
      {tab === "wetten" && <BettingReport path={`/teams/${data.team.id}/betting`} season={data.season} scope="der Mannschaft" />}
    </div>
  );
}

// --------------------------------------------------------------------------- overview

function Overview({ data, matches }: { data: TeamOverview; matches: Fixture[] | null }) {
  const upcoming = (matches ?? []).filter((m) => !m.finished).slice(0, 5);
  const recent = (matches ?? []).filter((m) => m.finished).slice(-5).reverse();
  const next = upcoming[0];
  return (
    <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
      <div className="space-y-4">
        {next && <NextMatch f={next} teamId={data.team.id} />}
        <Card title="Letzte Spiele">
          {matches === null ? <Loading /> : recent.length === 0 ? <Empty /> : <MatchList items={recent} teamId={data.team.id} />}
        </Card>
      </div>
      <div className="space-y-4">
        {data.streaks.length > 0 && (
          <Card title="Aktuelle Serien">
            <div className="flex flex-wrap gap-2">
              {data.streaks.map((s) => (
                <span key={s.key} className="inline-flex items-center gap-2 rounded-lg bg-slate-50 px-3 py-2 text-sm">
                  <span className="text-xl font-semibold tabular-nums">{s.length}</span>
                  <span className="text-slate-600">{s.label}</span>
                </span>
              ))}
            </div>
          </Card>
        )}
        <Card title="Nächste Spiele">
          {matches === null ? <Loading /> : upcoming.length === 0 ? <Empty text="Keine anstehenden Spiele in dieser Saison." /> : <MatchList items={upcoming} teamId={data.team.id} />}
        </Card>
      </div>
    </div>
  );
}

function NextMatch({ f, teamId }: { f: Fixture; teamId: number }) {
  const p = f.prediction?.probabilities ?? {};
  const home = f.home.id === teamId;
  const win = home ? p.home : p.away;
  const loss = home ? p.away : p.home;
  return (
    <Link href={`/spiel/${f.id}`} className="block rounded-xl border border-emerald-200 bg-gradient-to-b from-emerald-50/70 to-white p-4 shadow-sm hover:border-emerald-300">
      <div className="flex items-center justify-between text-xs text-slate-500">
        <span className="flex items-center gap-1.5 font-medium uppercase tracking-wide text-emerald-700">
          Nächstes Spiel <Logo src={f.league?.logo ?? leagueLogo(f.league_id)} alt="Wettbewerb" size={14} />
        </span>
        <span>{dateShort(f.kickoff)} · {time(f.kickoff)} Uhr</span>
      </div>
      <div className="mt-3 grid grid-cols-[1fr_auto_1fr] items-center gap-3">
        <span className="flex items-center justify-end gap-2 text-right font-semibold"><span className="truncate">{f.home.name}</span><TeamLogo team={f.home} size={32} /></span>
        <span className="text-slate-300">vs</span>
        <span className="flex items-center gap-2 font-semibold"><TeamLogo team={f.away} size={32} /><span className="truncate">{f.away.name}</span></span>
      </div>
      {win != null && (
        <div className="mt-3 grid grid-cols-3 gap-2 text-center text-sm">
          <Prob label="Sieg" value={win} tone="text-emerald-700" />
          <Prob label="Remis" value={p.draw} tone="text-slate-700" />
          <Prob label="Niederlage" value={loss} tone="text-rose-700" />
        </div>
      )}
      {f.picks && f.picks.length > 0 && (
        <div className="mt-3 text-xs text-slate-500">Tipps: {f.picks.map((pk) => `${pk.label} (${pct(pk.probability, 0)})`).join(" · ")}</div>
      )}
    </Link>
  );
}

function Prob({ label, value, tone }: { label: string; value: number | undefined; tone: string }) {
  return (
    <div className="rounded-lg bg-white/80 p-2">
      <div className="text-[11px] uppercase tracking-wide text-slate-500">{label}</div>
      <div className={`text-lg font-semibold tabular-nums ${tone}`}>{pct(value, 0)}</div>
    </div>
  );
}

// --------------------------------------------------------------------------- matches

function resultOf(f: Fixture, teamId: number): "S" | "U" | "N" | null {
  const [h, a] = f.score.ft;
  if (!f.finished || h === null || a === null) return null;
  const [gf, ga] = f.home.id === teamId ? [h, a] : [a, h];
  return gf > ga ? "S" : gf === ga ? "U" : "N";
}

const RESULT_TONE = { S: "bg-emerald-500", U: "bg-slate-400", N: "bg-rose-500" } as const;

function MatchList({ items, teamId, detail = false }: { items: Fixture[]; teamId: number; detail?: boolean }) {
  return (
    <ul className="divide-y divide-slate-100">
      {items.map((f) => {
        const home = f.home.id === teamId;
        const opp = home ? f.away : f.home;
        const res = resultOf(f, teamId);
        const p = f.prediction?.probabilities ?? {};
        const pickKey = f.prediction?.pick_1x2;
        const hits = (f.picks ?? []).filter((pk) => pk.outcome === true).length;
        return (
          <li key={f.id} className="flex items-center gap-2 py-2 text-sm sm:gap-3">
            <span className="w-16 shrink-0 text-xs tabular-nums text-slate-500">{dateShort(f.kickoff)}</span>
            <Logo src={f.league?.logo ?? leagueLogo(f.league_id)} alt={f.league?.name ?? "Wettbewerb"} size={16} />
            <span className="w-4 shrink-0 text-center text-xs text-slate-400" title={home ? "Heimspiel" : "Auswärtsspiel"}>{home ? "H" : "A"}</span>
            <span className="flex min-w-0 flex-1 items-center gap-2">
              <TeamLogo team={opp} size={18} />
              <TeamLink id={opp.id} className="truncate">{opp.name}</TeamLink>
            </span>
            {detail && (
              <span className="hidden w-28 shrink-0 text-right text-xs tabular-nums text-slate-500 sm:block" title="Modell: Sieg / Remis / Niederlage aus Sicht der Mannschaft">
                {p.home != null ? `${pct(home ? p.home : p.away, 0)} · ${pct(p.draw, 0)} · ${pct(home ? p.away : p.home, 0)}` : ""}
              </span>
            )}
            {detail && f.finished && (f.picks?.length ?? 0) > 0 && (
              <span className="hidden w-14 shrink-0 text-right text-xs text-slate-500 sm:block" title="eingetretene Tipps">{hits}/{f.picks!.length} Tipps</span>
            )}
            <Link href={`/spiel/${f.id}`} className="flex shrink-0 items-center gap-1.5 tabular-nums hover:opacity-80">
              {f.finished ? (
                <>
                  <span className="font-semibold">{f.score.ft[0]}:{f.score.ft[1]}</span>
                  {res && <span className={`grid h-5 w-5 place-items-center rounded text-[10px] font-bold text-white ${RESULT_TONE[res]}`}>{res}</span>}
                  {detail && pickKey && <OutcomeBadge outcome={f.prediction?.pick_1x2_hit ?? null} small />}
                </>
              ) : (
                <span className="text-xs text-slate-500">{time(f.kickoff)}</span>
              )}
            </Link>
          </li>
        );
      })}
    </ul>
  );
}

function Matches({ data, matches }: { data: TeamOverview; matches: Fixture[] | null }) {
  const [comp, setComp] = useState("alle");
  const [venue, setVenue] = useState("alle");
  if (matches === null) return <Card><Loading /></Card>;
  const items = matches.filter(
    (m) => (comp === "alle" || String(m.league_id) === comp) && (venue === "alle" || (venue === "heim") === (m.home.id === data.team.id)),
  );
  const options = [{ key: "alle", label: "Alle Wettbewerbe" }, ...data.competitions.map((c) => ({ key: String(c.league.id), label: c.league.name }))];
  return (
    <Card
      title={`Spiele ${items.length}`}
      actions={
        <span className="flex flex-wrap justify-end gap-2">
          <Segmented size="sm" options={options} value={comp} onChange={setComp} />
          <Segmented size="sm" options={[{ key: "alle", label: "Alle" }, { key: "heim", label: "Heim" }, { key: "auswaerts", label: "Auswärts" }]} value={venue} onChange={setVenue} />
        </span>
      }
    >
      {items.length === 0 ? <Empty /> : <MatchList items={items} teamId={data.team.id} detail />}
      <p className="mt-3 text-xs text-slate-400">Prozente: Modell vor dem Spiel (Sieg · Remis · Niederlage aus Sicht der Mannschaft); Haken: wahrscheinlichster Ausgang eingetreten; Tipps: eingetretene der 3 Tipps.</p>
    </Card>
  );
}

// --------------------------------------------------------------------------- statistics

const SPLIT_ROWS: { key: keyof TeamSplit; label: string; kind: "num" | "pct" | "int" }[] = [
  { key: "played", label: "Spiele", kind: "int" },
  { key: "points_per_game", label: "Punkte pro Spiel", kind: "num" },
  { key: "gf_per_game", label: "Tore pro Spiel", kind: "num" },
  { key: "ga_per_game", label: "Gegentore pro Spiel", kind: "num" },
  { key: "over_1_5", label: "Über 1,5 Tore", kind: "pct" },
  { key: "over_2_5", label: "Über 2,5 Tore", kind: "pct" },
  { key: "over_3_5", label: "Über 3,5 Tore", kind: "pct" },
  { key: "btts", label: "Beide treffen", kind: "pct" },
  { key: "clean_sheet", label: "Zu Null", kind: "pct" },
  { key: "failed_to_score", label: "Ohne eigenes Tor", kind: "pct" },
  { key: "ht_lead", label: "Führung zur Pause", kind: "pct" },
  { key: "first_half_goals", label: "Tore 1. HZ (beide)", kind: "num" },
  { key: "second_half_goals", label: "Tore 2. HZ (beide)", kind: "num" },
];

function fmt(v: number | null | undefined, kind: "num" | "pct" | "int") {
  if (v === null || v === undefined) return "–";
  return kind === "pct" ? pct(v, 0) : kind === "int" ? String(v) : num(v);
}

function Statistics({ data }: { data: TeamOverview }) {
  const [comp, setComp] = useState("alle");
  const [stats, setStats] = useState<TeamSeasonStats | null>(null);
  useEffect(() => {
    let current = true;
    setStats(null);
    api<TeamSeasonStats>(`/teams/${data.team.id}/stats`, { season: data.season, competition: comp === "alle" ? undefined : comp })
      .then((s) => current && setStats(s))
      .catch(() => current && setStats({ season: data.season, competition: null, splits: null }));
    return () => { current = false; };
  }, [data.team.id, data.season, comp]);
  const options = [{ key: "alle", label: "Alle Wettbewerbe" }, ...data.competitions.map((c) => ({ key: String(c.league.id), label: c.league.name }))];
  return (
    <div className="space-y-4">
      <Segmented size="sm" options={options} value={comp} onChange={setComp} />
      {!stats ? <Card><Loading /></Card> : !stats.splits ? <Card><Empty text="Noch keine beendeten Spiele." /></Card> : (
        <div className="grid gap-4 lg:grid-cols-2">
          <Card title="Heim und Auswärts">
            <table className="w-full text-sm tabular-nums">
              <thead>
                <tr className="text-[11px] uppercase tracking-wide text-slate-400">
                  <th className="py-1 text-left font-medium" />
                  <th className="py-1 text-right font-medium">Gesamt</th>
                  <th className="py-1 text-right font-medium">Heim</th>
                  <th className="py-1 text-right font-medium">Auswärts</th>
                </tr>
              </thead>
              <tbody>
                {SPLIT_ROWS.map((r) => (
                  <tr key={r.key} className="border-t border-slate-50">
                    <td className="py-1.5 text-slate-600">{r.label}</td>
                    {(["total", "home", "away"] as const).map((s) => (
                      <td key={s} className={`py-1.5 text-right ${s === "total" ? "font-semibold" : ""}`}>{fmt(stats.splits![s][r.key] as number | null | undefined, r.kind)}</td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </Card>
          <div className="space-y-4">
            {stats.segments && stats.segments.length > 0 && <Segments segments={stats.segments} />}
            {stats.expected_points && (
              <Card title="Punkte gegen die Modell-Erwartung">
                <p className="text-sm text-slate-600">
                  {stats.expected_points.points} Punkte aus {stats.expected_points.matches} Spielen, erwartet waren {num(stats.expected_points.expected, 1)}:{" "}
                  <b className={stats.expected_points.diff_per_game >= 0 ? "text-emerald-700" : "text-rose-700"}>
                    {stats.expected_points.diff_per_game >= 0 ? "+" : "−"}{num(Math.abs(stats.expected_points.diff_per_game))} pro Spiel
                  </b>.
                </p>
                <p className="mt-1 text-xs text-slate-400">Erwartung aus der Prognose vor jedem Spiel (3 × Siegchance + Remischance). Rückblick, kein Wettsignal.</p>
              </Card>
            )}
          </div>
          {stats.match_stats && stats.match_stats.rows.length > 0 && (
            <Card title={`Spielstatistik pro Spiel · Vergleich ${stats.match_stats.league.name ?? "Liga"}`} className="lg:col-span-2">
              <MatchStats rows={stats.match_stats.rows} />
            </Card>
          )}
        </div>
      )}
    </div>
  );
}

function Segments({ segments }: { segments: NonNullable<TeamSeasonStats["segments"]> }) {
  const max = Math.max(1, ...segments.flatMap((s) => [s.scored, s.conceded]));
  return (
    <Card title="Tore nach Spielminute">
      <div className="grid grid-cols-6 items-end gap-2">
        {segments.map((s) => (
          <div key={s.label} className="flex flex-col items-center gap-1">
            <div className="flex h-28 w-full items-end justify-center gap-1">
              <div className="w-1/3 rounded-t bg-emerald-500" style={{ height: `${(s.scored / max) * 100}%` }} title={`${s.scored} Tore`} />
              <div className="w-1/3 rounded-t bg-rose-400" style={{ height: `${(s.conceded / max) * 100}%` }} title={`${s.conceded} Gegentore`} />
            </div>
            <div className="text-[11px] tabular-nums text-slate-600">{s.scored}:{s.conceded}</div>
            <div className="text-[10px] text-slate-400">{s.label}′</div>
          </div>
        ))}
      </div>
      <p className="mt-2 flex gap-3 text-xs text-slate-500">
        <span className="flex items-center gap-1"><span className="h-2 w-2 rounded-sm bg-emerald-500" />Tore</span>
        <span className="flex items-center gap-1"><span className="h-2 w-2 rounded-sm bg-rose-400" />Gegentore</span>
        <span className="text-slate-400">{segments[0].matches} Spiele mit Ereignisdaten, Nachspielzeit zählt zum letzten Abschnitt der Halbzeit</span>
      </p>
    </Card>
  );
}

function MatchStats({ rows }: { rows: NonNullable<TeamSeasonStats["match_stats"]>["rows"] }) {
  return (
    <div className="grid gap-x-8 gap-y-3 sm:grid-cols-2">
      {rows.map((r) => {
        const scale = Math.max(r.team, r.against ?? 0, r.league ?? 0) || 1;
        const digits = r.key === "xg" ? 2 : 1;
        return (
          <div key={r.key}>
            <div className="mb-1 flex items-baseline justify-between text-sm">
              <span className="text-slate-600">{r.label}</span>
              <span className="tabular-nums">
                <b>{num(r.team, digits)}</b>
                {r.against !== null && <span className="text-slate-400"> · Gegner {num(r.against, digits)}</span>}
              </span>
            </div>
            <div className="relative h-2 rounded-full bg-slate-100">
              <div className="h-2 rounded-full bg-emerald-500" style={{ width: `${(r.team / scale) * 100}%` }} />
              {r.league !== null && (
                <div className="absolute top-1/2 h-3.5 w-0.5 -translate-y-1/2 bg-slate-700" style={{ left: `${(r.league / scale) * 100}%` }} title={`Ligaschnitt ${num(r.league, digits)}`} />
              )}
            </div>
          </div>
        );
      })}
      <p className="text-xs text-slate-400 sm:col-span-2">Balken: Mannschaft, Strich: Ligaschnitt pro Team und Spiel.</p>
    </div>
  );
}

// --------------------------------------------------------------------------- squad

const POS_LABEL: Record<string, string> = { G: "Torwart", D: "Abwehr", M: "Mittelfeld", F: "Sturm" };

function Squad({ data }: { data: TeamOverview }) {
  const [squad, setSquad] = useState<TeamSquad | null>(null);
  useEffect(() => {
    let current = true;
    setSquad(null);
    api<TeamSquad>(`/teams/${data.team.id}/squad`, { season: data.season }).then((s) => current && setSquad(s)).catch(() => current && setSquad({ season: data.season, players: [], common_xi: null, rotation: null }));
    return () => { current = false; };
  }, [data.team.id, data.season]);
  if (!squad) return <Card><Loading /></Card>;
  if (squad.players.length === 0) return <Card><Empty text="Keine Spielerdaten für diese Saison." /></Card>;
  const groups = ["G", "D", "M", "F", ""].map((pos) => ({ pos, players: squad.players.filter((p) => (p.position ?? "") === pos) })).filter((g) => g.players.length);
  return (
    <div className="space-y-4">
      {squad.common_xi && (
        <Card title={`Häufigste Startelf${squad.common_xi.formation ? ` · ${squad.common_xi.formation}` : ""}`}>
          <div className="flex flex-wrap gap-3">
            {squad.common_xi.players.map((p) => (
              <div key={p.player_id} className="flex w-20 flex-col items-center gap-1 text-center">
                <Logo src={p.photo} alt={p.name} size={44} shape="round" />
                <PlayerLink id={p.player_id} className="w-full truncate text-xs font-medium">{p.name}</PlayerLink>
                <span className="text-[11px] text-slate-400">{p.starts}/{squad.common_xi!.matches} Startelf</span>
              </div>
            ))}
          </div>
          {squad.rotation?.avg_changes != null && (
            <p className="mt-3 text-xs text-slate-500">
              Rotation: im Schnitt <b>{num(squad.rotation.avg_changes, 1)}</b> Wechsel in der Startelf von Spiel zu Spiel ({squad.rotation.matches} Spiele mit Aufstellung).
            </p>
          )}
        </Card>
      )}
      <Card title={`Kader ${squad.players.length} Spieler`}>
        <div className="-mx-4 overflow-x-auto">
          <table className="w-full min-w-[40rem] text-sm tabular-nums">
            <thead>
              <tr className="text-[11px] uppercase tracking-wide text-slate-400">
                <th className="px-4 py-1.5 text-left font-medium">Spieler</th>
                <th className="px-2 py-1.5 text-right font-medium" title="Einsätze (davon Startelf)">Sp.</th>
                <th className="px-2 py-1.5 text-right font-medium">Min.</th>
                <th className="px-2 py-1.5 text-right font-medium">Tore</th>
                <th className="px-2 py-1.5 text-right font-medium">Vorl.</th>
                <th className="px-2 py-1.5 text-right font-medium" title="Schüsse / Schlüsselpässe">Sch. / SP</th>
                <th className="px-2 py-1.5 text-right font-medium">Karten</th>
                <th className="px-4 py-1.5 text-right font-medium">Note</th>
              </tr>
            </thead>
            {groups.map((g) => (
              <tbody key={g.pos}>
                <tr><td colSpan={8} className="bg-slate-50 px-4 py-1 text-[11px] font-semibold uppercase tracking-wide text-slate-500">{POS_LABEL[g.pos] ?? "Ohne Position"}</td></tr>
                {g.players.map((p) => <PlayerRow key={p.player_id} p={p} />)}
              </tbody>
            ))}
          </table>
        </div>
        <p className="mt-3 text-xs text-slate-400">Alle Wettbewerbe mit Spielerdaten in dieser Saison. Note: Ø API-Football-Bewertung. Status: Ausfälle für das nächste Spiel.</p>
      </Card>
    </div>
  );
}

function PlayerRow({ p }: { p: SquadPlayer }) {
  return (
    <tr className="border-t border-slate-50">
      <td className="px-4 py-1.5">
        <span className="flex items-center gap-2">
          <Logo src={p.photo} alt={p.name} size={28} shape="round" />
          <span className="w-6 text-right text-xs text-slate-400">{p.number ?? ""}</span>
          <PlayerLink id={p.player_id} className="truncate font-medium">{p.name}</PlayerLink>
          {p.status && (
            <span className={`rounded px-1.5 text-[10px] font-semibold ${p.status.type === "missing" ? "bg-rose-100 text-rose-700" : "bg-amber-100 text-amber-800"}`} title={p.status.reason}>
              {p.status.type === "missing" ? "fehlt" : "fraglich"}
            </span>
          )}
        </span>
      </td>
      <td className="px-2 py-1.5 text-right">{p.apps}<span className="text-xs text-slate-400"> ({p.starts})</span></td>
      <td className="px-2 py-1.5 text-right">{p.minutes}</td>
      <td className="px-2 py-1.5 text-right font-semibold">{p.goals || ""}</td>
      <td className="px-2 py-1.5 text-right">{p.assists || ""}</td>
      <td className="px-2 py-1.5 text-right text-slate-500">{p.shots} / {p.key_passes}</td>
      <td className="px-2 py-1.5 text-right">
        {p.yellow > 0 && <span className="mr-1 inline-flex items-center gap-0.5"><span className="inline-block h-3 w-2 rounded-[1px] bg-yellow-400" />{p.yellow}</span>}
        {p.red > 0 && <span className="inline-flex items-center gap-0.5"><span className="inline-block h-3 w-2 rounded-[1px] bg-rose-600" />{p.red}</span>}
      </td>
      <td className="px-4 py-1.5 text-right">{p.rating ? num(p.rating, 1) : "–"}</td>
    </tr>
  );
}

function Loading() {
  return <p className="text-sm text-slate-400">Wird geladen …</p>;
}

function Empty({ text = "Keine Spiele." }: { text?: string }) {
  return <p className="text-sm text-slate-500">{text}</p>;
}

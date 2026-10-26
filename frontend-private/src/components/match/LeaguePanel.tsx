"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Card, TeamLogo } from "@/components/ui";
import { api } from "@/lib/api";
import { num, pct, seasonLabel } from "@/lib/format";
import type { FixtureDetail, LeagueOverview, LeaguePlayer, TableRow } from "@/lib/types";
import { FormChips } from "./FormPanel";
import { Segmented } from "./Segmented";

const SCOPES = [
  { key: "total", label: "Gesamt" },
  { key: "home", label: "Heim" },
  { key: "away", label: "Auswärts" },
  { key: "before", label: "Vor dem Spiel" },
] as const;
type Scope = (typeof SCOPES)[number]["key"];

/** League details of the fixture's competition season: table, top scorers, assists and league figures. */
export function LeaguePanel({ data }: { data: FixtureDetail }) {
  const [league, setLeague] = useState<LeagueOverview | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [scope, setScope] = useState<Scope>("total");
  const id = data.fixture.id;

  useEffect(() => {
    let current = true;
    api<LeagueOverview>(`/fixtures/${id}/league`)
      .then((l) => current && setLeague(l))
      .catch((e) => current && setError(String(e instanceof Error ? e.message : e)));
    return () => { current = false; };
  }, [id]);

  if (error) return <p className="rounded-md bg-rose-50 p-3 text-sm text-rose-700">{error}</p>;
  if (!league) return <Card><p className="text-sm text-slate-400">Liga-Daten werden geladen …</p></Card>;
  const title = `${league.league?.name ?? "Wettbewerb"} ${seasonLabel(league.season)}${league.group ? ` · ${league.group.replace("Group", "Gruppe")}` : ""}`;
  const highlight = { [league.home_id]: "home", [league.away_id]: "away" } as Record<number, "home" | "away">;

  return (
    <div className="grid gap-4 lg:grid-cols-[minmax(0,2fr)_minmax(0,1fr)]">
      <div className="space-y-4">
        {league.table ? (
          <Card
            title={title}
            actions={<Segmented size="sm" options={[...SCOPES]} value={scope} onChange={(v) => setScope(v as Scope)} />}
          >
            {scope === "before" && <p className="mb-2 text-xs text-slate-500">Tabelle mit allen Spielen vor dem Anpfiff dieses Spiels.</p>}
            <Table rows={league.table[scope]} league={league} highlight={highlight} />
          </Card>
        ) : (
          <Card title={title}><p className="text-sm text-slate-500">Für diese Runde gibt es keine Tabelle (K.-o.-Runde).</p></Card>
        )}
        {league.figures && <Figures f={league.figures} />}
      </div>
      <div className="space-y-4">
        <PlayerCard title="Torjäger" players={league.scorers} league={league} highlight={highlight} kind="goals" />
        <PlayerCard title="Vorlagen" players={league.assists} league={league} highlight={highlight} kind="assists" />
        {(["home", "away"] as const).map((side) => {
          const team = league.teams[side === "home" ? league.home_id : league.away_id];
          return (
            <PlayerCard
              key={side}
              title={<span className="flex items-center gap-2">{team && <TeamLogo team={team} size={16} />}Torschützen {team?.name}</span>}
              players={league.team_scorers[side]}
              league={league}
              highlight={{}}
              kind="goals"
              compact
            />
          );
        })}
      </div>
    </div>
  );
}

function Table({ rows, league, highlight }: { rows: TableRow[]; league: LeagueOverview; highlight: Record<number, "home" | "away"> }) {
  return (
    <div className="-mx-4 overflow-x-auto">
      <table className="w-full min-w-[22rem] text-sm tabular-nums">
        <thead>
          <tr className="border-b border-slate-100 text-[11px] uppercase tracking-wide text-slate-400">
            <th className="w-8 px-2 py-1.5 text-right font-medium">#</th>
            <th className="w-full px-2 py-1.5 text-left font-medium">Team</th>
            <th className="px-1.5 py-1.5 text-right font-medium">Sp</th>
            <th className="hidden px-1.5 py-1.5 text-right font-medium sm:table-cell">S</th>
            <th className="hidden px-1.5 py-1.5 text-right font-medium sm:table-cell">U</th>
            <th className="hidden px-1.5 py-1.5 text-right font-medium sm:table-cell">N</th>
            <th className="px-1.5 py-1.5 text-right font-medium">Tore</th>
            <th className="px-1.5 py-1.5 text-right font-medium">Diff</th>
            <th className="px-2 py-1.5 text-right font-medium">Pkt</th>
            <th className="hidden px-2 py-1.5 text-left font-medium md:table-cell">Form</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => {
            const team = league.teams[r.team_id];
            const side = highlight[r.team_id];
            return (
              <tr key={r.team_id} className={`border-b border-slate-50 last:border-0 ${side === "home" ? "bg-emerald-50 font-semibold" : side === "away" ? "bg-sky-50 font-semibold" : ""}`}>
                <td className="px-2 py-1.5 text-right text-slate-500">{r.rank}</td>
                <td className="max-w-0 px-2 py-1.5">
                  <span className="flex min-w-0 items-center gap-2">
                    {team && <TeamLogo team={team} size={16} />}
                    <span className="truncate">{team?.name ?? r.team_id}</span>
                  </span>
                </td>
                <td className="px-1.5 py-1.5 text-right">{r.played}</td>
                <td className="hidden px-1.5 py-1.5 text-right sm:table-cell">{r.won}</td>
                <td className="hidden px-1.5 py-1.5 text-right sm:table-cell">{r.drawn}</td>
                <td className="hidden px-1.5 py-1.5 text-right sm:table-cell">{r.lost}</td>
                <td className="whitespace-nowrap px-1.5 py-1.5 text-right">{r.gf}:{r.ga}</td>
                <td className="px-1.5 py-1.5 text-right">{r.gd > 0 ? `+${r.gd}` : r.gd < 0 ? `−${-r.gd}` : "0"}</td>
                <td className="px-2 py-1.5 text-right font-semibold">{r.points}</td>
                <td className="hidden px-2 py-1.5 md:table-cell">{r.form && <FormChips sequence={r.form} size="h-4 w-4" />}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function PlayerCard({ title, players, league, highlight, kind, compact = false }: {
  title: React.ReactNode; players: LeaguePlayer[]; league: LeagueOverview; highlight: Record<number, "home" | "away">; kind: "goals" | "assists"; compact?: boolean;
}) {
  return (
    <Card title={title}>
      {players.length === 0 ? (
        <p className="text-sm text-slate-500">Noch keine Daten.</p>
      ) : (
        <ol className="space-y-1.5 text-sm">
          {players.map((p) => {
            const team = league.teams[p.team_id];
            const side = highlight[p.team_id];
            return (
              <li key={p.player_id} className={`flex items-center gap-2 rounded px-1 ${side === "home" ? "bg-emerald-50" : side === "away" ? "bg-sky-50" : ""}`}>
                <span className="w-5 text-right text-xs tabular-nums text-slate-400">{p.rank}.</span>
                {!compact && team && <TeamLogo team={team} size={16} />}
                <span className="min-w-0 flex-1 truncate">{p.name}</span>
                <span className="text-xs tabular-nums text-slate-400" title={kind === "goals" ? "Vorlagen" : "Tore"}>
                  {kind === "goals" ? `${p.assists} Vorl.` : `${p.goals} Tore`}
                </span>
                <span className="w-8 text-right font-semibold tabular-nums" title={kind === "goals" && p.penalties ? `davon ${p.penalties} Elfmeter` : undefined}>
                  {kind === "goals" ? p.goals : p.assists}
                </span>
              </li>
            );
          })}
        </ol>
      )}
    </Card>
  );
}

function Figures({ f }: { f: NonNullable<LeagueOverview["figures"]> }) {
  const tiles = [
    { label: "Tore pro Spiel", value: num(f.goals_per_match, 2) },
    { label: "Heimsiege", value: pct(f.home_win, 0) },
    { label: "Remis", value: pct(f.draw, 0) },
    { label: "Auswärtssiege", value: pct(f.away_win, 0) },
    { label: "Über 2,5 Tore", value: pct(f.over_2_5, 0) },
    { label: "Beide treffen", value: pct(f.btts, 0) },
    { label: "0:0", value: pct(f.nil_nil, 0) },
  ];
  return (
    <Card title={`Ligazahlen (${f.matches} Spiele)`}>
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
        {tiles.map((t) => (
          <div key={t.label} className="rounded-lg bg-slate-50 p-2 text-center">
            <div className="text-[11px] uppercase tracking-wide text-slate-500">{t.label}</div>
            <div className="text-lg font-semibold tabular-nums">{t.value}</div>
          </div>
        ))}
      </div>
      <p className="mt-2 text-xs text-slate-400">
        Alle beendeten Spiele des Wettbewerbs in dieser Saison (Pokale inkl. Qualifikation), Ergebnis nach 90 Minuten.{" "}
        <Link href="/explorer" className="text-emerald-700 hover:underline">Mehr im Daten-Explorer</Link>
      </p>
    </Card>
  );
}

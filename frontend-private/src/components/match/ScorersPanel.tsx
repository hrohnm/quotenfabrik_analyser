"use client";

import { useState } from "react";
import { Logo } from "@/components/Logo";
import { Card, OutcomeBadge, ProbabilityBar, TeamLogo } from "@/components/ui";
import { num, odd, pct } from "@/lib/format";
import { playerPhoto } from "@/lib/media";
import type { FixtureDetail, Pattern, Scorer, Team } from "@/lib/types";

const POSITION: Record<string, string> = { G: "Torwart", D: "Abwehr", M: "Mittelfeld", F: "Sturm" };
const TOP = 8;

export function ScorersPanel({ data }: { data: FixtureDetail }) {
  const { fixture: f } = data;
  if (data.scorers.length === 0) return <Card><p className="text-sm text-slate-500">Keine Torschützen-Prognose vorhanden.</p></Card>;
  // Season form of the regular scorers (pattern details, computed before kickoff)
  const form = new Map<number, Pattern>();
  for (const p of data.patterns) if (p.group === "scorers") form.set(Number(p.key.split("_").at(-1)), p);
  // Goals per player from the match events (own goals do not count for scorer bets)
  const goals = new Map<number, number>();
  for (const g of data.goals) {
    if (g.player_id && g.detail !== "Own Goal" && g.detail !== "Missed Penalty") goals.set(g.player_id, (goals.get(g.player_id) ?? 0) + 1);
  }
  return (
    <div className="space-y-3">
      <p className="text-xs text-slate-500">
        Anytime = trifft mindestens einmal. Faire Quote = 1 / Wahrscheinlichkeit. Saisonform: Tore und Tore pro 90 Minuten vor diesem Spiel.
      </p>
      <div className="grid gap-4 lg:grid-cols-2">
        {[f.home, f.away].map((t) => (
          <TeamScorers key={t.id} team={t} scorers={data.scorers.filter((s) => s.team_id === t.id)} form={form} goals={goals} finished={f.finished} />
        ))}
      </div>
    </div>
  );
}

function TeamScorers({ team, scorers, form, goals, finished }: { team: Team; scorers: Scorer[]; form: Map<number, Pattern>; goals: Map<number, number>; finished: boolean }) {
  const [all, setAll] = useState(false);
  const rows = all ? scorers : scorers.slice(0, TOP);
  return (
    <Card title={<span className="flex items-center gap-2"><TeamLogo team={team} size={20} />{team.name}</span>}>
      <ul className="divide-y divide-slate-100">
        {rows.map((s) => {
          const d = form.get(s.player_id)?.details;
          const scored = goals.get(s.player_id) ?? s.goals ?? 0;
          return (
            <li key={s.player_id} className="flex items-center gap-3 py-2">
              <Logo src={playerPhoto(s.player_id)} alt={s.name ?? String(s.player_id)} size={36} shape="round" />
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-1.5 text-sm font-medium">
                  <span className="truncate">{s.name ?? s.player_id}</span>
                  {finished && scored > 0 && <span title={`${scored} Tor(e)`} className="text-xs">{"⚽".repeat(Math.min(scored, 3))}</span>}
                </div>
                <div className="truncate text-xs text-slate-400">
                  {POSITION[s.position ?? ""] ?? "–"}
                  {s.is_starter === false && " · Bank"}
                  {d && ` · ${d.goals} Tore (${num(d.goals_per90)}/90)`}
                </div>
                <div className="mt-1 max-w-48"><ProbabilityBar value={s.anytime ?? 0} tone={(s.anytime ?? 0) >= 0.3 ? "emerald" : "slate"} /></div>
              </div>
              <div className="w-14 text-right">
                <div className="text-sm font-semibold tabular-nums">{pct(s.anytime, 0)}</div>
                <div className="text-xs tabular-nums text-slate-400">{s.anytime ? odd(1 / s.anytime) : "–"}</div>
              </div>
              <div className="hidden w-14 text-right sm:block" title="Erster Torschütze">
                <div className="text-xs text-slate-400">Erster</div>
                <div className="text-xs tabular-nums text-slate-600">{pct(s.first, 0)}</div>
              </div>
              {finished && <OutcomeBadge outcome={s.anytime_outcome} small />}
            </li>
          );
        })}
      </ul>
      {scorers.length > TOP && (
        <button type="button" onClick={() => setAll(!all)} className="mt-2 text-xs font-medium text-emerald-700 hover:underline">
          {all ? "weniger anzeigen" : `alle ${scorers.length} Spieler anzeigen`}
        </button>
      )}
    </Card>
  );
}

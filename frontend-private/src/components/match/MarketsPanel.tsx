"use client";

import { useState } from "react";
import { Card, OutcomeBadge, ProbabilityBar, TeamLogo } from "@/components/ui";
import { dateShort, odd, pct, time } from "@/lib/format";
import { lineLabel, lines, market, pick, selectionLabel, signedLine } from "@/lib/markets";
import type { Fixture, FixtureDetail, Market, Team } from "@/lib/types";
import { BetanoOdd } from "@/components/BetanoOdd";
import { Segmented } from "./Segmented";

const GROUPS = [
  { key: "1x2", label: "Spielausgang" },
  { key: "totals", label: "Tore gesamt" },
  { key: "team_totals", label: "Tore pro Team" },
  { key: "halves", label: "Halbzeiten" },
];

export function MarketsPanel({ markets, fixture: f, odds }: { markets: Market[]; fixture: Fixture; odds?: FixtureDetail["odds"] }) {
  const [group, setGroup] = useState("1x2");
  if (markets.length === 0) return <Card><p className="text-sm text-slate-500">Für dieses Spiel liegt noch keine Prognose vor.</p></Card>;
  const names = { home: f.home.name, away: f.away.name };
  const sel = (key: string, title?: string) => {
    const m = market(markets, key);
    return m ? <SelectionCard key={key} m={m} title={title} names={names} finished={f.finished} /> : null;
  };
  const ou = (key: string, title: string, team?: Team) => {
    const ls = lines(markets, key);
    return ls.length ? <OverUnderTable key={key} title={title} team={team} lines={ls} finished={f.finished} /> : null;
  };

  return (
    <div className="space-y-4">
      <Segmented options={GROUPS} value={group} onChange={setGroup} />
      <p className="text-xs text-slate-500">
        Faire Quote = 1 / Wahrscheinlichkeit (ohne Buchmachermarge). Der wahrscheinlichere Ausgang ist hervorgehoben.{" "}
        {odds?.betano_at ? (
          <>
            <span className="rounded bg-orange-50 px-1 font-medium text-orange-700">Betano-Quote</span>{" "}
            {odds.closing ? "letzte vor Anpfiff" : `Stand ${dateShort(odds.betano_at)} ${time(odds.betano_at)} Uhr`};{" "}
            <span className="rounded bg-emerald-100 px-1 font-medium text-emerald-800">grün</span> = Modell sieht mindestens 5 % Vorteil (Wahrscheinlichkeit × Quote).
            Details beim Darüberfahren.
          </>
        ) : (
          "Für dieses Spiel liegen (noch) keine Betano-Quoten vor."
        )}
      </p>

      {group === "1x2" && (
        <div className="grid gap-4 md:grid-cols-3">
          {sel("1x2", "1X2")}
          {sel("dc")}
          {sel("dnb")}
          <div className="md:col-span-3"><HandicapTable lines={lines(markets, "eh")} names={names} finished={f.finished} /></div>
        </div>
      )}

      {group === "totals" && (
        <div className="grid gap-4 md:grid-cols-2">
          {ou("ou_ft", "Über/Unter Tore")}
          <div className="space-y-4">
            {sel("btts")}
            <ExactGoals m={market(markets, "exact_goals")} finished={f.finished} />
          </div>
        </div>
      )}

      {group === "team_totals" && (
        <div className="grid gap-4 md:grid-cols-2">
          {ou("ou_home", f.home.name, f.home)}
          {ou("ou_away", f.away.name, f.away)}
          {sel("clean_sheet", "Zu null")}
        </div>
      )}

      {group === "halves" && (
        <div className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            {sel("ht_1x2", "Halbzeit 1X2")}
            {sel("highest_half")}
            {sel("btts_1h")}
            {sel("btts_2h")}
          </div>
          <div className="grid gap-4 md:grid-cols-2">
            {ou("ou_1h", "Tore 1. Halbzeit")}
            {ou("ou_2h", "Tore 2. Halbzeit")}
            {ou("ou_home_1h", `${f.home.name} · 1. HZ`, f.home)}
            {ou("ou_away_1h", `${f.away.name} · 1. HZ`, f.away)}
            {ou("ou_home_2h", `${f.home.name} · 2. HZ`, f.home)}
            {ou("ou_away_2h", `${f.away.name} · 2. HZ`, f.away)}
          </div>
        </div>
      )}
    </div>
  );
}

function SelectionCard({ m, title, names, finished }: { m: Market; title?: string; names: { home: string; away: string }; finished: boolean }) {
  const best = pick(m);
  return (
    <Card title={title ?? m.label}>
      <ul className="space-y-2.5">
        {m.selections.map((s) => {
          const isPick = s.selection === best?.selection && m.selections.length > 1;
          return (
            <li key={s.selection}>
              <div className="mb-1 flex items-center justify-between gap-2 text-sm">
                <span className={`truncate ${isPick ? "font-semibold" : "text-slate-600"}`}>{selectionLabel(s, names.home, names.away)}</span>
                <span className="flex shrink-0 items-center gap-2 tabular-nums">
                  <span className={isPick ? "font-semibold" : ""}>{pct(s.probability, 0)}</span>
                  <span className="w-10 text-right text-xs text-slate-400">{odd(s.fair_odd)}</span>
                  <span className="w-11 text-right"><BetanoOdd prices={s} /></span>
                  {finished && <OutcomeBadge outcome={s.outcome} small />}
                </span>
              </div>
              <ProbabilityBar value={s.probability} tone={isPick ? "emerald" : "slate"} />
            </li>
          );
        })}
      </ul>
    </Card>
  );
}

/** One row per line: over and under side by side. */
function OverUnderTable({ title, team, lines: ls, finished }: { title: string; team?: Team; lines: Market[]; finished: boolean }) {
  return (
    <Card title={<span className="flex items-center gap-2">{team && <TeamLogo team={team} size={18} />}{title}</span>}>
      <table className="w-full text-sm">
        <thead>
          <tr className="text-xs text-slate-400">
            <th className="pb-2 text-left font-medium">Linie</th>
            <th className="pb-2 text-left font-medium">Über</th>
            <th className="pb-2 text-right font-medium">Unter</th>
            {finished && <th className="pb-2 text-right font-medium">Ergebnis</th>}
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {ls.map((m) => {
            const over = m.selections.find((s) => s.selection === "over");
            const under = m.selections.find((s) => s.selection === "under");
            const p = over?.probability ?? 0;
            const happened = over?.outcome === true ? "Über" : over?.outcome === false ? "Unter" : null;
            const hit = over?.outcome === null || over?.outcome === undefined ? null : over.outcome === p >= 0.5;
            return (
              <tr key={m.line}>
                <td className="py-1.5 pr-3 font-medium tabular-nums">{lineLabel(m.line)}</td>
                <td className="w-full py-1.5">
                  <div className="flex items-center gap-2">
                    <span className={`w-32 shrink-0 tabular-nums ${p >= 0.5 ? "font-semibold" : "text-slate-500"}`}>
                      {pct(p, 0)} <span className="text-xs font-normal text-slate-400">{odd(over?.fair_odd)}</span>
                      {over && <BetanoOdd prices={over} className="ml-1" />}
                    </span>
                    <SplitBar value={p} />
                  </div>
                </td>
                <td className={`whitespace-nowrap py-1.5 pl-2 text-right tabular-nums ${p < 0.5 ? "font-semibold" : "text-slate-500"}`}>
                  {under && <BetanoOdd prices={under} className="mr-1" />}
                  <span className="text-xs font-normal text-slate-400">{odd(under?.fair_odd)}</span> {pct(under?.probability, 0)}
                </td>
                {finished && (
                  <td className="py-1.5 pl-3 text-right">
                    <span className="inline-flex items-center gap-1.5 text-xs text-slate-500">{happened}<OutcomeBadge outcome={hit} small /></span>
                  </td>
                )}
              </tr>
            );
          })}
        </tbody>
      </table>
    </Card>
  );
}

function SplitBar({ value }: { value: number }) {
  return (
    <div className="flex h-2 min-w-16 flex-1 overflow-hidden rounded-full bg-slate-200">
      <div className="h-full bg-emerald-500" style={{ width: `${value * 100}%` }} />
    </div>
  );
}

function HandicapTable({ lines: ls, names, finished }: { lines: Market[]; names: { home: string; away: string }; finished: boolean }) {
  if (ls.length === 0) return null;
  return (
    <Card title="Europäisches Handicap (aus Sicht des Heimteams)">
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-xs text-slate-400">
              <th className="pb-2 text-left font-medium">Handicap</th>
              <th className="pb-2 text-right font-medium">{names.home}</th>
              <th className="pb-2 text-right font-medium">Remis</th>
              <th className="pb-2 text-right font-medium">{names.away}</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {ls.map((m) => {
              const best = pick(m);
              return (
                <tr key={m.line}>
                  <td className="py-1.5 font-medium tabular-nums">{signedLine(m.line ?? 0)} : 0</td>
                  {["H", "D", "A"].map((k) => {
                    const s = m.selections.find((x) => x.selection === k);
                    return (
                      <td key={k} className={`py-1.5 text-right tabular-nums ${s?.selection === best?.selection ? "font-semibold text-emerald-700" : "text-slate-600"}`}>
                        <span className="inline-flex items-center gap-1.5">
                          {pct(s?.probability, 0)}
                          <span className="hidden text-xs font-normal text-slate-400 sm:inline">{odd(s?.fair_odd)}</span>
                          {s && <BetanoOdd prices={s} />}
                          {finished && s?.outcome && <OutcomeBadge outcome={s.selection === best?.selection} small />}
                        </span>
                      </td>
                    );
                  })}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </Card>
  );
}

function ExactGoals({ m, finished }: { m?: Market; finished: boolean }) {
  if (!m) return null;
  const order = ["0", "1", "2", "3", "4", "5", "6+"];
  const sels = order.map((k) => m.selections.find((s) => s.selection === k)).filter((s) => s !== undefined);
  const max = Math.max(...sels.map((s) => s.probability));
  return (
    <Card title="Exakte Toranzahl">
      <div className="flex h-32 items-end gap-2">
        {sels.map((s) => (
          <div key={s.selection} className="flex flex-1 flex-col items-center gap-1">
            <span className="text-[11px] tabular-nums text-slate-500">{pct(s.probability, 0)}</span>
            <div
              className={`w-full rounded-t ${finished && s.outcome ? "bg-amber-400" : s.probability === max ? "bg-emerald-500" : "bg-slate-300"}`}
              style={{ height: `${(s.probability / max) * 72 + 2}px` }}
              title={`faire Quote ${odd(s.fair_odd)}`}
            />
            <span className="text-xs font-medium">{s.selection}</span>
          </div>
        ))}
      </div>
      {finished && <p className="mt-2 text-xs text-slate-400"><span className="mr-1 inline-block h-2 w-2 rounded-sm bg-amber-400" />tatsächliche Toranzahl</p>}
    </Card>
  );
}

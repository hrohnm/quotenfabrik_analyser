"use client";

import { useState } from "react";
import type { MatchEvent, Team } from "@/lib/types";

const minuteLabel = (e: MatchEvent) => `${e.minute ?? "?"}${e.extra_minute ? `+${e.extra_minute}` : ""}'`;

const KIND_LABEL: Record<MatchEvent["kind"], string> = {
  goal: "Tor", penalty: "Tor (Elfmeter)", own_goal: "Eigentor", missed_penalty: "Elfmeter verschossen", yellow: "Gelbe Karte",
  second_yellow: "Gelb-Rot", red: "Rote Karte", sub: "Wechsel", var: "Videobeweis",
};

const VAR_DETAIL: Record<string, string> = {
  "Goal cancelled": "Tor aberkannt", "Goal confirmed": "Tor bestätigt", "Penalty confirmed": "Elfmeter bestätigt",
  "Penalty cancelled": "Elfmeter zurückgenommen", "Penalty awarded": "Elfmeter gegeben", "Card upgrade": "Karte verschärft",
  "Red card cancelled": "Rote Karte zurückgenommen", "Card reviewed": "Karte überprüft",
};

function describe(e: MatchEvent): string {
  if (e.kind === "own_goal") return `${minuteLabel(e)} Eigentor: ${e.player ?? "?"}${e.score ? ` – ${e.score[0]}:${e.score[1]}` : ""}`;
  if (e.kind === "sub") return `${minuteLabel(e)} Wechsel: ${e.related ?? "?"} für ${e.player ?? "?"}`;
  if (e.kind === "var") return `${minuteLabel(e)} Videobeweis: ${VAR_DETAIL[e.detail ?? ""] ?? e.detail ?? ""}${e.player ? ` (${e.player})` : ""}`;
  const assist = (e.kind === "goal" || e.kind === "penalty") && e.related ? `, Vorlage ${e.related}` : "";
  const score = e.score ? ` – ${e.score[0]}:${e.score[1]}` : "";
  return `${minuteLabel(e)} ${KIND_LABEL[e.kind]}: ${e.player ?? "?"}${assist}${score}`;
}

/** Small icon per event kind (goals, cards, substitutions, VAR). */
function Icon({ kind }: { kind: MatchEvent["kind"] }) {
  switch (kind) {
    case "goal":
    case "penalty":
      return <span className="text-sm leading-none">⚽</span>;
    case "own_goal":
      return <span className="rounded bg-rose-100 px-0.5 text-[10px] font-bold leading-tight text-rose-700">ET</span>;
    case "missed_penalty":
      return <span className="text-xs font-bold leading-none text-slate-400">✕</span>;
    case "yellow":
      return <span className="inline-block h-3.5 w-2.5 rounded-[2px] bg-yellow-400" />;
    case "red":
      return <span className="inline-block h-3.5 w-2.5 rounded-[2px] bg-rose-600" />;
    case "second_yellow":
      return <span className="inline-block h-3.5 w-2.5 rounded-[2px] bg-gradient-to-br from-yellow-400 from-50% to-rose-600 to-50%" />;
    case "sub":
      return <span className="text-xs leading-none text-sky-600">⇄</span>;
    case "var":
      return <span className="rounded bg-slate-200 px-0.5 text-[9px] font-bold leading-tight text-slate-600">VAR</span>;
  }
}

/** Timeline of a finished (or running) match: home events above, away events below the line. */
export function Timeline({ events, home, away }: { events: MatchEvent[]; home: Team; away: Team }) {
  const [subs, setSubs] = useState(false);
  const shown = events.filter((e) => subs || e.kind !== "sub");
  if (events.length === 0) return null;
  const end = Math.max(90, ...events.map((e) => (e.minute ?? 0) + (e.extra_minute ?? 0) * 0.5 + 1));
  const pos = (e: MatchEvent) => (((e.minute ?? 0) + (e.extra_minute ?? 0) * 0.5) / end) * 100;
  // stack markers of one side that would overlap
  const rows = (side: MatchEvent["side"]) => {
    const placed: { e: MatchEvent; left: number; row: number }[] = [];
    for (const e of shown.filter((x) => x.side === side)) {
      const left = pos(e);
      let row = 0;
      while (placed.some((p) => p.row === row && Math.abs(p.left - left) < 2.2)) row++;
      placed.push({ e, left, row });
    }
    return placed;
  };
  const top = rows("home");
  const bottom = rows("away");
  const depth = (list: typeof top) => Math.max(1, ...list.map((p) => p.row + 1));

  return (
    <div className="border-t border-slate-100 px-4 py-4 sm:px-6">
      <div className="mb-2 flex items-center justify-between text-xs text-slate-500">
        <span className="font-medium uppercase tracking-wide">Spielverlauf</span>
        {events.some((e) => e.kind === "sub") && (
          <button type="button" onClick={() => setSubs(!subs)} className="text-emerald-700 hover:underline">
            {subs ? "Wechsel ausblenden" : "Wechsel einblenden"}
          </button>
        )}
      </div>

      {/* desktop: horizontal timeline */}
      <div className="hidden sm:block">
        <div className="relative" style={{ height: `${depth(top) * 22}px` }}>
          {top.map(({ e, left, row }, i) => (
            <span key={i} title={describe(e)} className="absolute -translate-x-1/2 cursor-default" style={{ left: `${left}%`, bottom: `${row * 22}px` }}>
              <Icon kind={e.kind} />
            </span>
          ))}
        </div>
        <div className="relative my-1 h-1.5 rounded-full bg-slate-200">
          <div className="absolute top-1/2 h-3 w-px -translate-y-1/2 bg-slate-400" style={{ left: `${(45 / end) * 100}%` }} title="Halbzeit" />
          {shown.filter((e) => e.score).map((e, i) => (
            <span key={i} className="absolute top-1/2 h-2.5 w-2.5 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-white bg-slate-900" style={{ left: `${pos(e)}%` }} />
          ))}
        </div>
        <div className="relative" style={{ height: `${depth(bottom) * 22}px` }}>
          {bottom.map(({ e, left, row }, i) => (
            <span key={i} title={describe(e)} className="absolute -translate-x-1/2 cursor-default" style={{ left: `${left}%`, top: `${row * 22}px` }}>
              <Icon kind={e.kind} />
            </span>
          ))}
        </div>
        <div className="mt-1 flex justify-between text-[10px] tabular-nums text-slate-400">
          <span>0&apos;</span><span style={{ marginLeft: `${(45 / end) * 100 - 4}%` }}>45&apos;</span><span className="ml-auto">90&apos;</span>
        </div>
        <div className="mt-1 flex justify-between text-[11px] text-slate-400"><span>oben: {home.name}</span><span>unten: {away.name}</span></div>
      </div>

      {/* events as a list (all screens; on desktop collapsed below the timeline) */}
      <ul className="mt-2 space-y-1 text-xs sm:mt-3 sm:columns-2 sm:gap-6">
        {shown.map((e, i) => (
          <li key={i} className={`flex break-inside-avoid items-center gap-2 ${e.side === "away" ? "flex-row-reverse text-right sm:flex-row sm:text-left" : ""}`}>
            <span className="w-9 shrink-0 tabular-nums text-slate-400">{minuteLabel(e)}</span>
            <span className="grid w-5 shrink-0 place-items-center"><Icon kind={e.kind} /></span>
            <span className="min-w-0 text-slate-700">
              {e.kind === "sub" ? <>{e.related} <span className="text-slate-400">für {e.player}</span></> : e.kind === "var" ? <>{VAR_DETAIL[e.detail ?? ""] ?? e.detail}{e.player ? <span className="text-slate-400"> ({e.player})</span> : null}</> : e.player}
              {e.score && <span className="ml-1 font-semibold tabular-nums text-slate-900">{e.score[0]}:{e.score[1]}</span>}
              <span className="ml-1 text-slate-400">
                <span className="hidden sm:inline">· </span>{e.kind === "own_goal" ? "Eigentor, zählt für " : ""}{e.side === "home" ? home.name : away.name}
              </span>
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}

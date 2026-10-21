"use client";

import { useState, type ReactNode } from "react";
import { TeamLogo } from "@/components/ui";
import type { MatchEvent, Team } from "@/lib/types";

const minuteLabel = (e: MatchEvent) => `${e.minute ?? "?"}${e.extra_minute ? `+${e.extra_minute}` : ""}'`;

const KIND_LABEL: Record<MatchEvent["kind"], string> = {
  goal: "Tor", penalty: "Tor (Elfmeter)", own_goal: "Eigentor", missed_penalty: "Elfmeter verschossen", yellow: "Gelbe Karte",
  second_yellow: "Gelb-Rote Karte", red: "Rote Karte", sub: "Wechsel", var: "Videobeweis",
};

/** Accent of the tooltip header per event kind. */
const KIND_TONE: Record<MatchEvent["kind"], string> = {
  goal: "bg-emerald-50 text-emerald-800", penalty: "bg-emerald-50 text-emerald-800", own_goal: "bg-rose-50 text-rose-800",
  missed_penalty: "bg-slate-100 text-slate-700", yellow: "bg-yellow-50 text-yellow-800", second_yellow: "bg-orange-50 text-orange-800",
  red: "bg-rose-50 text-rose-800", sub: "bg-sky-50 text-sky-800", var: "bg-slate-100 text-slate-700",
};

const VAR_DETAIL: Record<string, string> = {
  "Goal cancelled": "Tor aberkannt", "Goal confirmed": "Tor bestätigt", "Penalty confirmed": "Elfmeter bestätigt",
  "Penalty cancelled": "Elfmeter zurückgenommen", "Penalty awarded": "Elfmeter gegeben", "Card upgrade": "Karte verschärft",
  "Red card cancelled": "Rote Karte zurückgenommen", "Card reviewed": "Karte überprüft",
};

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

/** Card shown on hover (desktop) or tap (mobile) of a marker. */
function Tooltip({ e, team, left }: { e: MatchEvent; team: Team; left: number }) {
  const align = left < 18 ? "left-0" : left > 82 ? "right-0" : "left-1/2 -translate-x-1/2";
  let sub: ReactNode = null;
  if ((e.kind === "goal" || e.kind === "penalty") && e.related) sub = <>Vorlage: {e.related}</>;
  else if (e.kind === "own_goal") sub = <>zählt für {team.name}</>;
  else if (e.kind === "var") sub = <>{VAR_DETAIL[e.detail ?? ""] ?? e.detail}</>;
  return (
    <span
      role="tooltip"
      className={`pointer-events-none absolute bottom-full z-20 mb-2 w-56 overflow-hidden rounded-xl border border-slate-200 bg-white text-left opacity-0 shadow-lg ring-1 ring-black/5 transition duration-150 group-hover:opacity-100 group-focus:opacity-100 ${align}`}
    >
      <span className={`flex items-center gap-2 px-3 py-1.5 text-[11px] font-semibold ${KIND_TONE[e.kind]}`}>
        <span className="grid w-4 place-items-center"><Icon kind={e.kind} /></span>
        <span className="flex-1">{KIND_LABEL[e.kind]}</span>
        <span className="tabular-nums opacity-70">{minuteLabel(e)}</span>
      </span>
      <span className="block px-3 py-2">
        {e.kind === "sub" ? (
          <>
            <span className="flex items-center gap-1.5 text-sm font-semibold text-slate-900"><span className="text-emerald-600">▲</span>{e.related ?? "?"}</span>
            <span className="mt-0.5 flex items-center gap-1.5 text-xs text-slate-500"><span className="text-rose-500">▼</span>{e.player ?? "?"}</span>
          </>
        ) : (
          <>
            {e.player && <span className="block text-sm font-semibold text-slate-900">{e.player}</span>}
            {sub && <span className="mt-0.5 block text-xs text-slate-500">{sub}</span>}
          </>
        )}
      </span>
      <span className="flex items-center gap-2 border-t border-slate-100 bg-slate-50 px-3 py-1.5 text-[11px] text-slate-500">
        <TeamLogo team={team} size={14} />
        <span className="min-w-0 flex-1 truncate">{team.name}</span>
        {e.score && <span className="rounded bg-slate-900 px-1.5 py-0.5 font-semibold tabular-nums text-white">{e.score[0]}:{e.score[1]}</span>}
      </span>
    </span>
  );
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
      while (placed.some((p) => p.row === row && Math.abs(p.left - left) < 3)) row++;
      placed.push({ e, left, row });
    }
    return placed;
  };
  const top = rows("home");
  const bottom = rows("away");
  const depth = (list: typeof top) => Math.max(1, ...list.map((p) => p.row + 1));
  const marker = ({ e, left, row }: (typeof top)[number], i: number, edge: "bottom" | "top") => (
    <span
      key={i}
      tabIndex={0}
      aria-label={`${minuteLabel(e)} ${KIND_LABEL[e.kind]} ${e.player ?? ""}`}
      className="group absolute grid h-5 w-5 -translate-x-1/2 cursor-default place-items-center rounded outline-none transition hover:z-10 hover:scale-125 focus:z-10 focus:scale-125"
      style={{ left: `${left}%`, [edge]: `${row * 22}px` }}
    >
      <Icon kind={e.kind} />
      <Tooltip e={e} team={e.side === "home" ? home : away} left={left} />
    </span>
  );

  return (
    <div className="border-t border-slate-100 px-4 py-4 sm:px-6">
      <div className="mb-3 flex items-center justify-between text-xs text-slate-500">
        <span className="font-medium uppercase tracking-wide">Spielverlauf</span>
        {events.some((e) => e.kind === "sub") && (
          <button type="button" onClick={() => setSubs(!subs)} className="text-emerald-700 hover:underline">
            {subs ? "Wechsel ausblenden" : "Wechsel einblenden"}
          </button>
        )}
      </div>

      <div className="flex items-stretch gap-2 sm:gap-3">
        <div className="flex w-5 shrink-0 flex-col justify-between py-0.5">
          <TeamLogo team={home} size={18} />
          <TeamLogo team={away} size={18} />
        </div>
        <div className="min-w-0 flex-1">
          <div className="relative" style={{ height: `${depth(top) * 22}px` }}>
            {top.map((p, i) => marker(p, i, "bottom"))}
          </div>
          <div className="relative my-1 h-1.5 rounded-full bg-slate-200">
            <div className="absolute top-1/2 h-3 w-px -translate-y-1/2 bg-slate-400" style={{ left: `${(45 / end) * 100}%` }} title="Halbzeit" />
            {shown.filter((e) => e.score).map((e, i) => (
              <span key={i} className="absolute top-1/2 h-2.5 w-2.5 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-white bg-slate-900" style={{ left: `${pos(e)}%` }} />
            ))}
          </div>
          <div className="relative" style={{ height: `${depth(bottom) * 22}px` }}>
            {bottom.map((p, i) => marker(p, i, "top"))}
          </div>
          <div className="relative mt-1 h-3 text-[10px] tabular-nums text-slate-400">
            <span className="absolute left-0">0&apos;</span>
            <span className="absolute -translate-x-1/2" style={{ left: `${(45 / end) * 100}%` }}>45&apos;</span>
            <span className={`absolute ${end > 93 ? "-translate-x-1/2" : "-translate-x-full"}`} style={{ left: `${(90 / end) * 100}%` }}>90&apos;</span>
          </div>
        </div>
      </div>
    </div>
  );
}

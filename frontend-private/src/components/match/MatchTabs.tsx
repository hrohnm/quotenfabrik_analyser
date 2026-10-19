"use client";

import { useEffect, useState } from "react";
import type { FixtureDetail } from "@/lib/types";
import { MarketsPanel } from "./MarketsPanel";
import { PatternsPanel } from "./PatternsPanel";
import { ScorersPanel } from "./ScorersPanel";
import { StatsPanel } from "./StatsPanel";

const TABS = [
  { key: "maerkte", label: "Märkte" },
  { key: "torschuetzen", label: "Torschützen" },
  { key: "pattern", label: "Pattern" },
  { key: "statistik", label: "Statistik" },
];

export function MatchTabs({ data }: { data: FixtureDetail }) {
  const [tab, setTab] = useState("maerkte");
  // Keep the active tab in the URL hash so reloads and links keep it
  useEffect(() => {
    const hash = window.location.hash.slice(1);
    if (TABS.some((t) => t.key === hash)) setTab(hash);
  }, []);
  const select = (key: string) => {
    setTab(key);
    window.history.replaceState(null, "", `#${key}`);
  };
  const counts: Record<string, number | undefined> = {
    torschuetzen: data.scorers.length || undefined,
    pattern: data.patterns.filter((p) => p.signal !== null && p.group !== "scorers").length || undefined,
  };
  return (
    <div className="space-y-4">
      <div className="sticky top-[57px] z-10 -mx-4 border-b border-slate-200 bg-background/95 px-4 backdrop-blur">
        <nav className="flex gap-1 overflow-x-auto">
          {TABS.map((t) => (
            <button
              key={t.key}
              type="button"
              onClick={() => select(t.key)}
              className={`-mb-px flex items-center gap-1.5 whitespace-nowrap border-b-2 px-3 py-2.5 text-sm transition ${
                tab === t.key ? "border-slate-900 font-semibold text-slate-900" : "border-transparent text-slate-500 hover:text-slate-800"
              }`}
            >
              {t.label}
              {counts[t.key] !== undefined && <span className="rounded-full bg-slate-200 px-1.5 text-[10px] font-medium text-slate-600">{counts[t.key]}</span>}
            </button>
          ))}
        </nav>
      </div>
      {tab === "maerkte" && <MarketsPanel markets={data.markets} fixture={data.fixture} />}
      {tab === "torschuetzen" && <ScorersPanel data={data} />}
      {tab === "pattern" && <PatternsPanel patterns={data.patterns} fixture={data.fixture} />}
      {tab === "statistik" && <StatsPanel data={data} />}
    </div>
  );
}

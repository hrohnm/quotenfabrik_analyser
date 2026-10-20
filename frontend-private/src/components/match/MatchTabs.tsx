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
  // European cups: results only – no goalscorers, patterns or match statistics
  const tabs = data.fixture.cup ? TABS.filter((t) => t.key === "maerkte") : TABS;
  const counts: Record<string, number | undefined> = {
    torschuetzen: data.scorers.length || undefined,
    pattern: data.patterns.filter((p) => p.signal !== null && p.group !== "scorers").length || undefined,
  };
  return (
    <div className="space-y-4">
      <div className="sticky top-[57px] z-10 -mx-4 border-b border-slate-200 bg-background/95 px-4 backdrop-blur">
        <nav className="flex gap-1 overflow-x-auto">
          {tabs.map((t) => (
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
      {data.fixture.cup && (
        <p className="text-xs text-slate-500">
          Europapokal: Prognose aus der gemeinsamen Stärkeskala aller Ligen (Nachweis: docs/15_europapokal.md). Abgerechnet wird nach 90 Minuten;
          Torschützen, Pattern und Spielstatistik gibt es für Pokalspiele nicht.
        </p>
      )}
      {(tab === "maerkte" || data.fixture.cup) && <MarketsPanel markets={data.markets} fixture={data.fixture} />}
      {!data.fixture.cup && tab === "torschuetzen" && <ScorersPanel data={data} />}
      {!data.fixture.cup && tab === "pattern" && <PatternsPanel patterns={data.patterns} fixture={data.fixture} />}
      {!data.fixture.cup && tab === "statistik" && <StatsPanel data={data} />}
    </div>
  );
}

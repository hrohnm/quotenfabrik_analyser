"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { dayMonth, odd, pct, signedPct, time } from "@/lib/format";
import type { DayCombo } from "@/lib/types";
import { Card, OutcomeBadge, TeamLogo } from "@/components/ui";
import { Logo } from "@/components/Logo";
import { leagueLogo } from "@/lib/media";
import { BetDialog, type BetDraft } from "./BetDialog";
import { BetanoOdd } from "@/components/BetanoOdd";

const KIND_HINT: Record<DayCombo["kind"], string> = {
  tore: "Über x,5 Tore im Spiel",
  team_tore: "Über x,5 Tore einer Mannschaft",
  doppelte_chance: "1X, X2 oder 12",
};

/** Daily combos of ``day``: one Tore-Über, one Team-Tore-Über and one Doppelte-Chance combo, target odds 5–10. */
export function DayCombos({ day }: { day: string }) {
  const [combos, setCombos] = useState<DayCombo[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [draft, setDraft] = useState<BetDraft | null>(null);

  useEffect(() => {
    let current = true;  // ignore answers for a day the user already left
    setCombos(null);
    setError(null);
    api<DayCombo[]>("/combos", { date: day })
      .then((c) => current && setCombos(c))
      .catch((e) => current && setError(String(e instanceof Error ? e.message : e)));
    return () => { current = false; };
  }, [day]);

  const toDraft = (c: DayCombo): BetDraft => ({
    label: `Tageskombi ${c.label} ${dayMonth(day)}`,
    source: "tageskombi",
    odds: c.odds,
    realOdds: c.real_odds,
    probability: c.probability,
    legs: c.legs.map((l) => ({ fixture_id: l.fixture_id, market: l.market, selection: l.selection, line: l.line, label: `${l.home.name} – ${l.away.name}: ${l.label}`, probability: l.probability, odds: l.odds })),
  });

  return (
    <section className="space-y-3">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold">Tageskombis</h2>
          <p className="max-w-3xl text-sm text-slate-500">
            Pro Tag je eine Kombi aus Tore-Über-, Team-Tore-Über- und Doppelte-Chance-Tipps über alle Spiele, Zielquote 5–10.
            Die Kombis ziehen abwechselnd die jeweils besten Tipps und nutzen jedes Spiel möglichst nur einmal.
            Tipps mit sehr niedriger Quote (Standard: unter 1,20) werden ausgelassen. Quoten sind echte Betano-Quoten
            (<span className="rounded bg-orange-50 px-1 text-orange-700">orange</span>, grün = Modell sieht Vorteil); fehlt sie, ist sie geschätzt (≈, faire Quote abzüglich Marge).
          </p>
        </div>
      </div>
      {error && <p className="rounded-md bg-rose-50 p-3 text-sm text-rose-700">{error}</p>}
      {!combos && !error && <Card><p className="text-sm text-slate-400">Kombis werden berechnet …</p></Card>}
      {combos && combos.length === 0 && (
        <Card><p className="text-sm text-slate-500">An diesem Tag gibt es nicht genug passende Tipps für eine Kombi mit Quote 5–10.</p></Card>
      )}
      {combos && combos.length > 0 && (
        <div className="grid gap-4 lg:grid-cols-3">
          {combos.map((c) => (
            <Card
              key={c.kind}
              title={<span className="flex items-center gap-2">{c.label}<span className="text-xs font-normal text-slate-400">{KIND_HINT[c.kind]}</span></span>}
              actions={<OutcomeBadge outcome={c.outcome} />}
            >
              <ul className="space-y-2">
                {c.legs.map((l) => (
                  <li key={`${l.fixture_id}${l.market}`} className="flex items-center justify-between gap-2 text-sm">
                    <Link href={`/spiel/${l.fixture_id}`} className="min-w-0 hover:opacity-80">
                      <div className="flex items-center gap-1.5 text-xs text-slate-500">
                        <Logo src={l.league.logo ?? leagueLogo(l.league.id)} alt="Liga" size={12} />
                        <TeamLogo team={l.home} size={14} /><span className="truncate">{l.home.name}</span>
                        <span>–</span>
                        <TeamLogo team={l.away} size={14} /><span className="truncate">{l.away.name}</span>
                        <span className="shrink-0">· {time(l.kickoff)}</span>
                      </div>
                      <div className="font-medium">{l.label}</div>
                    </Link>
                    <span className="flex shrink-0 items-center gap-2 text-right tabular-nums">
                      <span className="flex flex-col items-end text-xs text-slate-500">
                        {pct(l.probability, 0)}
                        {l.odds_source === "betano" ? <BetanoOdd prices={{ betano: l.odds, pinnacle: l.pinnacle, edge: l.edge }} /> : <span title="geschätzte Quote">≈ {odd(l.odds)}</span>}
                      </span>
                      <OutcomeBadge outcome={l.outcome} small />
                    </span>
                  </li>
                ))}
              </ul>
              <div className="mt-4 flex items-end justify-between gap-2 border-t border-slate-100 pt-3">
                <div className="text-sm">
                  <div>{c.real_odds ? "Betano-Quote" : "Quote ca."} <b className="tabular-nums">{odd(c.odds)}</b></div>
                  <div className="text-xs text-slate-500">Modell-Chance {pct(c.probability)} · {c.legs.length} Tipps</div>
                  <div className={`text-xs ${c.probability * c.odds >= 1 ? "text-emerald-700" : "text-rose-700"}`} title="Modell-Chance × Quote − 1: Gewinn oder Verlust pro Euro Einsatz auf lange Sicht, wenn das Modell stimmt">
                    Erwartungswert laut Modell {signedPct(c.probability * c.odds - 1)}
                  </div>
                </div>
                <button type="button" onClick={() => setDraft(toDraft(c))} className="rounded-md bg-slate-900 px-3 py-1.5 text-xs text-white">Als Wette erfassen</button>
              </div>
            </Card>
          ))}
        </div>
      )}
      {draft && <BetDialog draft={draft} onClose={() => setDraft(null)} />}
    </section>
  );
}

"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { odd, pct } from "@/lib/format";
import type { BetSource } from "@/lib/types";
import { BetDialog, type BetDraft } from "./BetDialog";

/** One selection on the bet slip (from the 3 tips or the value tips). */
export type SlipLeg = {
  fixture_id: number;
  market: string;
  selection: string;
  line: number | null;
  label: string;
  match: string;
  kickoff: string;
  probability: number | null;
  odds: number | null;
  origin: "tipps" | "value";
};

const STORAGE = "qf.betslip";
const keyOf = (l: Pick<SlipLeg, "fixture_id" | "market" | "selection" | "line">) => `${l.fixture_id}|${l.market}|${l.selection}|${l.line ?? ""}`;

type Slip = { legs: SlipLeg[]; has: (l: SlipLeg) => boolean; toggle: (l: SlipLeg) => void; remove: (key: string) => void; clear: () => void };
const SlipContext = createContext<Slip | null>(null);

export function useBetSlip(): Slip | null {
  return useContext(SlipContext);
}

/** Bet slip shared by the Tipps and Value pages (kept in the browser), logged as single bets or one combo. */
export function BetSlipProvider({ children }: { children: ReactNode }) {
  const [legs, setLegs] = useState<SlipLeg[]>([]);
  useEffect(() => {
    try {
      const saved = localStorage.getItem(STORAGE);
      if (saved) setLegs(JSON.parse(saved));
    } catch {
      /* storage unavailable: start empty */
    }
  }, []);
  const save = useCallback((next: SlipLeg[]) => {
    setLegs(next);
    try {
      localStorage.setItem(STORAGE, JSON.stringify(next));
    } catch {
      /* storage unavailable: keep in memory */
    }
  }, []);
  const value = useMemo<Slip>(() => ({
    legs,
    has: (l) => legs.some((x) => keyOf(x) === keyOf(l)),
    toggle: (l) => save(legs.some((x) => keyOf(x) === keyOf(l)) ? legs.filter((x) => keyOf(x) !== keyOf(l)) : [...legs, l]),
    remove: (key) => setLegs((cur) => {
      const next = cur.filter((x) => keyOf(x) !== key);
      try { localStorage.setItem(STORAGE, JSON.stringify(next)); } catch { /* memory only */ }
      return next;
    }),
    clear: () => save([]),
  }), [legs, save]);
  return (
    <SlipContext.Provider value={value}>
      {children}
      <SlipPanel />
    </SlipContext.Provider>
  );
}

/** "+" button that puts a selection on the bet slip (✓ when it is on it). */
export function AddToSlip({ leg, className = "" }: { leg: SlipLeg; className?: string }) {
  const slip = useBetSlip();
  if (!slip) return null;
  const on = slip.has(leg);
  return (
    <button
      type="button"
      onClick={(e) => { e.preventDefault(); e.stopPropagation(); slip.toggle(leg); }}
      title={on ? "vom Wettschein nehmen" : "auf den Wettschein"}
      aria-pressed={on}
      className={`grid h-6 w-6 shrink-0 place-items-center rounded-full border text-sm font-semibold leading-none transition ${on ? "border-emerald-600 bg-emerald-600 text-white" : "border-slate-300 bg-white text-slate-500 hover:border-emerald-500 hover:text-emerald-700"} ${className}`}
    >
      {on ? "✓" : "+"}
    </button>
  );
}

function source(legs: SlipLeg[]): BetSource {
  const origins = new Set(legs.map((l) => l.origin));
  return origins.size > 1 ? "wettschein" : origins.has("value") ? "value" : "tipps";
}

function draftOf(legs: SlipLeg[]): BetDraft {
  const known = legs.every((l) => l.odds != null);
  const sameGame = new Set(legs.map((l) => l.fixture_id)).size < legs.length;
  const probability = sameGame || legs.some((l) => l.probability == null) ? null : legs.reduce((p, l) => p * (l.probability ?? 1), 1);
  return {
    label: legs.length === 1 ? `${legs[0].match}: ${legs[0].label}` : `Kombi aus ${legs.length} Tipps`,
    source: source(legs),
    odds: legs.reduce((o, l) => o * (l.odds ?? 1), 1),
    realOdds: known && !sameGame,
    probability,
    legs: legs.map((l) => ({ fixture_id: l.fixture_id, market: l.market, selection: l.selection, line: l.line, label: `${l.match}: ${l.label}`, probability: l.probability, odds: l.odds })),
  };
}

function SlipPanel() {
  const slip = useBetSlip();
  const [open, setOpen] = useState(false);
  const [draft, setDraft] = useState<{ bet: BetDraft; keys: string[] } | null>(null);
  const start = (ls: SlipLeg[]) => setDraft({ bet: draftOf(ls), keys: ls.map(keyOf) });
  // logged legs leave the slip, the others stay
  const saved = () => draft?.keys.forEach((k) => slip?.remove(k));
  const dialog = draft && <BetDialog draft={draft.bet} onClose={() => setDraft(null)} onSaved={saved} />;
  if (!slip || slip.legs.length === 0) return dialog || null;
  const legs = slip.legs;
  const product = legs.reduce((o, l) => o * (l.odds ?? 1), 1);
  const sameGame = new Set(legs.map((l) => l.fixture_id)).size < legs.length;
  return (
    <>
      <div className="fixed bottom-4 right-4 z-30 w-[22rem] max-w-[calc(100vw-2rem)]">
        {open ? (
          <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-xl ring-1 ring-black/5">
            <div className="flex items-center justify-between bg-slate-900 px-3 py-2 text-sm text-white">
              <span className="font-semibold">Wettschein · {legs.length} {legs.length === 1 ? "Tipp" : "Tipps"}</span>
              <button type="button" onClick={() => setOpen(false)} className="text-slate-300 hover:text-white" aria-label="einklappen">▾</button>
            </div>
            <ul className="max-h-72 divide-y divide-slate-100 overflow-y-auto text-sm">
              {legs.map((l) => (
                <li key={keyOf(l)} className="flex items-start gap-2 px-3 py-2">
                  <div className="min-w-0 flex-1">
                    <div className="truncate text-xs text-slate-500">{l.match}</div>
                    <div className="font-medium">{l.label}</div>
                    <div className="text-xs text-slate-400">{l.origin === "value" ? "Value-Tipp" : "Tipp"}{l.probability != null && ` · ${pct(l.probability, 0)}`}</div>
                  </div>
                  <span className="shrink-0 tabular-nums font-semibold">{odd(l.odds)}</span>
                  <button type="button" onClick={() => start([l])} className="shrink-0 text-xs text-emerald-700 hover:underline">einzeln</button>
                  <button type="button" onClick={() => slip.remove(keyOf(l))} className="shrink-0 text-slate-400 hover:text-rose-600" aria-label="entfernen">✕</button>
                </li>
              ))}
            </ul>
            <div className="space-y-2 border-t border-slate-100 bg-slate-50 px-3 py-2 text-sm">
              {legs.length > 1 && (
                <div className="flex items-center justify-between">
                  <span className="text-slate-600">Kombi-Quote {sameGame ? "(Einzelquoten multipliziert)" : ""}</span>
                  <span className="font-semibold tabular-nums">{odd(product)}</span>
                </div>
              )}
              {sameGame && <p className="text-xs text-amber-700">Mehrere Tipps aus einem Spiel: Bei Betano nur als Bet Builder, die Quote liegt dort niedriger.</p>}
              <div className="flex items-center justify-between gap-2">
                <button type="button" onClick={() => slip.clear()} className="text-xs text-slate-500 hover:text-rose-600">leeren</button>
                <button type="button" onClick={() => start(legs)} className="rounded-md bg-slate-900 px-3 py-1.5 text-xs font-medium text-white">
                  {legs.length === 1 ? "Als Wette erfassen" : "Als Kombi erfassen"}
                </button>
              </div>
            </div>
          </div>
        ) : (
          <button type="button" onClick={() => setOpen(true)} className="ml-auto flex items-center gap-2 rounded-full bg-slate-900 px-4 py-2 text-sm font-medium text-white shadow-lg">
            Wettschein <span className="rounded-full bg-emerald-500 px-2 text-xs">{legs.length}</span>
          </button>
        )}
      </div>
      {dialog}
    </>
  );
}

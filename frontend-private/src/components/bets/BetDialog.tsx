"use client";

import { useState } from "react";
import { apiSend } from "@/lib/api";
import { odd, pct } from "@/lib/format";
import type { BetSource, NewBetLeg } from "@/lib/types";

export type BetDraft = { label: string; source: BetSource; odds: number; realOdds?: boolean; probability: number | null; legs: NewBetLeg[] };

const parse = (v: string) => Number(v.replace(",", "."));

/** Logs a bet: stake and the bookmaker's actual odds (preset with the estimate). */
export function BetDialog({ draft, onClose, onSaved }: { draft: BetDraft; onClose: () => void; onSaved?: () => void }) {
  const [stake, setStake] = useState("10");
  const [odds, setOdds] = useState(draft.odds.toFixed(2).replace(".", ","));
  const [notes, setNotes] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  const stakeN = parse(stake);
  const oddsN = parse(odds);
  const valid = stakeN > 0 && oddsN > 1;
  const ev = valid && draft.probability != null ? stakeN * (draft.probability * oddsN - 1) : null;

  const save = async () => {
    setSaving(true);
    setError(null);
    try {
      await apiSend("POST", "/bets", { label: draft.label, source: draft.source, stake: stakeN, odds: oddsN, probability: draft.probability, notes: notes || null, legs: draft.legs });
      setSaved(true);
      onSaved?.();
    } catch (e) {
      setError(String(e instanceof Error ? e.message : e));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-40 grid place-items-center bg-slate-900/40 p-4" onClick={onClose}>
      <div className="max-h-[90vh] w-full max-w-lg overflow-y-auto rounded-xl bg-white p-5 shadow-xl" onClick={(e) => e.stopPropagation()}>
        <div className="mb-3 flex items-start justify-between gap-3">
          <div>
            <div className="text-xs font-medium uppercase tracking-wide text-slate-400">Wette erfassen</div>
            <div className="font-semibold">{draft.label}</div>
          </div>
          <button type="button" onClick={onClose} className="text-slate-400 hover:text-slate-700" aria-label="schließen">✕</button>
        </div>
        <ul className="mb-4 space-y-1 text-sm">
          {draft.legs.map((l, i) => (
            <li key={i} className="flex justify-between gap-3 border-b border-slate-100 pb-1">
              <span className="min-w-0">{l.label}</span>
              <span className="shrink-0 tabular-nums text-slate-500">{l.probability != null ? pct(l.probability, 0) : ""} {l.odds != null ? `· ${odd(l.odds)}` : ""}</span>
            </li>
          ))}
        </ul>
        {saved ? (
          <div className="space-y-3">
            <p className="rounded-md bg-emerald-50 p-3 text-sm text-emerald-800">Gespeichert. Die Wette wird nach Spielende automatisch abgerechnet (Seite „Wetten“).</p>
            <button type="button" onClick={onClose} className="rounded-md bg-slate-900 px-4 py-2 text-sm text-white">Schließen</button>
          </div>
        ) : (
          <>
            <div className="grid grid-cols-2 gap-3">
              <label className="text-xs font-medium text-slate-500">
                Einsatz (€)
                <input inputMode="decimal" value={stake} onChange={(e) => setStake(e.target.value)} className="mt-1 w-full rounded-md border border-slate-300 px-2 py-1.5 text-sm text-slate-900" />
              </label>
              <label className="text-xs font-medium text-slate-500">
                Quote bei Betano
                <input inputMode="decimal" value={odds} onChange={(e) => setOdds(e.target.value)} className="mt-1 w-full rounded-md border border-slate-300 px-2 py-1.5 text-sm text-slate-900" />
              </label>
            </div>
            <p className="mt-2 text-xs text-slate-500">
              {draft.realOdds
                ? <>Vorbelegt mit der aktuellen Betano-Quote {odd(draft.odds)} (Produkt der Einzelquoten) – vor der Abgabe auf dem Wettschein prüfen.</>
                : <>Vorbelegt mit der geschätzten Quote {odd(draft.odds)}{draft.source === "tipps" ? " (Bet Builder: Betano-Einzelquoten bereinigt um den Zusammenhang der Tipps)" : ""} – bitte die tatsächliche Quote vom Wettschein eintragen.</>}
              {draft.probability != null && <> Modell-Chance {pct(draft.probability)}{ev != null && <>, erwarteter Gewinn {ev.toFixed(2).replace(".", ",")} €</>}.</>}
            </p>
            <label className="mt-3 block text-xs font-medium text-slate-500">
              Notiz
              <input value={notes} onChange={(e) => setNotes(e.target.value)} className="mt-1 w-full rounded-md border border-slate-300 px-2 py-1.5 text-sm text-slate-900" />
            </label>
            {error && <p className="mt-3 rounded-md bg-rose-50 p-2 text-sm text-rose-700">{error}</p>}
            <div className="mt-4 flex justify-end gap-2">
              <button type="button" onClick={onClose} className="rounded-md border border-slate-300 px-4 py-2 text-sm">Abbrechen</button>
              <button type="button" disabled={!valid || saving} onClick={save} className="rounded-md bg-emerald-600 px-4 py-2 text-sm font-medium text-white disabled:opacity-40">
                {saving ? "speichert …" : "Wette speichern"}
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

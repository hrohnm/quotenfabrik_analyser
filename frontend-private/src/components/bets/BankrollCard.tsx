"use client";

import { useState } from "react";
import { apiSend } from "@/lib/api";
import { dateShort, signedPct } from "@/lib/format";
import type { Bankroll, BankrollTransaction } from "@/lib/types";
import { Card, StatTile } from "@/components/ui";

export const euro = (v: number | null | undefined) =>
  v === null || v === undefined ? "–" : `${v.toLocaleString("de-DE", { minimumFractionDigits: 2, maximumFractionDigits: 2 })} €`;

const parse = (v: string) => Number(v.trim().replace(",", "."));

const KIND_LABEL: Record<BankrollTransaction["kind"], string> = { start: "Startkapital", deposit: "Einzahlung", withdrawal: "Auszahlung" };

/** Bankroll of the current period: starting capital, deposits, withdrawals and the balance incl. bet profits. */
export function BankrollCard({ bankroll: b, transactions, onChanged, onError }: {
  bankroll: Bankroll; transactions: BankrollTransaction[]; onChanged: () => void; onError: (m: string) => void;
}) {
  const [kind, setKind] = useState<BankrollTransaction["kind"]>(b.configured ? "deposit" : "start");
  const [amount, setAmount] = useState("");
  const [note, setNote] = useState("");

  const add = async () => {
    const a = parse(amount);
    if (!(a > 0)) return;
    try {
      await apiSend("POST", "/bankroll", { kind, amount: a, note: note || null });
      setAmount("");
      setNote("");
      onChanged();
    } catch (e) {
      onError(String(e instanceof Error ? e.message : e));
    }
  };
  const remove = async (t: BankrollTransaction) => {
    if (!window.confirm(`${KIND_LABEL[t.kind]} über ${euro(t.amount)} löschen?`)) return;
    try {
      await apiSend("DELETE", `/bankroll/${t.id}`);
      onChanged();
    } catch (e) {
      onError(String(e instanceof Error ? e.message : e));
    }
  };

  return (
    <Card title="Bankroll">
      {b.configured ? (
        <div className="mb-4 grid grid-cols-2 gap-3 lg:grid-cols-4">
          <StatTile label="Kontostand" value={euro(b.balance)} hint={[`Start ${euro(b.start)}`, b.deposits ? `+${euro(b.deposits)} eingezahlt` : "", b.withdrawals ? `−${euro(b.withdrawals)} ausgezahlt` : ""].filter(Boolean).join(" · ")} />
          <StatTile label="Verfügbar" value={euro(b.available)} hint={b.open_stakes ? `${euro(b.open_stakes)} in offenen Wetten` : "keine offenen Wetten"} />
          <StatTile label="Gewinn aus Wetten" value={euro(b.profit)} tone={b.profit > 0 ? "good" : b.profit < 0 ? "bad" : undefined} />
          <StatTile label="Rendite auf Bankroll" value={b.roi != null ? signedPct(b.roi) : "–"} tone={(b.roi ?? 0) > 0 ? "good" : (b.roi ?? 0) < 0 ? "bad" : undefined}
            hint="Gewinn ÷ (Startkapital + Einzahlungen)" />
        </div>
      ) : (
        <p className="mb-3 text-sm text-slate-500">Trage dein Startkapital ein, dann siehst du Kontostand, verfügbares Guthaben und die Rendite auf deine Bankroll.</p>
      )}
      <div className="flex flex-wrap items-end gap-2">
        <label className="text-xs font-medium text-slate-500">
          Buchung
          <select value={kind} onChange={(e) => setKind(e.target.value as BankrollTransaction["kind"])} className="mt-1 block rounded-md border border-slate-300 bg-white px-2 py-1.5 text-sm text-slate-900">
            {(Object.keys(KIND_LABEL) as BankrollTransaction["kind"][]).map((k) => <option key={k} value={k}>{KIND_LABEL[k]}</option>)}
          </select>
        </label>
        <label className="w-28 text-xs font-medium text-slate-500">
          Betrag (€)
          <input inputMode="decimal" value={amount} onChange={(e) => setAmount(e.target.value)} className="mt-1 w-full rounded-md border border-slate-300 px-2 py-1.5 text-sm text-slate-900" />
        </label>
        <label className="min-w-40 flex-1 text-xs font-medium text-slate-500">
          Notiz
          <input value={note} onChange={(e) => setNote(e.target.value)} className="mt-1 w-full rounded-md border border-slate-300 px-2 py-1.5 text-sm text-slate-900" />
        </label>
        <button type="button" disabled={!(parse(amount) > 0)} onClick={add} className="rounded-md bg-slate-900 px-4 py-2 text-sm text-white disabled:opacity-40">buchen</button>
      </div>
      {transactions.length > 0 && (
        <table className="mt-4 w-full text-sm">
          <tbody className="divide-y divide-slate-100">
            {[...transactions].reverse().map((t) => (
              <tr key={t.id}>
                <td className="py-1.5 pr-2 text-xs tabular-nums text-slate-500">{dateShort(t.at)}</td>
                <td className="py-1.5 pr-2">{KIND_LABEL[t.kind]}</td>
                <td className="py-1.5 pr-2 text-slate-500">{t.note}</td>
                <td className={`py-1.5 pr-2 text-right font-semibold tabular-nums ${t.kind === "withdrawal" ? "text-rose-700" : ""}`}>
                  {t.kind === "withdrawal" ? "−" : "+"}{euro(t.amount)}
                </td>
                <td className="py-1.5 text-right"><button type="button" onClick={() => remove(t)} className="text-xs text-slate-400 hover:text-rose-700">löschen</button></td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </Card>
  );
}

/** New evaluation period: statistics and bankroll start over (earlier bets are kept unless deleted). */
export function ResetDialog({ onClose, onDone, onError }: { onClose: () => void; onDone: () => void; onError: (m: string) => void }) {
  const [capital, setCapital] = useState("");
  const [deleteBets, setDeleteBets] = useState(false);
  const [busy, setBusy] = useState(false);

  const reset = async () => {
    if (deleteBets && !window.confirm("Alle bisher erfassten Wetten endgültig löschen? Das lässt sich nicht rückgängig machen.")) return;
    setBusy(true);
    try {
      const c = parse(capital);
      await apiSend("POST", "/bets/reset", { delete_bets: deleteBets, start_capital: c > 0 ? c : null });
      onDone();
    } catch (e) {
      onError(String(e instanceof Error ? e.message : e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="fixed inset-0 z-40 grid place-items-center bg-slate-900/40 p-4" onClick={onClose}>
      <div className="w-full max-w-md rounded-xl bg-white p-5 shadow-xl" onClick={(e) => e.stopPropagation()}>
        <div className="mb-2 font-semibold">Auswertung zurücksetzen</div>
        <p className="text-sm text-slate-600">
          Ab jetzt beginnt ein neuer Zeitraum: Statistik, Gewinnverlauf und Bankroll zählen nur noch Wetten und Buchungen danach.
          Die bisherigen Wetten bleiben erhalten und sind über „frühere Wetten anzeigen“ weiter sichtbar.
        </p>
        <label className="mt-4 block text-xs font-medium text-slate-500">
          Startkapital für den neuen Zeitraum (optional, €)
          <input inputMode="decimal" value={capital} onChange={(e) => setCapital(e.target.value)} className="mt-1 w-full rounded-md border border-slate-300 px-2 py-1.5 text-sm text-slate-900" />
        </label>
        <label className="mt-3 flex items-center gap-2 text-sm text-slate-700">
          <input type="checkbox" checked={deleteBets} onChange={(e) => setDeleteBets(e.target.checked)} />
          bisherige Wetten endgültig löschen
        </label>
        <div className="mt-5 flex justify-end gap-2">
          <button type="button" onClick={onClose} className="rounded-md border border-slate-300 px-4 py-2 text-sm">Abbrechen</button>
          <button type="button" disabled={busy} onClick={reset} className="rounded-md bg-rose-600 px-4 py-2 text-sm font-medium text-white disabled:opacity-40">
            {busy ? "setzt zurück …" : "Zurücksetzen"}
          </button>
        </div>
      </div>
    </div>
  );
}

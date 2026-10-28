"use client";

import { useCallback, useEffect, useState } from "react";
import { api } from "@/lib/api";
import { dateShort, time } from "@/lib/format";
import { Card } from "@/components/ui";
import { Logo } from "@/components/Logo";
import { leagueLogo } from "@/lib/media";
import type { OddsArchive } from "./types";

const share = (n: number, of: number) => (of ? `${Math.round((n / of) * 100)} %` : "–");

function Coverage({ n, of }: { n: number; of: number }) {
  const p = of ? n / of : 0;
  const tone = p >= 0.8 ? "bg-emerald-500" : p >= 0.4 ? "bg-amber-400" : "bg-rose-400";
  return (
    <span className="flex items-center justify-end gap-2" title={`${n} von ${of}`}>
      <span className="tabular-nums">{n}<span className="text-slate-400">/{of}</span></span>
      <span className="h-1.5 w-12 overflow-hidden rounded-full bg-slate-100"><span className={`block h-full ${tone}`} style={{ width: `${p * 100}%` }} /></span>
    </span>
  );
}

const duration = (minutes: number) => (minutes >= 90 ? `${Math.round(minutes / 6) / 10} Stunden`.replace(".", ",") : `${minutes} Minuten`);
const size = (mb: number) => (mb >= 1000 ? `${(mb / 1000).toFixed(1).replace(".", ",")} GB` : `${mb} MB`);

/** Betano/Pinnacle odds archive per league: coverage since January 2026, gaps, backfill and refit. */
export function OddsArchiveCard({ jobRunning, onStart }: { jobRunning: boolean; onStart: (kind: "odds_backfill" | "refit", leagueId?: number) => void }) {
  const [data, setData] = useState<OddsArchive | null>(null);
  const [error, setError] = useState<string | null>(null);
  const load = useCallback((fresh = false) => {
    api<OddsArchive>("/admin/odds-archive", fresh ? { fresh: "true" } : {}).then(setData).catch((e) => setError(String(e)));
  }, []);
  useEffect(() => { load(); }, [load, jobRunning]);

  const warnings = data?.leagues.flatMap((l) => l.warnings.map((w) => `${l.name}: ${w}`)) ?? [];
  const b = data?.backfill;
  return (
    <Card
      title="Quotenarchiv (Betano / Pinnacle über OddsPapi)"
      actions={<button type="button" onClick={() => load(true)} className="text-xs text-slate-500 hover:text-slate-900">aktualisieren</button>}
    >
      {error && <p className="mb-3 text-sm text-rose-700">{error}</p>}
      {!data ? (
        <p className="text-sm text-slate-400">Archiv wird geprüft …</p>
      ) : (
        <div className="space-y-4">
          <p className="text-sm text-slate-500">
            Quotenverläufe gibt es bei OddsPapi ab {dateShort(`${data.since}T12:00:00Z`)}. Der Cron lädt alle 3 Stunden kommende Spiele und die letzten {data.history_days} Tage
            (Einstellung „OddsPapi: Quotenverläufe zurück“). Ältere Spiele neuer Ligen fehlen, bis sie nachgeladen werden – ohne sie bleiben CLV- und
            Value-Backtest klein.
          </p>
          {warnings.length > 0 && (
            <ul className="space-y-1 rounded-lg bg-amber-50 px-3 py-2 text-sm text-amber-800">
              {warnings.map((w) => <li key={w}>⚠ {w}</li>)}
            </ul>
          )}
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs text-slate-400">
                  <th className="pb-2 font-medium">Liga</th>
                  <th className="pb-2 text-right font-medium" title="Beendete Spiele seit 01/2026 mit Betano-Verlauf">Betano</th>
                  <th className="pb-2 text-right font-medium" title="… mit Pinnacle-Verlauf (Referenz für faire Preise)">Pinnacle</th>
                  <th className="pb-2 text-right font-medium" title="Verknüpft, aber Verlauf noch nicht geladen">Nachzuladen</th>
                  <th className="pb-2 text-right font-medium" title="Geladen, OddsPapi hatte keine Daten">Ohne Daten</th>
                  <th className="pb-2 text-right font-medium" title="Kommende Spiele (14 Tage) mit Betano-Quote">Kommend</th>
                  <th className="pb-2 text-right font-medium">Letzter Abruf</th>
                  <th className="pb-2" />
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {data.leagues.map((l) => (
                  <tr key={l.id} className={l.tournament ? "" : "text-slate-400"}>
                    <td className="py-1.5 pr-2">
                      <span className="flex items-center gap-2"><Logo src={leagueLogo(l.id)} alt={l.name} size={18} /><span className="truncate">{l.name}</span></span>
                    </td>
                    <td className="py-1.5"><Coverage n={l.with_betano} of={l.finished} /></td>
                    <td className="py-1.5 text-right tabular-nums text-slate-500">{share(l.with_pinnacle, l.finished)}</td>
                    <td className={`py-1.5 text-right tabular-nums ${l.to_load ? "font-semibold text-amber-700" : "text-slate-400"}`}>{l.to_load || "–"}</td>
                    <td className="py-1.5 text-right tabular-nums text-slate-400">{l.no_data || "–"}</td>
                    <td className="py-1.5 text-right tabular-nums">{l.upcoming_betano}<span className="text-slate-400">/{l.upcoming}</span></td>
                    <td className="whitespace-nowrap py-1.5 text-right tabular-nums text-slate-500">{l.last_sync ? `${dateShort(l.last_sync)} ${time(l.last_sync)}` : "–"}</td>
                    <td className="py-1.5 pl-2 text-right">
                      {l.to_load > 0 && (
                        <button type="button" disabled={jobRunning} onClick={() => onStart("odds_backfill", l.id)} className="text-xs text-emerald-700 hover:underline disabled:opacity-40">
                          nachladen
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="grid gap-3 md:grid-cols-2">
            <div className="rounded-lg border border-slate-200 p-3 text-sm">
              <div className="font-medium">Alle fehlenden Verläufe nachladen</div>
              {b && b.fixtures > 0 ? (
                <p className="mt-1 text-slate-500">
                  {b.fixtures.toLocaleString("de-DE")} Spiele · ca. {duration(b.minutes)} (5 s pro Spiel, kostenloser Endpunkt) · ca. {size(b.megabytes)} zusätzlicher
                  Speicher in der Datenbank (Rohdaten + Preisverläufe; auch die Backups wachsen). Läuft im Hintergrund, ein Abbruch setzt beim nächsten Mal fort.
                </p>
              ) : (
                <p className="mt-1 text-slate-500">Alle verknüpften Spiele seit 01/2026 sind geladen.</p>
              )}
              <button type="button" disabled={jobRunning || !b?.fixtures} onClick={() => onStart("odds_backfill")} className="mt-2 rounded-md bg-slate-900 px-3 py-1.5 text-xs font-medium text-white disabled:opacity-40">
                Alle nachladen
              </button>
            </div>
            <div className="rounded-lg border border-slate-200 p-3 text-sm">
              <div className="font-medium">Modelle mit den neuen Quoten neu rechnen</div>
              <p className="mt-1 text-slate-500">
                {data.model_fitted_at ? `Tippschein-Modell zuletzt trainiert am ${dateShort(data.model_fitted_at)}. ` : "Tippschein-Modell noch nicht trainiert. "}
                {data.new_since_fit > 0 ? `Seitdem ${data.new_since_fit} Spiele mit neuen Quoten.` : "Seitdem keine neuen Quoten."} Neu gerechnet werden das
                Tippschein-Modell und die Berichte zu CLV und Value-Tipps (einige Minuten; montags automatisch).
              </p>
              <button type="button" disabled={jobRunning} onClick={() => onStart("refit")}
                className={`mt-2 rounded-md px-3 py-1.5 text-xs font-medium disabled:opacity-40 ${data.new_since_fit > 50 || !data.model_fitted_at ? "bg-emerald-600 text-white" : "border border-slate-300 bg-white text-slate-700"}`}>
                Jetzt neu rechnen
              </button>
            </div>
          </div>
          {data.computed_at && <p className="text-xs text-slate-400">Stand {time(data.computed_at)} Uhr</p>}
        </div>
      )}
    </Card>
  );
}

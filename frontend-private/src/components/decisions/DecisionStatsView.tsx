"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { num, odd, pct, seasonLabel, signedPct } from "@/lib/format";
import type { DecisionStats } from "@/lib/types";
import { Card, StatTile } from "@/components/ui";

const COLORS = ["bg-rose-600", "bg-rose-500", "bg-orange-500", "bg-amber-400", "bg-sky-400", "bg-sky-600", "bg-emerald-600"];

/** Evaluation of the Tippschein: hit rate per decision against the model's expectation and a naive reference. */
export function DecisionStatsView({ league }: { league?: string }) {
  const [data, setData] = useState<DecisionStats | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    setData(null);
    api<DecisionStats>("/stats/decisions", { league: league || undefined }).then(setData).catch((e) => setError(String(e)));
  }, [league]);

  if (error) return <p className="rounded-md bg-rose-50 p-3 text-sm text-rose-700">{error}</p>;
  if (!data) return <Card><p className="text-sm text-slate-400">Auswertung wird berechnet …</p></Card>;
  if (!data.fixtures || !data.decisions) return <Card><p className="text-sm text-slate-500">Noch keine abgerechneten Spiele.</p></Card>;
  const dist = data.correct_per_fixture ?? {};
  return (
    <div className="space-y-4">
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatTile label="Richtig je Spiel" value={`${num(data.mean_correct ?? null, 1)} von 6`} hint={`${data.fixtures.toLocaleString("de-DE")} abgerechnete Spiele`} />
        <StatTile label="Alle 6 richtig" value={pct(dist["6"] ?? null, 0)} hint={`5 von 6: ${pct(dist["5"] ?? null, 0)} · 4 von 6: ${pct(dist["4"] ?? null, 0)}`} />
        <StatTile label="Entscheidungen getroffen" value={pct(data.total?.hit_rate ?? null)} hint={`Modell erwartet ${pct(data.total?.expected ?? null)}`} />
        <StatTile
          label="Einzeln zur Betano-Quote"
          value={<span className={(data.betano?.roi ?? 0) > 0 ? "text-emerald-700" : "text-rose-700"}>{signedPct(data.betano?.roi ?? null)}</span>}
          hint={data.betano ? `${data.betano.n.toLocaleString("de-DE")} Entscheidungen mit Quote · Ø ${odd(data.betano.odds)}` : "noch keine Betano-Quoten"}
        />
      </div>

      <Card title="Je Entscheidung">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-xs text-slate-400">
                <th className="pb-2 font-medium">Entscheidung</th>
                <th className="pb-2 font-medium">Modell tippt</th>
                <th className="pb-2 text-right font-medium">Getroffen</th>
                <th className="pb-2 text-right font-medium">Erwartet</th>
                <th className="pb-2 text-right font-medium" title="Immer das Ergebnis, das in den Vorsaisons am häufigsten war (gleiche Spiele ab der 2. Saison)">Immer häufigstes</th>
                <th className="pb-2 text-right font-medium" title="Modell minus „immer häufigstes“ auf denselben Spielen">Vorsprung</th>
                <th className="pb-2 text-right font-medium" title="Gewinn je Einsatz zur letzten Betano-Quote vor Anpfiff">Betano-ROI</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {data.decisions.map((d) => {
                const total = Object.values(d.picked).reduce((a, b) => a + b, 0) || 1;
                const lead = d.reference ? d.reference.model - d.reference.hit_rate : null;
                return (
                  <tr key={d.key}>
                    <td className="py-1.5 pr-2">{d.label}</td>
                    <td className="py-1.5 pr-2 text-xs text-slate-500">
                      {Object.entries(d.picked).filter(([, n]) => n > 0).map(([lbl, n]) => `${lbl} ${pct(n / total, 0)}`).join(" · ")}
                    </td>
                    <td className="py-1.5 text-right font-semibold tabular-nums">{pct(d.hit_rate)}</td>
                    <td className="py-1.5 text-right tabular-nums text-slate-500">{pct(d.expected)}</td>
                    <td className="py-1.5 text-right tabular-nums text-slate-500">{pct(d.reference?.hit_rate ?? null)}</td>
                    <td className={`whitespace-nowrap py-1.5 text-right tabular-nums ${lead == null ? "" : lead > 0.005 ? "text-emerald-700" : lead < -0.005 ? "text-rose-700" : "text-slate-500"}`}>
                      {lead == null ? "–" : `${lead >= 0 ? "+" : "−"}${Math.abs(lead * 100).toFixed(1).replace(".", ",")} Pkt.`}
                    </td>
                    <td className={`whitespace-nowrap py-1.5 text-right tabular-nums ${(d.betano?.roi ?? 0) > 0 ? "text-emerald-700" : "text-rose-700"}`} title={d.betano ? `${d.betano.n} mit Quote, Ø ${odd(d.betano.odds)}` : undefined}>
                      {signedPct(d.betano?.roi ?? null)}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
        <p className="mt-3 text-xs text-slate-500">
          Das Modell tippt immer die wahrscheinlichere Seite (ab 50 %). Wo es fast immer „Ja“ sagt, entspricht der Tippschein „immer Ja“ – echten
          Mehrwert zeigt nur ein positiver Vorsprung gegenüber „immer häufigstes Ergebnis“.
        </p>
      </Card>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card title="Wie viele der 6 Entscheidungen stimmen?">
          <div className="flex h-8 overflow-hidden rounded-lg text-xs font-medium text-white">
            {["0", "1", "2", "3", "4", "5", "6"].map((k, i) => (
              <div key={k} className={COLORS[i]} style={{ width: `${(dist[k] ?? 0) * 100}%` }} title={`${k} von 6: ${pct(dist[k] ?? null)}`}>
                {(dist[k] ?? 0) > 0.06 && <span className="grid h-full place-items-center">{pct(dist[k] ?? null, 0)}</span>}
              </div>
            ))}
          </div>
          <div className="mt-2 flex justify-between text-xs text-slate-500"><span>0 von 6</span><span>3</span><span>6 von 6</span></div>
        </Card>
        <Card title="Saison für Saison">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs text-slate-400">
                  <th className="pb-2 font-medium">Saison</th>
                  <th className="pb-2 text-right font-medium">Gesamt</th>
                  <th className="pb-2 text-right font-medium">Sieger</th>
                  <th className="pb-2 text-right font-medium">Ü 1,5</th>
                  <th className="pb-2 text-right font-medium">Ü 2,5</th>
                  <th className="pb-2 text-right font-medium">BT</th>
                  <th className="pb-2 text-right font-medium">1. HZ</th>
                  <th className="pb-2 text-right font-medium">2. HZ</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {(data.seasons ?? []).map((s) => (
                  <tr key={s.season}>
                    <td className="py-1.5">{seasonLabel(s.season)}</td>
                    <td className="py-1.5 text-right font-semibold tabular-nums">{pct(s.hit_rate, 0)}</td>
                    {["winner", "o15", "o25", "btts", "goal_1h", "goal_2h"].map((k) => (
                      <td key={k} className="py-1.5 text-right tabular-nums text-slate-600">{pct(s[k] as number | null, 0)}</td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      </div>
    </div>
  );
}

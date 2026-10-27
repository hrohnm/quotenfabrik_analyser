"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { num, odd, pct, seasonLabel, signedPct } from "@/lib/format";
import type { DecisionStats } from "@/lib/types";
import { Segmented } from "@/components/match/Segmented";
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
        <StatTile
          label="Tipps getroffen"
          value={pct(data.tipped?.hit_rate ?? data.total?.hit_rate ?? null)}
          hint={data.tipped ? `immer häufigstes Ergebnis ${pct(data.tipped.reference)} · Modell erwartet ${pct(data.tipped.expected)}` : `Modell erwartet ${pct(data.total?.expected ?? null)}`}
        />
        <StatTile label="Tipps je Spiel" value={`${num(data.tips_per_fixture ?? null, 1)} von 6`} hint={`${pct(data.tipped?.share ?? null, 0)} der Entscheidungen · ${data.fixtures.toLocaleString("de-DE")} Spiele`} />
        <StatTile label="Alle Tipps eines Spiels richtig" value={pct(data.all_tips_right ?? null, 0)} hint={`ohne Konfidenz-Filter alle 6 richtig: ${pct(dist["6"] ?? null, 0)}`} />
        <StatTile
          label="Einzeln zur Betano-Quote"
          value={<span className={(data.betano?.roi ?? 0) > 0 ? "text-emerald-700" : "text-rose-700"}>{signedPct(data.betano?.roi ?? null)}</span>}
          hint={data.betano ? `alle Entscheidungen, ${data.betano.n.toLocaleString("de-DE")} mit Quote · Ø ${odd(data.betano.odds)}` : "noch keine Betano-Quoten"}
        />
      </div>

      <Card title="Je Entscheidung (nur getippte)">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-xs text-slate-400">
                <th className="pb-2 font-medium">Entscheidung</th>
                <th className="pb-2 text-right font-medium" title="Anteil der Spiele mit Tipp (Konfidenz ≥ Mindest-Konfidenz)">Getippt</th>
                <th className="pb-2 text-right font-medium">Getroffen</th>
                <th className="pb-2 text-right font-medium">Erwartet</th>
                <th className="pb-2 text-right font-medium" title="Immer das Ergebnis, das in den Vorsaisons am häufigsten war – auf denselben Spielen">Immer häufigstes</th>
                <th className="pb-2 text-right font-medium" title="Alle Spiele, ohne Konfidenz-Filter">Ohne Filter</th>
                <th className="pb-2 pl-3 font-medium" title="In wie vielen Spielen das Modell welche Seite gewählt hat – keine Wahrscheinlichkeit">Gewählte Seite (Anteil der Spiele)</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {data.decisions.map((d) => {
                const total = Object.values(d.picked).reduce((a, b) => a + b, 0) || 1;
                const t = d.tipped;
                // without decision model (no confidence yet): all decisions count, reference over all fixtures
                const reference = t?.reference ?? d.reference?.hit_rate ?? null;
                const lead = t ? (t.hit_rate != null && t.reference != null ? t.hit_rate - t.reference : null) : d.reference ? d.reference.model - d.reference.hit_rate : null;
                return (
                  <tr key={d.key}>
                    <td className="py-1.5 pr-2">{d.label}</td>
                    <td className="py-1.5 text-right tabular-nums text-slate-500">{pct(t?.share ?? null, 0)}</td>
                    <td className="py-1.5 text-right font-semibold tabular-nums">{pct(t?.hit_rate ?? d.hit_rate)}</td>
                    <td className="py-1.5 text-right tabular-nums text-slate-500">{pct(t?.expected ?? d.expected)}</td>
                    <td className="whitespace-nowrap py-1.5 text-right tabular-nums text-slate-500">
                      {pct(reference)}
                      {lead != null && Math.abs(lead) >= 0.005 && <span className={`ml-1 text-xs ${lead > 0 ? "text-emerald-700" : "text-rose-700"}`}>({lead > 0 ? "+" : "−"}{Math.abs(lead * 100).toFixed(1).replace(".", ",")})</span>}
                    </td>
                    <td className="py-1.5 text-right tabular-nums text-slate-500">{pct(d.hit_rate)}</td>
                    <td className="py-1.5 pl-3 text-xs text-slate-500">
                      {Object.entries(d.picked).filter(([, n]) => n > 0).map(([lbl, n]) => `${lbl} ${pct(n / total, 0)}`).join(" · ")}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
        {data.decisions.every((d) => !d.tipped) && (
          <p className="mt-3 rounded-md bg-amber-50 px-3 py-2 text-xs text-amber-800">
            Noch kein Entscheidungsmodell trainiert: Es gibt keine Konfidenz, daher wird jede Entscheidung getippt. Einmalig <code>qf model decisions</code>{" "}
            ausführen (danach läuft es montags per Cron).
          </p>
        )}
        <p className="mt-3 text-xs text-slate-500">
          „Gewählte Seite“ ist der Anteil der Spiele, nicht die Sicherheit: Über 1,5 Tore und ein Tor je Halbzeit fallen so häufig (in der Bundesliga rund 74–83 %
          der Spiele), dass das Modell selbst im torärmsten Duell noch über 50 % für „Ja“ sieht – „Nein“ wird deshalb praktisch nie gewählt. Getippt wird nur ab der Mindest-Konfidenz (Einstellungen → Tippschein). Bei „Ja“-lastigen Entscheidungen (Über 1,5, Tor in einer Halbzeit) entspricht der
          Tipp fast immer „immer Ja“ – die Konfidenz wählt dort die Spiele aus, in denen „Ja“ besonders wahrscheinlich ist.
        </p>
      </Card>

      <ConfidenceCurves decisions={data.decisions} />

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

/** Hit rate by minimum confidence per decision: how much surer the tips get when fewer are made. */
function ConfidenceCurves({ decisions }: { decisions: NonNullable<DecisionStats["decisions"]> }) {
  const [key, setKey] = useState(decisions[0]?.key ?? "winner");
  const d = decisions.find((x) => x.key === key) ?? decisions[0];
  if (!d || d.curve.length === 0) return null;
  return (
    <Card
      title="Trefferquote nach Mindest-Konfidenz"
      actions={<Segmented options={decisions.map((x) => ({ key: x.key, label: x.label.replace("Tor in der ", "Tor ").replace(" Halbzeit", " HZ") }))} value={key} onChange={setKey} size="sm" />}
    >
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-xs text-slate-400">
              <th className="pb-2 font-medium">Mindest-Konfidenz</th>
              <th className="pb-2 text-right font-medium">Getippt</th>
              <th className="pb-2 font-medium" />
              <th className="pb-2 text-right font-medium">Getroffen</th>
              <th className="pb-2 text-right font-medium">Erwartet</th>
              <th className="pb-2 text-right font-medium">Immer häufigstes</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {d.curve.map((c) => (
              <tr key={c.min_confidence}>
                <td className="py-1.5 tabular-nums">{c.min_confidence === 0 ? "alle" : `ab ${c.min_confidence}`}</td>
                <td className="py-1.5 text-right tabular-nums text-slate-500">{pct(c.share, 0)}</td>
                <td className="w-40 py-1.5 pl-3">
                  <div className="h-2 overflow-hidden rounded-full bg-slate-100"><div className="h-full bg-emerald-500" style={{ width: `${(c.hit_rate ?? 0) * 100}%` }} /></div>
                </td>
                <td className="py-1.5 text-right font-semibold tabular-nums">{pct(c.hit_rate)}</td>
                <td className="py-1.5 text-right tabular-nums text-slate-500">{pct(c.expected)}</td>
                <td className="py-1.5 text-right tabular-nums text-slate-500">{pct(c.reference)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  );
}

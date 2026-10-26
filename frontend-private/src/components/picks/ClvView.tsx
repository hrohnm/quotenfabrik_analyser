"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { dateShort, odd, pct, signedPct } from "@/lib/format";
import type { ClvResult, ClvRow } from "@/lib/types";
import { Card, StatTile } from "@/components/ui";

const tone = (v: number | null | undefined) => (v == null ? "" : v > 0 ? "text-emerald-700" : v < 0 ? "text-rose-700" : "");

/** Verdict like the report (docs/23_clv.md): distance to the odds-matched baseline in standard errors. */
function verdict(r: ClvRow): string {
  if (!r.n || r.delta == null || !r.clv_se) return "Noch zu wenig Daten für eine Aussage.";
  const z = r.delta / r.clv_se;
  if ((r.clv ?? 0) > 0 && z >= 2) return "Positiver CLV und deutlich über der Vergleichsgruppe: Hinweis auf einen echten Vorteil gegenüber dem Markt.";
  if (z >= 2) return "Die Tipps schlagen Auswahlen gleicher Quotenhöhe deutlich – das Modell erkennt die Richtung, in die sich der Markt bewegt. Nach der Betano-Marge liegen sie aber noch unter dem fairen Schlusspreis: ohne Value-Filter kein Gewinn zu erwarten.";
  if (z <= -2) return "Die Tipps liegen deutlich unter der Vergleichsgruppe: Der Markt bewegt sich gegen die Tipps.";
  return "Kein belastbarer Unterschied zu Auswahlen gleicher Quotenhöhe.";
}

/** Closing line value of the picks: Betano odds when a pick was published against the fair closing price. */
export function ClvView() {
  const [data, setData] = useState<ClvResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => { api<ClvResult>("/stats/clv").then(setData).catch((e) => setError(String(e))); }, []);

  if (error) return <p className="rounded-md bg-rose-50 p-3 text-sm text-rose-700">{error}</p>;
  if (!data) return <Card><p className="text-sm text-slate-400">CLV wird berechnet …</p></Card>;
  if (!data.picks || !data.total) return <Card><p className="text-sm text-slate-500">Noch keine Tipps mit Betano-Quotenverlauf.</p></Card>;
  const t = data.total;
  return (
    <div className="space-y-4">
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatTile label="CLV der Tipps" value={<span className={tone(t.clv)}>{signedPct(t.clv)}</span>} hint={`± ${pct(t.clv_se)} · ${t.n.toLocaleString("de-DE")} Tipps, ${t.fixtures} Spiele`} />
        <StatTile label="Auswahlen gleicher Quote" value={signedPct(t.baseline)} hint="alle Auswahlen derselben Märkte, gewichtet auf die Quoten der Tipps" />
        <StatTile label="Abstand" value={<span className={tone(t.delta)}>{signedPct(t.delta)}</span>} hint={t.delta != null && t.clv_se ? `${(t.delta / t.clv_se).toFixed(1).replace(".", ",")} Standardfehler` : undefined} />
        <StatTile label="Quote fiel nach dem Tipp" value={pct(t.beat_close ?? null, 0)} hint={`stieg bei ${pct(t.worse_close ?? null, 0)} · Ø Quote ${odd(t.odds)}`} />
      </div>
      <p className="rounded-lg bg-slate-50 px-3 py-2 text-sm text-slate-700">{verdict(t)}</p>
      <div className="grid gap-4 lg:grid-cols-2">
        <ClvTable title="Quelle" rows={[...(data.sources ?? []), ...(data.value ? [{ ...data.value, label: "nur Tipps mit Modell-EV > 0" }] : [])]} />
        <ClvTable title="Profil" rows={data.profiles ?? []} />
        <ClvTable title="Marktgruppe" rows={data.groups ?? []} />
        <ClvTable title="Vorlauf bis Anpfiff" rows={data.leads ?? []} />
        <ClvTable title="Liga" rows={data.leagues ?? []} />
      </div>
      <p className="text-xs text-slate-500">
        CLV = Betano-Quote zum Zeitpunkt des Tipps × Pinnacle-Wahrscheinlichkeit ohne Marge beim Anpfiff − 1. Live-Tipps zählen ab dem Fixieren
        des Tages, Backtest-Tipps ab dem ersten Anpfiff des Spieltags (Modell kennt nur Spiele davor). Alle Ligen
        {data.from && data.to ? `, Spiele vom ${dateShort(data.from)} bis ${dateShort(data.to)}` : ""} · Bericht: docs/23_clv.md.
      </p>
    </div>
  );
}

function ClvTable({ title, rows }: { title: string; rows: ClvRow[] }) {
  if (rows.length === 0) return null;
  return (
    <Card title={`Nach ${title}`}>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-xs text-slate-400">
              <th className="pb-2 font-medium">{title}</th>
              <th className="pb-2 text-right font-medium">Tipps</th>
              <th className="pb-2 text-right font-medium">Ø Quote</th>
              <th className="pb-2 text-right font-medium">CLV</th>
              <th className="pb-2 text-right font-medium" title="CLV minus Auswahlen gleicher Quotenhöhe">Abstand</th>
              <th className="pb-2 text-right font-medium" title="Gewinn je Einsatz zur genommenen Quote (abgerechnete Tipps)">ROI</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {rows.map((r) => (
              <tr key={String(r.key) + r.label}>
                <td className="py-1.5">{r.label}</td>
                <td className="py-1.5 text-right tabular-nums">{r.n.toLocaleString("de-DE")}</td>
                <td className="py-1.5 text-right tabular-nums">{odd(r.odds)}</td>
                <td className={`whitespace-nowrap py-1.5 text-right font-semibold tabular-nums ${tone(r.clv)}`}>{signedPct(r.clv)}</td>
                <td className={`whitespace-nowrap py-1.5 text-right tabular-nums ${tone(r.delta)}`} title={r.clv_se ? `± ${pct(r.clv_se)}` : undefined}>{signedPct(r.delta)}</td>
                <td className={`whitespace-nowrap py-1.5 text-right tabular-nums ${tone(r.roi)}`}>{signedPct(r.roi)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  );
}

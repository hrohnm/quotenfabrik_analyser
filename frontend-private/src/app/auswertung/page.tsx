"use client";

import { useEffect, useMemo, useState } from "react";
import { api, getMeta } from "@/lib/api";
import { num, pct, seasonLabel, signedPct } from "@/lib/format";
import type { Meta } from "@/lib/types";
import { Card, Select, StatTile } from "@/components/ui";
import { CalibrationChart, HitRateBars } from "@/components/charts";

type GroupStat = { group: string; label: string; picks: number; hit_rate: number; expected_hit_rate: number };
type Overview = { fixtures: number; seasons: number[]; groups: GroupStat[]; scorers: { picks: number; hit_rate: number; expected_hit_rate: number } | null };
type MarketStat = { group: string; group_label: string; market: string; label: string; line: number | null; picks: number; hit_rate: number; expected_hit_rate: number; brier: number | null; most_picked: string | null };
type Bin = { bin: string; picks: number; hit_rate: number; expected_hit_rate: number };
type Calib = { bin: string; n: number; predicted: number; observed: number };
type SeasonStat = { season: number; picks: number; hit_rate: number; expected_hit_rate: number };

const keyOf = (m: { market: string; line: number | null }) => `${m.market}|${m.line ?? ""}`;

export default function EvaluationPage() {
  const [meta, setMeta] = useState<Meta | null>(null);
  const [league, setLeague] = useState("");
  const [season, setSeason] = useState("");
  const [group, setGroup] = useState("");
  const [overview, setOverview] = useState<Overview | null>(null);
  const [markets, setMarkets] = useState<MarketStat[]>([]);
  const [selected, setSelected] = useState("1x2|");
  const [confidence, setConfidence] = useState<Bin[]>([]);
  const [seasons, setSeasons] = useState<SeasonStat[]>([]);
  const [calibration, setCalibration] = useState<Calib[]>([]);
  const [calibSel, setCalibSel] = useState("H");
  const [scorers, setScorers] = useState<{ calibration: Calib[] } | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => { getMeta().then((m) => { setMeta(m); setLeague(String(m.leagues[0]?.id ?? "")); }).catch((e) => setError(String(e))); }, []);

  useEffect(() => {
    if (!league) return;
    const p = { league, season: season || undefined };
    Promise.all([api<Overview>("/stats/overview", p), api<MarketStat[]>("/stats/markets", { ...p, group: group || undefined }), api<{ calibration: Calib[] }>("/stats/scorers", p)])
      .then(([o, m, s]) => { setOverview(o); setMarkets(m); setScorers(s); })
      .catch((e) => setError(String(e)));
  }, [league, season, group]);

  const [market, lineStr] = selected.split("|");
  const line = lineStr === "" ? undefined : Number(lineStr);
  const selections = useMemo(() => meta?.markets.find((m) => m.market === market && (line === undefined ? m.line === null : m.line === line))?.selections ?? [], [meta, market, line]);

  useEffect(() => {
    if (selections.length && !selections.includes(calibSel)) {
      setCalibSel(selections.includes("over") ? "over" : selections.includes("yes") ? "yes" : selections.includes("H") ? "H" : selections[0]);
    }
  }, [selections, calibSel]);

  useEffect(() => {
    if (!league) return;
    const p = { league, market, line };
    Promise.all([api<Bin[]>("/stats/confidence", { ...p, season: season || undefined }), api<SeasonStat[]>("/stats/seasons", p)])
      .then(([c, s]) => { setConfidence(c); setSeasons(s); })
      .catch((e) => setError(String(e)));
  }, [league, season, market, line]);

  useEffect(() => {
    if (!league || !calibSel) return;
    api<Calib[]>("/stats/calibration", { league, season: season || undefined, market, line, selection: calibSel })
      .then(setCalibration)
      .catch((e) => setError(String(e)));
  }, [league, season, market, line, calibSel]);

  const selectedMarket = markets.find((m) => keyOf(m) === selected);
  const marketName = (m: { label: string; line: number | null }) => `${m.label}${m.line !== null ? ` ${num(m.line, m.line % 1 ? 1 : 0)}` : ""}`;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Auswertung</h1>
          <p className="max-w-3xl text-sm text-slate-500">
            Wie oft hat die Vorhersage zugetroffen? <b>Getroffen</b> = die wahrscheinlichste Auswahl eines Marktes ist eingetreten
            (bei Ja/Nein-Märkten: Ja ab 50 %). <b>Erwartet</b> = durchschnittliche Modellwahrscheinlichkeit dieser Tipps – liegen beide nah beieinander, ist das Modell gut kalibriert.
          </p>
        </div>
        <div className="flex flex-wrap gap-3">
          <Select label="Liga" value={league} onChange={setLeague}>
            {meta?.leagues.map((l) => <option key={l.id} value={l.id}>{l.name}</option>)}
          </Select>
          <Select label="Saison" value={season} onChange={setSeason}>
            <option value="">alle (2016/17 – heute)</option>
            {meta?.seasons.filter((s) => s >= 2016).map((s) => <option key={s} value={s}>{seasonLabel(s)}</option>)}
          </Select>
          <Select label="Marktgruppe" value={group} onChange={setGroup}>
            <option value="">alle</option>
            {Object.entries(meta?.groups ?? {}).filter(([g]) => g !== "scorers").map(([g, l]) => <option key={g} value={g}>{l}</option>)}
          </Select>
        </div>
      </div>

      {error && <p className="rounded-md bg-rose-50 p-3 text-sm text-rose-700">{error}</p>}

      {overview && (
        <div className="grid grid-cols-2 gap-4 md:grid-cols-3 lg:grid-cols-6">
          <StatTile label="Spiele ausgewertet" value={overview.fixtures.toLocaleString("de-DE")} hint={overview.seasons.length > 1 ? `${seasonLabel(overview.seasons[0])} – ${seasonLabel(overview.seasons.at(-1)!)}` : overview.seasons[0] ? seasonLabel(overview.seasons[0]) : ""} />
          {overview.groups.map((g) => (
            <StatTile key={g.group} label={g.label} value={pct(g.hit_rate)} hint={`erwartet ${pct(g.expected_hit_rate)} · ${g.picks.toLocaleString("de-DE")} Tipps`} />
          ))}
          {overview.scorers && (
            <StatTile label="Top-Torschütze je Team" value={pct(overview.scorers.hit_rate)} hint={`erwartet ${pct(overview.scorers.expected_hit_rate)} · ${overview.scorers.picks.toLocaleString("de-DE")} Tipps`} />
          )}
        </div>
      )}

      <Card title="Trefferquote pro Markt" actions={<span className="text-xs text-slate-400">Zeile anklicken für Details</span>}>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-xs text-slate-400">
                <th className="pb-2 font-medium">Gruppe</th><th className="pb-2 font-medium">Markt</th><th className="pb-2 text-right font-medium">Tipps</th>
                <th className="pb-2 text-right font-medium">Getroffen</th><th className="pb-2 text-right font-medium">Erwartet</th>
                <th className="pb-2 text-right font-medium">Differenz</th><th className="pb-2 text-right font-medium">Brier</th><th className="pb-2 pl-4 font-medium">Häufigster Tipp</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {markets.map((m) => {
                const diff = m.hit_rate - m.expected_hit_rate;
                const active = keyOf(m) === selected;
                return (
                  <tr key={keyOf(m)} onClick={() => setSelected(keyOf(m))} className={`cursor-pointer ${active ? "bg-emerald-50" : "hover:bg-slate-50"}`}>
                    <td className="py-1.5 text-slate-500">{m.group_label}</td>
                    <td className="py-1.5 font-medium">{marketName(m)}</td>
                    <td className="py-1.5 text-right tabular-nums">{m.picks.toLocaleString("de-DE")}</td>
                    <td className="py-1.5 text-right font-semibold tabular-nums">{pct(m.hit_rate)}</td>
                    <td className="py-1.5 text-right tabular-nums text-slate-600">{pct(m.expected_hit_rate)}</td>
                    <td className={`py-1.5 text-right tabular-nums ${Math.abs(diff) < 0.02 ? "text-slate-500" : diff > 0 ? "text-emerald-700" : "text-rose-700"}`}>{signedPct(diff)}</td>
                    <td className="py-1.5 text-right tabular-nums text-slate-600">{num(m.brier, 4)}</td>
                    <td className="py-1.5 pl-4 text-slate-500">{m.most_picked ?? "–"}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </Card>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card title={`Trefferquote nach Konfidenz · ${selectedMarket ? marketName(selectedMarket) : market}`}>
          <p className="mb-2 text-xs text-slate-500">Wahrscheinlichkeit des gewählten Tipps (z. B. „Favorit mit 60–70 %“) und wie oft er eingetreten ist.</p>
          <HitRateBars data={confidence} xKey="bin" />
          <BinTable rows={confidence.map((c) => ({ label: c.bin, n: c.picks, a: c.hit_rate, b: c.expected_hit_rate }))} />
        </Card>
        <Card title={`Saison für Saison · ${selectedMarket ? marketName(selectedMarket) : market}`}>
          <p className="mb-2 text-xs text-slate-500">Trefferquote des Tipps pro Saison (unabhängig vom Saison-Filter).</p>
          <HitRateBars data={seasons.map((s) => ({ ...s, label: seasonLabel(s.season) }))} xKey="label" />
          <BinTable rows={seasons.map((s) => ({ label: seasonLabel(s.season), n: s.picks, a: s.hit_rate, b: s.expected_hit_rate }))} />
        </Card>
        <Card
          title={`Kalibrierung · ${selectedMarket ? marketName(selectedMarket) : market}`}
          actions={
            <select value={calibSel} onChange={(e) => setCalibSel(e.target.value)} className="rounded-md border border-slate-300 px-2 py-1 text-xs">
              {selections.map((s) => <option key={s} value={s}>{meta?.selection_labels[s] ?? s}</option>)}
            </select>
          }
        >
          <p className="mb-2 text-xs text-slate-500">Vorhergesagte Wahrscheinlichkeit (Klassen) gegen tatsächliche Häufigkeit. Liegen beide Linien übereinander, stimmen die Wahrscheinlichkeiten.</p>
          <CalibrationChart data={calibration} />
          <BinTable rows={calibration.map((c) => ({ label: c.bin, n: c.n, a: c.observed, b: c.predicted }))} aLabel="Eingetreten" bLabel="Vorhergesagt" />
        </Card>
        <Card title="Torschützen (Anytime) – Kalibrierung">
          <p className="mb-2 text-xs text-slate-500">Alle Feldspieler mit bekannter Aufstellung. Torschützen-Tipps treffen selten – entscheidend ist, dass die Wahrscheinlichkeiten stimmen.</p>
          <CalibrationChart data={scorers?.calibration ?? []} />
          <BinTable rows={(scorers?.calibration ?? []).map((c) => ({ label: c.bin, n: c.n, a: c.observed, b: c.predicted }))} aLabel="Eingetreten" bLabel="Vorhergesagt" />
        </Card>
      </div>
    </div>
  );
}

function BinTable({ rows, aLabel = "Getroffen", bLabel = "Erwartet" }: { rows: { label: string; n: number; a: number; b: number }[]; aLabel?: string; bLabel?: string }) {
  if (rows.length === 0) return null;
  return (
    <details className="mt-2 text-xs text-slate-600">
      <summary className="cursor-pointer text-slate-400">Tabelle anzeigen</summary>
      <table className="mt-2 w-full">
        <thead><tr className="text-left text-slate-400"><th className="font-medium">Klasse</th><th className="text-right font-medium">n</th><th className="text-right font-medium">{aLabel}</th><th className="text-right font-medium">{bLabel}</th></tr></thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.label}><td>{r.label}</td><td className="text-right tabular-nums">{r.n.toLocaleString("de-DE")}</td><td className="text-right tabular-nums">{pct(r.a)}</td><td className="text-right tabular-nums">{pct(r.b)}</td></tr>
          ))}
        </tbody>
      </table>
    </details>
  );
}

"use client";

import { useEffect, useMemo, useState } from "react";
import { Logo } from "@/components/Logo";
import { Card } from "@/components/ui";
import { api, apiSend } from "@/lib/api";
import type { ApiStatus, ConfiguredLeague, LeaguePreset } from "./types";

type Props = {
  leagues: ConfiguredLeague[];
  status: ApiStatus | null;
  jobRunning: boolean;
  onChanged: () => void;
  onReload: (leagueIds: number[]) => void;
  onError: (msg: string) => void;
};

const TOP5 = [39, 140, 135, 61, 78];
const seasonLabel = (s: number) => `${s}/${String((s + 1) % 100).padStart(2, "0")}`;
const currentSeason = () => {
  const now = new Date();
  return now.getUTCMonth() >= 6 ? now.getUTCFullYear() : now.getUTCFullYear() - 1;
};

/** Results-only leagues: their matches only feed the strength scale (not shown, no forecasts or odds). */
export function RatingsLeaguesCard({ leagues, status, jobRunning, onChanged, onReload, onError }: Props) {
  const [choosing, setChoosing] = useState(false);

  const toggle = async (lg: ConfiguredLeague) => {
    try {
      await apiSend("PATCH", `/admin/leagues/${lg.id}`, { active: !lg.active });
      onChanged();
    } catch (e) {
      onError(String(e instanceof Error ? e.message : e));
    }
  };

  const reload = () => {
    const ids = leagues.filter((l) => l.active).map((l) => l.id);
    if (ids.length && window.confirm(`Ergebnisse von ${ids.length} Stärke-Ligen nachladen?\n\nKosten: 1 API-Football-Request pro Saison und Liga.`)) onReload(ids);
  };

  return (
    <Card
      title="Stärke-Ligen und Europapokal (nur Ergebnisse)"
      actions={
        <div className="flex gap-2">
          {leagues.length > 0 && (
            <button type="button" disabled={jobRunning} onClick={reload} className="rounded-md border border-slate-300 px-3 py-1 text-xs text-slate-700 disabled:opacity-40">
              alle nachladen
            </button>
          )}
          {!choosing && (
            <button type="button" onClick={() => setChoosing(true)} className="rounded-md bg-slate-900 px-3 py-1 text-xs text-white">
              + Europäische Ligen
            </button>
          )}
        </div>
      }
    >
      <p className="mb-3 text-sm text-slate-500">
        Nur Spielergebnisse (1 Request pro Saison) – für eine gemeinsame Stärkeskala über Ländergrenzen. Die Ligen werden über die Europapokalspiele
        miteinander verbunden. Sie erscheinen nicht in Spieltagen und Tipps.
      </p>
      {leagues.length > 0 && (
        <div className="grid gap-x-6 gap-y-1 sm:grid-cols-2 lg:grid-cols-3">
          {leagues.map((lg) => (
            <div key={lg.id} className={`flex items-center justify-between gap-2 border-b border-slate-100 py-1.5 text-sm ${lg.active ? "" : "text-slate-400"}`}>
              <span className="flex min-w-0 items-center gap-2">
                <Logo src={lg.logo} alt={lg.name} size={18} />
                <span className="truncate">{lg.name}</span>
                <span className="shrink-0 text-xs text-slate-400">{lg.kind === "cup" ? "Europapokal" : lg.country}</span>
              </span>
              <span className="flex shrink-0 items-center gap-2">
                <span className="text-xs text-slate-400" title={lg.seasons ? `${seasonLabel(lg.seasons[0])} – ${seasonLabel(lg.seasons[1])}` : undefined}>
                  {lg.finished ? `${lg.finished.toLocaleString("de-DE")} Sp.` : "keine Daten"}
                </span>
                <button
                  type="button"
                  onClick={() => toggle(lg)}
                  className={`relative inline-flex h-4 w-7 items-center rounded-full transition ${lg.active ? "bg-emerald-500" : "bg-slate-300"}`}
                  title={lg.active ? "nicht mehr verwenden (Daten bleiben)" : "wieder verwenden"}
                >
                  <span className={`inline-block h-3 w-3 rounded-full bg-white shadow transition ${lg.active ? "translate-x-3.5" : "translate-x-0.5"}`} />
                </button>
              </span>
            </div>
          ))}
        </div>
      )}
      {choosing && (
        <ChoosePresets
          status={status}
          jobRunning={jobRunning}
          onCancel={() => setChoosing(false)}
          onStarted={() => { setChoosing(false); onChanged(); }}
          onError={onError}
        />
      )}
    </Card>
  );
}

function ChoosePresets({ status, jobRunning, onCancel, onStarted, onError }: { status: ApiStatus | null; jobRunning: boolean; onCancel: () => void; onStarted: () => void; onError: (m: string) => void }) {
  const [presets, setPresets] = useState<LeaguePreset[]>([]);
  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [firstSeason, setFirstSeason] = useState(2017);
  const [starting, setStarting] = useState(false);

  useEffect(() => {
    api<LeaguePreset[]>("/admin/leagues/presets")
      .then((list) => {
        setPresets(list);
        setSelected(new Set(list.filter((p) => !p.configured).map((p) => p.id)));  // default: everything not yet configured
      })
      .catch((e) => onError(String(e instanceof Error ? e.message : e)));
  }, [onError]);

  const free = presets.filter((p) => !p.configured);
  const last = currentSeason();
  const requests = useMemo(
    () => presets.filter((p) => selected.has(p.id)).reduce((n, p) => n + Math.max(0, last - Math.max(firstSeason, p.seasons_from) + 1), 0),
    [presets, selected, firstSeason, last],
  );
  const api_ = status?.api_football;
  const freeQuota = api_?.limit != null && api_.used != null ? api_.limit - api_.used - (status?.settings_reserve.api ?? 0) : null;

  const flip = (id: number) => setSelected((s) => { const n = new Set(s); if (n.has(id)) n.delete(id); else n.add(id); return n; });
  const choose = (ids: number[]) => setSelected(new Set(ids.filter((id) => free.some((p) => p.id === id))));

  const start = async () => {
    setStarting(true);
    try {
      await apiSend("POST", "/admin/leagues/ratings", { ids: [...selected], first_season: firstSeason });
      onStarted();
    } catch (e) {
      onError(String(e instanceof Error ? e.message : e));
    } finally {
      setStarting(false);
    }
  };

  return (
    <div className="mt-4 rounded-lg border border-slate-200 bg-slate-50 p-4">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <div className="text-sm font-semibold">Europapokal und erste Ligen europäischer Länder</div>
        <div className="flex gap-3 text-xs">
          <button type="button" onClick={() => choose(free.map((p) => p.id))} className="text-emerald-700 hover:underline">alle</button>
          <button type="button" onClick={() => choose(TOP5)} className="text-emerald-700 hover:underline">Top 5</button>
          <button type="button" onClick={() => setSelected(new Set())} className="text-emerald-700 hover:underline">keine</button>
          <button type="button" onClick={onCancel} className="text-slate-500 hover:underline">abbrechen</button>
        </div>
      </div>
      {(["cup", "ratings"] as const).map((kind) => (
        <div key={kind} className="mb-3">
          <div className="mb-1 text-xs font-medium uppercase tracking-wide text-slate-400">{kind === "cup" ? "Europapokal (verbindet die Ligen)" : "Ligen"}</div>
      <div className="grid gap-x-4 gap-y-1 sm:grid-cols-2 lg:grid-cols-3">
        {presets.filter((p) => p.kind === kind).map((p) => (
          <label key={p.id} className={`flex items-center gap-2 rounded px-1 py-1 text-sm ${p.configured ? "text-slate-400" : "cursor-pointer hover:bg-white"}`}>
            <input type="checkbox" disabled={!!p.configured} checked={!!p.configured || selected.has(p.id)} onChange={() => flip(p.id)} />
            <Logo src={p.logo} alt={p.name} size={18} />
            <span className="truncate">{p.name}</span>
            <span className="shrink-0 text-xs text-slate-400">{p.kind === "cup" ? "" : p.country}{p.configured === "full" ? " · bereits volle Liga" : p.configured ? " · vorhanden" : ""}</span>
          </label>
        ))}
      </div>
        </div>
      ))}
      <div className="mt-4 flex flex-wrap items-end justify-between gap-4">
        <label className="text-sm">
          <div className="mb-1 text-xs text-slate-500">Ergebnisse ab Saison</div>
          <select value={firstSeason} onChange={(e) => setFirstSeason(Number(e.target.value))} className="rounded-md border border-slate-300 bg-white px-2 py-1.5 text-sm">
            {Array.from({ length: last - 2014 }, (_, i) => 2015 + i).map((s) => <option key={s} value={s}>{seasonLabel(s)}</option>)}
          </select>
          <div className="mt-1 text-xs text-slate-400">Für das Modell reichen 3 Jahre; ältere Saisons nur für Backtests.</div>
        </label>
        <div className="text-right">
          <div className="text-sm">
            {selected.size} Wettbewerbe · <b>{requests.toLocaleString("de-DE")} API-Football-Requests</b>
            {freeQuota != null && <span className="text-slate-500"> · heute frei (ohne Reserve): {freeQuota.toLocaleString("de-DE")}</span>}
          </div>
          <button
            type="button"
            disabled={!selected.size || starting || jobRunning || (freeQuota != null && requests > freeQuota)}
            onClick={start}
            className="mt-2 rounded-md bg-emerald-600 px-4 py-2 text-sm font-medium text-white disabled:opacity-40"
          >
            {starting ? "startet …" : "Ergebnisse laden"}
          </button>
        </div>
      </div>
    </div>
  );
}

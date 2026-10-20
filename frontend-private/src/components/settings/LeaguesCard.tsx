"use client";

import { useEffect, useState } from "react";
import { Logo } from "@/components/Logo";
import { Card } from "@/components/ui";
import { api, apiSend } from "@/lib/api";
import type { ApiStatus, ConfiguredLeague, Estimate, LeagueSearchResult, Tournament } from "./types";

type Props = {
  leagues: ConfiguredLeague[];
  status: ApiStatus | null;
  jobRunning: boolean;
  onChanged: () => void;
  onReload: (leagueId: number) => void;
  onReloadOdds: (leagueId: number) => void;
  onError: (msg: string) => void;
};

export function LeaguesCard({ leagues, status, jobRunning, onChanged, onReload, onReloadOdds, onError }: Props) {
  const [adding, setAdding] = useState(false);
  const [editing, setEditing] = useState<number | null>(null);

  const reloadOdds = (lg: ConfiguredLeague) => {
    const ok = window.confirm(
      `${lg.name}: Betano-Quoten neu laden (OddsPapi-Turnier ${lg.oddspapi_tournament})?\n\nLädt den Spielplan des Turniers (1 OddsPapi-Request), verknüpft die Spiele neu und holt die Quotenverläufe aller offenen Spiele seit Januar 2026 – auch solcher, für die bisher keine Quoten gespeichert sind (kostenlos, ca. 5 Sekunden pro Spiel).`,
    );
    if (ok) onReloadOdds(lg.id);
  };

  const toggle = async (lg: ConfiguredLeague) => {
    try {
      await apiSend("PATCH", `/admin/leagues/${lg.id}`, { active: !lg.active });
      onChanged();
    } catch (e) {
      onError(String(e instanceof Error ? e.message : e));
    }
  };

  const reload = (lg: ConfiguredLeague) => {
    const ok = window.confirm(
      `${lg.name}: Import erneut ausführen?\n\nLädt nur Fehlendes nach (bereits gespeicherte Spiele werden übersprungen) und berechnet danach Prognosen und Tipps neu.\nKosten: ca. 2 API-Football-Requests pro Saison und 1 OddsPapi-Request. Dauer: einige Minuten.`,
    );
    if (ok) onReload(lg.id);
  };

  return (
    <Card
      title="Ligen"
      actions={!adding && <button type="button" onClick={() => setAdding(true)} className="rounded-md bg-slate-900 px-3 py-1 text-xs text-white">+ Liga hinzufügen</button>}
    >
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-xs text-slate-400">
              <th className="pb-2 font-medium">Liga</th><th className="pb-2 font-medium">football-data</th><th className="pb-2 font-medium">OddsPapi</th>
              <th className="pb-2 font-medium">Daten</th><th className="pb-2 text-right font-medium">Aktiv</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {leagues.filter((lg) => lg.kind === "full").map((lg) => (
              <tr key={lg.id} className={lg.active ? "" : "text-slate-400"}>
                <td className="py-2">
                  <span className="flex items-center gap-2">
                    <Logo src={lg.logo} alt={lg.name} size={20} />
                    <span className="font-medium">{lg.name}</span>
                    <span className="text-xs text-slate-400">{lg.country} · ID {lg.id}</span>
                  </span>
                </td>
                <td className="py-2 font-mono text-xs">{lg.fd_code ?? "–"}</td>
                <td className="py-2 text-xs">
                  {editing === lg.id ? (
                    <TournamentEditor
                      league={lg}
                      onCancel={() => setEditing(null)}
                      onSaved={(reload) => { setEditing(null); onChanged(); if (reload) onReloadOdds(lg.id); }}
                      jobRunning={jobRunning}
                      onError={onError}
                    />
                  ) : (
                    <span className="flex flex-wrap items-center gap-x-2">
                      <span className="font-mono">{lg.oddspapi_tournament ?? "–"}</span>
                      <button type="button" onClick={() => setEditing(lg.id)} className="text-emerald-700 hover:underline">ändern</button>
                      {lg.oddspapi_tournament && (
                        <button
                          type="button"
                          disabled={jobRunning}
                          onClick={() => reloadOdds(lg)}
                          className="text-emerald-700 hover:underline disabled:text-slate-300 disabled:no-underline"
                          title={jobRunning ? "Es läuft bereits ein Hintergrund-Job" : "Spielplan und Quotenverläufe neu laden"}
                        >
                          Quoten neu laden
                        </button>
                      )}
                    </span>
                  )}
                </td>
                <td className="py-2 text-xs text-slate-500">
                  {lg.seasons ? `${lg.seasons[0]}/${String((lg.seasons[0] + 1) % 100).padStart(2, "0")} – ${lg.seasons[1]}/${String((lg.seasons[1] + 1) % 100).padStart(2, "0")} · ${lg.finished.toLocaleString("de-DE")} Spiele` : "noch keine Daten"}
                  <button
                    type="button"
                    disabled={jobRunning}
                    onClick={() => reload(lg)}
                    className="ml-2 text-emerald-700 hover:underline disabled:text-slate-300 disabled:no-underline"
                    title={jobRunning ? "Es läuft bereits ein Hintergrund-Job" : "Import erneut ausführen (lädt nur Fehlendes nach)"}
                  >
                    nachladen
                  </button>
                </td>
                <td className="py-2 text-right">
                  <button
                    type="button"
                    onClick={() => toggle(lg)}
                    className={`relative inline-flex h-5 w-9 items-center rounded-full transition ${lg.active ? "bg-emerald-500" : "bg-slate-300"}`}
                    title={lg.active ? "Liga deaktivieren (Daten bleiben erhalten)" : "Liga aktivieren"}
                  >
                    <span className={`inline-block h-4 w-4 rounded-full bg-white shadow transition ${lg.active ? "translate-x-4" : "translate-x-0.5"}`} />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="mt-2 text-xs text-slate-400">Deaktivierte Ligen verschwinden aus Spieltagen, Tipps und Auswertung; ihre Daten bleiben gespeichert.</p>
      {adding && (
        <AddLeague
          status={status}
          jobRunning={jobRunning}
          onCancel={() => setAdding(false)}
          onStarted={() => { setAdding(false); onChanged(); }}
          onError={onError}
        />
      )}
    </Card>
  );
}

/** Changes the OddsPapi tournament of a league (search in the stored tournament list, free) and offers a reload. */
function TournamentEditor({ league, jobRunning, onCancel, onSaved, onError }: { league: ConfiguredLeague; jobRunning: boolean; onCancel: () => void; onSaved: (reload: boolean) => void; onError: (m: string) => void }) {
  const [q, setQ] = useState(`${league.country ?? ""} ${league.name}`.trim());
  const [list, setList] = useState<Tournament[]>([]);
  const [value, setValue] = useState(league.oddspapi_tournament ? String(league.oddspapi_tournament) : "");
  const [reload, setReload] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    const t = setTimeout(() => { api<Tournament[]>("/admin/oddspapi/tournaments", { q }).then(setList).catch(() => setList([])); }, 250);
    return () => clearTimeout(t);
  }, [q]);

  const id = value.trim() ? Number(value) : null;
  const valid = id === null || (Number.isInteger(id) && id > 0);

  const save = async () => {
    setSaving(true);
    try {
      await apiSend("PATCH", `/admin/leagues/${league.id}`, { oddspapi_tournament: id });
      onSaved(reload && id !== null && !jobRunning);
    } catch (e) {
      onError(String(e instanceof Error ? e.message : e));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="flex min-w-72 flex-col gap-1.5 rounded-md border border-slate-200 bg-slate-50 p-2">
      <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Turnier suchen" className="rounded border border-slate-300 bg-white px-2 py-1" />
      <select value={list.some((t) => String(t.id) === value) ? value : ""} onChange={(e) => e.target.value && setValue(e.target.value)} className="rounded border border-slate-300 bg-white px-2 py-1">
        <option value="">{list.length ? "– Treffer wählen –" : "keine Treffer"}</option>
        {list.map((t) => <option key={t.id} value={t.id}>{t.category} · {t.name} (ID {t.id})</option>)}
      </select>
      <label className="flex items-center gap-2">
        ID
        <input value={value} onChange={(e) => setValue(e.target.value.replace(/[^0-9]/g, ""))} inputMode="numeric" placeholder="leer = keines" className="w-24 rounded border border-slate-300 bg-white px-2 py-1 font-mono" />
      </label>
      <label className="flex items-center gap-2 text-slate-600">
        <input type="checkbox" checked={reload && id !== null} disabled={id === null || jobRunning} onChange={(e) => setReload(e.target.checked)} />
        danach Quoten neu laden{jobRunning ? " (erst nach dem laufenden Job möglich)" : ""}
      </label>
      <div className="flex gap-2">
        <button type="button" disabled={!valid || saving} onClick={save} className="rounded bg-slate-900 px-2 py-1 text-white disabled:opacity-40">{saving ? "speichert …" : "Speichern"}</button>
        <button type="button" onClick={onCancel} className="text-slate-500 hover:text-slate-900">abbrechen</button>
      </div>
    </div>
  );
}

const seasonLabel = (s: number) => `${s}/${String((s + 1) % 100).padStart(2, "0")}`;

function AddLeague({ status, jobRunning, onCancel, onStarted, onError }: { status: ApiStatus | null; jobRunning: boolean; onCancel: () => void; onStarted: () => void; onError: (m: string) => void }) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<LeagueSearchResult[] | null>(null);
  const [searching, setSearching] = useState(false);
  const [picked, setPicked] = useState<LeagueSearchResult | null>(null);
  const [codes, setCodes] = useState<{ code: string; label: string }[]>([]);
  const [fdCode, setFdCode] = useState("");
  const [tQuery, setTQuery] = useState("");
  const [tournaments, setTournaments] = useState<Tournament[]>([]);
  const [tournament, setTournament] = useState<number | null>(null);
  const [firstSeason, setFirstSeason] = useState<number | null>(null);
  const [estimate, setEstimate] = useState<Estimate | null>(null);
  const [starting, setStarting] = useState(false);

  useEffect(() => { api<{ code: string; label: string }[]>("/admin/football-data/codes").then(setCodes).catch(() => setCodes([])); }, []);

  useEffect(() => {
    if (!picked) return;
    const t = setTimeout(() => {
      api<Tournament[]>("/admin/oddspapi/tournaments", { q: tQuery })
        .then((list) => {
          setTournaments(list);
          // preselect the exact match (same country and name) as long as nothing was chosen
          const exact = list.find((t) => t.category === picked.country && t.name === picked.name);
          if (exact) setTournament((cur) => cur ?? exact.id);
        })
        .catch(() => setTournaments([]));
    }, 250);
    return () => clearTimeout(t);
  }, [picked, tQuery]);

  useEffect(() => {
    if (!firstSeason) return;
    api<Estimate>("/admin/leagues/estimate", { first_season: firstSeason, last_season: picked?.current ?? undefined }).then(setEstimate).catch(() => setEstimate(null));
  }, [firstSeason, picked]);

  const search = async () => {
    setSearching(true);
    try {
      setResults(await api<LeagueSearchResult[]>("/admin/leagues/search", { q: query }));
    } catch (e) {
      onError(String(e instanceof Error ? e.message : e));
    } finally {
      setSearching(false);
    }
  };

  const pick = (r: LeagueSearchResult) => {
    setPicked(r);
    setFdCode(r.suggested_fd_code ?? "");
    setTQuery(`${r.country ?? ""} ${r.name}`.trim());
    setTournament(null);
    const usable = r.seasons.filter((s) => r.details_from === null || s >= r.details_from);
    const current = r.current ?? r.seasons.at(-1) ?? 2026;
    setFirstSeason(Math.max(usable[0] ?? current, current - 10));
  };

  const start = async () => {
    if (!picked || !firstSeason) return;
    setStarting(true);
    try {
      await apiSend("POST", "/admin/leagues", {
        id: picked.id, name: picked.name, country: picked.country, fd_code: fdCode || null,
        oddspapi_tournament: tournament, first_season: firstSeason, last_season: picked.current,
      });
      onStarted();
    } catch (e) {
      onError(String(e instanceof Error ? e.message : e));
    } finally {
      setStarting(false);
    }
  };

  const af = status?.api_football;
  const free = af?.limit !== undefined && af?.used !== undefined ? af.limit - af.used - (status?.settings_reserve.api ?? 0) : null;
  const tooExpensive = estimate !== null && free !== null && estimate.total > free;

  return (
    <div className="mt-4 space-y-4 rounded-xl border border-slate-200 bg-slate-50 p-4">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold">Liga hinzufügen</h3>
        <button type="button" onClick={onCancel} className="text-xs text-slate-500 hover:text-slate-900">abbrechen</button>
      </div>

      <div>
        <label className="text-xs font-medium text-slate-500">1. Liga bei API-Football suchen (Land oder Name)</label>
        <div className="mt-1 flex gap-2">
          <input value={query} onChange={(e) => setQuery(e.target.value)} onKeyDown={(e) => e.key === "Enter" && query.length >= 3 && search()} placeholder="z. B. England, Serie A, Eredivisie" className="flex-1 rounded-md border border-slate-300 bg-white px-2 py-1.5 text-sm" />
          <button type="button" disabled={query.trim().length < 3 || searching} onClick={search} className="rounded-md bg-slate-900 px-3 py-1.5 text-sm text-white disabled:opacity-40">
            {searching ? "sucht …" : "Suchen"}
          </button>
        </div>
        <p className="mt-1 text-xs text-slate-400">Jede Suche kostet 1 API-Football-Request.</p>
        {results && !picked && (
          <ul className="mt-2 max-h-72 divide-y divide-slate-100 overflow-auto rounded-md border border-slate-200 bg-white">
            {results.length === 0 && <li className="p-2 text-sm text-slate-500">Keine Treffer.</li>}
            {results.map((r) => (
              <li key={r.id}>
                <button type="button" disabled={r.configured} onClick={() => pick(r)} className="flex w-full items-center gap-2 p-2 text-left text-sm hover:bg-slate-50 disabled:opacity-40">
                  <Logo src={r.logo} alt={r.name} size={20} />
                  <span className="font-medium">{r.name}</span>
                  <span className="text-xs text-slate-500">{r.country} · {r.type === "Cup" ? "Pokal" : "Liga"} · {r.seasons[0]}–{r.seasons.at(-1)}</span>
                  {r.configured && <span className="ml-auto text-xs">bereits konfiguriert</span>}
                  {r.ratings && <span className="ml-auto text-xs text-emerald-700">Stärke-Liga → wird zur vollen Liga</span>}
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>

      {picked && (
        <>
          <div className="flex items-center gap-2 rounded-md bg-white p-2 text-sm">
            <Logo src={picked.logo} alt={picked.name} size={24} />
            <span className="font-medium">{picked.name}</span>
            <span className="text-xs text-slate-500">{picked.country} · ID {picked.id}{picked.details_from ? ` · Details ab ${seasonLabel(picked.details_from)}` : ""}</span>
            {picked.ratings && <span className="text-xs text-emerald-700">· bisher Stärke-Liga: Ergebnisse bleiben, Details, Quoten und Tipps kommen dazu</span>}
            <button type="button" onClick={() => setPicked(null)} className="ml-auto text-xs text-slate-500 hover:text-slate-900">andere Liga</button>
          </div>

          <div className="grid gap-4 md:grid-cols-3">
            <label className="flex flex-col gap-1 text-xs font-medium text-slate-500">
              2. Daten ab Saison
              <select value={firstSeason ?? ""} onChange={(e) => setFirstSeason(Number(e.target.value))} className="rounded-md border border-slate-300 bg-white px-2 py-1.5 text-sm text-slate-900">
                {picked.seasons.map((s) => <option key={s} value={s}>{seasonLabel(s)}</option>)}
              </select>
              <span className="font-normal text-slate-400">Mehr Saisonen = besseres Modell, aber mehr Requests.</span>
            </label>
            <label className="flex flex-col gap-1 text-xs font-medium text-slate-500">
              3. football-data.co.uk (Historie + Quoten, kostenlos)
              <select value={fdCode} onChange={(e) => setFdCode(e.target.value)} className="rounded-md border border-slate-300 bg-white px-2 py-1.5 text-sm text-slate-900">
                <option value="">– keine –</option>
                {codes.map((c) => <option key={c.code} value={c.code}>{c.code} · {c.label}</option>)}
              </select>
              <span className="font-normal text-slate-400">{picked.suggested_fd_code ? "Vorschlag anhand des Namens." : "Nur für die großen Ligen verfügbar."}</span>
            </label>
            <div className="flex flex-col gap-1 text-xs font-medium text-slate-500">
              4. OddsPapi-Turnier (Betano-Quoten, kostenlos)
              <input value={tQuery} onChange={(e) => setTQuery(e.target.value)} className="rounded-md border border-slate-300 bg-white px-2 py-1.5 text-sm text-slate-900" />
              <select value={tournament ?? ""} onChange={(e) => setTournament(e.target.value ? Number(e.target.value) : null)} className="rounded-md border border-slate-300 bg-white px-2 py-1.5 text-sm text-slate-900">
                <option value="">– keines –</option>
                {tournaments.map((t) => <option key={t.id} value={t.id}>{t.category} · {t.name} (ID {t.id})</option>)}
              </select>
            </div>
          </div>

          {estimate && (
            <div className={`rounded-md p-3 text-sm ${tooExpensive ? "bg-rose-50 text-rose-800" : "bg-white text-slate-700"}`}>
              <div className="font-medium">
                Geschätzt bis zu {estimate.total.toLocaleString("de-DE")} API-Football-Requests
                {free !== null && <> · heute frei (ohne Reserve): {free.toLocaleString("de-DE")}</>}
              </div>
              <div className="mt-1 text-xs text-slate-500">
                Spielpläne {estimate.fixtures} · Details {estimate.details} · Halbzeit-Stats ab 2024 {estimate.half_stats} · Ausfälle {estimate.injuries}. Obergrenze für 20 Teams – kleinere Ligen brauchen weniger.
                {tooExpensive && " Reicht das Kontingent nicht, bricht der Import an der Reserve ab; ein erneuter Start lädt nur Fehlendes nach."}
              </div>
            </div>
          )}

          <div className="flex items-center justify-between gap-3">
            <p className="text-xs text-slate-500">
              Ablauf: Import → Teams zuordnen → Betano-Quoten → <b>Backup</b> → Modelle & Tipps → Berichte → Backup. Dauer je nach Umfang 10–40 Minuten; der Fortschritt erscheint oben.
            </p>
            <button type="button" disabled={starting || jobRunning || !firstSeason || !status?.keys.api_football} onClick={start} className="shrink-0 rounded-md bg-emerald-600 px-4 py-2 text-sm font-medium text-white disabled:opacity-40">
              {jobRunning ? "Job läuft …" : starting ? "startet …" : "Hinzufügen & Daten laden"}
            </button>
          </div>
        </>
      )}
    </div>
  );
}

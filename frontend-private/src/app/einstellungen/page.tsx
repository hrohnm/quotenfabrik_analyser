"use client";

import { useCallback, useEffect, useState } from "react";
import { api, apiSend } from "@/lib/api";
import { JobsCard } from "@/components/settings/JobsCard";
import { LeaguesCard } from "@/components/settings/LeaguesCard";
import { OddsArchiveCard } from "@/components/settings/OddsArchiveCard";
import { RatingsLeaguesCard } from "@/components/settings/RatingsLeaguesCard";
import { SettingsForm } from "@/components/settings/SettingsForm";
import { StatusCard } from "@/components/settings/StatusCard";
import type { ApiStatus, ConfiguredLeague, Job, SettingField } from "@/components/settings/types";

export default function SettingsPage() {
  const [status, setStatus] = useState<ApiStatus | null>(null);
  const [leagues, setLeagues] = useState<ConfiguredLeague[]>([]);
  const [fields, setFields] = useState<SettingField[]>([]);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [error, setError] = useState<string | null>(null);

  const jobRunning = jobs.some((j) => j.status === "running" || j.status === "queued");

  const loadJobs = useCallback(() => api<Job[]>("/admin/jobs", { limit: 10 }).then(setJobs), []);
  const loadAll = useCallback(() => {
    Promise.all([
      api<ApiStatus>("/admin/status").then(setStatus),
      api<ConfiguredLeague[]>("/admin/leagues").then(setLeagues),
      api<{ settings: SettingField[] }>("/admin/settings").then((r) => setFields(r.settings)),
      loadJobs(),
    ]).catch((e) => setError(String(e instanceof Error ? e.message : e)));
  }, [loadJobs]);

  useEffect(() => { loadAll(); }, [loadAll]);

  // poll while a job runs; reload everything once it is finished
  useEffect(() => {
    if (!jobRunning) return;
    const t = setInterval(() => {
      api<Job[]>("/admin/jobs", { limit: 10 })
        .then((next) => {
          setJobs(next);
          if (!next.some((j) => j.status === "running" || j.status === "queued")) loadAll();
        })
        .catch(() => undefined);
    }, 3000);
    return () => clearInterval(t);
  }, [jobRunning, loadAll]);

  const startJob = async (kind: Job["kind"], leagueId?: number, leagueIds?: number[]) => {
    try {
      await apiSend("POST", "/admin/jobs", { kind, league_id: leagueId, league_ids: leagueIds });
      setError(null);
      loadJobs();
    } catch (e) {
      setError(String(e instanceof Error ? e.message : e));
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Einstellungen</h1>
        <p className="text-sm text-slate-500">
          Ligen verwalten, Schwellen der Tipps und Modellparameter anpassen, Backups. API-Keys werden nicht hier, sondern als Umgebungsvariablen (Codespaces-Secrets) gesetzt.
        </p>
      </div>

      {error && (
        <div className="flex items-start justify-between gap-3 rounded-md bg-rose-50 p-3 text-sm text-rose-700">
          <span>{error}</span>
          <button type="button" onClick={() => setError(null)} className="text-xs">schließen</button>
        </div>
      )}

      <JobsCard
        jobs={jobs}
        onRetry={(j) => (j.kind === "add_ratings" ? startJob("add_ratings", undefined, j.params.league_ids as number[]) : j.kind === "odds_backfill" ? startJob("odds_backfill", j.params.league_id ? Number(j.params.league_id) : undefined) : startJob(j.kind === "odds" ? "odds" : "add_league", Number(j.params.league_id)))}
      />
      <StatusCard status={status} onBackup={() => startJob("backup")} busy={jobRunning} />
      <LeaguesCard leagues={leagues} status={status} jobRunning={jobRunning} onChanged={loadAll} onReload={(id) => startJob("add_league", id)} onReloadOdds={(id) => startJob("odds", id)} onError={setError} />
      <OddsArchiveCard jobRunning={jobRunning} onStart={(kind, id) => startJob(kind, id)} />
      <RatingsLeaguesCard
        leagues={leagues.filter((l) => l.kind === "ratings" || l.kind === "cup")}
        status={status}
        jobRunning={jobRunning}
        onChanged={loadAll}
        onReload={(ids) => startJob("add_ratings", undefined, ids)}
        onError={setError}
      />
      <SettingsForm fields={fields} jobRunning={jobRunning} onSaved={setFields} onStartJob={startJob} onError={setError} />
    </div>
  );
}

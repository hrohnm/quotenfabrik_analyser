"use client";

import { useState } from "react";
import { Card } from "@/components/ui";
import type { Job, JobStep } from "./types";

const KIND_LABELS: Record<Job["kind"], string> = {
  add_league: "Liga hinzufügen",
  models: "Modelle neu berechnen",
  picks: "Tipps neu berechnen",
  backup: "Backup",
};

const STATUS: Record<JobStep["status"] | Job["status"], { icon: string; tone: string; label: string }> = {
  pending: { icon: "○", tone: "text-slate-300", label: "wartet" },
  queued: { icon: "○", tone: "text-slate-400", label: "wartet" },
  running: { icon: "◐", tone: "text-sky-600 animate-pulse", label: "läuft" },
  done: { icon: "✓", tone: "text-emerald-600", label: "fertig" },
  skipped: { icon: "–", tone: "text-slate-400", label: "übersprungen" },
  failed: { icon: "✗", tone: "text-rose-600", label: "fehlgeschlagen" },
};

const time = (iso: string | null) => (iso ? new Date(iso).toLocaleString("de-DE", { dateStyle: "short", timeStyle: "short", timeZone: "Europe/Berlin" }) : "");

function JobView({ job, open, onRetry }: { job: Job; open: boolean; onRetry?: (job: Job) => void }) {
  const [expanded, setExpanded] = useState(open);
  const s = STATUS[job.status];
  const league = job.params.league_id ? ` · Liga ${job.params.league_id}` : "";
  return (
    <li className="py-2">
      <button type="button" onClick={() => setExpanded(!expanded)} className="flex w-full items-center justify-between gap-2 text-left text-sm">
        <span className="flex items-center gap-2">
          <span className={`w-4 text-center ${s.tone}`}>{s.icon}</span>
          <span className="font-medium">{KIND_LABELS[job.kind]}{league}</span>
          <span className="text-xs text-slate-400">#{job.id} · {time(job.created_at)}</span>
        </span>
        <span className={`text-xs ${s.tone}`}>{s.label} {expanded ? "▴" : "▾"}</span>
      </button>
      {expanded && (
        <ol className="mt-2 space-y-1.5 pl-6">
          {job.steps.map((step) => {
            const st = STATUS[step.status];
            return (
              <li key={step.name} className="text-sm">
                <div className="flex gap-2">
                  <span className={`w-4 shrink-0 text-center ${st.tone}`}>{st.icon}</span>
                  <div className="min-w-0">
                    <span className={step.status === "pending" ? "text-slate-400" : ""}>{step.label}</span>
                    {step.message && <div className="text-xs text-slate-500">{step.message}</div>}
                    {step.status === "running" && step.log.length > 0 && <div className="text-xs text-sky-700">{step.log.at(-1)}</div>}
                  </div>
                </div>
              </li>
            );
          })}
          {job.status === "failed" && job.kind === "add_league" && onRetry && (
            <li>
              <button type="button" onClick={() => onRetry(job)} className="rounded-md bg-slate-900 px-3 py-1 text-xs text-white">
                Erneut ausführen (lädt nur Fehlendes nach)
              </button>
            </li>
          )}
          {job.status === "failed" && job.error && (
            <details className="text-xs text-rose-700">
              <summary className="cursor-pointer">Fehlerdetails</summary>
              <pre className="mt-1 max-h-48 overflow-auto whitespace-pre-wrap rounded bg-rose-50 p-2">{job.error}</pre>
            </details>
          )}
        </ol>
      )}
    </li>
  );
}

export function JobsCard({ jobs, onRetry }: { jobs: Job[]; onRetry?: (job: Job) => void }) {
  if (jobs.length === 0) return null;
  return (
    <Card title="Hintergrund-Jobs">
      <ul className="divide-y divide-slate-100">
        {jobs.map((j, i) => <JobView key={j.id} job={j} onRetry={i === 0 ? onRetry : undefined} open={i === 0 && (j.status === "running" || j.status === "queued" || j.status === "failed")} />)}
      </ul>
    </Card>
  );
}

"use client";

import { Card } from "@/components/ui";
import type { ApiStatus } from "./types";

const mb = (bytes: number) => `${(bytes / 1e6).toFixed(1).replace(".", ",")} MB`;
const when = (iso: string) => new Date(iso).toLocaleString("de-DE", { dateStyle: "short", timeStyle: "short", timeZone: "Europe/Berlin" });

function Quota({ label, used, limit, reserve, unit, keySet, error }: { label: string; used?: number; limit?: number; reserve: number; unit: string; keySet: boolean; error?: string }) {
  if (!keySet) {
    return (
      <div>
        <div className="text-sm font-medium">{label}</div>
        <p className="mt-1 text-sm text-rose-700">Key fehlt – als Umgebungsvariable bzw. Codespaces-Secret hinterlegen. Ohne Key können keine Daten geladen werden.</p>
      </div>
    );
  }
  if (error || used === undefined || limit === undefined) {
    return (
      <div>
        <div className="text-sm font-medium">{label}</div>
        <p className="mt-1 text-sm text-amber-700">Status nicht abrufbar{error ? `: ${error}` : ""}</p>
      </div>
    );
  }
  const free = limit - used;
  return (
    <div>
      <div className="flex items-baseline justify-between text-sm">
        <span className="font-medium">{label}</span>
        <span className="tabular-nums text-slate-600">{used.toLocaleString("de-DE")} / {limit.toLocaleString("de-DE")} {unit}</span>
      </div>
      <div className="relative mt-1.5 h-2 overflow-hidden rounded-full bg-slate-100">
        <div className="h-full bg-emerald-500" style={{ width: `${Math.min(1, used / limit) * 100}%` }} />
        <div className="absolute inset-y-0 bg-amber-300/70" style={{ left: `${((limit - reserve) / limit) * 100}%`, right: 0 }} title="Reserve" />
      </div>
      <div className="mt-1 text-xs text-slate-500">frei: {free.toLocaleString("de-DE")} · davon Reserve {reserve.toLocaleString("de-DE")} (gelb, wird von Importen nicht genutzt)</div>
    </div>
  );
}

export function StatusCard({ status, onBackup, busy }: { status: ApiStatus | null; onBackup: () => void; busy: boolean }) {
  if (!status) return <Card title="Status"><p className="text-sm text-slate-500">lädt …</p></Card>;
  const af = status.api_football;
  const op = status.oddspapi;
  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <Card title="API-Kontingent">
        <div className="space-y-4">
          <Quota label={`API-Football${af?.plan ? ` (${af.plan})` : ""}`} used={af?.used} limit={af?.limit} reserve={status.settings_reserve.api} unit="heute" keySet={status.keys.api_football} error={af?.error} />
          <Quota label={`OddsPapi${op?.plan ? ` (${op.plan})` : ""}`} used={op?.used} limit={op?.limit} reserve={status.settings_reserve.oddspapi} unit="im Monat" keySet={status.keys.oddspapi} error={op?.error} />
          {af?.end && <p className="text-xs text-slate-400">API-Football-Abo endet am {new Date(af.end).toLocaleDateString("de-DE")} (keine automatische Verlängerung).</p>}
        </div>
      </Card>
      <Card
        title="Backups"
        actions={<button type="button" disabled={busy} onClick={onBackup} className="rounded-md bg-slate-900 px-3 py-1 text-xs text-white disabled:opacity-40">Backup jetzt</button>}
      >
        <p className="mb-3 text-xs text-slate-500">
          Nach jedem Liga-Import entsteht automatisch ein Backup (Datenbank inkl. Rohdaten der API). Standardmäßig wird auch <code>seed/quotenfabrik_seed.dump</code> ersetzt – per <code>git commit</code> bleiben die Daten dauerhaft erhalten, auch wenn der Codespace gelöscht wird.
        </p>
        {status.backups.length === 0 ? (
          <p className="text-sm text-slate-500">Noch kein Backup.</p>
        ) : (
          <ul className="divide-y divide-slate-100 text-sm">
            {status.backups.map((b) => (
              <li key={b.name} className="flex items-center justify-between gap-2 py-1.5">
                <span className="truncate font-mono text-xs">{b.name}</span>
                <span className="flex shrink-0 items-center gap-3 text-xs text-slate-500">
                  {when(b.created_at)} · {mb(b.size)}
                  <a href={`/api/admin/backups/${encodeURIComponent(b.name)}`} className="font-medium text-emerald-700 hover:underline">Download</a>
                </span>
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  );
}

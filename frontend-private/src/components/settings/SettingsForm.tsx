"use client";

import { useEffect, useMemo, useState } from "react";
import { Card } from "@/components/ui";
import { apiSend } from "@/lib/api";
import type { SettingField } from "./types";

type Props = {
  fields: SettingField[];
  jobRunning: boolean;
  onSaved: (fields: SettingField[]) => void;
  onStartJob: (kind: "picks" | "models") => void;
  onError: (msg: string) => void;
};

const toInput = (f: SettingField) => (f.percent ? String(Math.round(Number(f.value) * 1000) / 10) : String(f.value));

export function SettingsForm({ fields, jobRunning, onSaved, onStartJob, onError }: Props) {
  const [draft, setDraft] = useState<Record<string, string>>({});
  const [saving, setSaving] = useState(false);
  const [savedGroups, setSavedGroups] = useState<Set<string>>(new Set());

  useEffect(() => { setDraft(Object.fromEntries(fields.map((f) => [f.key, toInput(f)]))); }, [fields]);

  const groups = useMemo(() => {
    const map = new Map<string, SettingField[]>();
    fields.forEach((f) => map.set(f.group, [...(map.get(f.group) ?? []), f]));
    return [...map.entries()];
  }, [fields]);

  const changed = fields.filter((f) => draft[f.key] !== undefined && draft[f.key] !== toInput(f));

  const save = async () => {
    const values: Record<string, number | string> = {};
    for (const f of changed) {
      const raw = draft[f.key].replace(",", ".");
      values[f.key] = f.type === "choice" ? raw : f.percent ? Number(raw) / 100 : Number(raw);
    }
    setSaving(true);
    try {
      const res = await apiSend<{ settings: SettingField[] }>("PUT", "/admin/settings", values);
      setSavedGroups(new Set(changed.map((f) => f.group)));
      onSaved(res.settings);
    } catch (e) {
      onError(String(e instanceof Error ? e.message : e));
    } finally {
      setSaving(false);
    }
  };

  const reset = (f: SettingField) => setDraft((d) => ({ ...d, [f.key]: f.percent ? String(Number(f.default) * 100) : String(f.default) }));
  const picksChanged = [...savedGroups].some((g) => g.startsWith("Tipps"));
  const modelChanged = [...savedGroups].some((g) => g.startsWith("Modell"));

  return (
    <Card
      title="Einstellungen"
      actions={
        <button type="button" disabled={changed.length === 0 || saving} onClick={save} className="rounded-md bg-slate-900 px-3 py-1 text-xs text-white disabled:opacity-40">
          {saving ? "speichert …" : changed.length ? `${changed.length} Änderung${changed.length > 1 ? "en" : ""} speichern` : "gespeichert"}
        </button>
      }
    >
      {(picksChanged || modelChanged) && (
        <div className="mb-4 flex flex-wrap items-center gap-3 rounded-md bg-amber-50 p-3 text-sm text-amber-900">
          <span>Gespeichert. Die neuen Werte wirken erst nach einer Neuberechnung:</span>
          {picksChanged && <button type="button" disabled={jobRunning} onClick={() => onStartJob("picks")} className="rounded-md bg-amber-600 px-3 py-1 text-xs text-white disabled:opacity-40">Tipps neu berechnen (≈ 2 Min. je Liga)</button>}
          {modelChanged && <button type="button" disabled={jobRunning} onClick={() => onStartJob("models")} className="rounded-md bg-amber-600 px-3 py-1 text-xs text-white disabled:opacity-40">Modelle neu berechnen (≈ 7 Min. je Liga)</button>}
        </div>
      )}
      <div className="grid gap-6 lg:grid-cols-2">
        {groups.map(([group, items]) => (
          <fieldset key={group} className="space-y-3">
            <legend className="mb-1 text-sm font-semibold text-slate-700">{group}</legend>
            {items.map((f) => {
              const isChanged = draft[f.key] !== toInput(f);
              const isDefault = String(f.value) === String(f.default);
              return (
                <div key={f.key} className="grid grid-cols-[1fr_8rem] items-start gap-3">
                  <div>
                    <div className="text-sm">{f.label}</div>
                    <div className="text-xs text-slate-400">
                      {f.help} {!isDefault && <button type="button" onClick={() => reset(f)} className="text-emerald-700 hover:underline">Standard: {f.percent ? `${Number(f.default) * 100} %` : String(f.default).replace(".", ",")}</button>}
                    </div>
                  </div>
                  {f.type === "choice" ? (
                    <select value={draft[f.key] ?? ""} onChange={(e) => setDraft((d) => ({ ...d, [f.key]: e.target.value }))} className={`rounded-md border px-2 py-1 text-sm ${isChanged ? "border-amber-400" : "border-slate-300"}`}>
                      {f.choices.map((c) => <option key={c} value={c}>{c}</option>)}
                    </select>
                  ) : (
                    <label className={`flex items-center rounded-md border bg-white px-2 ${isChanged ? "border-amber-400" : "border-slate-300"}`}>
                      <input
                        inputMode="decimal"
                        value={(draft[f.key] ?? "").replace(".", ",")}
                        onChange={(e) => setDraft((d) => ({ ...d, [f.key]: e.target.value.replace(",", ".") }))}
                        className="w-full py-1 text-right text-sm tabular-nums outline-none"
                      />
                      {f.percent && <span className="pl-1 text-xs text-slate-400">%</span>}
                    </label>
                  )}
                </div>
              );
            })}
          </fieldset>
        ))}
      </div>
    </Card>
  );
}

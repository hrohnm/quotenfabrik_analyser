"use client";

import { useState } from "react";
import type { FixtureDetail } from "@/lib/types";

/** "Einschätzung": generated text preview of the match (headline, summary, sections). */
export function PreviewCard({ preview }: { preview: NonNullable<FixtureDetail["preview"]> }) {
  const [open, setOpen] = useState(true);
  return (
    <section className="rounded-xl border border-emerald-200 bg-gradient-to-b from-emerald-50/70 to-white p-4 shadow-sm sm:p-5">
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="text-xs font-medium uppercase tracking-wide text-emerald-700">Einschätzung</div>
          <h2 className="mt-0.5 text-lg font-semibold leading-snug text-slate-900">{preview.headline}</h2>
        </div>
        <button type="button" onClick={() => setOpen(!open)} className="shrink-0 text-xs text-slate-500 hover:text-slate-900">
          {open ? "weniger" : "mehr"}
        </button>
      </div>
      <p className="mt-2 text-sm leading-relaxed text-slate-700">{preview.summary}</p>
      {open && preview.sections.length > 0 && (
        <dl className="mt-3 space-y-2 text-sm leading-relaxed">
          {preview.sections.map((s) => (
            <div key={s.title} className="sm:grid sm:grid-cols-[150px_1fr] sm:gap-3">
              <dt className="font-semibold text-slate-800">{s.title}</dt>
              <dd className="whitespace-pre-line text-slate-600">{s.text}</dd>
            </div>
          ))}
        </dl>
      )}
      <p className="mt-3 text-[11px] text-slate-400">Automatisch aus Prognosen, Form, Spielstil, Pattern und Betano-Quoten erstellt – nur Daten von vor dem Anpfiff.</p>
    </section>
  );
}

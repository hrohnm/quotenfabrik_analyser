"use client";

import { useEffect, useRef, useState } from "react";

/** Small badge: league, national cup or European cup competition. */
export function CompetitionBadge({ cup, international = false, className = "" }: { cup: boolean; international?: boolean; className?: string }) {
  const label = !cup ? "Liga" : international ? "Europapokal" : "Pokal";
  const tone = !cup ? "bg-slate-100 text-slate-500" : international ? "bg-indigo-100 text-indigo-800" : "bg-amber-100 text-amber-800";
  return (
    <span
      className={`inline-flex shrink-0 items-center rounded px-1 py-px text-[10px] font-semibold uppercase tracking-wide ${tone} ${className}`}
      title={!cup ? "Ligaspiel" : international ? "Europapokal (abgerechnet nach 90 Minuten)" : "Pokalspiel (abgerechnet nach 90 Minuten)"}
    >
      {label}
    </span>
  );
}

/** Country flag (API-Football SVG) or a globe for international competitions / when the image fails. */
export function CountryFlag({ src, label }: { src: string | null; label: string }) {
  const [failed, setFailed] = useState(false);
  const ref = useRef<HTMLImageElement>(null);
  // a server-rendered image can fail before hydration (no onError then)
  useEffect(() => {
    const img = ref.current;
    if (img && img.complete && img.naturalWidth === 0) setFailed(true);
  }, [src]);
  if (!src || failed) {
    return <span className="grid h-3.5 w-5 shrink-0 place-items-center text-xs leading-none" aria-label={label}>{src ? "🏳️" : "🌍"}</span>;
  }
  // eslint-disable-next-line @next/next/no-img-element
  return <img ref={ref} src={src} alt={label} onError={() => setFailed(true)} className="h-3.5 w-5 shrink-0 rounded-[2px] object-cover ring-1 ring-black/10" />;
}

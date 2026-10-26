"use client";

import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import type { SearchResult } from "@/lib/types";
import { TeamLogo } from "./ui";

/** Search for teams in the header (players follow with the player pages). */
export function SearchBox() {
  const router = useRouter();
  const [q, setQ] = useState("");
  const [result, setResult] = useState<SearchResult | null>(null);
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(0);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (q.trim().length < 2) {
      setResult(null);
      return;
    }
    let current = true;
    const t = setTimeout(() => {
      api<SearchResult>("/search", { q: q.trim() }).then((r) => current && (setResult(r), setActive(0))).catch(() => current && setResult(null));
    }, 200);
    return () => {
      current = false;
      clearTimeout(t);
    };
  }, [q]);

  useEffect(() => {
    const close = (e: MouseEvent) => !ref.current?.contains(e.target as Node) && setOpen(false);
    document.addEventListener("mousedown", close);
    return () => document.removeEventListener("mousedown", close);
  }, []);

  const teams = result?.teams ?? [];
  const go = (id: number) => {
    setOpen(false);
    setQ("");
    router.push(`/team/${id}`);
  };

  return (
    <div ref={ref} className="relative">
      <input
        type="search"
        value={q}
        placeholder="Team suchen …"
        onChange={(e) => { setQ(e.target.value); setOpen(true); }}
        onFocus={() => setOpen(true)}
        onKeyDown={(e) => {
          if (e.key === "ArrowDown") { e.preventDefault(); setActive((a) => Math.min(a + 1, teams.length - 1)); }
          if (e.key === "ArrowUp") { e.preventDefault(); setActive((a) => Math.max(a - 1, 0)); }
          if (e.key === "Enter" && teams[active]) go(teams[active].id);
          if (e.key === "Escape") setOpen(false);
        }}
        className="w-28 rounded-md border border-slate-200 bg-white px-2 py-1 text-sm text-slate-900 placeholder:text-slate-400 focus:w-48 focus:border-slate-400 focus:outline-none sm:w-40 sm:focus:w-56"
        aria-label="Team suchen"
      />
      {open && q.trim().length >= 2 && result && (
        <div className="absolute right-0 top-full z-30 mt-1.5 w-64 overflow-hidden rounded-xl border border-slate-200 bg-white p-1 text-sm shadow-lg ring-1 ring-black/5">
          {teams.length === 0 ? (
            <p className="px-2 py-1.5 text-slate-400">Keine Mannschaft gefunden.</p>
          ) : (
            teams.map((t, i) => (
              <button
                key={t.id}
                type="button"
                onMouseEnter={() => setActive(i)}
                onClick={() => go(t.id)}
                className={`flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-left ${i === active ? "bg-slate-100" : ""} ${t.active ? "text-slate-800" : "text-slate-400"}`}
              >
                <TeamLogo team={t} size={20} />
                <span className="truncate">{t.name}</span>
              </button>
            ))
          )}
        </div>
      )}
    </div>
  );
}

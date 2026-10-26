"use client";

import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import type { SearchResult } from "@/lib/types";
import { Logo } from "./Logo";
import { TeamLogo } from "./ui";

type Item = { kind: "team" | "player"; id: number; name: string; href: string; sub?: string; logo?: string | null; photo?: string };

/** Search for teams and players in the header (``wide``: full width, e.g. in the mobile menu). */
export function SearchBox({ wide = false }: { wide?: boolean }) {
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

  const items: Item[] = [
    ...(result?.teams ?? []).map((t) => ({ kind: "team" as const, id: t.id, name: t.name, href: `/team/${t.id}`, logo: t.logo })),
    ...(result?.players ?? []).map((p) => ({ kind: "player" as const, id: p.id, name: p.name, href: `/spieler/${p.id}`, sub: p.team?.name, photo: p.photo })),
  ];
  const go = (item: Item) => {
    setOpen(false);
    setQ("");
    router.push(item.href);
  };

  return (
    <div ref={ref} className="relative">
      <input
        type="search"
        value={q}
        placeholder="Team oder Spieler suchen …"
        onChange={(e) => { setQ(e.target.value); setOpen(true); }}
        onFocus={() => setOpen(true)}
        onKeyDown={(e) => {
          if (e.key === "ArrowDown") { e.preventDefault(); setActive((a) => Math.min(a + 1, items.length - 1)); }
          if (e.key === "ArrowUp") { e.preventDefault(); setActive((a) => Math.max(a - 1, 0)); }
          if (e.key === "Enter" && items[active]) go(items[active]);
          if (e.key === "Escape") setOpen(false);
        }}
        className={`rounded-md border border-slate-200 bg-white px-2 py-1 text-sm text-slate-900 placeholder:text-slate-400 focus:border-slate-400 focus:outline-none ${wide ? "w-full py-2" : "w-44 focus:w-64"}`}
        aria-label="Team oder Spieler suchen"
      />
      {open && q.trim().length >= 2 && result && (
        <div className={`absolute top-full z-30 mt-1.5 overflow-hidden rounded-xl border border-slate-200 bg-white p-1 text-sm shadow-lg ring-1 ring-black/5 ${wide ? "inset-x-0" : "right-0 w-72"}`}>
          {items.length === 0 && <p className="px-2 py-1.5 text-slate-400">Nichts gefunden.</p>}
          {items.map((item, i) => (
            <div key={`${item.kind}-${item.id}`}>
              {(i === 0 || items[i - 1].kind !== item.kind) && (
                <div className="px-2 pb-0.5 pt-1.5 text-[10px] font-semibold uppercase tracking-wide text-slate-400">{item.kind === "team" ? "Mannschaften" : "Spieler"}</div>
              )}
              <button
                type="button"
                onMouseEnter={() => setActive(i)}
                onClick={() => go(item)}
                className={`flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-left text-slate-800 ${i === active ? "bg-slate-100" : ""}`}
              >
                {item.kind === "team" ? <TeamLogo team={{ id: item.id, name: item.name, logo: item.logo }} size={20} /> : <Logo src={item.photo} alt={item.name} size={22} shape="round" />}
                <span className="min-w-0 flex-1 truncate">{item.name}</span>
                {item.sub && <span className="truncate text-xs text-slate-400">{item.sub}</span>}
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

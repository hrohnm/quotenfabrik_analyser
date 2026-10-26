"use client";

import Link from "next/link";
import { usePathname, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useRef, useState } from "react";
import { getMeta } from "@/lib/api";
import { leagueLogo } from "@/lib/media";
import { Logo } from "./Logo";
import { SearchBox } from "./SearchBox";

const LINKS = [
  { href: "/spieltage", label: "Spieltage" },
  { href: "/tipps", label: "Tipps" },
  { href: "/wetten", label: "Wetten" },
  { href: "/explorer", label: "Daten-Explorer" },
  { href: "/auswertung", label: "Auswertung" },
  { href: "/einstellungen", label: "Einstellungen" },
];

export function Nav() {
  const pathname = usePathname();
  const [leagues, setLeagues] = useState<{ id: number; name: string; country?: string }[]>([]);
  useEffect(() => { getMeta().then((m) => setLeagues(m.leagues)).catch(() => setLeagues([])); }, []);
  return (
    <header className="sticky top-0 z-20 border-b border-slate-200 bg-white/90 backdrop-blur">
      <div className="mx-auto flex max-w-7xl items-center gap-4 px-4 py-3 sm:gap-8">
        <Link href="/spieltage" className="flex items-center gap-2 font-semibold tracking-tight">
          <span className="grid h-7 w-7 place-items-center rounded-md bg-emerald-600 text-sm font-bold text-white">Q</span>
          <span className="hidden sm:inline">Quotenfabrik</span>
        </Link>
        <nav className="flex gap-1 overflow-x-auto text-sm">
          {LINKS.map((l) => {
            const active = pathname.startsWith(l.href) || (l.href === "/spieltage" && pathname.startsWith("/spiel/"));
            return (
              <Link
                key={l.href}
                href={l.href}
                className={`whitespace-nowrap rounded-md px-3 py-1.5 transition ${
                  active ? "bg-slate-900 text-white" : "text-slate-600 hover:bg-slate-100"
                }`}
              >
                {l.label}
              </Link>
            );
          })}
        </nav>
        <span className="ml-auto flex shrink-0 items-center gap-3 text-xs text-slate-400">
          <SearchBox />
          {leagues.length > 0 && <Suspense fallback={null}><LeagueMenu leagues={leagues} /></Suspense>}
          <span className="hidden whitespace-nowrap lg:inline">Modell dc-v1</span>
        </span>
      </div>
    </header>
  );
}

/** Dropdown of the shown leagues: opens the matchday overview filtered to one league. */
function LeagueMenu({ leagues }: { leagues: { id: number; name: string; country?: string }[] }) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const pathname = usePathname();
  const params = useSearchParams();
  const active = pathname.startsWith("/spieltage") ? params.get("liga") : null;
  const current = leagues.find((l) => String(l.id) === active);

  useEffect(() => setOpen(false), [pathname, params]);
  useEffect(() => {
    if (!open) return;
    const close = (e: MouseEvent | KeyboardEvent) => {
      if (e instanceof KeyboardEvent ? e.key === "Escape" : !ref.current?.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", close);
    document.addEventListener("keydown", close);
    return () => {
      document.removeEventListener("mousedown", close);
      document.removeEventListener("keydown", close);
    };
  }, [open]);

  return (
    <div ref={ref} className="relative">
      <button
        type="button"
        onClick={() => setOpen(!open)}
        aria-expanded={open}
        className="flex items-center gap-2 rounded-md border border-slate-200 bg-white px-2 py-1 text-sm text-slate-700 hover:border-slate-400"
      >
        {current ? (
          <><Logo src={leagueLogo(current.id)} alt={current.name} size={16} /><span className="hidden max-w-[10rem] truncate sm:inline">{current.name}</span></>
        ) : (
          <>
            <span className="flex -space-x-1.5">
              {leagues.slice(0, 3).map((l) => <span key={l.id} className="rounded-full bg-white ring-2 ring-white"><Logo src={leagueLogo(l.id)} alt={l.name} size={16} shape="round" /></span>)}
            </span>
            <span className="hidden sm:inline">Ligen</span>
            <span className="rounded-full bg-slate-100 px-1.5 text-[11px] text-slate-500">{leagues.length}</span>
          </>
        )}
        <svg viewBox="0 0 20 20" className={`h-3.5 w-3.5 text-slate-400 transition ${open ? "rotate-180" : ""}`} fill="currentColor" aria-hidden>
          <path d="M5.3 7.3a1 1 0 0 1 1.4 0L10 10.6l3.3-3.3a1 1 0 1 1 1.4 1.4l-4 4a1 1 0 0 1-1.4 0l-4-4a1 1 0 0 1 0-1.4z" />
        </svg>
      </button>
      {open && (
        <div className="absolute right-0 top-full z-30 mt-1.5 max-h-[70vh] w-64 overflow-y-auto rounded-xl border border-slate-200 bg-white p-1 text-sm shadow-lg ring-1 ring-black/5">
          <Link href="/spieltage" className={`flex items-center gap-2 rounded-md px-2 py-1.5 hover:bg-slate-50 ${!current ? "font-semibold text-slate-900" : "text-slate-700"}`}>
            <span className="grid h-5 w-5 place-items-center rounded bg-slate-100 text-[10px] text-slate-500">∑</span>Alle Ligen
          </Link>
          <div className="my-1 border-t border-slate-100" />
          {leagues.map((l) => (
            <Link
              key={l.id}
              href={`/spieltage?liga=${l.id}`}
              className={`flex items-center gap-2 rounded-md px-2 py-1.5 hover:bg-slate-50 ${String(l.id) === active ? "bg-slate-100 font-semibold text-slate-900" : "text-slate-700"}`}
            >
              <Logo src={leagueLogo(l.id)} alt={l.name} size={20} />
              <span className="min-w-0 flex-1 truncate">{l.name}</span>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}

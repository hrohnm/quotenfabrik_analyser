"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { getMeta } from "@/lib/api";
import { leagueLogo } from "@/lib/media";
import { Logo } from "./Logo";

const LINKS = [
  { href: "/spieltage", label: "Spieltage" },
  { href: "/tipps", label: "Tipps" },
  { href: "/explorer", label: "Daten-Explorer" },
  { href: "/auswertung", label: "Auswertung" },
  { href: "/einstellungen", label: "Einstellungen" },
];

export function Nav() {
  const pathname = usePathname();
  const [leagues, setLeagues] = useState<{ id: number; name: string }[]>([]);
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
        <span className="ml-auto hidden items-center gap-2 text-xs text-slate-400 sm:flex">
          {leagues.map((l) => <span key={l.id} title={l.name}><Logo src={leagueLogo(l.id)} alt={l.name} size={18} /></span>)}
          <span className="whitespace-nowrap">Modell dc-v1</span>
        </span>
      </div>
    </header>
  );
}

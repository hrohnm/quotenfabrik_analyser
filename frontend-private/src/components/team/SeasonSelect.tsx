"use client";

import { useRouter } from "next/navigation";
import { seasonLabel } from "@/lib/format";

export function SeasonSelect({ basePath, season, seasons }: { basePath: string; season: number; seasons: number[] }) {
  const router = useRouter();
  return (
    <label className="flex items-center gap-2 text-xs text-slate-500">
      Saison
      <select
        value={season}
        onChange={(e) => router.push(`${basePath}?saison=${e.target.value}`)}
        className="rounded-md border border-slate-300 bg-white px-2 py-1 text-sm text-slate-900"
      >
        {seasons.map((s) => <option key={s} value={s}>{seasonLabel(s)}</option>)}
      </select>
    </label>
  );
}

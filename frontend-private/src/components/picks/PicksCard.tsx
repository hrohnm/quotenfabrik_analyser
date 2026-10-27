"use client";

import { useState } from "react";
import { Card } from "@/components/ui";
import { Segmented } from "@/components/match/Segmented";
import { pct } from "@/lib/format";
import type { Pick, PickCombo, PickProfile, PickStats } from "@/lib/types";
import { PickList } from "./PickList";

type Props = { picks: Record<string, Pick[]>; combos?: Record<string, PickCombo>; profiles: PickProfile[]; stats: PickStats["profiles"] | null; finished: boolean };

export function PicksCard({ picks, combos, profiles, stats, finished }: Props) {
  const [profile, setProfile] = useState(profiles.find((p) => p.default)?.key ?? profiles[0]?.key ?? "ausgewogen");
  const current = profiles.find((p) => p.key === profile);
  const history = stats?.find((s) => s.profile === profile);
  return (
    <Card
      title="Unsere 3 Tipps"
      actions={<Segmented options={profiles.map((p) => ({ key: p.key, label: p.label }))} value={profile} onChange={setProfile} size="sm" />}
    >
      <PickList picks={picks[profile] ?? []} combo={combos?.[profile]} finished={finished} />
      <p className="mt-3 text-xs text-slate-400">
        Profil {current?.label}: Tipps mit {pct(current?.min_p, 0)} – {pct(current?.max_p, 0)} Wahrscheinlichkeit, je Marktgruppe höchstens einer.
        {history?.singles.hit_rate != null && ` Bisher getroffen: ${pct(history.singles.hit_rate, 0)} der Einzeltipps, ${pct(history.combo.hit_rate, 0)} der Kombis (${history.combo.n.toLocaleString("de-DE")} Spiele).`}
      </p>
    </Card>
  );
}

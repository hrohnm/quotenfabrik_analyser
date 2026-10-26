import { notFound } from "next/navigation";
import { ApiError, api } from "@/lib/api";
import { PlayerHeader } from "@/components/player/PlayerHeader";
import { PlayerTabs } from "@/components/player/PlayerTabs";
import { TeamLink } from "@/components/TeamLink";
import type { PlayerOverview } from "@/lib/types";

export const dynamic = "force-dynamic";

export default async function PlayerPage({ params, searchParams }: { params: Promise<{ id: string }>; searchParams: Promise<{ saison?: string }> }) {
  const { id } = await params;
  const { saison } = await searchParams;
  let data: PlayerOverview;
  try {
    data = await api<PlayerOverview>(`/players/${id}`, { season: saison });
  } catch (e) {
    if (e instanceof ApiError && e.status === 404) notFound();
    throw e;
  }
  const team = data.teams[data.team_id];
  return (
    <div className="space-y-6">
      <TeamLink id={data.team_id} className="text-sm text-slate-500 hover:text-slate-900">← {team?.name ?? "Mannschaft"}</TeamLink>
      <PlayerHeader data={data} />
      <PlayerTabs data={data} />
    </div>
  );
}

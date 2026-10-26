import Link from "next/link";
import { notFound } from "next/navigation";
import { ApiError, api } from "@/lib/api";
import { TeamHeader } from "@/components/team/TeamHeader";
import { TeamTabs } from "@/components/team/TeamTabs";
import type { TeamOverview } from "@/lib/types";

export const dynamic = "force-dynamic";

export default async function TeamPage({ params, searchParams }: { params: Promise<{ id: string }>; searchParams: Promise<{ saison?: string }> }) {
  const { id } = await params;
  const { saison } = await searchParams;
  let data: TeamOverview;
  try {
    data = await api<TeamOverview>(`/teams/${id}`, { season: saison });
  } catch (e) {
    if (e instanceof ApiError && e.status === 404) notFound();
    throw e;
  }
  return (
    <div className="space-y-6">
      <Link href="/spieltage" className="text-sm text-slate-500 hover:text-slate-900">← Spieltage</Link>
      <TeamHeader data={data} />
      <TeamTabs data={data} />
    </div>
  );
}

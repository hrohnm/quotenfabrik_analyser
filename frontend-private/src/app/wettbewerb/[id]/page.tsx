import Link from "next/link";
import { notFound } from "next/navigation";
import { ApiError, api } from "@/lib/api";
import { CompetitionHeader } from "@/components/competition/CompetitionHeader";
import { CompetitionTabs } from "@/components/competition/CompetitionTabs";
import type { CompetitionOverview } from "@/lib/types";

export const dynamic = "force-dynamic";

export default async function CompetitionPage({ params, searchParams }: { params: Promise<{ id: string }>; searchParams: Promise<{ saison?: string }> }) {
  const { id } = await params;
  const { saison } = await searchParams;
  let data: CompetitionOverview;
  try {
    data = await api<CompetitionOverview>(`/competitions/${id}`, { season: saison });
  } catch (e) {
    if (e instanceof ApiError && e.status === 404) notFound();
    throw e;
  }
  return (
    <div className="space-y-6">
      <Link href={`/spieltage?liga=${data.league.id}`} className="text-sm text-slate-500 hover:text-slate-900">← Spieltage {data.league.name}</Link>
      <CompetitionHeader data={data} />
      <CompetitionTabs data={data} />
    </div>
  );
}

import Link from "next/link";
import { notFound } from "next/navigation";
import { ApiError, api, getFixture, getMeta } from "@/lib/api";
import { Hero } from "@/components/match/Hero";
import { MatchTabs } from "@/components/match/MatchTabs";
import { Summary } from "@/components/match/Summary";
import { PicksCard } from "@/components/picks/PicksCard";
import type { FixtureDetail, PickStats } from "@/lib/types";

export const dynamic = "force-dynamic";

export default async function FixturePage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  let data: FixtureDetail;
  try {
    data = await getFixture(id);
  } catch (e) {
    if (e instanceof ApiError && e.status === 404) notFound();
    throw e;
  }
  const { fixture: f, prediction } = data;
  // optional extras: a failure here must not break the page
  const [meta, stats] = await Promise.all([
    getMeta().catch(() => null),
    api<PickStats>("/stats/picks", { league: f.league_id }).catch(() => null),
  ]);
  const day = new Date(f.kickoff).toLocaleDateString("en-CA", { timeZone: "Europe/Berlin" });

  return (
    <div className="space-y-6">
      <Link href={`/spieltage?datum=${day}`} className="text-sm text-slate-500 hover:text-slate-900">← zurück zum Spieltag</Link>
      <Hero data={data} />
      {prediction?.kind === "backtest" && (
        <p className="-mt-3 text-center text-xs text-slate-400">
          Rückwirkende Prognose: Modell nur mit Spielen vor diesem {data.fixture.cup ? "Spiel" : "Spieltag"} trainiert (Walk-Forward), Torschützen mit bekannter Aufstellung (sonst wahrscheinlicher Kader).
        </p>
      )}
      <section className="space-y-3">
        <h2 className="text-lg font-semibold">Auf einen Blick</h2>
        {meta?.pick_profiles?.length ? (
          <PicksCard picks={data.picks ?? {}} profiles={meta.pick_profiles} stats={stats?.profiles ?? null} finished={f.finished} />
        ) : null}
        <Summary data={data} />
      </section>
      <section className="space-y-3">
        <h2 className="text-lg font-semibold">Details</h2>
        <MatchTabs data={data} />
      </section>
    </div>
  );
}

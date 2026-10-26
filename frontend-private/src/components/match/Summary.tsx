import { Logo } from "@/components/Logo";
import { PlayerLink } from "@/components/PlayerLink";
import { Card, OutcomeBadge, ProbabilityBar, TeamLogo } from "@/components/ui";
import { num, odd, pct } from "@/lib/format";
import { expectedGoals, market, pick, selection } from "@/lib/markets";
import { playerPhoto } from "@/lib/media";
import { patternValue, signals } from "@/lib/patterns";
import type { FixtureDetail, Selection } from "@/lib/types";
import { BetanoOdd } from "@/components/BetanoOdd";

/** "Auf einen Blick": 1X2, key metrics, top scorers and the strongest pattern signals. */
export function Summary({ data }: { data: FixtureDetail }) {
  const { fixture: f, markets } = data;
  const m1x2 = market(markets, "1x2");
  const best = pick(m1x2);
  const xg = expectedGoals(markets);
  const metrics: { label: string; s?: Selection }[] = [
    { label: "Über 2,5 Tore", s: selection(markets, "ou_ft", "over", 2.5) },
    { label: "Beide treffen", s: selection(markets, "btts", "yes") },
    { label: `${f.home.name} trifft`, s: selection(markets, "ou_home", "over", 0.5) },
    { label: `${f.away.name} trifft`, s: selection(markets, "ou_away", "over", 0.5) },
    { label: "Tor in der 1. HZ", s: selection(markets, "ou_1h", "over", 0.5) },
  ];
  const tiles = [
    { sel: "H", label: "Heimsieg", logo: <TeamLogo team={f.home} size={28} /> },
    { sel: "D", label: "Remis", logo: <span className="grid h-7 w-7 place-items-center rounded bg-slate-100 text-sm font-bold text-slate-500">X</span> },
    { sel: "A", label: "Auswärtssieg", logo: <TeamLogo team={f.away} size={28} /> },
  ];
  const scorers = data.scorers.filter((s) => s.anytime).slice(0, 3);
  const team = (id?: number | null) => (id === f.home.id ? f.home : id === f.away.id ? f.away : null);
  const sig = signals(data.patterns).slice(0, 5);

  if (!m1x2) {
    return <Card><p className="text-sm text-slate-500">Für dieses Spiel liegt noch keine Prognose vor.</p></Card>;
  }

  return (
    <div className="grid gap-4 lg:grid-cols-3">
      <Card title="Spielausgang" className="lg:col-span-2">
        <div className="grid grid-cols-3 gap-2 sm:gap-3">
          {tiles.map((t) => {
            const s = m1x2.selections.find((x) => x.selection === t.sel);
            const isPick = s?.selection === best?.selection;
            return (
              <div key={t.sel} className={`relative rounded-xl border p-3 text-center ${isPick ? "border-emerald-400 bg-emerald-50" : "border-slate-200"}`}>
                {f.finished && <div className="absolute right-2 top-2"><OutcomeBadge outcome={s?.outcome} small /></div>}
                <div className="flex justify-center">{t.logo}</div>
                <div className="mt-1 text-xs text-slate-500">{t.label}</div>
                <div className={`text-2xl font-semibold tabular-nums ${isPick ? "text-emerald-700" : ""}`}>{pct(s?.probability, 0)}</div>
                <div className="text-xs text-slate-400">faire Quote {odd(s?.fair_odd)}</div>
                {s?.betano != null && <div className="mt-1 text-xs text-slate-500">Betano <BetanoOdd prices={s} /></div>}
              </div>
            );
          })}
        </div>

        <div className="mt-5 grid gap-x-6 gap-y-3 sm:grid-cols-2">
          <div className="flex items-center justify-between rounded-lg bg-slate-50 px-3 py-2 sm:col-span-2">
            <span className="text-sm text-slate-600">Erwartete Tore</span>
            <span className="text-lg font-semibold tabular-nums">{num(xg, 1)}</span>
          </div>
          {metrics.map(({ label, s }) => (
            <div key={label}>
              <div className="mb-1 flex items-center justify-between gap-2 text-sm">
                <span className="truncate text-slate-600">{label}</span>
                <span className="flex items-center gap-2 font-medium tabular-nums">
                  {pct(s?.probability, 0)}
                  {f.finished && <OutcomeBadge outcome={s?.outcome} small />}
                </span>
              </div>
              <ProbabilityBar value={s?.probability ?? 0} tone={(s?.probability ?? 0) >= 0.5 ? "emerald" : "slate"} />
            </div>
          ))}
        </div>
      </Card>

      <div className="space-y-4">
        <Card title="Wahrscheinlichste Torschützen">
          {scorers.length === 0 ? (
            <p className="text-sm text-slate-500">Keine Prognose vorhanden.</p>
          ) : (
            <ul className="space-y-3">
              {scorers.map((s) => {
                const t = team(s.team_id);
                return (
                  <li key={s.player_id} className="flex items-center gap-3">
                    <Logo src={playerPhoto(s.player_id)} alt={s.name ?? String(s.player_id)} size={36} shape="round" />
                    <div className="min-w-0 flex-1">
                      <PlayerLink id={s.player_id} className="block truncate text-sm font-medium">{s.name}</PlayerLink>
                      <div className="flex items-center gap-1 text-xs text-slate-500">
                        {t && <TeamLogo team={t} size={14} />}
                        <span className="truncate">{t?.name}</span>
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="font-semibold tabular-nums">{pct(s.anytime, 0)}</div>
                      <div className="text-xs text-slate-400">{s.anytime ? odd(1 / s.anytime) : "–"}</div>
                    </div>
                    {f.finished && <OutcomeBadge outcome={s.anytime_outcome} small />}
                  </li>
                );
              })}
            </ul>
          )}
        </Card>

        <Card title="Auffällige Pattern">
          {sig.length === 0 ? (
            <p className="text-sm text-slate-500">Keine signifikanten Abweichungen vom Ligaschnitt.</p>
          ) : (
            <ul className="space-y-2">
              {sig.map((p) => {
                const t = p.scope === "home" ? f.home : p.scope === "away" ? f.away : null;
                return (
                  <li key={p.key} className="flex items-start gap-2 text-sm">
                    {t ? <TeamLogo team={t} size={18} /> : <span className="h-[18px] w-[18px] shrink-0" />}
                    <span className="flex-1 text-slate-700">{p.label}</span>
                    <span className={`shrink-0 rounded px-1.5 py-0.5 text-xs font-medium tabular-nums ${p.signal === "high" ? "bg-emerald-100 text-emerald-700" : "bg-rose-100 text-rose-700"}`}>
                      {patternValue(p)}
                    </span>
                  </li>
                );
              })}
            </ul>
          )}
        </Card>
      </div>
    </div>
  );
}

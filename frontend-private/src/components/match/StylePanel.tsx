import { Card, TeamLogo } from "@/components/ui";
import { num, pct } from "@/lib/format";
import type { FixtureDetail, StyleMetric, Team, TeamStyle } from "@/lib/types";

const GROUPS: { key: StyleMetric["group"]; label: string }[] = [
  { key: "control", label: "Spielkontrolle" },
  { key: "attack", label: "Offensivdruck" },
  { key: "finishing", label: "Verwertung" },
  { key: "defence", label: "Defensive" },
  { key: "intensity", label: "Intensität" },
];

function value(m: Pick<StyleMetric, "unit">, v: number | null): string {
  if (v == null) return "–";
  if (m.unit === "pct" || m.unit === "ratio") return pct(v, 0);
  if (m.unit === "pp") {
    const r = Math.round(v * 1000) / 10;
    return `${r > 0 ? "+" : r < 0 ? "−" : "±"}${num(Math.abs(r), 1)} Pkt.`;
  }
  return num(v, v >= 100 ? 0 : 1);
}

/** Bar of the percentile; green = good for the team, red = weak, grey = pure style (no better/worse). */
function Rank({ m }: { m: StyleMetric }) {
  if (m.percentile == null) return <div className="h-1.5 rounded-full bg-slate-100" />;
  const good = m.better === "high" ? m.percentile : m.better === "low" ? 1 - m.percentile : null;
  const color = good == null ? "bg-slate-400" : good >= 0.67 ? "bg-emerald-500" : good <= 0.33 ? "bg-rose-500" : "bg-slate-400";
  return (
    <div className="h-1.5 rounded-full bg-slate-100" title={`Rang: höher als ${pct(m.percentile, 0)} der Teams`}>
      <div className={`h-full rounded-full ${color}`} style={{ width: `${Math.max(4, m.percentile * 100)}%` }} />
    </div>
  );
}

/** Playing style of both teams: possession, attacking pressure, finishing, defence, intensity. */
export function StylePanel({ data }: { data: FixtureDetail }) {
  const home = data.style?.home ?? null;
  const away = data.style?.away ?? null;
  if (!home && !away) return <Card><p className="text-sm text-slate-500">Für diese Teams liegen zu wenige Spielstatistiken vor.</p></Card>;
  const ref = home ?? away!;
  const byKey = (s: TeamStyle | null, key: string) => s?.metrics.find((m) => m.key === key);
  return (
    <div className="space-y-4">
      <p className="text-xs text-slate-500">
        Spielstil aus den Statistiken der letzten {ref.matches} Spiele vor Anpfiff (Liga; bei Europapokal alle Wettbewerbe), eingeordnet gegen die {ref.peers} Teams des
        Wettbewerbs. Der Balken zeigt den Rang: grün = stark, rot = schwach, grau = reine Stilfrage. Im Backtest (docs/18_spielstil.md) verbessern vor allem
        Schüsse und Schussanteil die Tor-Erwartung leicht; hohe Verwertung und starke gegnerische Torhüter gleichen sich eher wieder aus.
      </p>
      <div className="grid gap-4 md:grid-cols-2">
        <Labels team={data.fixture.home} style={home} />
        <Labels team={data.fixture.away} style={away} />
      </div>
      <div className="grid gap-4 lg:grid-cols-2">
        {GROUPS.map((g) => (
          <Card key={g.key} title={g.label}>
            <table className="w-full table-fixed text-sm">
              <thead>
                <tr className="text-xs text-slate-400">
                  <th className="w-[38%] pb-2 text-left font-medium" />
                  <th className="pb-2 text-left font-medium"><span className="flex items-center gap-1"><TeamLogo team={data.fixture.home} size={14} />Heim</span></th>
                  <th className="pb-2 text-left font-medium"><span className="flex items-center gap-1"><TeamLogo team={data.fixture.away} size={14} />Gast</span></th>
                  <th className="w-14 pb-2 text-right font-medium">Schnitt</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {ref.metrics.filter((m) => m.group === g.key).map((m) => {
                  const h = byKey(home, m.key);
                  const a = byKey(away, m.key);
                  if (h?.value == null && a?.value == null) return null;
                  return (
                    <tr key={m.key}>
                      <td className="py-1.5 pr-2 text-xs text-slate-600">{m.label}</td>
                      {[h, a].map((x, i) => (
                        <td key={i} className="py-1.5 pr-3">
                          <div className="text-xs font-semibold tabular-nums">{x ? value(x, x.value) : "–"}</div>
                          {x && <Rank m={x} />}
                        </td>
                      ))}
                      <td className="py-1.5 text-right text-xs tabular-nums text-slate-400">{value(m, m.league_avg)}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </Card>
        ))}
      </div>
    </div>
  );
}

function Labels({ team, style }: { team: Team; style: TeamStyle | null }) {
  return (
    <Card title={<span className="flex items-center gap-2"><TeamLogo team={team} size={18} />{team.name}</span>}>
      {!style ? (
        <p className="text-sm text-slate-500">Zu wenige Spiele mit Statistik.</p>
      ) : style.labels.length ? (
        <div className="flex flex-wrap gap-1.5">
          {style.labels.map((l) => <span key={l} className="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-700">{l}</span>)}
        </div>
      ) : (
        <p className="text-sm text-slate-500">Unauffälliger Spielstil (überall im Mittelfeld der Liga).</p>
      )}
      {style && <p className="mt-2 text-[11px] text-slate-400">{style.matches} Spiele{style.xg_matches ? `, davon ${style.xg_matches} mit xG` : ", ohne xG-Daten"}</p>}
    </Card>
  );
}

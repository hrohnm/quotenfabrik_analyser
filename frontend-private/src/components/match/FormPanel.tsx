import Link from "next/link";
import { TeamLink } from "@/components/TeamLink";
import { Logo } from "@/components/Logo";
import { Card, TeamLogo } from "@/components/ui";
import { dateShort, num } from "@/lib/format";
import type { FixtureDetail, Team, TeamForm } from "@/lib/types";

const RESULT_CLASS = { S: "bg-emerald-500", U: "bg-slate-400", N: "bg-rose-500" } as const;

const signed = (v: number | null | undefined) => {
  if (v == null) return "–";
  const r = Math.round(v * 100) / 100;
  return `${r > 0 ? "+" : r < 0 ? "−" : "±"}${num(Math.abs(r))}`;
};

/** Result chips S/U/N (oldest first). */
export function FormChips({ sequence, size = "h-5 w-5" }: { sequence: string; size?: string }) {
  return (
    <span className="inline-flex flex-wrap justify-center gap-0.5">
      {[...sequence].map((r, i) => (
        <span key={i} className={`grid ${size} place-items-center rounded text-[10px] font-bold text-white ${RESULT_CLASS[r as "S" | "U" | "N"]}`}>{r}</span>
      ))}
    </span>
  );
}

/** Last 10 matches of both teams in all competitions and the form pattern. */
export function FormPanel({ data }: { data: FixtureDetail }) {
  if (!data.form) return <Card><p className="text-sm text-slate-500">Keine Daten.</p></Card>;
  return (
    <div className="space-y-4">
      <p className="text-xs text-slate-500">
        Letzte 10 Pflichtspiele vor Anpfiff in allen Wettbewerben (Liga, Europapokal; Stärke-Ligen nur mit Ergebnis). Form = Punkte minus
        Modell-Erwartung pro Spiel in den letzten 6 Spielen: über 0 heißt mehr geholt als erwartet. Im Backtest (docs/17_form.md) sagt die
        Form das nächste Spiel nicht besser voraus als das Modell – sie ist ein Hinweis, kein Wettsignal.
      </p>
      <div className="grid gap-4 lg:grid-cols-2">
        <TeamCard team={data.fixture.home} form={data.form.home} />
        <TeamCard team={data.fixture.away} form={data.form.away} />
      </div>
    </div>
  );
}

function TeamCard({ team, form }: { team: Team; form: TeamForm }) {
  const f = form.form;
  const tone = f.signal === "high" ? "text-emerald-700" : f.signal === "low" ? "text-rose-700" : "text-slate-900";
  return (
    <Card title={<span className="flex items-center gap-2"><TeamLogo team={team} size={18} /><TeamLink id={team.id}>{team.name}</TeamLink></span>}>
      <div className="mb-3 grid grid-cols-3 gap-2 text-center">
        <div className="rounded-lg bg-slate-50 p-2">
          <div className="text-[11px] uppercase tracking-wide text-slate-500">Letzte {f.matches}</div>
          <div className="mt-1"><FormChips sequence={f.sequence} size="h-4 w-4 sm:h-5 sm:w-5" /></div>
        </div>
        <div className="rounded-lg bg-slate-50 p-2">
          <div className="text-[11px] uppercase tracking-wide text-slate-500">Punkte/Spiel</div>
          <div className="text-lg font-semibold tabular-nums">{num(f.ppg)}</div>
          <div className="text-[11px] text-slate-500">erwartet {num(f.expected_ppg)}</div>
        </div>
        <div className="rounded-lg bg-slate-50 p-2" title={`aus ${f.n_expected} Spielen mit Prognose`}>
          <div className="text-[11px] uppercase tracking-wide text-slate-500">Form</div>
          <div className={`text-lg font-semibold tabular-nums ${tone}`}>{signed(f.residual)}</div>
          <div className="text-[11px] text-slate-500">{f.signal === "high" ? "über Erwartung" : f.signal === "low" ? "unter Erwartung" : f.residual == null ? "zu wenige Daten" : "im Rahmen"}</div>
        </div>
      </div>
      <table className="w-full text-sm">
        <tbody className="divide-y divide-slate-100">
          {form.matches.map((m) => (
            <tr key={m.fixture_id}>
              <td className="whitespace-nowrap py-1.5 pr-2 text-xs tabular-nums text-slate-500">{dateShort(m.kickoff)}</td>
              <td className="py-1.5 pr-2"><Logo src={m.league.logo} alt={m.league.name ?? "Wettbewerb"} size={16} /></td>
              <td className="py-1.5 pr-2 text-xs text-slate-400" title={m.venue === "home" ? "Heimspiel" : "Auswärtsspiel"}>{m.venue === "home" ? "H" : "A"}</td>
              <td className="w-full max-w-0 py-1.5 pr-2">
                <Link href={`/spiel/${m.fixture_id}`} className="flex items-center gap-1.5 hover:opacity-80" title={[m.league.name, m.round_label].filter(Boolean).join(" · ")}>
                  <TeamLogo team={m.opponent} size={16} /><span className="truncate">{m.opponent.name}</span>
                </Link>
              </td>
              <td className="py-1.5 pr-2 text-right font-semibold tabular-nums">{m.gf}:{m.ga}</td>
              <td className="py-1.5 pr-2"><FormChips sequence={m.result} size="h-4 w-4" /></td>
              <td className="py-1.5 text-right text-xs tabular-nums text-slate-400" title="erwartete Punkte laut Modell vor dem Spiel">{m.xpts == null ? "" : num(m.xpts, 1)}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <p className="mt-2 text-[11px] text-slate-400">Rechte Spalte: erwartete Punkte laut Modell vor dem Spiel (leer = keine Prognose, z. B. Stärke-Liga).</p>
    </Card>
  );
}

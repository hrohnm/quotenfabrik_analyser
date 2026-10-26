import { Card, TeamLogo } from "@/components/ui";
import { TeamLink } from "@/components/TeamLink";
import { dateShort } from "@/lib/format";
import type { Absence, FixtureDetail, LineupPlayer, Team, TeamLineup } from "@/lib/types";

type Side = "home" | "away";
type Orientation = "horizontal" | "vertical";

const FALLBACK = {
  home: { primary: "ffffff", number: "0f172a", border: "0f172a" },
  away: { primary: "0f172a", number: "ffffff", border: "ffffff" },
};

const POS_LABEL: Record<string, string> = { G: "TW", D: "AB", M: "MF", F: "ST" };
const POS_ROW: Record<string, number> = { G: 1, D: 2, M: 3, F: 4 };

const REASON: Record<string, string> = {
  "Knee Injury": "Knieverletzung", "Muscle Injury": "Muskelverletzung", "Ankle Injury": "Sprunggelenksverletzung",
  Injury: "Verletzung", Illness: "Krankheit", "Thigh Injury": "Oberschenkelverletzung", "Groin Injury": "Leistenverletzung",
  "Yellow Cards": "Gelbsperre", "Calf Injury": "Wadenverletzung", "Shoulder Injury": "Schulterverletzung",
  "Hip Injury": "Hüftverletzung", "Red Card": "Rotsperre", "Foot Injury": "Fußverletzung",
  "Achilles Tendon Injury": "Achillessehnenverletzung", "Back Injury": "Rückenverletzung", "Leg Injury": "Beinverletzung",
  Knock: "Prellung", "Lacking Match Fitness": "fehlende Spielpraxis", "Jumpers knee": "Patellasehne",
  "National selection": "Nationalmannschaft", "Tendon Injury": "Sehnenverletzung", "Hamstring Injury": "Oberschenkel hinten",
  "Broken ankle": "Knöchelbruch", "Abdominal strain": "Bauchmuskelzerrung", Concussion: "Gehirnerschütterung",
  "Broken Leg": "Beinbruch", "Toe Injury": "Zehenverletzung", Inactive: "inaktiv", "International duty": "Länderspielreise",
  "Broken calfbone": "Wadenbeinbruch", "Finger Injury": "Fingerverletzung", "Muscle bruise": "Muskelprellung",
  "Head Injury": "Kopfverletzung", "Hand Injury": "Handverletzung", "Elbow Injury": "Ellenbogenverletzung",
  Suspended: "gesperrt", Surgery: "Operation", "Stomach Disorder": "Magenprobleme", "Wrist Injury": "Handgelenksverletzung",
  "Personal Reasons": "persönliche Gründe", Contusion: "Prellung", "Health problems": "gesundheitliche Probleme",
  "Broken shinbone": "Schienbeinbruch", "Heart Problems": "Herzprobleme", Wound: "Wunde",
};

const reasonLabel = (r: string | null) => (r ? REASON[r] ?? r : "Grund unbekannt");

/** Relative luminance of a hex colour (WCAG). */
function luminance(hex: string): number {
  const v = /^[0-9a-f]{6}$/i.test(hex) ? hex : "808080";
  const [r, g, b] = [0, 2, 4].map((i) => {
    const c = parseInt(v.slice(i, i + 2), 16) / 255;
    return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
  });
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

const contrast = (a: string, b: string) => {
  const [x, y] = [luminance(a), luminance(b)].sort((m, n) => n - m);
  return (x + 0.05) / (y + 0.05);
};

/** Shirt colours of the API, with a readable number (the API colours are sometimes too close). */
function shirt(side: Side, colors: TeamLineup["colors"], keeper: boolean) {
  const c = { ...FALLBACK[side], ...(keeper ? colors?.goalkeeper : colors?.player) };
  if (contrast(c.primary, c.number) < 3) c.number = luminance(c.primary) > 0.4 ? "0f172a" : "ffffff";
  return c;
}

/** Position of every starter: depth from the own goal line (0–1) and lateral position from the team's left (0–1). */
function slots(players: LineupPlayer[]) {
  const parsed = players.map((p) => {
    const [row, col] = (p.grid ?? "").split(":").map(Number);
    return { p, row, col };
  });
  const valid = parsed.every((x) => x.row > 0 && x.col > 0);
  const rows = new Map<number, { p: LineupPlayer; row: number; col: number }[]>();
  for (const x of parsed) {
    const row = valid ? x.row : POS_ROW[x.p.pos ?? "M"] ?? 3;
    rows.set(row, [...(rows.get(row) ?? []), { ...x, row }]);
  }
  const depthRows = Math.max(...rows.keys());
  return [...rows.values()].flatMap((list) => {
    const sorted = valid ? [...list].sort((a, b) => a.col - b.col) : list;
    return sorted.map((x, i) => ({
      p: x.p,
      depth: depthRows > 1 ? (x.row - 1) / (depthRows - 1) : 0,
      lateral: (i + 0.5) / sorted.length,
    }));
  });
}

/** Screen coordinates in % (home: bottom / left half, away: top / right half). Grid column 1 is the team's left. */
function place(side: Side, depth: number, lateral: number, o: Orientation) {
  const d = 5 + depth * 39; // from the own goal line to just before the halfway line
  if (o === "horizontal") return side === "home" ? { left: d, top: lateral * 100 } : { left: 100 - d, top: 100 - lateral * 100 };
  return side === "home" ? { left: lateral * 100, top: 100 - d } : { left: 100 - lateral * 100, top: d };
}

function Marker({ p, side, colors, style }: { p: LineupPlayer; side: Side; colors: TeamLineup["colors"]; style: { left: number; top: number } }) {
  const c = shirt(side, colors, p.pos === "G");
  const title = [
    `${p.number ?? ""} ${p.name ?? "?"}`.trim(),
    p.replaces ? `ersetzt ${p.replaces} (fehlt)` : null,
    p.questionable ? "Einsatz fraglich" : null,
    p.absent ? "als fehlend gemeldet" : null,
  ].filter(Boolean).join(" · ");
  return (
    <div className="absolute flex w-16 -translate-x-1/2 -translate-y-1/2 flex-col items-center sm:w-20" style={{ left: `${style.left}%`, top: `${style.top}%` }} title={title}>
      <span
        className={`relative grid h-7 w-7 place-items-center rounded-full border-2 text-[11px] outline outline-1 outline-black/20 font-bold tabular-nums shadow-md ${p.replaces ? "ring-2 ring-sky-300" : ""}`}
        style={{ background: `#${c.primary}`, color: `#${c.number}`, borderColor: `#${c.border}` }}
      >
        {p.number ?? ""}
        {p.questionable && <span className="absolute -right-1.5 -top-1.5 grid h-3.5 w-3.5 place-items-center rounded-full bg-amber-400 text-[9px] font-bold text-amber-950">?</span>}
        {p.absent && <span className="absolute -right-1.5 -top-1.5 grid h-3.5 w-3.5 place-items-center rounded-full bg-rose-500 text-[9px] font-bold text-white">!</span>}
      </span>
      <span className="mt-0.5 max-w-full truncate rounded bg-black/40 px-1 text-[10px] font-medium leading-tight text-white">{p.name ?? "?"}</span>
    </div>
  );
}

function Pitch({ data, o }: { data: FixtureDetail; o: Orientation }) {
  const lu = data.lineups!;
  const h = o === "horizontal";
  const line = "absolute border-white/60";
  return (
    <div
      className={`relative w-full overflow-hidden rounded-xl shadow-inner ${h ? "aspect-[105/68]" : "aspect-[68/105]"}`}
      style={{ background: `repeating-linear-gradient(${h ? "90deg" : "0deg"}, #15803d 0 10%, #16a34a 10% 20%)` }}
    >
      <div className={`${line} inset-[2.5%] border`} />
      <div className={`${line} ${h ? "inset-y-[2.5%] left-1/2 border-l" : "inset-x-[2.5%] top-1/2 border-t"}`} />
      <div className={`${line} left-1/2 top-1/2 aspect-square -translate-x-1/2 -translate-y-1/2 rounded-full border ${h ? "h-[27%]" : "w-[27%]"}`} />
      {(["start", "end"] as const).map((end) => (
        <div
          key={end}
          className={`${line} border ${h ? `top-1/2 h-[59%] w-[16%] -translate-y-1/2 ${end === "start" ? "left-[2.5%]" : "right-[2.5%]"}` : `left-1/2 h-[16%] w-[59%] -translate-x-1/2 ${end === "start" ? "top-[2.5%]" : "bottom-[2.5%]"}`}`}
        />
      ))}
      {(["home", "away"] as const).map((side) =>
        slots(lu[side].start).map(({ p, depth, lateral }) => (
          <Marker key={`${side}-${p.player_id}`} p={p} side={side} colors={lu[side].colors} style={place(side, depth, lateral, o)} />
        )),
      )}
      {(["home", "away"] as const).map((side) => {
        const team = side === "home" ? data.fixture.home : data.fixture.away;
        const pos = h
          ? side === "home" ? "left-2 bottom-2" : "right-2 top-2"
          : side === "home" ? "left-2 bottom-2" : "right-2 top-2";
        return (
          <span key={side} className={`absolute ${pos} flex items-center gap-1 rounded bg-black/30 px-1.5 py-0.5 text-[10px] font-semibold text-white`}>
            <TeamLogo team={team} size={12} />
            {lu[side].formation ?? ""}
          </span>
        );
      })}
    </div>
  );
}

function AbsenceList({ missing }: { missing: Absence[] }) {
  if (missing.length === 0) return <p className="text-xs text-slate-400">Keine Ausfälle gemeldet.</p>;
  return (
    <ul className="space-y-1 text-xs">
      {missing.map((a) => {
        const questionable = a.type === "Questionable";
        return (
          <li key={a.player_id} className="flex items-center gap-2">
            <span className={`rounded px-1.5 py-0.5 text-[10px] font-semibold ${questionable ? "bg-amber-100 text-amber-800" : "bg-rose-100 text-rose-700"}`}>
              {questionable ? "fraglich" : "fehlt"}
            </span>
            <span className="text-slate-800">{a.name ?? "?"}</span>
            <span className="text-slate-400">{reasonLabel(a.reason)}</span>
          </li>
        );
      })}
    </ul>
  );
}

function TeamCard({ team, lineup, predicted }: { team: Team; lineup: TeamLineup; predicted: boolean }) {
  const replaced = lineup.start.filter((p) => p.replaces);
  return (
    <Card title={<span className="flex items-center gap-2"><TeamLogo team={team} size={18} /><TeamLink id={team.id}>{team.name}</TeamLink>{lineup.formation && <span className="font-normal text-slate-400">{lineup.formation}</span>}</span>}>
      <div className="space-y-4 text-sm">
        {lineup.coach && <p className="text-xs text-slate-500">Trainer: <span className="text-slate-800">{lineup.coach}</span></p>}
        {predicted && lineup.basis && (
          <p className="text-xs text-slate-500">
            Basis: Startelf vom {dateShort(lineup.basis.kickoff)} {lineup.basis.home ? "gegen" : "bei"} {lineup.basis.opponent ?? "?"}
            {replaced.length > 0 && <> · ersetzt: {replaced.map((p) => `${p.replaces} → ${p.name}`).join(", ")}</>}
          </p>
        )}
        {predicted && !lineup.basis && <p className="text-xs text-slate-500">Keine früheren Aufstellungen vorhanden.</p>}
        <div>
          <h3 className="mb-1.5 text-[11px] font-semibold uppercase tracking-wide text-slate-500">Startelf</h3>
          <ul className="grid grid-cols-1 gap-x-4 gap-y-1 text-xs sm:grid-cols-2">
            {lineup.start.map((p) => (
              <li key={p.player_id} className="flex items-center gap-2">
                <span className="w-5 text-right tabular-nums text-slate-400">{p.number ?? ""}</span>
                <span className="w-6 text-[10px] text-slate-400">{POS_LABEL[p.pos ?? ""] ?? ""}</span>
                <span className="truncate text-slate-800">{p.name}</span>
                {p.questionable && <span className="rounded bg-amber-100 px-1 text-[10px] text-amber-800">fraglich</span>}
                {p.absent && <span className="rounded bg-rose-100 px-1 text-[10px] text-rose-700">gemeldet fehlend</span>}
              </li>
            ))}
          </ul>
        </div>
        {lineup.bench && lineup.bench.length > 0 && (
          <div>
            <h3 className="mb-1.5 text-[11px] font-semibold uppercase tracking-wide text-slate-500">Bank</h3>
            <ul className="grid grid-cols-1 gap-x-4 gap-y-1 text-xs sm:grid-cols-2">
              {lineup.bench.map((p) => (
                <li key={p.player_id} className="flex items-center gap-2">
                  <span className="w-5 text-right tabular-nums text-slate-400">{p.number ?? ""}</span>
                  <span className="w-6 text-[10px] text-slate-400">{POS_LABEL[p.pos ?? ""] ?? ""}</span>
                  <span className="truncate text-slate-600">{p.name}</span>
                </li>
              ))}
            </ul>
          </div>
        )}
        <div>
          <h3 className="mb-1.5 text-[11px] font-semibold uppercase tracking-wide text-slate-500">Ausfälle</h3>
          <AbsenceList missing={lineup.missing} />
        </div>
      </div>
    </Card>
  );
}

/** Confirmed line-ups or the expected starting XI of both teams on a pitch, with bench and absences. */
export function LineupPanel({ data }: { data: FixtureDetail }) {
  const lu = data.lineups;
  if (!lu) return <Card><p className="text-sm text-slate-500">Für dieses Spiel liegt keine Aufstellung vor.</p></Card>;
  const predicted = lu.status === "predicted";
  const empty = lu.home.start.length === 0 && lu.away.start.length === 0;
  return (
    <div className="space-y-4">
      <div className="flex flex-col items-start gap-2 text-xs text-slate-500 sm:flex-row">
        <span className={`rounded-full px-2 py-0.5 font-semibold ${predicted ? "bg-amber-100 text-amber-800" : "bg-emerald-100 text-emerald-800"}`}>
          {predicted ? "Voraussichtliche Aufstellung" : "Bestätigte Aufstellung"}
        </span>
        <p className="min-w-0 flex-1">
          {predicted
            ? "Startelf aus dem letzten Spiel (alle Wettbewerbe); gemeldete Ausfälle werden durch den verfügbaren Spieler derselben Position mit den meisten Einsätzen zuletzt ersetzt. Im Backtest stimmen im Schnitt knapp 9 von 11 Spielern (docs/21_aufstellung.md). Die bestätigte Aufstellung erscheint 20–40 Minuten vor Anpfiff (Abruf alle 15 Minuten)."
            : "Offizielle Aufstellung laut API-Football."}
        </p>
      </div>
      {!empty && (
        <>
          <div className="mx-auto hidden max-w-4xl sm:block"><Pitch data={data} o="horizontal" /></div>
          <div className="mx-auto max-w-md sm:hidden"><Pitch data={data} o="vertical" /></div>
        </>
      )}
      <div className="grid gap-4 lg:grid-cols-2">
        <TeamCard team={data.fixture.home} lineup={lu.home} predicted={predicted} />
        <TeamCard team={data.fixture.away} lineup={lu.away} predicted={predicted} />
      </div>
    </div>
  );
}

import type { Market, Selection } from "./types";

export function market(markets: Market[], key: string, line: number | null = null): Market | undefined {
  return markets.find((m) => m.market === key && (line === null ? m.line === null : m.line === line));
}

export function selection(markets: Market[], key: string, sel: string, line: number | null = null): Selection | undefined {
  return market(markets, key, line)?.selections.find((s) => s.selection === sel);
}

/** All lines of an over/under or handicap market, sorted by line. */
export function lines(markets: Market[], key: string): Market[] {
  return markets.filter((m) => m.market === key && m.line !== null).sort((a, b) => (a.line ?? 0) - (b.line ?? 0));
}

/** Expected total goals from the exact-goals distribution (6+ counted as 6.5). */
export function expectedGoals(markets: Market[]): number | null {
  const m = market(markets, "exact_goals");
  if (!m) return null;
  return m.selections.reduce((sum, s) => sum + (s.selection === "6+" ? 6.5 : Number(s.selection)) * s.probability, 0);
}

export const lineLabel = (line: number | null) => (line === null ? "" : (line % 1 ? line.toFixed(1) : String(line)).replace(".", ","));

/** Most likely selection of a market. */
export function pick(m: Market | undefined): Selection | undefined {
  return m?.selections.reduce((best, s) => (s.probability > best.probability ? s : best));
}

/** Selection label with team names instead of "Heim"/"Gast". */
export function selectionLabel(s: Selection, home: string, away: string): string {
  if (s.selection === "H" || s.selection === "home") return home;
  if (s.selection === "A" || s.selection === "away") return away;
  if (s.selection === "D") return "Remis";
  return s.label;
}

export const signedLine = (line: number) => `${line > 0 ? "+" : line < 0 ? "−" : ""}${lineLabel(Math.abs(line))}`;

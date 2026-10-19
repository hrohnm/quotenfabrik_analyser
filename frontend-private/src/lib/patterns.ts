import { num, pct } from "./format";
import type { Pattern } from "./types";

/** Rates (0–1 with a league baseline) as percent, everything else (goals, xG, points, differences) as number. */
export function isRate(p: Pattern): boolean {
  if (p.value === null) return false;
  return p.baseline !== null && p.baseline <= 1 && p.value <= 1 && !/goals|xg|ppg|diff/.test(p.key);
}

export const patternValue = (p: Pattern) => (p.value === null ? "–" : isRate(p) ? pct(p.value, 0) : num(p.value));

/** Strongest signals first: flagged patterns sorted by distance to the league baseline. */
export function signals(patterns: Pattern[]): Pattern[] {
  return patterns
    .filter((p) => p.signal !== null && p.group !== "scorers")
    .sort((a, b) => Math.abs((b.value ?? 0) - (b.baseline ?? 0)) - Math.abs((a.value ?? 0) - (a.baseline ?? 0)));
}

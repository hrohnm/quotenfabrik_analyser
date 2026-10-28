import { countryLabel } from "@/lib/format";

export type LeagueInfo = { id: number; name: string; country?: string | null; flag?: string | null; cup?: boolean; type?: "league" | "cup" };
export type CountryGroup<T extends LeagueInfo> = { key: string; label: string; flag: string | null; leagues: T[] };

const INTERNATIONAL = "World";

/** Leagues grouped by country in configured order (first appearance), international competitions last;
 * within a country the leagues come before the cups. */
export function groupByCountry<T extends LeagueInfo>(leagues: T[]): CountryGroup<T>[] {
  const groups = new Map<string, CountryGroup<T>>();
  for (const l of leagues) {
    const key = l.country || INTERNATIONAL;
    if (!groups.has(key)) {
      groups.set(key, { key, label: key === INTERNATIONAL ? "International" : countryLabel(key), flag: l.flag ?? null, leagues: [] });
    }
    const g = groups.get(key)!;
    g.flag = g.flag ?? l.flag ?? null;
    g.leagues.push(l);
  }
  const out = [...groups.values()];
  for (const g of out) g.leagues.sort((a, b) => Number(a.type === "cup") - Number(b.type === "cup"));
  return out.sort((a, b) => Number(a.key === INTERNATIONAL) - Number(b.key === INTERNATIONAL));
}

export const isCup = (l: { type?: string; cup?: boolean } | null | undefined) => l?.type === "cup" || !!l?.cup;

/** European cup (international competition) vs. national league or cup. */
export const isInternational = (l: { country?: string | null; cup?: boolean } | null | undefined) => !!l?.cup || l?.country === INTERNATIONAL;

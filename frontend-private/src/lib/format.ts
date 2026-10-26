const TZ = "Europe/Berlin";

export const pct = (v: number | null | undefined, digits = 1) =>
  v === null || v === undefined || Number.isNaN(v) ? "–" : `${(v * 100).toFixed(digits).replace(".", ",")} %`;

export const odd = (v: number | null | undefined) => (v === null || v === undefined ? "–" : v.toFixed(2).replace(".", ","));

export const num = (v: number | null | undefined, digits = 2) =>
  v === null || v === undefined ? "–" : v.toFixed(digits).replace(".", ",");

export const signedPct = (v: number | null | undefined) =>
  v === null || v === undefined ? "–" : `${v >= 0 ? "+" : "−"}${Math.abs(v * 100).toFixed(1).replace(".", ",")} %`;

export const time = (iso: string) =>
  new Date(iso).toLocaleTimeString("de-DE", { hour: "2-digit", minute: "2-digit", timeZone: TZ });

export const dateLong = (iso: string) =>
  new Date(iso).toLocaleDateString("de-DE", { weekday: "long", day: "2-digit", month: "long", year: "numeric", timeZone: TZ });

export const dateShort = (iso: string) =>
  new Date(iso).toLocaleDateString("de-DE", { day: "2-digit", month: "2-digit", year: "2-digit", timeZone: TZ });

export const weekday = (isoDate: string) =>
  new Date(`${isoDate}T12:00:00Z`).toLocaleDateString("de-DE", { weekday: "short", timeZone: TZ });

export const dayMonth = (isoDate: string) =>
  new Date(`${isoDate}T12:00:00Z`).toLocaleDateString("de-DE", { day: "2-digit", month: "2-digit", timeZone: TZ });

const COUNTRIES: Record<string, string> = {
  World: "International", Germany: "Deutschland", England: "England", Spain: "Spanien", Italy: "Italien", France: "Frankreich",
  Netherlands: "Niederlande", Portugal: "Portugal", Belgium: "Belgien", Turkey: "Türkei", Scotland: "Schottland",
  Austria: "Österreich", Switzerland: "Schweiz", Denmark: "Dänemark", Sweden: "Schweden", Norway: "Norwegen",
  Poland: "Polen", Greece: "Griechenland", "Czech-Republic": "Tschechien", Croatia: "Kroatien", Serbia: "Serbien",
  Ukraine: "Ukraine", Russia: "Russland", USA: "USA", Brazil: "Brasilien", Argentina: "Argentinien", Japan: "Japan",
};
/** German name of an API-Football country. */
export const countryLabel = (c: string | null | undefined) => (c ? COUNTRIES[c] ?? c : "");
export const seasonLabel = (s: number) => `${s}/${String((s + 1) % 100).padStart(2, "0")}`;

export function berlinToday(): string {
  return new Date().toLocaleDateString("en-CA", { timeZone: TZ });
}

export function addDays(isoDate: string, days: number): string {
  const d = new Date(`${isoDate}T12:00:00Z`);
  d.setUTCDate(d.getUTCDate() + days);
  return d.toISOString().slice(0, 10);
}

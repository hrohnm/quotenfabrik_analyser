import type { Day, Fixture, FixtureDetail, Meta } from "./types";

// Server components call the backend directly; browser code uses the /api rewrite (see next.config.ts).
const SERVER_API = process.env.API_URL ?? "http://127.0.0.1:8000";

/** status 0 = backend not reachable */
export class ApiError extends Error {
  constructor(message: string, public status: number) {
    super(message);
  }
}

function base() {
  return typeof window === "undefined" ? SERVER_API : "";
}

export async function api<T>(path: string, params?: Record<string, string | number | null | undefined>): Promise<T> {
  const qs = new URLSearchParams();
  for (const [k, v] of Object.entries(params ?? {})) {
    if (v !== null && v !== undefined && v !== "") qs.set(k, String(v));
  }
  const url = `${base()}/api${path}${qs.size ? `?${qs}` : ""}`;
  let res: Response;
  try {
    res = await fetch(url, { cache: "no-store" });
  } catch {
    throw new ApiError(`API nicht erreichbar (${base() || "/api"}). Läuft das Backend auf Port 8000?`, 0);
  }
  if (!res.ok) throw new ApiError(`API ${path}: HTTP ${res.status}`, res.status);
  return res.json() as Promise<T>;
}

export const getMeta = () => api<Meta>("/meta");
export const getDays = (from: string, to: string) => api<Day[]>("/days", { from, to });
export const getFixtures = (date: string) => api<Fixture[]>("/fixtures", { date });
export const getFixture = (id: number | string) => api<FixtureDetail>(`/fixtures/${id}`);

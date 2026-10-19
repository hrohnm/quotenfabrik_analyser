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
  if (!res.ok) throw new ApiError(await errorText(res, path), res.status);
  return res.json() as Promise<T>;
}

/** German error message from FastAPI ({"detail": "..."}) or a generic one. */
async function errorText(res: Response, path: string): Promise<string> {
  try {
    const body = await res.json();
    if (typeof body?.detail === "string") return body.detail;
  } catch {
    /* no JSON body */
  }
  return `API ${path}: HTTP ${res.status}`;
}

/** POST / PUT / PATCH with a JSON body (browser only, via the /api rewrite). */
export async function apiSend<T>(method: "POST" | "PUT" | "PATCH", path: string, body: unknown): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${base()}/api${path}`, { method, headers: { "content-type": "application/json" }, body: JSON.stringify(body) });
  } catch {
    throw new ApiError("API nicht erreichbar. Läuft das Backend auf Port 8000?", 0);
  }
  if (!res.ok) throw new ApiError(await errorText(res, path), res.status);
  return res.json() as Promise<T>;
}

export const getMeta = () => api<Meta>("/meta");
export const getDays = (from: string, to: string, league?: string) => api<Day[]>("/days", { from, to, league });
export const getFixtures = (date: string, league?: string) => api<Fixture[]>("/fixtures", { date, league });
export const getFixture = (id: number | string) => api<FixtureDetail>(`/fixtures/${id}`);

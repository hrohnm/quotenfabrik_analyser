export type ApiStatus = {
  keys: { api_football: boolean; oddspapi: boolean };
  api_football: { plan?: string; end?: string; used?: number; limit?: number; error?: string } | null;
  oddspapi: { plan?: string; used?: number; limit?: number; error?: string } | null;
  backups: Backup[];
  settings_reserve: { api: number; oddspapi: number };
};

export type Backup = { name: string; size: number; created_at: string };

export type JobStep = { name: string; label: string; status: "pending" | "running" | "done" | "skipped" | "failed"; message: string | null; log: string[] };
export type Job = {
  id: number;
  kind: "add_league" | "add_ratings" | "models" | "picks" | "backup";
  params: Record<string, unknown>;
  status: "queued" | "running" | "done" | "failed";
  steps: JobStep[];
  error: string | null;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
};

export type ConfiguredLeague = {
  id: number;
  name: string;
  country: string | null;
  logo: string;
  fd_code: string | null;
  oddspapi_tournament: number | null;
  first_season: number;
  active: boolean;
  kind: "full" | "ratings" | "cup";
  fixtures: number;
  finished: number;
  seasons: [number, number] | null;
};

export type LeagueSearchResult = {
  id: number;
  name: string;
  type: string;
  logo: string;
  country: string | null;
  flag: string | null;
  seasons: number[];
  current: number | null;
  details_from: number | null;
  configured: boolean;
  suggested_fd_code: string | null;
};

export type LeaguePreset = { id: number; name: string; country: string; logo: string; seasons_from: number; kind: "ratings" | "cup"; configured: "full" | "ratings" | "cup" | null };

export type Tournament = { id: number; name: string; category: string };

export type SettingField = {
  key: string;
  group: string;
  label: string;
  help: string;
  type: "float" | "int" | "choice";
  default: number | string;
  min: number | null;
  max: number | null;
  choices: string[];
  percent: boolean;
  value: number | string;
};

export type Estimate = { seasons: [number, number] | null; total: number; fixtures: number; details: number; half_stats: number; injuries: number };

export type Team = { id: number; name: string; logo?: string | null };

export type FixtureSummary = {
  source: "forecast" | "backtest";
  probabilities: Partial<Record<"home" | "draw" | "away" | "over25" | "btts", number>>;
  outcomes: Partial<Record<"home" | "draw" | "away" | "over25" | "btts", boolean | null>>;
  pick_1x2?: "home" | "draw" | "away";
  pick_1x2_hit?: boolean | null;
};

export type Fixture = {
  id: number;
  league_id: number;
  season: number;
  round: string | null;
  matchday: number | null;
  kickoff: string;
  status: string;
  finished: boolean;
  venue?: string | null;
  referee?: string | null;
  home: Team;
  away: Team;
  score: { ft: [number | null, number | null]; ht: [number | null, number | null] };
  prediction?: FixtureSummary | null;
};

export type Day = { date: string; fixtures: number; finished: number };

export type Selection = {
  selection: string;
  label: string;
  probability: number;
  fair_odd: number | null;
  outcome: boolean | null;
};

export type Market = {
  group: string;
  group_label: string;
  market: string;
  label: string;
  line: number | null;
  selections: Selection[];
};

export type Scorer = {
  player_id: number;
  name?: string;
  team_id?: number | null;
  position?: string | null;
  is_starter?: boolean | null;
  goals?: number | null;
  anytime?: number;
  anytime_outcome?: boolean | null;
  first?: number;
  first_outcome?: boolean | null;
};

export type Pattern = {
  group: string;
  key: string;
  label: string;
  scope: "home" | "away" | "match";
  value: number | null;
  n: number | null;
  baseline: number | null;
  signal: "high" | "low" | null;
  details: Record<string, number> | null;
};

export type TeamStats = Record<string, number | null>;

export type FixtureDetail = {
  fixture: Fixture;
  prediction: { kind: "forecast" | "backtest"; predicted_at: string | null } | null;
  markets: Market[];
  scorers: Scorer[];
  patterns: Pattern[];
  stats: { home: Record<string, TeamStats>; away: Record<string, TeamStats> };
  goals: { minute: number; extra_minute: number | null; team_id: number; player_name: string; detail: string; comments: string | null }[];
};

export type Meta = {
  leagues: { id: number; name: string; country: string }[];
  seasons: number[];
  teams: Team[] & { logo_url?: string }[];
  groups: Record<string, string>;
  market_labels: Record<string, string>;
  selection_labels: Record<string, string>;
  markets: { group: string; market: string; line: number | null; selections: string[] }[];
};

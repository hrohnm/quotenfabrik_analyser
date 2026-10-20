export type Team = { id: number; name: string; logo?: string | null };

export type FixtureSummary = {
  source: "forecast" | "backtest";
  probabilities: Partial<Record<"home" | "draw" | "away" | "over25" | "btts", number>>;
  outcomes: Partial<Record<"home" | "draw" | "away" | "over25" | "btts", boolean | null>>;
  pick_1x2?: "home" | "draw" | "away";
  pick_1x2_hit?: boolean | null;
};

export type League = { id: number; name: string; logo?: string | null };

export type PickReason = { label: string; value: number | null; baseline: number | null; n: number | null; signal: "high" | "low" };

export type Pick = {
  rank: number;
  group: string;
  market: string;
  selection: string;
  line: number | null;
  label: string;
  probability: number;
  fair_odd: number | null;
  base_rate: number | null;
  outcome: boolean | null;
  reasons: PickReason[];
};

export type PickProfile = { key: string; label: string; min_p: number; max_p: number; default: boolean };

export type PickRate = { n: number; hit_rate: number | null; expected: number | null };
export type ComboRate = { n: number; hit_rate?: number; expected_naive?: number; fair_odd_median?: number };
export type PickStats = {
  profiles: { profile: string; label: string; singles: PickRate; combo: ComboRate }[];
  profile: string;
  detail: {
    singles: PickRate;
    combo: ComboRate;
    hits_distribution: Record<string, number | null>;
    per_rank: (PickRate & { rank: number })[];
    per_market: (PickRate & { market: string; selection: string; line: number | null; label: string })[];
    per_season: (PickRate & { season: number; combo: ComboRate })[];
    calibration: (PickRate & { bin: string })[];
    reasons: { with: PickRate; without: PickRate };
  };
};

export type Fixture = {
  id: number;
  league_id: number;
  league?: League;
  season: number;
  round: string | null;
  /** German label of the round, e.g. "Achtelfinale" or "Ligaphase, 3. Spieltag" */
  round_label?: string | null;
  /** European cup (results only: no goalscorers, patterns or statistics) */
  cup?: boolean;
  /** Second leg of a cup tie: first leg, score from the perspective of this fixture (home:away) */
  first_leg?: { fixture_id: number; kickoff: string; finished: boolean; score: [number | null, number | null] | null } | null;
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
  picks?: Pick[];
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
  picks: Record<string, Pick[]>;
  stats: { home: Record<string, TeamStats>; away: Record<string, TeamStats> };
  goals: { minute: number; extra_minute: number | null; team_id: number; player_id: number | null; player_name: string; detail: string; comments: string | null }[];
};

export type Meta = {
  leagues: { id: number; name: string; country: string; logo?: string }[];
  seasons: number[];
  teams: Team[] & { logo_url?: string }[];
  groups: Record<string, string>;
  pick_profiles: PickProfile[];
  market_labels: Record<string, string>;
  selection_labels: Record<string, string>;
  markets: { group: string; market: string; line: number | null; selections: string[] }[];
};

export type ComboLeg = {
  fixture_id: number;
  kickoff: string;
  league: { id: number; logo?: string | null };
  home: Team;
  away: Team;
  market: string;
  selection: string;
  line: number | null;
  label: string;
  probability: number;
  /** estimated bookmaker odds (fair odds minus margin) */
  odds: number;
  outcome: boolean | null;
};

export type DayCombo = {
  kind: "tore" | "team_tore" | "doppelte_chance";
  label: string;
  odds: number;
  probability: number;
  outcome: boolean | null;
  legs: ComboLeg[];
};

export type BetSource = "tageskombi" | "tipps" | "manuell";
export type BetStatus = "open" | "won" | "lost" | "void";

export type BetLegItem = {
  fixture_id: number | null;
  market: string | null;
  selection: string | null;
  line: number | null;
  label: string;
  probability: number | null;
  odds: number | null;
  outcome: boolean | null;
  kickoff: string | null;
  fixture_status: string | null;
  ft_home: number | null;
  ft_away: number | null;
};

export type BetItem = {
  id: number;
  placed_at: string;
  source: BetSource;
  label: string;
  bookmaker: string;
  stake: number;
  odds: number;
  probability: number | null;
  status: BetStatus;
  payout: number | null;
  settled_at: string | null;
  notes: string | null;
  legs: BetLegItem[];
};

export type BetBlock = {
  n: number;
  won?: number;
  stake?: number;
  return?: number;
  profit?: number;
  roi?: number | null;
  hit_rate?: number;
  expected_hit_rate?: number | null;
  expected_profit?: number | null;
  avg_odds?: number;
};

export type BetStats = { total: BetBlock; open: number; by_source: Record<string, BetBlock>; curve: { at: string; profit: number }[] };

export type NewBetLeg = Omit<BetLegItem, "outcome" | "kickoff" | "fixture_status" | "ft_home" | "ft_away">;

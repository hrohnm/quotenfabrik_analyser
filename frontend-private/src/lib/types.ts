export type Team = { id: number; name: string; logo?: string | null };

export type FixtureSummary = {
  source: "forecast" | "backtest";
  probabilities: Partial<Record<"home" | "draw" | "away" | "over25" | "btts", number>>;
  outcomes: Partial<Record<"home" | "draw" | "away" | "over25" | "btts", boolean | null>>;
  pick_1x2?: "home" | "draw" | "away";
  /** Betano 1X2 odds with Pinnacle and model edge (OddsPapi, last price before kickoff) */
  betano?: Partial<Record<"home" | "draw" | "away", BookPrices>>;
  pick_1x2_hit?: boolean | null;
};

export type League = { id: number; name: string; logo?: string | null };

export type PickReason = { label: string; value: number | null; baseline: number | null; n: number | null; signal: "high" | "low" };

/** Bookmaker prices (OddsPapi, last price before kickoff): Betano odds, Pinnacle without margin, model edge. */
export type BookPrices = {
  betano?: number | null;
  /** Pinnacle probability without margin */
  pinnacle?: number | null;
  /** model probability × Betano odds − 1 */
  edge?: number | null;
};

export type Pick = BookPrices & {
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

export type Selection = BookPrices & {
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
  /** match events for the timeline (goals with the score after them, cards, substitutions, VAR) */
  events?: MatchEvent[];
  /** last matches in all competitions before kickoff and the form (points above/below the model's expectation) */
  form?: Record<"home" | "away", TeamForm>;
  /** playing style before kickoff, ranked against the teams of the competition (null: too few matches with statistics) */
  style?: Record<"home" | "away", TeamStyle | null>;
  /** generated match preview in German (rules over the data above, only information from before kickoff) */
  preview?: { headline: string; summary: string; sections: { title: string; text: string }[] } | null;
  /** last Betano price change; closing = prices are the last ones before kickoff */
  odds?: { betano_at: string | null; closing: boolean };
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

export type ComboLeg = BookPrices & {
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
  /** Betano odds, or estimated (fair odds minus margin) when OddsPapi has no price */
  odds: number;
  odds_source: "betano" | "geschätzt";
  outcome: boolean | null;
};

export type DayCombo = {
  kind: "tore" | "team_tore" | "doppelte_chance";
  label: string;
  odds: number;
  /** all legs priced with real Betano odds */
  real_odds: boolean;
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
  /** payout entered by hand (cash-out, boost, …), not stake × odds */
  payout_manual: boolean;
  settled_at: string | null;
  notes: string | null;
  legs: BetLegItem[];
  /** placed in the current evaluation period (after the last reset) */
  in_period: boolean;
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

export type TeamForm = {
  form: {
    matches: number;
    ppg: number | null;
    goal_diff: number | null;
    expected_ppg: number | null;
    /** points minus expected points per match (null with fewer than 4 predicted matches) */
    residual: number | null;
    n_expected: number;
    /** S/U/N, oldest first */
    sequence: string;
    signal: "high" | "low" | null;
  };
  matches: {
    fixture_id: number;
    kickoff: string;
    league: { id: number; name: string | null; logo: string };
    round_label: string | null;
    venue: "home" | "away";
    opponent: { id: number; name: string };
    gf: number;
    ga: number;
    result: "S" | "U" | "N";
    points: number;
    xpts: number | null;
  }[];
};

export type StyleMetric = {
  key: string;
  label: string;
  group: "control" | "attack" | "finishing" | "defence" | "intensity";
  /** pct/ratio: 0–1 shown as %, pp: difference in percentage points, num: per match */
  unit: "pct" | "ratio" | "pp" | "num";
  /** which direction is good ('' = style only) */
  better: "high" | "low" | "";
  value: number | null;
  /** rank among the competition's teams, 0 = lowest value, 1 = highest */
  percentile: number | null;
  league_avg: number | null;
};

export type TeamStyle = { matches: number; xg_matches: number; peers: number; labels: string[]; metrics: StyleMetric[] };

export type Bankroll = {
  start: number;
  deposits: number;
  withdrawals: number;
  profit: number;
  open_stakes: number;
  balance: number;
  available: number;
  roi: number | null;
  configured: boolean;
};

export type BankrollTransaction = { id: number; at: string; kind: "start" | "deposit" | "withdrawal"; amount: number; note: string | null };

export type BetsResponse = {
  bets: BetItem[];
  stats: BetStats;
  bankroll: Bankroll;
  transactions: BankrollTransaction[];
  /** start of the current evaluation period (last reset), null = all time */
  period_start: string | null;
  earlier_bets: number;
};

export type MatchEvent = {
  minute: number | null;
  extra_minute: number | null;
  side: "home" | "away";
  kind: "goal" | "penalty" | "own_goal" | "missed_penalty" | "yellow" | "second_yellow" | "red" | "sub" | "var";
  player: string | null;
  /** goals: assist; substitutions: player coming on */
  related: string | null;
  detail: string | null;
  comments: string | null;
  /** score after a goal (home, away) */
  score?: [number, number];
};

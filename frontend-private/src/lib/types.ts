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
  /** generated explanation: why this pick, why the model considers it likely */
  explain?: { why: string[]; likely: string[] };
  /** when the pick was published (day frozen, else forecast) and the Betano odds at that time */
  taken_at?: string | null;
  betano_taken?: number | null;
  /** closing line value: odds taken × Pinnacle probability without margin (now / at kickoff) − 1 */
  clv?: number | null;
};

/** Same-game combo of the picks of a fixture: joint probability from the model (the picks are correlated) and
 * the estimated Betano Bet Builder odds. */
export type PickCombo = {
  /** product of the single probabilities (ignores the correlation) */
  naive: number;
  probability: number | null;
  /** joint / product on the model's goal grid (> 1: the picks tend to come true together) */
  factor: number | null;
  fair_odd: number | null;
  betano_product: number | null;
  /** estimate: product of the Betano single odds ÷ factor */
  builder_odds: number | null;
};

/** Closing line value of a set of picks (``/stats/clv``). */
export type ClvRow = {
  key: string | number;
  label: string;
  n: number;
  fixtures?: number;
  odds?: number;
  clv?: number | null;
  clv_se?: number | null;
  baseline?: number | null;
  delta?: number | null;
  beat_close?: number;
  worse_close?: number;
  hit_rate?: number | null;
  roi?: number | null;
};
export type ClvResult = {
  picks: number;
  fixtures?: number;
  from?: string;
  to?: string;
  total?: ClvRow;
  sources?: ClvRow[];
  profiles?: ClvRow[];
  groups?: ClvRow[];
  leads?: ClvRow[];
  leagues?: ClvRow[];
  value?: ClvRow | null;
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
  pick_combo?: PickCombo | null;
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
  pick_combos?: Record<string, PickCombo>;
  stats: { home: Record<string, TeamStats>; away: Record<string, TeamStats> };
  goals: { minute: number; extra_minute: number | null; team_id: number; player_id: number | null; player_name: string; detail: string; comments: string | null }[];
  /** match events for the timeline (goals with the score after them, cards, substitutions, VAR) */
  events?: MatchEvent[];
  lineups?: Lineups | null;
  /** schedule and absences (facts, not used by the model) */
  context?: { home: TeamContext; away: TeamContext };
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
  /** time the combos of the day were frozen (morning job); null = computed now (provisional or backtest) */
  frozen_at: string | null;
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

export type LineupPlayer = {
  player_id: number;
  name: string | null;
  number: number | null;
  pos: "G" | "D" | "M" | "F" | null;
  grid: string | null;
  replaces?: string | null; // expected XI: absent player whose slot he takes
  questionable?: boolean;
  absent?: boolean;
};
export type Absence = { player_id: number; name: string | null; type: string | null; reason: string | null };
type ShirtColors = { primary?: string; number?: string; border?: string };
export type TeamLineup = {
  colors: { player?: ShirtColors; goalkeeper?: ShirtColors } | null;
  missing: Absence[];
  formation: string | null;
  start: LineupPlayer[];
  bench?: LineupPlayer[];
  coach?: string | null;
  basis?: { fixture_id: number; kickoff: string; opponent: string | null; home: boolean } | null;
};
export type Lineups = { status: "confirmed" | "predicted"; home: TeamLineup; away: TeamLineup };

export type TableRow = {
  rank: number;
  team_id: number;
  played: number;
  won: number;
  drawn: number;
  lost: number;
  gf: number;
  ga: number;
  gd: number;
  points: number;
  /** last results, oldest first: S / U / N */
  form: string;
};
export type LeaguePlayer = { rank: number; player_id: number; name: string; team_id: number; goals: number; assists: number; penalties?: number };
export type LeagueOverview = {
  league: { id: number; name: string; logo: string } | null;
  season: number;
  group: string | null;
  teams: Record<number, Team>;
  home_id: number;
  away_id: number;
  table: { total: TableRow[]; home: TableRow[]; away: TableRow[]; before: TableRow[] } | null;
  scorers: LeaguePlayer[];
  assists: LeaguePlayer[];
  team_scorers: { home: LeaguePlayer[]; away: LeaguePlayer[] };
  figures: {
    matches: number;
    goals_per_match: number;
    home_win: number;
    draw: number;
    away_win: number;
    over_2_5: number;
    btts: number;
    nil_nil: number;
  } | null;
};

export type NeighbourMatch = {
  fixture_id: number;
  kickoff: string;
  days: number;
  league_id: number;
  league: string;
  cup: boolean;
  home: boolean;
  opponent: string;
  /** own goals first (previous match only) */
  score: [number, number] | null;
};
export type ContextAbsence = {
  player_id: number;
  name: string | null;
  type: "missing" | "doubtful";
  reason: string | null;
  reason_label: string;
  position: string | null;
  start_share: number;
  attack_share: number;
  regular: boolean;
};
export type TeamContext = { prev: NeighbourMatch | null; next: NeighbourMatch | null; absences: ContextAbsence[] };

export type TeamSplit = {
  played: number;
  won?: number;
  drawn?: number;
  lost?: number;
  points_per_game?: number;
  gf_per_game?: number;
  ga_per_game?: number;
  over_1_5?: number | null;
  over_2_5?: number | null;
  over_3_5?: number | null;
  btts?: number | null;
  clean_sheet?: number | null;
  failed_to_score?: number | null;
  ht_lead?: number | null;
  first_half_goals?: number | null;
  second_half_goals?: number | null;
};
export type Streak = { key: string; label: string; length: number };
export type ExpectedPoints = { matches: number; points: number; expected: number; diff_per_game: number };
export type TeamCompetition = {
  league: { id: number; name: string; logo: string; flag: string | null; cup: boolean };
  played: number;
  rank: number | null;
  points: number | null;
  teams: number | null;
  group: string | null;
};
export type TeamOverview = {
  team: Team;
  season: number;
  seasons: number[];
  competitions: TeamCompetition[];
  venue: { id: number; name: string; city: string | null; image: string } | null;
  coach: { id: number | null; name: string; photo: string | null } | null;
  form: { fixture_id: number; result: "S" | "U" | "N"; score: [number, number]; home: boolean; opponent: Team | null; league_id: number }[];
  totals: TeamSplit;
  streaks: Streak[];
  expected_points: ExpectedPoints | null;
};
export type TeamSeasonStats = {
  season: number;
  competition: number | null;
  splits: { total: TeamSplit; home: TeamSplit; away: TeamSplit } | null;
  segments?: { label: string; scored: number; conceded: number; matches: number }[];
  streaks?: Streak[];
  match_stats?: { league: { id: number; name: string | null }; rows: { key: string; label: string; team: number; against: number | null; league: number | null; matches: number }[] };
  expected_points?: ExpectedPoints | null;
};
export type SquadPlayer = {
  player_id: number;
  name: string;
  photo: string;
  position: "G" | "D" | "M" | "F" | null;
  number: number | null;
  apps: number;
  starts: number;
  minutes: number;
  goals: number;
  assists: number;
  yellow: number;
  red: number;
  rating: number | null;
  shots: number;
  key_passes: number;
  status: { type: "missing" | "doubtful"; reason: string } | null;
};
export type TeamSquad = {
  season: number;
  players: SquadPlayer[];
  common_xi: { formation: string | null; matches: number; players: { player_id: number; name: string; number: number | null; pos: string | null; starts: number; photo: string }[] } | null;
  rotation: { avg_changes: number | null; matches: number } | null;
};
export type SearchResult = {
  teams: (Team & { league_id: number | null; active: boolean })[];
  players: { id: number; name: string; photo: string; team: Team | null }[];
};

export type CompetitionLeague = { id: number; name: string; country: string | null; flag: string | null; logo: string; cup: boolean };
export type LeagueFigures = NonNullable<LeagueOverview["figures"]>;
export type KnockoutRound = {
  round: string;
  label: string | null;
  kickoff: string;
  ties: { team_a: number; team_b: number; aggregate: [number, number] | null; legs: { fixture_id: number; kickoff: string; score: [number, number] | null }[] }[];
};
export type CompetitionOverview = {
  league: CompetitionLeague;
  season: number;
  seasons: number[];
  progress: { matches: number; finished: number; matchday: number | null; matchdays: number | null; next_kickoff: string | null };
  tables: { group: string | null; rows: TableRow[] }[];
  knockout: KnockoutRound[];
  figures: LeagueFigures | null;
  teams: Record<number, Team>;
};
export type ExpectedRow = { rank: number; team_id: number; matches: number; points: number; expected: number; diff: number };
export type CompetitionTables = {
  season: number;
  group: string | null;
  groups: string[];
  tables: { total: TableRow[]; home: TableRow[]; away: TableRow[]; first_half: TableRow[]; second_half: TableRow[]; form: TableRow[] } | null;
  expected?: ExpectedRow[];
  history?: { matchdays: number[]; positions: Record<number, (number | null)[]> };
  teams?: Record<number, Team>;
};
export type TeamRanking = {
  team_id: number;
  matches: number;
  shots: number | null;
  shots_on: number | null;
  xg: number | null;
  possession: number | null;
  goals: number | null;
  conceded: number | null;
  shots_against: number | null;
  conversion: number | null;
};
export type CompetitionStats = {
  season: number;
  figures: LeagueFigures | null;
  history: (LeagueFigures & { season: number })[];
  segments: { label: string; goals: number; matches: number }[];
  halves: { first: number; second: number; matches: number } | null;
  events: { matches: number; penalties_scored: number; penalties_missed: number; own_goals: number; red_cards: number };
  per_match: Record<string, number | null>;
  teams_ranked: TeamRanking[];
  teams: Record<number, Team>;
};
export type RankedPlayer = { player_id: number; name: string; team_id: number; value: number } & Record<string, number | string | null>;
export type CompetitionPlayers = {
  season: number;
  rankings: Partial<Record<"goals" | "assists" | "points" | "goals_per_90" | "points_per_90" | "rating" | "cards", RankedPlayer[]>> & { min_minutes?: number };
  teams: Record<number, Team>;
};

export type PlayerSummary = {
  apps: number;
  starts?: number;
  minutes?: number;
  rating?: number | null;
  goals?: number;
  assists?: number;
  shots_total?: number;
  shots_on?: number;
  key_passes?: number;
  yellow?: number;
  red?: number;
  penalties_scored?: number;
  penalties_missed?: number;
  per90?: { goals: number; assists: number; shots: number; key_passes: number };
  conversion?: number | null;
  minutes_per_goal?: number | null;
};
export type PlayerOverview = {
  player: { id: number; name: string; photo: string };
  team_id: number;
  number: number | null;
  position: "G" | "D" | "M" | "F" | null;
  status: { type: "missing" | "doubtful"; reason: string } | null;
  next: { fixture_id: number; kickoff: string; league_id: number; home: boolean; opponent_id: number; p_anytime: number | null; p_first: number | null } | null;
  season: number;
  seasons: number[];
  summary: PlayerSummary;
  team_share: { goals: number | null; assists: number | null; shots: number | null; minutes: number | null } | null;
  competitions: { league_id: number; apps: number; starts: number; minutes: number; goals: number; assists: number; rating: number | null }[];
  career: { season: number; team_id: number; apps: number; minutes: number; goals: number; assists: number; rating: number | null }[];
  penalties: { scored: number; missed: number; taker: boolean };
  teams: Record<number, Team>;
  leagues: Record<number, { id: number; name: string; logo: string }>;
};
export type PlayerMatch = {
  fixture_id: number;
  kickoff: string;
  league_id: number;
  home: boolean;
  opponent_id: number;
  score: [number, number] | null;
  starter: boolean | null;
  minutes: number | null;
  goals: number | null;
  assists: number | null;
  shots: number | null;
  shots_on: number | null;
  yellow: number | null;
  red: number | null;
  rating: number | null;
  p_anytime: number | null;
  p_first: number | null;
};
export type PlayerMatches = {
  season: number;
  matches: PlayerMatch[];
  scoring: { matches: number; expected: number; actual: number; series: { fixture_id: number; expected: number; actual: number }[] } | null;
  teams: Record<number, Team>;
  leagues: Record<number, { id: number; name: string; logo: string }>;
};
export type PlayerAbsences = {
  absences: { fixture_id: number; kickoff: string; league_id: number; type: "missing" | "doubtful"; reason: string; opponent_id: number }[];
  summary: { missed: number; doubtful: number; reasons: { reason: string; matches: number }[] };
  teams: Record<number, Team>;
  leagues: Record<number, { id: number; name: string; logo: string }>;
};

export type BetsSummary = {
  bets: number;
  open: number;
  won: number;
  lost: number;
  stake: number;
  profit: number;
  roi: number | null;
  legs: number;
  legs_won: number;
  legs_settled: number;
  recent: { id: number; placed_at: string; label: string; odds: number; stake: number; status: string; payout: number | null }[];
};
export type BettingReport = {
  season: number;
  model: {
    fixtures: number;
    groups: { group: string; label: string; n: number; hit_rate: number; expected: number }[];
    markets: { market: string; line: number | null; label: string; n: number; hit_rate: number; expected: number; most_picked: string }[];
    calibration: { bin: string; n: number; predicted: number; observed: number }[];
  };
  picks: {
    profile: string;
    label: string;
    singles: { n: number; hit_rate: number | null; expected: number | null };
    combo: { n: number; hit_rate?: number; expected_naive?: number };
    markets: { label: string; n: number; hit_rate: number | null; expected: number | null }[];
  }[];
  bets: BetsSummary;
  market: {
    selections: number;
    fixtures?: number;
    groups: { group: string; label: string; n: number; payback: number | null; above_pinnacle: number | null; edge_share: number; value_bets: number; value_roi: number | null }[];
  };
};

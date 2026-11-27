export interface LedgerMeta {
  id: string;
  name: string;
  description: string;
  is_demo: boolean;
  holding_count: number;
  total_equity: number;
  is_active: boolean;
}

export interface IndexQuote {
  name: string;
  point: number | null;
  change_pct: number | null;
  is_fallback?: boolean;
}

export interface OverviewResponse {
  ledger_id: string;
  total_equity: number;
  available_cash: number;
  in_transit_cash: number;
  holding_count: number;
  today_est_pnl: number;
  today_est_pnl_pct: number;
  cumulative_pnl: number;
  cumulative_pnl_pct: number;
  is_official_nav: boolean;
  market_verdict: {
    short_label: string;
    action_tag: string;
    regime: string;
    plan_mode: string;
    detail_explanation: string;
    data_safety_note: string;
  };
  indices: Record<string, IndexQuote>;
  top_risk_alert: {
    level: string;
    dimension: string;
    title: string;
    action: string;
  } | null;
}

export interface QuantModelMeta {
  id: string;
  name: string;
  tag: string;
  recommended_tiers?: string;
  scenario: string;
  principle: string;
}

export interface GoalAnalysis {
  target_return_pct: number;
  horizon_months: number;
  required_cagr_pct: number;
  current_tier: string;
  suggested_tier: string;
  has_collision: boolean;
  collision_message: string;
  recommended_model: string;
  feasibility: string;
  feasibility_level: 'high' | 'medium' | 'low';
  historical_hit_rate_pct: number;
  end_of_period_hit_rate_pct?: number;
  conditional_win_rate_pct?: number;
  monte_carlo_prob_pct?: number;
  no_loss_rate_pct?: number;
  windows_tested: number;
  median_return_pct: number;
  p05_worst_return_pct: number;
  p95_best_return_pct: number;
  avg_reach_months: number | null;
}

export type UniverseMode = 'full_market' | 'index_only';

export interface SolvedPortfolioContext {
  riskLevel: string;
  modelId: string;
  fundCount: number;
  targetReturnPct: number;
  horizonMonths: number;
  universeMode: UniverseMode;
  fundCodes: string[];
  excludeCodes?: string[];
  includeCodes?: string[];
}

export interface ConstraintAudit {
  exclude_codes: string[];
  include_codes: string[];
  requested_include_codes?: string[];
  warnings: string[];
}

export interface BenchmarkHorizonSummary {
  return_pct: number;
  annualized_return_pct: number;
  max_drawdown_pct: number;
  sharpe_ratio: number;
  trading_days: number;
}

export interface FunnelAudit {
  universe_mode: UniverseMode;
  universe_label: string;
  total_market_funds: number;
  compliant_screened_funds: number;
  elite_lakehouse_funds: number;
  eligible_depth_funds: number;
  shortlisted_candidates: number;
  final_selected_funds: number;
  lakehouse_latest_date: string;
}

export interface RealBacktestInfo {
  is_real_nav: boolean;
  common_start_date: string;
  common_end_date?: string;
  common_trading_days?: number;
  has_early_proxy_reference?: boolean;
}

export interface LakehouseStatus {
  status: string;
  synced_at?: string;
  latest_date?: string;
  start_date?: string;
  trading_days?: number;
  elite_fund_count?: number;
  active_fund_count?: number;
  index_eligible_count?: number;
  daily_sync_at?: string;
  bucket_counts?: Record<string, number>;
}

export interface QuantSolveJobResponse {
  job_id: string;
  status: 'running' | 'done' | 'error';
  progress_pct: number;
  stage_text: string;
  elapsed_ms?: number;
  error?: string | null;
  result?: {
    blueprint: BlueprintResponse;
    backtest_curves: BacktestCurvesResponse;
  };
}

export interface SolverAudit {
  engine_version: string;
  universe_mode?: UniverseMode;
  lakehouse_enabled?: boolean;
  solver_algorithm: string;
  math_summary: string;
  candidates_screened: number;
  history_trading_days: number;
  history_range: string;
  real_nav_common_start?: string;
  is_real_nav_backtest?: boolean;
  holding_days: number;
  target_annual_return_pct: number;
  tier_max_drawdown_cap_pct: number;
  ten_dim_equity_tilt_pct: number;
  oos_conditional_win_rate_pct: number;
  monte_carlo_paths: number;
  monte_carlo_prob_pct: number;
  portfolio_vol_annual_pct: number;
  max_risk_pcr_pct: number;
  risk_budget_verdict: string;
  regime_detected: string;
  regime_recommended_model: string;
  compute_ms: number;
  from_cache: boolean;
}

export interface AllocationLogicSummary {
  headline: string;
  steps: string[];
  class_weights_pct: Record<string, number>;
}

export interface AllocationBreakdown {
  fund_code: string;
  bucket: string;
  solver_weight_pct: number;
  factor_tilt_delta_pct: number;
  final_weight_pct: number;
  risk_contribution_pcr_pct: number;
  tilt_reason: string;
  allocation_formula_text: string;
}

export interface BlueprintItem {
  fund_code: string;
  fund_name: string;
  role: string;
  bucket_label?: string;
  asset_class?: string;
  is_active_fund?: boolean;
  real_scale_yi?: number | null;
  max_star?: number;
  inception_date?: string;
  why: string;
  quant_reason?: string;
  quant_score?: number;
  factor_profile?: {
    sharpe?: number;
    calmar?: number;
    max_dd_pct?: number;
    new_high_rate_pct?: number;
    total_fee_pct?: number;
  };
  allocation_breakdown?: AllocationBreakdown;
  solver_weight_pct?: number;
  factor_tilt_delta_pct?: number;
  risk_contribution_pcr_pct?: number;
  bias_20?: number | null;
  crowding_score?: number | null;
  ret_20d?: number | null;
  quadrant_tag?: string;
  fee_note?: string;
  quota_note?: string;
  action_guide?: string;
  weight_pct: number;
  suggested_amount: number;
  daily_limit: number;
}

export interface BlueprintResponse {
  risk_level: string;
  risk_meta: { label: string; drawdown_hint: string; desc: string };
  all_risk_levels: Record<string, { label: string; drawdown_hint: string; desc: string }>;
  model: string;
  model_meta: QuantModelMeta;
  all_models: QuantModelMeta[];
  universe_mode?: UniverseMode;
  fund_count: number;
  total_amount: number;
  market_regime: string;
  goal_analysis?: GoalAnalysis;
  solver_audit?: SolverAudit;
  constraint_audit?: ConstraintAudit;
  funnel_audit?: FunnelAudit;
  real_bt_info?: RealBacktestInfo;
  allocation_logic_summary?: AllocationLogicSummary;
  portfolio_weights?: Record<string, number>;
  count: number;
  items: BlueprintItem[];
}

export interface BacktestSummaryResponse {
  annualized_return_pct: number | null;
  live_calibrated_cagr_pct: number | null;
  max_drawdown_pct: number | null;
  sharpe_ratio: number | null;
  win_rate_pct: string | number | null;
  monthly_win_rate_pct: string | number | null;
  oos_sample_count: number;
  oos_excess_alpha_pct: number | null;
}

export interface BacktestMetrics {
  period_return_pct: number;
  theoretical_return_pct: number;
  annualized_return_pct: number | null;
  hs300_return_pct: number;
  excess_return_pct: number;
  max_drawdown_pct: number;
  hs300_mdd_pct: number;
  win_rate_label: string;
  win_rate_pct: number;
  win_rate_detail: string;
  sharpe_ratio: number;
  trading_days: number;
}

export interface GoalReconciliation {
  status: 'aligned' | 'backtest_below_goal' | 'backtest_above_goal';
  badge: string;
  headline: string;
  compare_metric_label: string;
  goal_comparable_pct: number;
  backtest_comparable_pct: number;
  gap_pct: number;
  goal_target_return_pct: number;
  goal_horizon_months: number;
  goal_required_cagr_pct: number;
  backtest_period_label: string;
  backtest_period_return_pct: number;
  reasons: Array<{ title: string; detail: string }>;
  why_still_recommend: string;
}

export interface ExtremeRecoveryEvent {
  id: string;
  name: string;
  desc: string;
  window: string;
  peak_date: string;
  trough_date: string;
  recovery_date: string;
  max_dd_pct: number;
  h300_mdd_pct: number;
  excess_defense_pct: number;
  fall_tdays: number;
  trough_to_recovery_tdays: number;
  trough_to_recovery_months: number;
  total_underwater_tdays: number;
  total_underwater_months: number;
  recovered: boolean;
  h300_total_underwater_tdays: number;
  h300_total_underwater_months: number;
  h300_recovered: boolean;
  days_faster_than_hs300: number;
  is_proxy_simulated?: boolean;
  proxy_note?: string;
}

export interface ExtremeFullCycleItem {
  cycle_id: string;
  cycle_label: string;
  peak1_date: string;
  trough_date: string;
  recovery_date: string;
  next_peak_date: string;
  recovered: boolean;
  drawdown_pct: number;
  fall_tdays: number;
  trough_to_recovery_tdays: number;
  underwater_tdays: number;
  underwater_months: number;
  expansion_tdays: number;
  full_cycle_tdays: number;
  full_cycle_months: number;
  peak_to_next_peak_return_pct: number;
  trough_to_next_peak_return_pct: number;
  cycle_cagr_pct: number;
}

export interface ExtremeCycleSummary {
  completed_cycles_count: number;
  total_cycles_count: number;
  dd_threshold_pct: number;
  avg_drawdown_pct: number;
  max_drawdown_pct: number;
  avg_underwater_tdays: number;
  avg_underwater_months: number;
  max_underwater_tdays: number;
  max_underwater_months: number;
  avg_full_cycle_tdays: number;
  avg_full_cycle_months: number;
  full_cycle_months_range: [number, number];
  avg_peak_to_next_peak_return_pct: number;
  median_peak_to_next_peak_return_pct: number;
  p75_peak_to_next_peak_return_pct: number;
  peak_to_next_peak_range_pct: [number, number];
  avg_trough_to_next_peak_return_pct: number;
  median_trough_to_next_peak_return_pct: number;
  trough_to_next_peak_range_pct: [number, number];
}

export interface ExtremeCycleAnalysis {
  status: string;
  date_range: string;
  trading_days_analyzed: number;
  plain_headline: string;
  expected_recovery: {
    n_simulations: number;
    horizon_days: number;
    extreme_shock_var95_pct: number;
    extreme_shock_cvar99_pct: number;
    tail_paths_count: number;
    recovery_prob_within_3y_pct: number;
    trough_to_recovery_tdays: {
      normal_median?: number;
      normal_median_months?: number;
      median: number;
      p75: number;
      p90: number;
      median_months: number;
    };
    peak_to_recovery_tdays: {
      normal_median?: number;
      normal_median_months?: number;
      median: number;
      p75: number;
      p90: number;
      median_months: number;
    };
    hs300_peak_to_recovery_median_tdays: number;
    hs300_peak_to_recovery_median_months: number;
    hs300_extreme_cvar99_pct: number;
    days_faster_than_hs300: number;
  };
  historical_recovery: {
    events: ExtremeRecoveryEvent[];
    avg_trough_to_recovery_tdays: number;
    avg_trough_to_recovery_months: number;
    avg_underwater_tdays: number;
    avg_underwater_months: number;
    max_underwater_tdays: number;
    max_underwater_months: number;
    hs300_avg_underwater_tdays: number;
    hs300_avg_underwater_months: number;
    days_faster_than_hs300: number;
  };
  full_cycles: {
    items: ExtremeFullCycleItem[];
    summary: ExtremeCycleSummary;
    hs300_summary: ExtremeCycleSummary;
  };
  take_profit_plan: {
    recommended_zone_pct: [number, number];
    core_cycle_zone_pct: [number, number];
    trailing_stop_drawdown_pct: number;
    current_cycle_position: {
      tag: string;
      level: 'accumulate' | 'hold_watch' | 'take_profit';
      erp_percentile: number;
      bias_20: number;
      advice: string;
    };
    anchors: Array<{
      step: number;
      code: string;
      title: string;
      trigger_label: string;
      action: string;
      rationale: string;
    }>;
  };
}

export interface WeightVsPcrItem {
  fund_code: string;
  fund_name: string;
  short_name: string;
  bucket_label: string;
  weight_pct: number;
  pcr_pct: number;
}

export interface BacktestCurvesResponse {
  status: string;
  tier: string;
  model?: string;
  universe_mode?: UniverseMode;
  fund_count?: number;
  target_return_pct?: number;
  horizon_months?: number;
  period?: string;
  period_label?: string;
  date_range?: string;
  mode: string;
  primary_name: string;
  secondary_name: string;
  portfolio_weights?: Record<string, number>;
  weight_vs_pcr?: WeightVsPcrItem[];
  solver_audit?: SolverAudit | null;
  funnel_audit?: FunnelAudit | null;
  real_bt_info?: RealBacktestInfo | null;
  goal_reconciliation?: GoalReconciliation | null;
  extreme_cycle_analysis?: ExtremeCycleAnalysis | null;
  metrics?: BacktestMetrics;
  benchmark_horizons?: {
    y1: BenchmarkHorizonSummary;
    all: BenchmarkHorizonSummary;
  };
  dates: string[];
  nav: {
    primary: number[];
    primary_otc: number[];
    secondary: number[];
    hs300: number[];
    dividend: number[];
    bond: number[];
  };
  cagr: {
    primary: number | null;
    primary_otc: number | null;
    secondary: number | null;
    hs300: number | null;
    dividend: number | null;
    bond: number | null;
  };
  drawdown: {
    primary: number[];
    secondary: number[];
    hs300: number[];
  };
  allocation: {
    ashare: number[];
    bond: number[];
    gold: number[];
    spx: number[];
  };
  slices: Array<{ start: string; end: string; label: string; color: string }>;
}

export interface CrowdingPoint {
  fund_code: string;
  fund_name: string;
  short_name: string;
  bias_20: number;
  crowding_score: number;
  ret_20d: number;
  quadrant: string;
  advisory_tip: string;
  in_holdings: boolean;
}

export interface HoldingRow {
  fund_code: string;
  fund_name: string;
  asset_class?: string;
  share_class: string;
  shares: number;
  cost_price: number;
  current_nav: number;
  market_value: number;
  weight_pct?: number;
  holding_days: number;
  est_chg_pct?: number;
  official_chg_pct?: number | null;
  floating_pnl?: number;
  floating_pnl_pct?: number;
  is_official_nav: boolean;
  redemption_fee_status?: {
    fee_rate_pct: number;
    status_code: string;
    label: string;
  };
  risk_tags: string[];
}

export interface ExposureResponse {
  status: string;
  holdings_count: number;
  total_equity: number;
  asset_classes: Record<string, number>;
  target_classes?: Record<string, number>;
  top_industries: Record<string, number>;
}

export interface RiskCheckResponse {
  active_sentry: {
    alert_count?: number;
    alerts?: Array<{
      level?: string;
      dimension?: string;
      title?: string;
      message?: string;
      action?: string;
    }>;
  };
}

export interface RebalanceItem {
  fund_code?: string;
  code?: string;
  fund_name?: string;
  name?: string;
  action?: string;
  diff_amount?: number;
  amount?: number;
  reason?: string;
  fee_note?: string;
  current_weight?: number;
  target_weight?: number;
}

export interface RebalanceGroup {
  title: string;
  count: number;
  summary?: string;
  recovered_cash?: number;
  c_sell_count?: number;
  items: RebalanceItem[];
}

export interface ScenarioKpi {
  days: number;
  net_return_pct: number;
  h300_return_pct: number;
  alpha_vs_h300: number;
  mdd_pct: number;
  h300_mdd_pct: number;
  verdict: string;
}

export interface ScenarioBacktestResponse {
  start_date: string;
  tier: string;
  portfolio_name?: string;
  used_proxy_early?: boolean;
  proxy_note?: string;
  portfolio_weights?: Record<string, number> | null;
  dynamic_rebalance: boolean;
  kpis: {
    m3?: ScenarioKpi | null;
    m6?: ScenarioKpi | null;
    y1?: ScenarioKpi | null;
    all?: ScenarioKpi | null;
  };
  dates: string[];
  strategy_nav: number[];
  hs300_nav: number[];
  balanced_nav: number[];
}

export interface EtfPremiumItem {
  code: string;
  name: string;
  price: number;
  iopv: number;
  premium_pct: number;
  advice: string;
  is_offline_snapshot?: boolean;
  timestamp?: string;
  source_label?: string;
}

export interface DividendAdviceResponse {
  ledger_id: string;
  erp_percentile: number;
  recommended_mode: string;
  recommended_label: string;
  summary: string;
}

export interface QuotaSplitPlan {
  fund_code: string;
  fund_name: string;
  needs_split: boolean;
  total_amount: number;
  days_needed: number;
  daily_limit?: number;
  schedule?: Array<{ day_index?: number; date?: string; amount?: number }>;
  settlement?: { confirm_date?: string; description?: string; t_plus?: string };
}

export interface RebalanceResponse {
  ledger_id: string;
  tier?: string;
  target_source?: 'ledger_smooth' | 'full_market_solved';
  target_summary?: string;
  plan_mode: string;
  is_empty: boolean;
  goal_comparison?: {
    target_return_pct: number;
    horizon_months: number;
    tier?: string;
    before: GoalAnalysis;
    after: GoalAnalysis;
    hit_rate_delta_pct: number;
    worst_return_delta_pct: number;
  } | null;
  tail_sweep: RebalanceGroup;
  c_replace: RebalanceGroup;
  core_trades: RebalanceGroup;
  buffer_hold: RebalanceGroup;
  quota_split_plans?: QuotaSplitPlan[];
  cheat_sheet_lines: string[];
  cheat_sheet_text: string;
}

export interface FundDetailResponse {
  fund_code: string;
  fund_name: string;
  is_fallback: boolean;
  latest_nav: number;
  latest_ac_nav: number;
  nav_date: string;
  daily_return_pct: number;
  fund_type: string;
  risk_level: string;
  charts: {
    dates: string[];
    unit_nav: number[];
    ac_nav: number[];
    cum_return_pct: number[];
  };
  historical_performance: Array<{
    period: string;
    fund_return_pct: number;
    benchmark_return_pct: number | null;
    excess_return_pct: number | null;
  }>;
  historical_nav: Array<{
    date: string;
    unit_nav: number;
    ac_nav: number;
    daily_return_pct: number;
    dividend: string;
  }>;
  dca_monthly: number;
  dca_simulation: Array<{
    period: string;
    periods: number;
    monthly_amount: number;
    total_invested: number;
    final_value: number;
    profit: number;
    return_pct: number;
    annualized_pct: number;
  }>;
  analytics: {
    window_days?: number;
    window_label?: string;
    categories?: Array<{ key: string; name: string; score: number; grade: string; desc: string }>;
    sub_metrics?: {
      return_ability: Array<{ name: string; value: string; hint: string }>;
      risk_control: Array<{ name: string; value: string; hint: string }>;
      tracking_ability: Array<{ name: string; value: string; hint: string }>;
      cost_performance: Array<{ name: string; value: string; hint: string }>;
    };
  };
  managers: Array<{
    name: string;
    start_date: string;
    end_date: string;
    is_current: boolean;
    days: number;
    return_pct: number | null;
    work_time: string;
    fund_size: string;
  }>;
  holdings_distribution: {
    quarter_label: string;
    asset_allocation: Array<{ name: string; pct: number }>;
    industry_distribution: Array<{ industry: string; weight_pct: number }>;
    top_stocks: Array<{
      stock_code: string;
      stock_name: string;
      weight_pct: number;
      shares_wan: string;
      value_wan: string;
    }>;
  };
  profile: {
    full_name: string;
    short_name: string;
    fund_code: string;
    fund_type: string;
    establish_date: string;
    scale_yi: number | null;
    company: string;
    custodian: string;
    benchmark: string;
    tracking_target: string;
    risk_level: string;
  };
  notices: Array<{ id: string; title: string; date: string; category: string; url: string }>;
  product_summary: {
    operation_mode: string;
    risk_level: string;
    invest_scope: string;
    dividend_policy: string;
    official_summary_url: string;
  };
  trading_rules: {
    purchase_status: string;
    redemption_status: string;
    min_purchase: string;
    min_dca: string;
    source_rate: string;
    discount_rate: string;
    management_fee: string;
    custody_fee: string;
    sales_service_fee: string;
    purchase_tiers: Array<{ condition: string; rate: string }>;
    redemption_tiers: Array<{ condition: string; rate: string }>;
    settlement_note: string;
  };
}

const API_BASE = '';

async function requestJson<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${url}`, {
    headers: { 'Content-Type': 'application/json', ...(init?.headers || {}) },
    ...init,
  });
  if (!res.ok) {
    let detail = `请求失败 (${res.status})`;
    try {
      const err = await res.json();
      if (err?.detail) detail = String(err.detail);
    } catch {
      // ignore parse error
    }
    throw new Error(detail);
  }
  return res.json() as Promise<T>;
}

export const api = {
  getLedgers: () => requestJson<{ active_ledger_id: string; items: LedgerMeta[] }>('/api/v1/ledgers'),
  setActiveLedger: (ledger_id: string) =>
    requestJson<{ active_ledger_id: string; switched: boolean }>('/api/v1/ledgers/active', {
      method: 'POST',
      body: JSON.stringify({ ledger_id }),
    }),
  createLedger: (name: string, initial_cash = 0) =>
    requestJson<{ ledger_id: string; name: string; created: boolean }>('/api/v1/ledgers', {
      method: 'POST',
      body: JSON.stringify({ name, initial_cash }),
    }),
  getOverview: (ledgerId?: string, force = false) => {
    const q = new URLSearchParams();
    if (ledgerId) q.set('ledger_id', ledgerId);
    if (force) q.set('force', 'true');
    const qs = q.toString();
    return requestJson<OverviewResponse>(`/api/v1/overview${qs ? `?${qs}` : ''}`);
  },
  getBlueprint: (
    riskLevel: string,
    amount: number,
    fundCount = 6,
    model = 'all_weather',
    targetReturnPct = 10,
    horizonMonths = 12,
    force = false,
    universeMode: UniverseMode = 'full_market',
    excludeCodes?: string[],
    includeCodes?: string[]
  ) => {
    const q = new URLSearchParams({
      risk_level: riskLevel,
      amount: String(amount),
      fund_count: String(fundCount),
      model,
      target_return_pct: String(targetReturnPct),
      horizon_months: String(horizonMonths),
      universe_mode: universeMode,
    });
    if (force) q.set('force', 'true');
    if (excludeCodes && excludeCodes.length > 0) q.set('exclude_codes', excludeCodes.join(','));
    if (includeCodes && includeCodes.length > 0) q.set('include_codes', includeCodes.join(','));
    return requestJson<BlueprintResponse>(`/api/v1/recommend/blueprint?${q.toString()}`);
  },
  startQuantSolve: (params: {
    risk_level: string;
    amount: number;
    fund_count: number;
    model: string;
    target_return_pct: number;
    horizon_months: number;
    universe_mode: UniverseMode;
    period: string;
    force?: boolean;
    exclude_codes?: string[];
    include_codes?: string[];
  }) =>
    requestJson<QuantSolveJobResponse>('/api/v1/quant/solve', {
      method: 'POST',
      body: JSON.stringify(params),
    }),
  pollQuantSolve: (jobId: string) =>
    requestJson<QuantSolveJobResponse>(`/api/v1/quant/solve/${encodeURIComponent(jobId)}`),
  getLakehouseStatus: () => requestJson<LakehouseStatus>('/api/v1/lakehouse/status'),
  syncLakehouseDaily: (cooldownMinutes = 30) =>
    requestJson<{
      status: string;
      updated_dates?: number;
      latest_date?: string;
      message?: string;
      requests_used?: number;
    }>('/api/v1/lakehouse/sync_daily', {
      method: 'POST',
      body: JSON.stringify({ cooldown_minutes: cooldownMinutes }),
    }),
  getBacktestSummary: (ledgerId?: string) =>
    requestJson<BacktestSummaryResponse>(`/api/v1/backtest/summary${ledgerId ? `?ledger_id=${encodeURIComponent(ledgerId)}` : ''}`),
  getBacktestCurves: (
    tier = 'C3',
    model = 'all_weather',
    fundCount = 6,
    period = '1y',
    mode = 'model_live',
    targetReturnPct = 10,
    horizonMonths = 12,
    force = false,
    universeMode: UniverseMode = 'full_market',
    excludeCodes?: string[],
    includeCodes?: string[]
  ) => {
    const q = new URLSearchParams({
      tier,
      model,
      fund_count: String(fundCount),
      period,
      mode,
      target_return_pct: String(targetReturnPct),
      horizon_months: String(horizonMonths),
      universe_mode: universeMode,
    });
    if (force) q.set('force', 'true');
    if (excludeCodes && excludeCodes.length > 0) q.set('exclude_codes', excludeCodes.join(','));
    if (includeCodes && includeCodes.length > 0) q.set('include_codes', includeCodes.join(','));
    return requestJson<BacktestCurvesResponse>(`/api/v1/charts/backtest_curves?${q.toString()}`);
  },
  getCrowdingQuadrant: (ledgerId?: string, codes?: string[]) => {
    const q = new URLSearchParams();
    if (ledgerId) q.set('ledger_id', ledgerId);
    if (codes && codes.length > 0) q.set('codes', codes.join(','));
    const qs = q.toString();
    return requestJson<{ ledger_id: string; scope_mode?: string; count: number; points: CrowdingPoint[] }>(
      `/api/v1/charts/crowding_quadrant${qs ? `?${qs}` : ''}`
    );
  },
  getHoldings: (ledgerId?: string) =>
    requestJson<{ ledger_id: string; count: number; items: HoldingRow[] }>(
      `/api/v1/holdings${ledgerId ? `?ledger_id=${encodeURIComponent(ledgerId)}` : ''}`
    ),
  deleteHolding: (code: string, ledgerId?: string) =>
    requestJson<{ deleted: boolean }>(
      `/api/v1/holdings/${encodeURIComponent(code)}${ledgerId ? `?ledger_id=${encodeURIComponent(ledgerId)}` : ''}`,
      { method: 'DELETE' }
    ),
  updateCash: (available_cash: number, ledger_id?: string) =>
    requestJson<{ available_cash: number; updated: boolean }>('/api/v1/holdings/cash', {
      method: 'POST',
      body: JSON.stringify({ ledger_id, available_cash }),
    }),
  getDiagnoseExposure: (ledgerId?: string) =>
    requestJson<ExposureResponse>(`/api/v1/diagnose/exposure${ledgerId ? `?ledger_id=${encodeURIComponent(ledgerId)}` : ''}`),
  getDiagnoseRiskCheck: (ledgerId?: string) =>
    requestJson<RiskCheckResponse>(`/api/v1/diagnose/risk_check${ledgerId ? `?ledger_id=${encodeURIComponent(ledgerId)}` : ''}`),
  getDiagnoseOverlap: (ledgerId?: string) =>
    requestJson<Record<string, unknown>>(`/api/v1/diagnose/overlap${ledgerId ? `?ledger_id=${encodeURIComponent(ledgerId)}` : ''}`),
  getDiagnoseStress: (ledgerId?: string) =>
    requestJson<Record<string, unknown>>(`/api/v1/diagnose/stress_test${ledgerId ? `?ledger_id=${encodeURIComponent(ledgerId)}` : ''}`),
  getTenDimVotes: (ledgerId?: string) =>
    requestJson<{ overall_regime: string; votes: Array<Record<string, unknown>> }>(
      `/api/v1/diagnose/ten_dim_votes${ledgerId ? `?ledger_id=${encodeURIComponent(ledgerId)}` : ''}`
    ),
  getWatchlist: () =>
    requestJson<{ items: Array<{ code: string; name: string; asset_type: string; change_pct: number }> }>('/api/v1/watchlist'),
  addWatchlistItem: (code: string, name: string) =>
    requestJson<{ items: Array<{ code: string; name: string; asset_type: string; change_pct: number }> }>('/api/v1/watchlist', {
      method: 'POST',
      body: JSON.stringify({ action: 'add', code, name }),
    }),
  removeWatchlistItem: (code: string) =>
    requestJson<{ items: Array<{ code: string; name: string; asset_type: string; change_pct: number }> }>(
      `/api/v1/watchlist/${encodeURIComponent(code)}`,
      { method: 'DELETE' }
    ),
  searchFunds: (q: string, limit = 8) =>
    requestJson<{ items: Array<{ code: string; name: string; asset_type: string; sector: string }> }>(
      `/api/v1/funds/search?q=${encodeURIComponent(q)}&limit=${limit}`
    ),
  getFundDetail: (fundCode: string, dcaMonthly = 1000) =>
    requestJson<FundDetailResponse>(
      `/api/v1/funds/${encodeURIComponent(fundCode)}/detail?dca_monthly=${encodeURIComponent(String(dcaMonthly))}`
    ),
  getScenarioBacktest: (
    startDate: string,
    tier = 'C3',
    dynamicRebalance = true,
    solvedOpts?: {
      model?: string;
      fundCount?: number;
      targetReturnPct?: number;
      horizonMonths?: number;
      universeMode?: UniverseMode;
      excludeCodes?: string[];
      includeCodes?: string[];
    }
  ) => {
    const q = new URLSearchParams();
    q.set('start_date', startDate);
    q.set('tier', tier);
    q.set('dynamic_rebalance', dynamicRebalance ? 'true' : 'false');
    if (solvedOpts?.model) q.set('model', solvedOpts.model);
    if (solvedOpts?.fundCount !== undefined) q.set('fund_count', String(solvedOpts.fundCount));
    if (solvedOpts?.targetReturnPct !== undefined) q.set('target_return_pct', String(solvedOpts.targetReturnPct));
    if (solvedOpts?.horizonMonths !== undefined) q.set('horizon_months', String(solvedOpts.horizonMonths));
    if (solvedOpts?.universeMode) q.set('universe_mode', solvedOpts.universeMode);
    if (solvedOpts?.excludeCodes && solvedOpts.excludeCodes.length > 0) q.set('exclude_codes', solvedOpts.excludeCodes.join(','));
    if (solvedOpts?.includeCodes && solvedOpts.includeCodes.length > 0) q.set('include_codes', solvedOpts.includeCodes.join(','));
    return requestJson<ScenarioBacktestResponse>(`/api/v1/charts/scenario_backtest?${q.toString()}`);
  },
  getEtfPremiums: () =>
    requestJson<{
      alert_count: number;
      is_offline_snapshot?: boolean;
      snapshot_timestamp?: string;
      source_label?: string;
      items: EtfPremiumItem[];
    }>('/api/v1/tools/etf_premiums'),
  getDividendAdvice: (ledgerId?: string) =>
    requestJson<DividendAdviceResponse>(
      `/api/v1/tools/dividend_advice${ledgerId ? `?ledger_id=${encodeURIComponent(ledgerId)}` : ''}`
    ),
  getAuditTrackers: (ledgerId?: string) =>
    requestJson<{ shadow_tracker?: Record<string, unknown>; forward_audit?: Record<string, unknown> }>(
      `/api/v1/audit/trackers${ledgerId ? `?ledger_id=${encodeURIComponent(ledgerId)}` : ''}`
    ),
  freezeShadowBaseline: (ledger_id: string, baseline_name?: string) =>
    requestJson<{ frozen: boolean; baseline_name: string; frozen_date: string }>('/api/v1/shadow/freeze', {
      method: 'POST',
      body: JSON.stringify({ ledger_id, baseline_name }),
    }),
  getBackups: () =>
    requestJson<{ count: number; snapshots: Array<{ snapshot_id: string; timestamp?: string; created_at?: string; reason?: string }> }>('/api/v1/backups'),
  restoreBackup: (snapshot_id: string) =>
    requestJson<{ restored: boolean }>('/api/v1/backups/restore', {
      method: 'POST',
      body: JSON.stringify({ snapshot_id }),
    }),
  getRebalance: (
    ledgerId?: string,
    targetReturnPct = 10,
    horizonMonths = 12,
    opts?: {
      tier?: string;
      targetSource?: 'ledger_smooth' | 'full_market_solved';
      model?: string;
      fundCount?: number;
      universeMode?: UniverseMode;
      excludeCodes?: string[];
      includeCodes?: string[];
    }
  ) => {
    const q = new URLSearchParams();
    if (ledgerId) q.set('ledger_id', ledgerId);
    q.set('target_return_pct', String(targetReturnPct));
    q.set('horizon_months', String(horizonMonths));
    if (opts?.tier) q.set('tier', opts.tier);
    if (opts?.targetSource) q.set('target_source', opts.targetSource);
    if (opts?.model) q.set('model', opts.model);
    if (opts?.fundCount !== undefined) q.set('fund_count', String(opts.fundCount));
    if (opts?.universeMode) q.set('universe_mode', opts.universeMode);
    if (opts?.excludeCodes && opts.excludeCodes.length > 0) q.set('exclude_codes', opts.excludeCodes.join(','));
    if (opts?.includeCodes && opts.includeCodes.length > 0) q.set('include_codes', opts.includeCodes.join(','));
    return requestJson<RebalanceResponse>(`/api/v1/rebalance?${q.toString()}`);
  },
  getCheckin: () =>
    requestJson<{ date?: string; checked_codes?: Record<string, { checked?: boolean; action?: string; amount?: number; ts?: string } | boolean> }>(
      '/api/v1/rebalance/checkin'
    ),
  saveCheckinItem: (fund_code: string, action: string, amount: number, checked: boolean) =>
    requestJson<{ date?: string; checked_codes?: Record<string, unknown> }>('/api/v1/rebalance/checkin', {
      method: 'POST',
      body: JSON.stringify({ fund_code, action, amount, checked }),
    }),
  planCashflow: (monthly_cash: number, ledger_id?: string) =>
    requestJson<{ dca_plan?: Record<string, unknown> }>('/api/v1/cashflow/plan', {
      method: 'POST',
      body: JSON.stringify({ ledger_id, monthly_new_cash: monthly_cash, plan_months: 1, emergency_reserve: 0 }),
    }),
  importText: (text: string, mode: 'preview' | 'merge' | 'overwrite', ledger_id?: string) =>
    requestJson<{ parsed_count: number; applied: boolean; items: Array<Record<string, unknown>> }>('/api/v1/import/text', {
      method: 'POST',
      body: JSON.stringify({ ledger_id, text, mode }),
    }),
  importOcr: async (file: File, mode: 'preview' | 'merge' | 'overwrite', ledger_id?: string) => {
    const fd = new FormData();
    fd.append('file', file);
    fd.append('mode', mode);
    if (ledger_id) fd.append('ledger_id', ledger_id);
    const res = await fetch('/api/v1/import/ocr', { method: 'POST', body: fd });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err?.detail || `OCR 请求失败 (${res.status})`);
    }
    return res.json() as Promise<{ parsed_count: number; applied: boolean; items: Array<Record<string, unknown>> }>;
  },
  commitImport: (
    items: Array<Record<string, unknown>>,
    mode: 'merge' | 'overwrite',
    ledger_id?: string,
    available_cash?: number
  ) =>
    requestJson<{ applied: boolean; committed_count: number; mode: string }>('/api/v1/import/commit', {
      method: 'POST',
      body: JSON.stringify({ ledger_id, mode, items, available_cash }),
    }),
  reconcileManual: (updates: Array<{ fund_code: string; fund_name?: string; shares: number; cost_price: number; current_nav?: number }>, ledger_id?: string) =>
    requestJson<{ applied: boolean; modified_count: number }>('/api/v1/holdings/reconcile', {
      method: 'POST',
      body: JSON.stringify({ ledger_id, updates, dry_run: false }),
    }),
};

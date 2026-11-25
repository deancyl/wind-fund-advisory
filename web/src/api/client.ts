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

export interface BlueprintItem {
  fund_code: string;
  fund_name: string;
  role: string;
  why: string;
  quant_reason?: string;
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
  fund_count: number;
  total_amount: number;
  market_regime: string;
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

export interface BacktestCurvesResponse {
  status: string;
  tier: string;
  model?: string;
  fund_count?: number;
  period?: string;
  period_label?: string;
  date_range?: string;
  mode: string;
  primary_name: string;
  secondary_name: string;
  metrics?: BacktestMetrics;
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
  plan_mode: string;
  is_empty: boolean;
  tail_sweep: RebalanceGroup;
  c_replace: RebalanceGroup;
  core_trades: RebalanceGroup;
  buffer_hold: RebalanceGroup;
  quota_split_plans?: QuotaSplitPlan[];
  cheat_sheet_lines: string[];
  cheat_sheet_text: string;
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
  getBlueprint: (riskLevel: string, amount: number, fundCount = 6, model = 'all_weather') =>
    requestJson<BlueprintResponse>(
      `/api/v1/recommend/blueprint?risk_level=${encodeURIComponent(riskLevel)}&amount=${encodeURIComponent(
        String(amount)
      )}&fund_count=${encodeURIComponent(String(fundCount))}&model=${encodeURIComponent(model)}`
    ),
  getBacktestSummary: (ledgerId?: string) =>
    requestJson<BacktestSummaryResponse>(`/api/v1/backtest/summary${ledgerId ? `?ledger_id=${encodeURIComponent(ledgerId)}` : ''}`),
  getBacktestCurves: (tier = 'C3', model = 'all_weather', fundCount = 6, period = '1y', mode = 'model_live') =>
    requestJson<BacktestCurvesResponse>(
      `/api/v1/charts/backtest_curves?tier=${encodeURIComponent(tier)}&model=${encodeURIComponent(
        model
      )}&fund_count=${encodeURIComponent(String(fundCount))}&period=${encodeURIComponent(period)}&mode=${encodeURIComponent(mode)}`
    ),
  getCrowdingQuadrant: (ledgerId?: string) =>
    requestJson<{ ledger_id: string; count: number; points: CrowdingPoint[] }>(
      `/api/v1/charts/crowding_quadrant${ledgerId ? `?ledger_id=${encodeURIComponent(ledgerId)}` : ''}`
    ),
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
  getScenarioBacktest: (startDate: string, tier = 'C3', dynamicRebalance = true) =>
    requestJson<ScenarioBacktestResponse>(
      `/api/v1/charts/scenario_backtest?start_date=${encodeURIComponent(startDate)}&tier=${encodeURIComponent(
        tier
      )}&dynamic_rebalance=${dynamicRebalance ? 'true' : 'false'}`
    ),
  getEtfPremiums: () => requestJson<{ alert_count: number; items: EtfPremiumItem[] }>('/api/v1/tools/etf_premiums'),
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
  getRebalance: (ledgerId?: string) =>
    requestJson<RebalanceResponse>(`/api/v1/rebalance${ledgerId ? `?ledger_id=${encodeURIComponent(ledgerId)}` : ''}`),
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
  reconcileManual: (updates: Array<{ fund_code: string; fund_name?: string; shares: number; cost_price: number; current_nav?: number }>, ledger_id?: string) =>
    requestJson<{ applied: boolean; modified_count: number }>('/api/v1/holdings/reconcile', {
      method: 'POST',
      body: JSON.stringify({ ledger_id, updates, dry_run: false }),
    }),
};

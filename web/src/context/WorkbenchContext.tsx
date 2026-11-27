import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from 'react';
import {
  api,
  type BacktestCurvesResponse,
  type BenchmarkHorizonSummary,
  type BlueprintItem,
  type BlueprintResponse,
  type LakehouseStatus,
  type LedgerMeta,
  type OverviewResponse,
  type SolvedPortfolioContext,
  type UniverseMode,
} from '../api/client';
import type { ConfirmModalConfig } from '../components/ConfirmDialog';

export type MainTab = 'quant_lab' | 'market' | 'holdings' | 'rebalance';
export type DataCenterTab = 'import' | 'ledgers' | 'backups' | 'lakehouse';

export interface AppliedSolveParams {
  riskLevel: string;
  modelId: string;
  fundCount: number;
  targetReturnPct: number;
  horizonMonths: number;
  universeMode: UniverseMode;
  excludeCodes: string[];
  includeCodes: string[];
}

export interface SavedSnapshot {
  id: string;
  label: string;
  savedAt: string;
  lakehouseDate: string;
  params: AppliedSolveParams;
  modelName: string;
  commonStartDate: string;
  y1: BenchmarkHorizonSummary | null;
  all: BenchmarkHorizonSummary | null;
  goalHitRatePct: number;
  condWinRatePct: number;
  mcProbPct: number;
  oosWinRatePct: number;
  portfolioVolPct: number;
  maxPcrPct: number;
  items: Array<{
    fund_code: string;
    fund_name: string;
    bucket_label: string;
    weight_pct: number;
    pcr_pct: number;
    quant_score: number;
  }>;
}

export interface ToastMessage {
  id: number;
  text: string;
  tone?: 'default' | 'success' | 'warning' | 'error';
}

const SNAPSHOT_STORAGE_KEY = 'agy2_saved_snapshots_v1';

function loadSnapshotsFromStorage(): SavedSnapshot[] {
  try {
    const raw = window.localStorage.getItem(SNAPSHOT_STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed.slice(0, 4) : [];
  } catch {
    return [];
  }
}

function sameList(a: string[], b: string[]): boolean {
  if (a.length !== b.length) return false;
  const sa = [...a].sort();
  const sb = [...b].sort();
  return sa.every((v, idx) => v === sb[idx]);
}

interface WorkbenchContextValue {
  // 导航与壳状态
  activeTab: MainTab;
  setActiveTab: (tab: MainTab) => void;
  sidebarCollapsed: boolean;
  setSidebarCollapsed: (v: boolean | ((p: boolean) => boolean)) => void;

  // 账本与宏观/湖仓状态
  ledgers: LedgerMeta[];
  activeLedgerId: string;
  currentLedger?: LedgerMeta;
  overview: OverviewResponse | null;
  lakehouse: LakehouseStatus | null;
  refreshing: boolean;
  refreshTick: number;
  syncingDaily: boolean;
  switchLedger: (id: string) => Promise<void>;
  createLedger: (name: string, initialCash?: number) => Promise<void>;
  refreshAll: () => Promise<void>;
  notifyDataMutated: (msg: string) => Promise<void>;
  syncLakehouseDaily: () => Promise<void>;

  // 量化实验室核心状态（切 Tab 保活，后台求解不中断）
  riskLevel: string;
  setRiskLevel: (v: string) => void;
  modelId: string;
  setModelId: (v: string) => void;
  fundCount: number;
  setFundCount: (v: number) => void;
  amount: number;
  setAmount: (v: number) => void;
  targetReturnPct: number;
  horizonMonths: number;
  setGoal: (ret: number, mon: number) => void;
  universeMode: UniverseMode;
  setUniverseMode: (v: UniverseMode) => void;
  period: string;
  setPeriod: (p: string) => void;
  excludeCodes: string[];
  includeCodes: string[];
  toggleExcludeCode: (code: string, autoSolve?: boolean) => void;
  toggleIncludeCode: (code: string, autoSolve?: boolean) => void;
  clearConstraints: (autoSolve?: boolean) => void;

  blueprint: BlueprintResponse | null;
  curves: BacktestCurvesResponse | null;
  curvesLoading: boolean;
  appliedParams: AppliedSolveParams | null;
  solvedContext: SolvedPortfolioContext;
  isDirty: boolean;
  staleHint: string;
  solving: boolean;
  solveProgress: number;
  solveStage: string;
  solveElapsedMs: number;
  solveError: string;
  runAsyncQuantSolve: (overrides?: Partial<AppliedSolveParams>, force?: boolean) => Promise<void>;

  // A/B 方案对比快照
  snapshots: SavedSnapshot[];
  saveCurrentSnapshot: (customLabel?: string) => void;
  removeSnapshot: (id: string) => void;
  applySnapshotToLab: (snap: SavedSnapshot, autoSolve?: boolean) => void;
  refreshSnapshot: (id: string) => Promise<void>;

  // 全局检查器 / 弹窗 / 命令面板 / Toast
  inspectorFundCode: string | null;
  inspectorFundMeta: BlueprintItem | null;
  openInspector: (code: string) => void;
  closeInspector: () => void;
  fullDetailFundCode: string | null;
  openFullDetail: (code: string) => void;
  closeFullDetail: () => void;
  dataCenterTab: DataCenterTab | null;
  openDataCenter: (tab?: DataCenterTab) => void;
  closeDataCenter: () => void;
  commandOpen: boolean;
  setCommandOpen: (v: boolean | ((p: boolean) => boolean)) => void;
  confirmModal: ConfirmModalConfig | null;
  openConfirm: (cfg: ConfirmModalConfig) => void;
  closeConfirm: () => void;
  toasts: ToastMessage[];
  pushToast: (text: string, tone?: ToastMessage['tone']) => void;
}

const WorkbenchContext = createContext<WorkbenchContextValue | null>(null);

export function WorkbenchProvider({ children }: { children: ReactNode }) {
  const [activeTab, setActiveTabState] = useState<MainTab>('quant_lab');
  const [sidebarCollapsed, setSidebarCollapsed] = useState<boolean>(() =>
    typeof window !== 'undefined' ? window.innerWidth < 1360 : false
  );

  // 账本、总览、湖仓（初始为空，等待 /api/v1/ledgers 返回本机真实活动账本，避免干净部署盲查固定 ID）
  const [ledgers, setLedgers] = useState<LedgerMeta[]>([]);
  const [activeLedgerId, setActiveLedgerId] = useState<string>('');
  const [overview, setOverview] = useState<OverviewResponse | null>(null);
  const [lakehouse, setLakehouse] = useState<LakehouseStatus | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  const [refreshTick, setRefreshTick] = useState(0);
  const [syncingDaily, setSyncingDaily] = useState(false);

  // 量化求解器参数（顶层常驻保活）
  const [riskLevel, setRiskLevel] = useState('C3');
  const [modelId, setModelId] = useState('all_weather');
  const [fundCount, setFundCount] = useState(6);
  const [amount, setAmount] = useState(50000);
  const [targetReturnPct, setTargetReturnPct] = useState(10);
  const [horizonMonths, setHorizonMonths] = useState(12);
  const [universeMode, setUniverseMode] = useState<UniverseMode>('full_market');
  const [period, setPeriodState] = useState('1y');
  const [excludeCodes, setExcludeCodes] = useState<string[]>([]);
  const [includeCodes, setIncludeCodes] = useState<string[]>([]);

  const [blueprint, setBlueprint] = useState<BlueprintResponse | null>(null);
  const [curves, setCurves] = useState<BacktestCurvesResponse | null>(null);
  const [curvesLoading, setCurvesLoading] = useState(false);
  const [appliedParams, setAppliedParams] = useState<AppliedSolveParams | null>(null);
  const [solving, setSolving] = useState(false);
  const [solveProgress, setSolveProgress] = useState(0);
  const [solveStage, setSolveStage] = useState('');
  const [solveElapsedMs, setSolveElapsedMs] = useState(0);
  const [solveError, setSolveError] = useState('');
  const solveSeqRef = useRef(0);
  const mountedRef = useRef(true);

  // A/B 快照
  const [snapshots, setSnapshots] = useState<SavedSnapshot[]>(loadSnapshotsFromStorage);

  // 全局浮层与确认框
  const [inspectorFundCode, setInspectorFundCode] = useState<string | null>(null);
  const [fullDetailFundCode, setFullDetailFundCode] = useState<string | null>(null);
  const [dataCenterTab, setDataCenterTab] = useState<DataCenterTab | null>(null);
  const [commandOpen, setCommandOpen] = useState(false);
  const [confirmModal, setConfirmModal] = useState<ConfirmModalConfig | null>(null);
  const [toasts, setToasts] = useState<ToastMessage[]>([]);
  const toastSeqRef = useRef(0);

  const pushToast = useCallback((text: string, tone: ToastMessage['tone'] = 'default') => {
    const id = ++toastSeqRef.current;
    setToasts((prev) => [...prev.slice(-2), { id, text, tone }]);
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, 3400);
  }, []);

  useEffect(() => {
    try {
      window.localStorage.setItem(SNAPSHOT_STORAGE_KEY, JSON.stringify(snapshots));
    } catch {
      // ignore quota error
    }
  }, [snapshots]);

  // Ctrl+K / Cmd+K 全局命令面板快捷键
  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        setCommandOpen((v) => !v);
      }
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, []);

  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
      solveSeqRef.current += 1;
    };
  }, []);

  const loadCore = useCallback(
    async (targetLedger?: string, force = false) => {
      setRefreshing(true);
      try {
        const lRes = await api.getLedgers();
        if (!mountedRef.current) return;
        const items = lRes.items || [];
        setLedgers(items);
        const lid = targetLedger || lRes.active_ledger_id || items[0]?.id || '';
        setActiveLedgerId(lid);
        const ov = await api.getOverview(lid || undefined, force);
        if (mountedRef.current) setOverview(ov);
      } catch (e) {
        pushToast(e instanceof Error ? e.message : '后端连接失败，请确认 api_server 已启动', 'error');
      } finally {
        if (mountedRef.current) setRefreshing(false);
      }
    },
    [pushToast]
  );

  useEffect(() => {
    void loadCore();
    api
      .getLakehouseStatus()
      .then((st) => {
        if (mountedRef.current) setLakehouse(st);
      })
      .catch(() => {});
  }, [loadCore]);

  const setActiveTab = useCallback((tab: MainTab) => {
    setFullDetailFundCode(null);
    setActiveTabState(tab);
  }, []);

  const setGoal = useCallback((ret: number, mon: number) => {
    setTargetReturnPct(Math.max(2, Math.min(60, Math.round(ret) || 10)));
    setHorizonMonths(mon);
  }, []);

  const runAsyncQuantSolve = useCallback(
    async (overrides?: Partial<AppliedSolveParams>, force = false) => {
      const seq = ++solveSeqRef.current;
      const eff: AppliedSolveParams = {
        riskLevel: overrides?.riskLevel ?? riskLevel,
        modelId: overrides?.modelId ?? modelId,
        fundCount: overrides?.fundCount ?? fundCount,
        targetReturnPct: overrides?.targetReturnPct ?? targetReturnPct,
        horizonMonths: overrides?.horizonMonths ?? horizonMonths,
        universeMode: overrides?.universeMode ?? universeMode,
        excludeCodes: overrides?.excludeCodes ?? excludeCodes,
        includeCodes: overrides?.includeCodes ?? includeCodes,
      };
      const cap = Math.max(1000, amount || 50000);

      setSolving(true);
      setSolveProgress(6);
      setSolveStage('正在启动全市场量化求解任务...');
      setSolveElapsedMs(0);
      setSolveError('');

      try {
        const startRes = await api.startQuantSolve({
          risk_level: eff.riskLevel,
          amount: cap,
          fund_count: eff.fundCount,
          model: eff.modelId,
          target_return_pct: eff.targetReturnPct,
          horizon_months: eff.horizonMonths,
          universe_mode: eff.universeMode,
          period,
          force,
          exclude_codes: eff.excludeCodes,
          include_codes: eff.includeCodes,
        });

        if (!mountedRef.current || solveSeqRef.current !== seq) return;
        setSolveProgress(Math.max(8, startRes.progress_pct || 8));
        if (startRes.stage_text) setSolveStage(startRes.stage_text);

        const jobId = startRes.job_id;
        for (let i = 0; i < 240; i++) {
          await new Promise((r) => setTimeout(r, 320));
          if (!mountedRef.current || solveSeqRef.current !== seq) return;
          const st = await api.pollQuantSolve(jobId);
          if (!mountedRef.current || solveSeqRef.current !== seq) return;

          setSolveProgress(st.progress_pct ?? 50);
          if (st.stage_text) setSolveStage(st.stage_text);
          if (st.elapsed_ms !== undefined) setSolveElapsedMs(st.elapsed_ms);

          if (st.status === 'done' && st.result) {
            const bp = st.result.blueprint;
            const bt = st.result.backtest_curves;
            setBlueprint(bp);
            setCurves(bt);
            // 若后端因 index_only 自动解绑了主动基金锁定，保持前端约束列表与生效列表同步
            const effInc = bp.constraint_audit?.include_codes ?? eff.includeCodes;
            const effEx = bp.constraint_audit?.exclude_codes ?? eff.excludeCodes;
            if (!sameList(effInc, eff.includeCodes)) {
              setIncludeCodes(effInc);
            }
            setAppliedParams({ ...eff, excludeCodes: effEx, includeCodes: effInc });
            setSolveProgress(100);
            setSolving(false);
            if (bp.constraint_audit?.warnings?.length) {
              pushToast(bp.constraint_audit.warnings[0], 'warning');
            }
            return;
          }
          if (st.status === 'error') {
            setSolveError(st.error || st.stage_text || '量化求解异常，请重试');
            setSolving(false);
            return;
          }
        }
        setSolveError('量化求解耗时超限，请稍后重试');
        setSolving(false);
      } catch (err) {
        if (!mountedRef.current || solveSeqRef.current !== seq) return;
        setSolveError(err instanceof Error ? err.message : '求解请求失败');
        setSolving(false);
      }
    },
    [riskLevel, modelId, fundCount, targetReturnPct, horizonMonths, universeMode, excludeCodes, includeCodes, amount, period, pushToast]
  );

  // 首次启动执行一次默认全市场量化求解（此后参数变动由用户显式点击 CTA 或快捷排除/锁定触发）
  const initSolvedRef = useRef(false);
  useEffect(() => {
    if (initSolvedRef.current) return;
    initSolvedRef.current = true;
    void runAsyncQuantSolve(undefined, false);
  }, [runAsyncQuantSolve]);

  // 切换回测统计周期（3m/6m/1y/2y/all）直接复用已求解参数缓存秒级切片
  const setPeriod = useCallback(
    (nextPeriod: string) => {
      setPeriodState(nextPeriod);
      if (!appliedParams) return;
      setCurvesLoading(true);
      api
        .getBacktestCurves(
          appliedParams.riskLevel,
          appliedParams.modelId,
          appliedParams.fundCount,
          nextPeriod,
          'model_live',
          appliedParams.targetReturnPct,
          appliedParams.horizonMonths,
          false,
          appliedParams.universeMode,
          appliedParams.excludeCodes,
          appliedParams.includeCodes
        )
        .then((res) => {
          if (mountedRef.current) setCurves(res);
        })
        .catch(() => {})
        .finally(() => {
          if (mountedRef.current) setCurvesLoading(false);
        });
    },
    [appliedParams]
  );

  const toggleExcludeCode = useCallback(
    (code: string, autoSolve = false) => {
      const nextInc = includeCodes.filter((c) => c !== code);
      const exists = excludeCodes.includes(code);
      const nextEx = exists ? excludeCodes.filter((c) => c !== code) : [...excludeCodes, code];
      setIncludeCodes(nextInc);
      setExcludeCodes(nextEx);
      pushToast(exists ? `已取消排除 ${code}` : `已将 ${code} 加入排除清单`, 'default');
      if (autoSolve) {
        void runAsyncQuantSolve({ excludeCodes: nextEx, includeCodes: nextInc }, false);
      }
    },
    [excludeCodes, includeCodes, pushToast, runAsyncQuantSolve]
  );

  const toggleIncludeCode = useCallback(
    (code: string, autoSolve = false) => {
      const nextEx = excludeCodes.filter((c) => c !== code);
      const exists = includeCodes.includes(code);
      const nextInc = exists ? includeCodes.filter((c) => c !== code) : [...includeCodes, code];
      setExcludeCodes(nextEx);
      setIncludeCodes(nextInc);
      pushToast(exists ? `已解除锁定 ${code}` : `已锁定 ${code} 必选参与组合`, 'default');
      if (autoSolve) {
        void runAsyncQuantSolve({ excludeCodes: nextEx, includeCodes: nextInc }, false);
      }
    },
    [excludeCodes, includeCodes, pushToast, runAsyncQuantSolve]
  );

  const clearConstraints = useCallback(
    (autoSolve = false) => {
      setExcludeCodes([]);
      setIncludeCodes([]);
      pushToast('已清空所有排除与锁定约束', 'default');
      if (autoSolve) {
        void runAsyncQuantSolve({ excludeCodes: [], includeCodes: [] }, false);
      }
    },
    [pushToast, runAsyncQuantSolve]
  );

  const switchLedger = useCallback(
    async (id: string) => {
      try {
        await api.setActiveLedger(id);
        setActiveLedgerId(id);
        await loadCore(id, false);
        setRefreshTick((t) => t + 1);
        const found = ledgers.find((l) => l.id === id);
        pushToast(`已切换账本：${found?.name || id}`, 'success');
      } catch (e) {
        pushToast(e instanceof Error ? e.message : '切换账本失败', 'error');
      }
    },
    [ledgers, loadCore, pushToast]
  );

  const createLedger = useCallback(
    async (name: string, initialCash = 0) => {
      const res = await api.createLedger(name.trim(), initialCash);
      await loadCore(res.ledger_id, true);
      setRefreshTick((t) => t + 1);
      setActiveTab('holdings');
      pushToast(`已新建账本「${res.name}」`, 'success');
    },
    [loadCore, pushToast, setActiveTab]
  );

  const refreshAll = useCallback(async () => {
    await loadCore(activeLedgerId, true);
    setRefreshTick((t) => t + 1);
    pushToast('已同步最新行情与持仓估值', 'success');
  }, [activeLedgerId, loadCore, pushToast]);

  const notifyDataMutated = useCallback(
    async (msg: string) => {
      await loadCore(activeLedgerId, true);
      setRefreshTick((t) => t + 1);
      pushToast(msg, 'success');
    },
    [activeLedgerId, loadCore, pushToast]
  );

  const syncLakehouseDaily = useCallback(async () => {
    setSyncingDaily(true);
    try {
      const res = await api.syncLakehouseDaily(30);
      if (!mountedRef.current) return;
      if (res.status === 'cooldown_skipped') {
        pushToast(res.message || '冷却期内无需重复同步', 'default');
      } else if (res.status === 'up_to_date') {
        pushToast(`本地湖仓已是最新交易日（${res.latest_date || lakehouse?.latest_date || ''}）`, 'success');
      } else if (res.status === 'updated') {
        pushToast(`安全日更完成：追加至 ${res.latest_date || ''}（仅 ${res.requests_used || 6} 次批量请求）`, 'success');
        const st = await api.getLakehouseStatus();
        if (mountedRef.current) setLakehouse(st);
      } else {
        pushToast(res.message || '同步状态已刷新', 'default');
      }
    } catch (e) {
      pushToast(e instanceof Error ? e.message : '盘后安全日更失败', 'error');
    } finally {
      if (mountedRef.current) setSyncingDaily(false);
    }
  }, [lakehouse, pushToast]);

  // A/B 快照管理（强绑定湖仓截止日与固定双口径指标）
  const saveCurrentSnapshot = useCallback(
    (customLabel?: string) => {
      if (!blueprint || !appliedParams) {
        pushToast('当前尚无已求解方案可保存', 'warning');
        return;
      }
      const nextIdx = snapshots.length + 1;
      const uTag = appliedParams.universeMode === 'full_market' ? '全市场' : '仅指数';
      const defaultLbl = `方案 ${String.fromCharCode(64 + ((nextIdx - 1) % 4) + 1)} · ${appliedParams.riskLevel} ${blueprint.model_meta?.name?.slice(0, 4) || appliedParams.modelId} (${uTag})`;
      const snap: SavedSnapshot = {
        id: `snap_${Date.now()}`,
        label: customLabel?.trim() || defaultLbl,
        savedAt: new Date().toLocaleTimeString('zh-CN', { hour12: false }),
        lakehouseDate: lakehouse?.latest_date || blueprint.funnel_audit?.lakehouse_latest_date || '',
        params: { ...appliedParams },
        modelName: blueprint.model_meta?.name || appliedParams.modelId,
        commonStartDate: blueprint.real_bt_info?.common_start_date || curves?.real_bt_info?.common_start_date || '',
        y1: curves?.benchmark_horizons?.y1 ?? null,
        all: curves?.benchmark_horizons?.all ?? null,
        goalHitRatePct: blueprint.goal_analysis?.historical_hit_rate_pct ?? 0,
        condWinRatePct: blueprint.goal_analysis?.conditional_win_rate_pct ?? 0,
        mcProbPct: blueprint.goal_analysis?.monte_carlo_prob_pct ?? 0,
        oosWinRatePct: blueprint.solver_audit?.oos_conditional_win_rate_pct ?? 0,
        portfolioVolPct: blueprint.solver_audit?.portfolio_vol_annual_pct ?? 0,
        maxPcrPct: blueprint.solver_audit?.max_risk_pcr_pct ?? 0,
        items: (blueprint.items || []).map((it) => ({
          fund_code: it.fund_code,
          fund_name: it.fund_name,
          bucket_label: it.bucket_label || it.role,
          weight_pct: it.weight_pct,
          pcr_pct: it.risk_contribution_pcr_pct ?? it.weight_pct,
          quant_score: it.quant_score ?? 0,
        })),
      };
      setSnapshots((prev) => [snap, ...prev].slice(0, 4));
      pushToast(`已保存至对比槽：${snap.label}`, 'success');
    },
    [blueprint, appliedParams, curves, lakehouse, snapshots.length, pushToast]
  );

  const removeSnapshot = useCallback((id: string) => {
    setSnapshots((prev) => prev.filter((s) => s.id !== id));
  }, []);

  const applySnapshotToLab = useCallback(
    (snap: SavedSnapshot, autoSolve = true) => {
      setRiskLevel(snap.params.riskLevel);
      setModelId(snap.params.modelId);
      setFundCount(snap.params.fundCount);
      setTargetReturnPct(snap.params.targetReturnPct);
      setHorizonMonths(snap.params.horizonMonths);
      setUniverseMode(snap.params.universeMode);
      setExcludeCodes(snap.params.excludeCodes || []);
      setIncludeCodes(snap.params.includeCodes || []);
      setActiveTab('quant_lab');
      if (autoSolve) {
        void runAsyncQuantSolve(snap.params, false);
      }
    },
    [runAsyncQuantSolve, setActiveTab]
  );

  const refreshSnapshot = useCallback(
    async (id: string) => {
      const target = snapshots.find((s) => s.id === id);
      if (!target) return;
      try {
        const [bp, bt] = await Promise.all([
          api.getBlueprint(
            target.params.riskLevel,
            amount,
            target.params.fundCount,
            target.params.modelId,
            target.params.targetReturnPct,
            target.params.horizonMonths,
            false,
            target.params.universeMode,
            target.params.excludeCodes,
            target.params.includeCodes
          ),
          api.getBacktestCurves(
            target.params.riskLevel,
            target.params.modelId,
            target.params.fundCount,
            '1y',
            'model_live',
            target.params.targetReturnPct,
            target.params.horizonMonths,
            false,
            target.params.universeMode,
            target.params.excludeCodes,
            target.params.includeCodes
          ),
        ]);
        const updated: SavedSnapshot = {
          ...target,
          savedAt: new Date().toLocaleTimeString('zh-CN', { hour12: false }),
          lakehouseDate: lakehouse?.latest_date || bp.funnel_audit?.lakehouse_latest_date || target.lakehouseDate,
          commonStartDate: bp.real_bt_info?.common_start_date || target.commonStartDate,
          y1: bt.benchmark_horizons?.y1 ?? null,
          all: bt.benchmark_horizons?.all ?? null,
          goalHitRatePct: bp.goal_analysis?.historical_hit_rate_pct ?? 0,
          condWinRatePct: bp.goal_analysis?.conditional_win_rate_pct ?? 0,
          mcProbPct: bp.goal_analysis?.monte_carlo_prob_pct ?? 0,
          oosWinRatePct: bp.solver_audit?.oos_conditional_win_rate_pct ?? 0,
          portfolioVolPct: bp.solver_audit?.portfolio_vol_annual_pct ?? 0,
          maxPcrPct: bp.solver_audit?.max_risk_pcr_pct ?? 0,
          items: (bp.items || []).map((it) => ({
            fund_code: it.fund_code,
            fund_name: it.fund_name,
            bucket_label: it.bucket_label || it.role,
            weight_pct: it.weight_pct,
            pcr_pct: it.risk_contribution_pcr_pct ?? it.weight_pct,
            quant_score: it.quant_score ?? 0,
          })),
        };
        setSnapshots((prev) => prev.map((s) => (s.id === id ? updated : s)));
        pushToast(`已按最新湖仓日期刷新快照：${target.label}`, 'success');
      } catch (e) {
        pushToast(e instanceof Error ? e.message : '刷新快照失败', 'error');
      }
    },
    [amount, lakehouse, pushToast, snapshots]
  );

  const isDirty = useMemo(() => {
    if (!appliedParams) return false;
    return (
      appliedParams.riskLevel !== riskLevel ||
      appliedParams.modelId !== modelId ||
      appliedParams.fundCount !== fundCount ||
      appliedParams.targetReturnPct !== targetReturnPct ||
      appliedParams.horizonMonths !== horizonMonths ||
      appliedParams.universeMode !== universeMode ||
      !sameList(appliedParams.excludeCodes || [], excludeCodes) ||
      !sameList(appliedParams.includeCodes || [], includeCodes)
    );
  }, [appliedParams, riskLevel, modelId, fundCount, targetReturnPct, horizonMonths, universeMode, excludeCodes, includeCodes]);

  const staleHint = useMemo(() => {
    if (!isDirty || !appliedParams) return '';
    const uTxt = appliedParams.universeMode === 'full_market' ? '全市场' : '仅指数';
    return `参数或约束已变更，下方仍展示上次已求解结果（${appliedParams.riskLevel} · ${appliedParams.horizonMonths}月+${appliedParams.targetReturnPct}% · ${uTxt} · ${appliedParams.fundCount}只），点击「启动全市场量化求解」同步更新。`;
  }, [isDirty, appliedParams]);

  const solvedContext: SolvedPortfolioContext = useMemo(() => {
    const src = appliedParams || {
      riskLevel,
      modelId,
      fundCount,
      targetReturnPct,
      horizonMonths,
      universeMode,
      excludeCodes,
      includeCodes,
    };
    return {
      ...src,
      fundCodes: (blueprint?.items || []).map((it) => it.fund_code),
    };
  }, [appliedParams, blueprint, riskLevel, modelId, fundCount, targetReturnPct, horizonMonths, universeMode, excludeCodes, includeCodes]);

  const inspectorFundMeta = useMemo(() => {
    if (!inspectorFundCode || !blueprint?.items) return null;
    return blueprint.items.find((it) => it.fund_code === inspectorFundCode) || null;
  }, [inspectorFundCode, blueprint]);

  const currentLedger = useMemo(() => ledgers.find((l) => l.id === activeLedgerId), [ledgers, activeLedgerId]);

  const value: WorkbenchContextValue = {
    activeTab,
    setActiveTab,
    sidebarCollapsed,
    setSidebarCollapsed,
    ledgers,
    activeLedgerId,
    currentLedger,
    overview,
    lakehouse,
    refreshing,
    refreshTick,
    syncingDaily,
    switchLedger,
    createLedger,
    refreshAll,
    notifyDataMutated,
    syncLakehouseDaily,
    riskLevel,
    setRiskLevel,
    modelId,
    setModelId,
    fundCount,
    setFundCount,
    amount,
    setAmount,
    targetReturnPct,
    horizonMonths,
    setGoal,
    universeMode,
    setUniverseMode,
    period,
    setPeriod,
    excludeCodes,
    includeCodes,
    toggleExcludeCode,
    toggleIncludeCode,
    clearConstraints,
    blueprint,
    curves,
    curvesLoading,
    appliedParams,
    solvedContext,
    isDirty,
    staleHint,
    solving,
    solveProgress,
    solveStage,
    solveElapsedMs,
    solveError,
    runAsyncQuantSolve,
    snapshots,
    saveCurrentSnapshot,
    removeSnapshot,
    applySnapshotToLab,
    refreshSnapshot,
    inspectorFundCode,
    inspectorFundMeta,
    openInspector: (code: string) => setInspectorFundCode(code),
    closeInspector: () => setInspectorFundCode(null),
    fullDetailFundCode,
    openFullDetail: (code: string) => {
      setInspectorFundCode(null);
      setFullDetailFundCode(code);
      window.scrollTo({ top: 0, behavior: 'smooth' });
    },
    closeFullDetail: () => setFullDetailFundCode(null),
    dataCenterTab,
    openDataCenter: (tab: DataCenterTab = 'import') => setDataCenterTab(tab),
    closeDataCenter: () => setDataCenterTab(null),
    commandOpen,
    setCommandOpen,
    confirmModal,
    openConfirm: (cfg) => setConfirmModal(cfg),
    closeConfirm: () => setConfirmModal(null),
    toasts,
    pushToast,
  };

  return <WorkbenchContext.Provider value={value}>{children}</WorkbenchContext.Provider>;
}

export function useWorkbench() {
  const ctx = useContext(WorkbenchContext);
  if (!ctx) throw new Error('useWorkbench must be used inside WorkbenchProvider');
  return ctx;
}

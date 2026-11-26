import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  ArrowRight,
  Sparkles,
  Target,
  AlertTriangle,
  Cpu,
  RefreshCw,
  ChevronDown,
  ChevronRight,
  Scale,
  Database,
  Filter,
  Play,
  CheckCircle2,
} from 'lucide-react';
import {
  api,
  type BacktestCurvesResponse,
  type BlueprintResponse,
  type CrowdingPoint,
  type LakehouseStatus,
  type OverviewResponse,
  type SolvedPortfolioContext,
  type UniverseMode,
} from '../api/client';
import { BacktestCharts } from '../components/charts/BacktestCharts';
import { ScenarioBacktestPanel } from '../components/charts/ScenarioBacktestPanel';
import { CrowdingQuadrantChart } from '../components/charts/CrowdingQuadrantChart';
import { ExtremeCyclePanel } from '../components/charts/ExtremeCyclePanel';

interface SignalPageProps {
  overview: OverviewResponse | null;
  ledgerId: string;
  targetReturnPct: number;
  horizonMonths: number;
  initialSolvedCtx?: SolvedPortfolioContext;
  onSolvedContextChange?: (ctx: SolvedPortfolioContext) => void;
  onChangeGoal: (ret: number, mon: number) => void;
  onGoHoldings: () => void;
  onOpenProDrawer: () => void;
  onSelectFund: (code: string) => void;
}

interface AppliedSolveParams {
  riskLevel: string;
  modelId: string;
  fundCount: number;
  targetReturnPct: number;
  horizonMonths: number;
  universeMode: UniverseMode;
}

const ROLE_STYLES = [
  { bar: '#D97706', badge: 'bg-amber-50 text-amber-800 border-amber-200' },
  { bar: '#1D4ED8', badge: 'bg-blue-50 text-blue-800 border-blue-200' },
  { bar: '#0D9488', badge: 'bg-teal-50 text-teal-800 border-teal-200' },
  { bar: '#6366F1', badge: 'bg-indigo-50 text-indigo-800 border-indigo-200' },
  { bar: '#E11D48', badge: 'bg-rose-50 text-rose-800 border-rose-200' },
  { bar: '#B45309', badge: 'bg-orange-50 text-orange-800 border-orange-200' },
];

const RISK_LEVELS = [
  { id: 'C1', label: 'C1 稳健' },
  { id: 'C2', label: 'C2 偏稳' },
  { id: 'C3', label: 'C3 均衡' },
  { id: 'C4', label: 'C4 进取' },
  { id: 'C5', label: 'C5 积极' },
];

const FUND_COUNTS = [3, 4, 5, 6, 8];

const BACKTEST_PERIODS = [
  { id: '3m', label: '近 3 个月' },
  { id: '6m', label: '近 6 个月' },
  { id: '1y', label: '近 1 年' },
  { id: '2y', label: '近 2 年' },
  { id: 'all', label: '全周期' },
];

const HORIZON_OPTIONS = [
  { months: 6, label: '6 个月' },
  { months: 12, label: '1 年' },
  { months: 24, label: '2 年' },
  { months: 36, label: '3 年' },
];

const UNIVERSE_MODES: Array<{ id: UniverseMode; label: string; hint: string }> = [
  { id: 'full_market', label: '全市场量化海选', hint: '主动绩优 + 指增 + 固收+ + 纯债 + QDII + 黄金' },
  { id: 'index_only', label: '仅指数/宽基低费池', hint: '透明被动工具 + 纯债 + 黄金，零主动漂移' },
];

const SOLVE_STAGES = [
  { threshold: 10, label: '① 全市场真净值湖仓' },
  { threshold: 30, label: '② 跨周期去冗余入围' },
  { threshold: 52, label: '③ SLSQP/HRP 换基寻优' },
  { threshold: 82, label: '④ 真净值回测 & 万次MC' },
];

export function SignalPage({
  overview,
  ledgerId,
  targetReturnPct,
  horizonMonths,
  initialSolvedCtx,
  onSolvedContextChange,
  onChangeGoal,
  onGoHoldings,
  onOpenProDrawer,
  onSelectFund,
}: SignalPageProps) {
  const [riskLevel, setRiskLevel] = useState(initialSolvedCtx?.riskLevel || 'C3');
  const [amount, setAmount] = useState(50000);
  const [fundCount, setFundCount] = useState(initialSolvedCtx?.fundCount || 6);
  const [modelId, setModelId] = useState(initialSolvedCtx?.modelId || 'all_weather');
  const [universeMode, setUniverseMode] = useState<UniverseMode>(initialSolvedCtx?.universeMode || 'full_market');
  const [period, setPeriod] = useState('1y');
  const [btSubTab, setBtSubTab] = useState<'full' | 'scenario'>('full');
  const [showAllocLogic, setShowAllocLogic] = useState(false);

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

  const [lakehouse, setLakehouse] = useState<LakehouseStatus | null>(null);
  const [syncingDaily, setSyncingDaily] = useState(false);
  const [syncNotice, setSyncNotice] = useState('');

  const [crowdingScope, setCrowdingScope] = useState<'recommended' | 'holdings'>('recommended');
  const [crowding, setCrowding] = useState<CrowdingPoint[]>([]);
  const [crowdingLoading, setCrowdingLoading] = useState(true);

  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
      solveSeqRef.current += 1;
    };
  }, []);

  // 拉取本地真净值湖仓状态（0 外部请求）
  useEffect(() => {
    api
      .getLakehouseStatus()
      .then((st) => {
        if (mountedRef.current) setLakehouse(st);
      })
      .catch(() => {});
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
            setBlueprint(st.result.blueprint);
            setCurves(st.result.backtest_curves);
            setAppliedParams(eff);
            if (onSolvedContextChange) {
              const solvedCodes = (st.result.blueprint.items || []).map((it) => it.fund_code);
              onSolvedContextChange({ ...eff, fundCodes: solvedCodes });
            }
            setSolveProgress(100);
            setSolving(false);
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
    [riskLevel, modelId, fundCount, targetReturnPct, horizonMonths, universeMode, amount, period, onSolvedContextChange]
  );

  // 首次进入页面自动执行一次默认全市场量化求解（之后调整参数由用户显式点击 CTA 触发，避免逐键抖动）
  const initTriggeredRef = useRef(false);
  useEffect(() => {
    if (initTriggeredRef.current) return;
    initTriggeredRef.current = true;
    void runAsyncQuantSolve(undefined, false);
  }, [runAsyncQuantSolve]);

  // 切换回测统计周期（3m/6m/1y/2y/all）直接复用已求解参数缓存，秒级切片不重跑优化器
  const prevPeriodRef = useRef(period);
  useEffect(() => {
    if (prevPeriodRef.current === period) return;
    prevPeriodRef.current = period;
    if (!appliedParams) return;
    let alive = true;
    setCurvesLoading(true);
    api
      .getBacktestCurves(
        appliedParams.riskLevel,
        appliedParams.modelId,
        appliedParams.fundCount,
        period,
        'model_live',
        appliedParams.targetReturnPct,
        appliedParams.horizonMonths,
        false,
        appliedParams.universeMode
      )
      .then((res) => {
        if (alive) setCurves(res);
      })
      .catch(() => {})
      .finally(() => {
        if (alive) setCurvesLoading(false);
      });
    return () => {
      alive = false;
    };
  }, [period, appliedParams]);

  const recommendedCodesKey = useMemo(
    () => (blueprint?.items || []).map((it) => it.fund_code).join(','),
    [blueprint]
  );

  useEffect(() => {
    let alive = true;
    const recCodes = recommendedCodesKey ? recommendedCodesKey.split(',').filter(Boolean) : [];
    if (crowdingScope === 'recommended' && recCodes.length === 0) {
      return;
    }
    setCrowdingLoading(true);
    api
      .getCrowdingQuadrant(ledgerId, crowdingScope === 'recommended' ? recCodes : undefined)
      .then((res) => {
        if (alive) setCrowding(res.points || []);
      })
      .catch(() => {})
      .finally(() => {
        if (alive) setCrowdingLoading(false);
      });
    return () => {
      alive = false;
    };
  }, [ledgerId, crowdingScope, recommendedCodesKey]);

  const handleSyncDaily = async () => {
    setSyncingDaily(true);
    setSyncNotice('');
    try {
      const res = await api.syncLakehouseDaily(30);
      if (!mountedRef.current) return;
      if (res.status === 'cooldown_skipped') {
        setSyncNotice(res.message || '冷却期内无需重复同步');
      } else if (res.status === 'up_to_date') {
        setSyncNotice(`已是最新交易日（${res.latest_date || lakehouse?.latest_date || ''}）`);
      } else if (res.status === 'updated') {
        setSyncNotice(`安全日更完成：追加 ${res.updated_dates || 1} 个交易日至 ${res.latest_date || ''}（仅 ${res.requests_used || 6} 次批量请求）`);
        const st = await api.getLakehouseStatus();
        if (mountedRef.current) setLakehouse(st);
      } else {
        setSyncNotice(res.message || '同步状态已刷新');
      }
    } catch (e) {
      if (mountedRef.current) setSyncNotice(e instanceof Error ? e.message : '日更失败');
    } finally {
      if (mountedRef.current) setSyncingDaily(false);
    }
  };

  // 参数脏状态检测：改动目标收益/周期/C档/模型/只数/选基范围后提示显式点击 CTA
  const isDirty = useMemo(() => {
    if (!appliedParams) return false;
    return (
      appliedParams.riskLevel !== riskLevel ||
      appliedParams.modelId !== modelId ||
      appliedParams.fundCount !== fundCount ||
      appliedParams.targetReturnPct !== targetReturnPct ||
      appliedParams.horizonMonths !== horizonMonths ||
      appliedParams.universeMode !== universeMode
    );
  }, [appliedParams, riskLevel, modelId, fundCount, targetReturnPct, horizonMonths, universeMode]);

  const staleHint = useMemo(() => {
    if (!isDirty || !appliedParams) return '';
    const uTxt = appliedParams.universeMode === 'full_market' ? '全市场' : '仅指数';
    return `当前下方回测与图表展示上次已求解方案（${appliedParams.riskLevel} · ${appliedParams.horizonMonths}月+${appliedParams.targetReturnPct}% · ${uTxt} · ${appliedParams.fundCount}只），点击上方「启动全市场量化求解」后同步更新。`;
  }, [isDirty, appliedParams]);

  // 拟投金额实时本地按权重等比折算（免去重跑量化求解）
  const liveCapital = Math.max(1000, amount || 50000);
  const displayedItems = useMemo(() => {
    const raw = blueprint?.items || [];
    return raw.map((f) => ({
      ...f,
      suggested_amount: Math.round((liveCapital * f.weight_pct) / 100),
    }));
  }, [blueprint, liveCapital]);

  const verdict = overview?.market_verdict;
  const indices = overview?.indices || {};
  const indexCards = [
    { key: 'sh000300', fallbackName: '沪深 300', note: 'A股核心大盘风向标' },
    { key: 'sh000688', fallbackName: '科创 50', note: '硬核科技弹性指标' },
    { key: 'sh000922', fallbackName: '中证红利', note: '高股息防御底仓锚' },
  ];

  const solverAudit = blueprint?.solver_audit;
  const funnelAudit = blueprint?.funnel_audit || curves?.funnel_audit;
  const realBtInfo = curves?.real_bt_info || blueprint?.real_bt_info;
  const allocLogic = blueprint?.allocation_logic_summary;
  const recon = curves?.goal_reconciliation;

  return (
    <div className="space-y-6 fade-in">
      {/* 1. 深海墨蓝投研英雄看板 */}
      <section className="hero-navy text-white rounded-2xl p-5 sm:p-7 shadow-lg border border-[#1E3A5F] space-y-5">
        <div className="flex flex-col md:flex-row md:items-start justify-between gap-5">
          <div className="space-y-2.5 max-w-3xl">
            <div className="flex flex-wrap items-center gap-2.5">
              <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-amber-400/15 text-amber-300 border border-amber-400/30">
                <span className="w-1.5 h-1.5 rounded-full bg-amber-400" />
                {verdict?.short_label || '市场信号加载中'} · {verdict?.action_tag || '量化研判'}
              </span>
              <span className="text-xs text-slate-300/85">
                {overview?.is_official_nav ? '已同步盘后官方净值' : '实时行情与估值已连接'}
              </span>
            </div>
            <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-white leading-snug">
              {verdict?.detail_explanation || '正在根据十维量化模型与宏观估值信号生成今日大势定调...'}
            </h1>
            <p className="text-xs sm:text-sm text-slate-300 leading-relaxed">
              空仓 / 新钱用户可直接在下方设定「目标收益 × 持有周期 × 选基范围」，基于本地全市场真实复权净值湖仓运行量化海选；已有持仓请切至「我的持仓与体检」。
            </p>
          </div>
          <div className="flex flex-col sm:flex-row md:flex-col gap-2 shrink-0">
            <button
              type="button"
              onClick={onGoHoldings}
              className="px-4 py-2.5 rounded-xl text-xs font-semibold bg-white text-[#0A192F] hover:bg-slate-100 transition-colors shadow-sm inline-flex items-center justify-center gap-1.5 cursor-pointer"
            >
              <span>我有持仓，去体检</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
            <button
              type="button"
              onClick={onOpenProDrawer}
              className="px-4 py-2 rounded-xl text-xs font-medium bg-white/10 text-slate-200 border border-white/15 hover:bg-white/15 transition-colors cursor-pointer"
            >
              查看十维量化投票
            </button>
          </div>
        </div>

        {/* 3 大核心指数毛玻璃行情条 */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3.5 pt-4 border-t border-white/10">
          {indexCards.map(({ key, fallbackName, note }) => {
            const q = indices[key];
            const chg = q?.change_pct ?? null;
            const up = chg !== null && chg >= 0;
            return (
              <div
                key={key}
                className="px-4 py-3 rounded-xl bg-white/[0.06] border border-white/10 flex items-center justify-between gap-2"
              >
                <div>
                  <div className="text-xs text-slate-300 font-medium">{q?.name || fallbackName}</div>
                  <div className="text-base font-bold tabular-nums text-white mt-0.5">
                    {q?.point ? Number(q.point).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : '--'}
                  </div>
                  <div className="text-[11px] text-slate-400 mt-0.5">{note}</div>
                </div>
                <div className="text-right">
                  <div className={`text-sm font-bold tabular-nums ${chg === null ? 'text-slate-300' : up ? 'text-rose-400' : 'text-emerald-400'}`}>
                    {chg === null ? '--' : `${up ? '+' : ''}${Number(chg).toFixed(2)}%`}
                  </div>
                  <div className="text-[10px] text-slate-400 mt-1">{q?.is_fallback ? '缓存快照' : '实时行情'}</div>
                </div>
              </div>
            );
          })}
        </div>
      </section>

      {/* 2. 全市场量化选基方案生成器（28,177 漏斗 → 离线真净值湖仓 → 显式 4 阶段异步求解） */}
      <section className="card-elevated rounded-2xl p-5 sm:p-6 space-y-5">
        <div className="flex flex-col xl:flex-row xl:items-start justify-between gap-4">
          <div className="space-y-1.5">
            <div className="flex flex-wrap items-center gap-2">
              <span className="w-1 h-4 rounded-full bg-[#1D4ED8]" />
              <h2 className="text-base font-bold text-slate-900">空仓 / 新钱全市场量化选基方案生成器</h2>
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-medium bg-blue-50 text-blue-700">
                <Sparkles className="w-3 h-3" />
                28,177 全市场漏斗 · 真实复权净值寻优
              </span>
            </div>
            <p className="text-xs text-slate-500 pl-3">
              <strong>零在线爬虫防封禁架构：</strong>先调好目标收益、周期、C 档、模型与选基范围，再点击<strong>「启动全市场量化求解」</strong>，在本地真实复权净值湖仓上完成相关性去冗余、SLSQP/HRP 换基寻优与双万次蒙特卡洛。
            </p>
          </div>

          {/* 本地真净值湖仓状态 + 防封禁盘后日更胶囊 */}
          <div className="flex flex-wrap items-center gap-2 shrink-0">
            <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-xl bg-slate-50 border border-slate-200 text-[11px] text-slate-600 tabular-nums">
              <Database className="w-3.5 h-3.5 text-emerald-600 shrink-0" />
              <span>
                本地真净值湖仓{' '}
                <strong className="text-slate-900">{lakehouse?.elite_fund_count ?? funnelAudit?.elite_lakehouse_funds ?? '--'}</strong> 只
                {lakehouse?.latest_date ? ` · 截至 ${lakehouse.latest_date}` : ''}
              </span>
              <button
                type="button"
                onClick={handleSyncDaily}
                disabled={syncingDaily}
                title="仅用 6~8 次批量请求安全追加最新盘后官方复权净值（30 分钟冷却防封禁）"
                className="px-2 py-0.5 rounded-md bg-white border border-slate-300 text-slate-700 font-semibold hover:border-emerald-500 hover:text-emerald-700 inline-flex items-center gap-1 cursor-pointer disabled:opacity-50"
              >
                <RefreshCw className={`w-3 h-3 ${syncingDaily ? 'animate-spin text-emerald-600' : ''}`} />
                <span>{syncingDaily ? '安全日更中' : '盘后安全日更'}</span>
              </button>
            </div>
          </div>
        </div>

        {syncNotice && (
          <div className="px-3.5 py-2 rounded-lg bg-emerald-50 border border-emerald-200 text-xs text-emerald-800 flex items-center justify-between gap-2">
            <span className="inline-flex items-center gap-1.5">
              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 shrink-0" />
              <span>{syncNotice}</span>
            </span>
            <button type="button" onClick={() => setSyncNotice('')} className="text-[11px] text-emerald-700 hover:underline cursor-pointer">
              关闭
            </button>
          </div>
        )}

        {/* 第一排控制区：选基范围 + 拟投金额 + 只数 + C1~C5 */}
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex flex-wrap items-center gap-2">
            <div className="inline-flex items-center gap-1 bg-slate-100 p-1 rounded-xl border border-slate-200" role="group" aria-label="选基范围模式">
              <span className="px-2 text-[11px] text-slate-500 font-medium inline-flex items-center gap-1">
                <Filter className="w-3 h-3" />
                选基池
              </span>
              {UNIVERSE_MODES.map((u) => (
                <button
                  key={u.id}
                  type="button"
                  title={u.hint}
                  onClick={() => setUniverseMode(u.id)}
                  className={`px-2.5 py-1 rounded-lg text-xs font-semibold transition-all cursor-pointer ${
                    universeMode === u.id ? 'bg-indigo-700 text-white shadow-xs' : 'text-slate-600 hover:text-slate-900'
                  }`}
                >
                  {u.label}
                </button>
              ))}
            </div>

            <label className="flex items-center gap-2 text-xs font-medium text-slate-600">
              <span>拟投金额 (¥)</span>
              <input
                type="number"
                min={1000}
                step={5000}
                value={amount}
                onChange={(e) => setAmount(Number(e.target.value))}
                className="w-28 h-9 px-3 rounded-lg bg-slate-50 border border-slate-200 text-slate-900 font-bold tabular-nums text-sm focus:border-[#1D4ED8] focus:bg-white focus:outline-none"
              />
            </label>
          </div>

          <div className="flex flex-wrap items-center gap-2.5">
            <div className="flex items-center gap-1 bg-slate-100 p-1 rounded-xl border border-slate-200" role="group" aria-label="基金数量">
              <span className="px-2 text-[11px] text-slate-500 font-medium">只数</span>
              {FUND_COUNTS.map((n) => (
                <button
                  key={n}
                  type="button"
                  onClick={() => setFundCount(n)}
                  className={`px-2.5 py-1 rounded-lg text-xs font-semibold transition-all cursor-pointer ${
                    fundCount === n ? 'bg-[#1D4ED8] text-white shadow-xs' : 'text-slate-600 hover:text-slate-900'
                  }`}
                >
                  {n}只
                </button>
              ))}
            </div>

            <div className="flex items-center gap-1 bg-slate-100 p-1 rounded-xl border border-slate-200" role="group" aria-label="风险偏好档位">
              {RISK_LEVELS.map((r) => (
                <button
                  key={r.id}
                  type="button"
                  onClick={() => setRiskLevel(r.id)}
                  className={`px-2.5 py-1 rounded-lg text-xs font-semibold transition-all cursor-pointer ${
                    riskLevel === r.id ? 'bg-[#0A192F] text-white shadow-xs' : 'text-slate-600 hover:text-slate-900'
                  }`}
                >
                  {r.label}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* 第二排控制区：目标收益 × 目标持有周期 + 显式启动全市场量化求解 CTA */}
        <div
          className={`p-4 rounded-xl border flex flex-wrap items-center justify-between gap-4 transition-colors ${
            isDirty ? 'bg-amber-50/70 border-amber-300' : 'bg-slate-50 border-slate-200'
          }`}
        >
          <div className="flex flex-wrap items-center gap-3">
            <span className="inline-flex items-center gap-1.5 text-xs font-bold text-slate-800">
              <Target className="w-4 h-4 text-blue-700" />
              <span>我的投资目标</span>
            </span>
            <div className="inline-flex flex-wrap items-center gap-1.5 text-xs text-slate-600">
              <span>在</span>
              <div className="inline-flex items-center gap-1 bg-white p-0.5 rounded-lg border border-slate-200" role="group" aria-label="目标持有周期">
                {HORIZON_OPTIONS.map((h) => (
                  <button
                    key={h.months}
                    type="button"
                    onClick={() => onChangeGoal(targetReturnPct, h.months)}
                    className={`px-2 py-1 rounded-md text-xs font-semibold cursor-pointer ${
                      horizonMonths === h.months ? 'bg-[#0A192F] text-white' : 'text-slate-600 hover:text-slate-900'
                    }`}
                  >
                    {h.label}
                  </button>
                ))}
              </div>
              <label className="inline-flex items-center gap-1.5">
                <span>内，可控波动下期望收益</span>
                <input
                  type="number"
                  min={2}
                  max={60}
                  step={1}
                  value={targetReturnPct}
                  onChange={(e) => onChangeGoal(Math.max(2, Math.min(60, Number(e.target.value) || 10)), horizonMonths)}
                  aria-label="目标收益率百分比"
                  className="w-16 h-8 px-2 rounded-lg bg-white border border-slate-300 text-center font-bold text-blue-700 tabular-nums"
                />
                <span className="font-bold text-slate-700">%</span>
              </label>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-2.5 text-xs tabular-nums">
            {blueprint?.goal_analysis && !isDirty && (
              <>
                <span className="text-slate-500">
                  折合年化 <strong className="text-slate-900">+{blueprint.goal_analysis.required_cagr_pct.toFixed(1)}%</strong>
                </span>
                <span className="px-2.5 py-1 rounded-full font-bold bg-blue-50 text-blue-800 border border-blue-200">
                  滚动触达率 {blueprint.goal_analysis.historical_hit_rate_pct.toFixed(1)}%
                </span>
                {blueprint.goal_analysis.conditional_win_rate_pct !== undefined && (
                  <span className="px-2.5 py-1 rounded-full font-semibold bg-indigo-50 text-indigo-800 border border-indigo-200">
                    同温层胜率 {blueprint.goal_analysis.conditional_win_rate_pct.toFixed(1)}%
                  </span>
                )}
                {blueprint.goal_analysis.monte_carlo_prob_pct !== undefined && (
                  <span className="px-2.5 py-1 rounded-full font-semibold bg-white text-slate-700 border border-slate-200">
                    MC 概率 {blueprint.goal_analysis.monte_carlo_prob_pct.toFixed(1)}%
                  </span>
                )}
                <span
                  className={`px-2 py-0.5 rounded-full text-[11px] font-semibold ${
                    blueprint.goal_analysis.feasibility_level === 'high'
                      ? 'bg-emerald-50 text-emerald-700'
                      : blueprint.goal_analysis.feasibility_level === 'medium'
                      ? 'bg-amber-50 text-amber-700'
                      : 'bg-rose-50 text-rose-700'
                  }`}
                >
                  {blueprint.goal_analysis.feasibility}
                </span>
              </>
            )}

            {isDirty && !solving && (
              <span className="text-xs font-semibold text-amber-800">
                参数已变更，点击右侧按钮启动全市场重算
              </span>
            )}

            <button
              type="button"
              onClick={() => void runAsyncQuantSolve(undefined, !isDirty)}
              disabled={solving}
              data-testid="btn-start-quant-solve"
              className={`px-4 py-2 rounded-xl text-xs font-bold inline-flex items-center gap-1.5 transition-all cursor-pointer disabled:opacity-60 shadow-xs ${
                isDirty
                  ? 'bg-[#1D4ED8] text-white hover:bg-blue-800 ring-2 ring-blue-500/30'
                  : 'bg-[#0A192F] text-white hover:bg-slate-800'
              }`}
            >
              {solving ? (
                <RefreshCw className="w-3.5 h-3.5 animate-spin" />
              ) : (
                <Play className="w-3.5 h-3.5 fill-current" />
              )}
              <span>
                {solving
                  ? `求解中 ${solveProgress}%`
                  : isDirty
                  ? '启动全市场量化求解'
                  : '重新全市场量化求解'}
              </span>
            </button>
          </div>
        </div>

        {/* 4 套量化模型选择卡 */}
        {blueprint?.all_models && blueprint.all_models.length > 0 && (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
            {blueprint.all_models.map((m) => {
              const active = m.id === modelId;
              return (
                <button
                  key={m.id}
                  type="button"
                  onClick={() => setModelId(m.id)}
                  className={`text-left p-3.5 rounded-xl border transition-all cursor-pointer ${
                    active
                      ? 'bg-blue-50/80 border-blue-600 shadow-xs ring-1 ring-blue-600/20'
                      : 'bg-slate-50/70 border-slate-200 hover:border-slate-300 hover:bg-white'
                  }`}
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className={`font-bold text-xs ${active ? 'text-blue-900' : 'text-slate-800'}`}>{m.name}</span>
                    <span
                      className={`px-1.5 py-0.5 rounded text-[10px] font-semibold shrink-0 ${
                        active ? 'bg-blue-600 text-white' : 'bg-slate-200/80 text-slate-600'
                      }`}
                    >
                      {m.tag}
                    </span>
                  </div>
                  <p className="text-[11px] text-slate-600 mt-1.5 leading-relaxed">{m.scenario}</p>
                </button>
              );
            })}
          </div>
        )}

        {/* 真实 4 阶段异步量化求解进度条 */}
        {solving && (
          <div
            data-testid="quant-solve-progress"
            className="p-4 rounded-xl bg-gradient-to-r from-blue-50 via-indigo-50/70 to-slate-50 border border-blue-200 space-y-3"
          >
            <div className="flex flex-wrap items-center justify-between gap-2 text-xs">
              <div className="flex items-center gap-2 font-bold text-blue-950">
                <Cpu className="w-4 h-4 text-blue-600 animate-pulse shrink-0" />
                <span>{solveStage || '正在运行全市场真实复权净值量化求解...'}</span>
              </div>
              <span className="font-mono font-bold text-blue-700 tabular-nums">
                {solveProgress}% · 已耗时 {(solveElapsedMs / 1000).toFixed(1)}s
              </span>
            </div>
            <div className="h-2 rounded-full bg-white border border-blue-100 overflow-hidden">
              <div
                className="h-full rounded-full bg-gradient-to-r from-blue-600 to-indigo-600 transition-all duration-300"
                style={{ width: `${Math.max(6, Math.min(100, solveProgress))}%` }}
              />
            </div>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-[11px]">
              {SOLVE_STAGES.map((st) => {
                const done = solveProgress >= st.threshold + 20;
                const current = solveProgress >= st.threshold && !done;
                return (
                  <div
                    key={st.label}
                    className={`px-2.5 py-1 rounded-lg border font-medium transition-colors ${
                      done
                        ? 'bg-emerald-50 border-emerald-200 text-emerald-800'
                        : current
                        ? 'bg-blue-600 border-blue-600 text-white'
                        : 'bg-white/80 border-slate-200 text-slate-400'
                    }`}
                  >
                    {st.label}
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {solveError && (
          <div className="px-4 py-2.5 rounded-xl bg-rose-50 border border-rose-200 text-xs text-rose-800 flex items-center justify-between gap-2">
            <span>量化求解提示：{solveError}</span>
            <button
              type="button"
              onClick={() => void runAsyncQuantSolve(undefined, false)}
              className="px-2.5 py-1 rounded-lg bg-rose-600 text-white font-semibold hover:bg-rose-700 cursor-pointer"
            >
              重试求解
            </button>
          </div>
        )}

        {/* 全市场透明选基漏斗条 */}
        {funnelAudit && (
          <div
            data-testid="full-market-funnel-bar"
            className="px-4 py-2.5 rounded-xl bg-slate-900 text-slate-100 text-[11px] flex flex-wrap items-center justify-between gap-2 tabular-nums"
          >
            <div className="flex flex-wrap items-center gap-1.5">
              <span className="px-2 py-0.5 rounded bg-white/10 text-amber-300 font-bold">全市场海选漏斗</span>
              <span>
                全市场 <strong>{funnelAudit.total_market_funds.toLocaleString()}</strong> 只
              </span>
              <span className="text-slate-500">→</span>
              <span>
                合规初筛 <strong>{funnelAudit.compliant_screened_funds.toLocaleString()}</strong> 只
              </span>
              <span className="text-slate-500">→</span>
              <span>
                本地真净值湖仓 <strong className="text-emerald-300">{funnelAudit.elite_lakehouse_funds}</strong> 只
              </span>
              <span className="text-slate-500">→</span>
              <span>
                跨周期达标 <strong>{funnelAudit.eligible_depth_funds}</strong> 只
              </span>
              <span className="text-slate-500">→</span>
              <span>
                相关性去冗余入围 <strong className="text-sky-300">{funnelAudit.shortlisted_candidates}</strong> 只
              </span>
              <span className="text-slate-500">→</span>
              <span>
                终选 <strong className="text-amber-300">{funnelAudit.final_selected_funds}</strong> 只
              </span>
            </div>
            <span className="text-slate-400">{funnelAudit.universe_label}</span>
          </div>
        )}

        {/* 目标可行性与风险-收益碰撞诊断提示 */}
        {blueprint?.goal_analysis && (
          <div
            className={`px-4 py-2.5 rounded-xl border text-xs flex flex-wrap items-center justify-between gap-2 ${
              blueprint.goal_analysis.has_collision
                ? 'bg-amber-50/80 border-amber-200 text-amber-900'
                : 'bg-emerald-50/60 border-emerald-200 text-emerald-900'
            }`}
          >
            <span className="flex items-start gap-1.5 leading-relaxed">
              {blueprint.goal_analysis.has_collision && <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />}
              <span>
                {blueprint.goal_analysis.collision_message}
                {blueprint.goal_analysis.windows_tested > 0 && (
                  <span className="ml-1.5 text-slate-600">
                    （真实复权净值共 {blueprint.goal_analysis.windows_tested} 个滚动起点实测：中位收益{' '}
                    {blueprint.goal_analysis.median_return_pct >= 0 ? '+' : ''}
                    {blueprint.goal_analysis.median_return_pct.toFixed(1)}%，P05 最差情景{' '}
                    {blueprint.goal_analysis.p05_worst_return_pct.toFixed(1)}%，正收益概率{' '}
                    {(blueprint.goal_analysis.no_loss_rate_pct ?? 0).toFixed(1)}%
                    {blueprint.goal_analysis.avg_reach_months ? `，达标平均耗时 ${blueprint.goal_analysis.avg_reach_months} 个月` : ''}）
                  </span>
                )}
              </span>
            </span>
            {blueprint.goal_analysis.has_collision && (
              <button
                type="button"
                onClick={() => {
                  const nextTier = blueprint.goal_analysis!.suggested_tier;
                  const nextModel = blueprint.goal_analysis!.recommended_model;
                  setRiskLevel(nextTier);
                  setModelId(nextModel);
                  void runAsyncQuantSolve({ riskLevel: nextTier, modelId: nextModel }, false);
                }}
                className="px-3 py-1 rounded-lg text-[11px] font-semibold bg-amber-600 text-white hover:bg-amber-700 shrink-0 cursor-pointer"
              >
                一键对齐至 {blueprint.goal_analysis.suggested_tier} 档位与推荐模型并重算
              </button>
            )}
          </div>
        )}

        {/* 真量化求解器透明遥测栏 + 可展开的「资金与比例分配产生原因」 */}
        {blueprint && (
          <div className="rounded-xl bg-blue-50/60 border border-blue-100 overflow-hidden">
            <div className="px-4 py-2.5 text-xs text-slate-700 flex flex-wrap items-center justify-between gap-2">
              <div className="flex flex-wrap items-center gap-2">
                <Cpu className="w-3.5 h-3.5 text-blue-700 shrink-0" />
                <span>
                  求解引擎：<strong className="text-slate-900">{solverAudit?.solver_algorithm || blueprint.model_meta?.name}</strong> ·{' '}
                  <strong className="text-slate-900">{blueprint.risk_meta.label}</strong>
                </span>
                {solverAudit && (
                  <span className="px-2 py-0.5 rounded bg-white/90 border border-blue-200 text-[11px] font-mono text-blue-800 tabular-nums">
                    {solverAudit.from_cache ? `命中当日求解缓存 (原算 ${solverAudit.compute_ms}ms)` : `实算耗时 ${solverAudit.compute_ms}ms`} · 样本外 OOS 胜率 {solverAudit.oos_conditional_win_rate_pct.toFixed(1)}% · 组合年化波动 {solverAudit.portfolio_vol_annual_pct.toFixed(1)}%
                  </span>
                )}
              </div>
              <div className="flex items-center gap-3">
                <span className="font-bold text-blue-800 tabular-nums">
                  合计：¥{liveCapital.toLocaleString()}（严格精选 {blueprint.count} 只 · 权重 100.0%）
                </span>
                {allocLogic && (
                  <button
                    type="button"
                    onClick={() => setShowAllocLogic((v) => !v)}
                    className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg bg-white border border-blue-200 text-[11px] font-semibold text-blue-800 hover:bg-blue-50 cursor-pointer"
                  >
                    {showAllocLogic ? <ChevronDown className="w-3.5 h-3.5" /> : <ChevronRight className="w-3.5 h-3.5" />}
                    <span>资金与比例是如何算出来的</span>
                  </button>
                )}
              </div>
            </div>

            {showAllocLogic && allocLogic && (
              <div className="px-4 py-3 bg-white/90 border-t border-blue-100 text-xs space-y-2.5">
                <p className="text-slate-700 font-medium leading-relaxed">{allocLogic.headline}</p>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                  {allocLogic.steps.map((s, idx) => (
                    <div key={idx} className="p-2.5 rounded-lg bg-slate-50 border border-slate-200/80 text-[11px] text-slate-600 leading-relaxed">
                      {s}
                    </div>
                  ))}
                </div>
                {allocLogic.class_weights_pct && Object.keys(allocLogic.class_weights_pct).length > 0 && (
                  <div className="flex flex-wrap items-center gap-2 pt-1 text-[11px]">
                    <span className="font-semibold text-slate-600">风格桶配比：</span>
                    {Object.entries(allocLogic.class_weights_pct).map(([k, v]) => (
                      <span key={k} className="px-2 py-0.5 rounded-full bg-slate-100 text-slate-700 font-semibold tabular-nums">
                        {k} {Number(v).toFixed(1)}%
                      </span>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {solving && !blueprint ? (
          <div className="py-10 text-center text-xs text-slate-500">
            正在从本地 28,177 全市场漏斗与真实复权净值湖仓运行 SLSQP / HRP / 局部换基与双万次蒙特卡洛求解...
          </div>
        ) : (
          <div className={`grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 transition-opacity ${solving ? 'opacity-60' : ''}`}>
            {displayedItems.map((f, idx) => {
              const st = ROLE_STYLES[idx % ROLE_STYLES.length];
              return (
                <article
                  key={f.fund_code}
                  onClick={() => onSelectFund(f.fund_code)}
                  role="button"
                  tabIndex={0}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' || e.key === ' ') {
                      e.preventDefault();
                      onSelectFund(f.fund_code);
                    }
                  }}
                  className="rounded-xl bg-white border border-slate-200 overflow-hidden hover:border-blue-400 hover:shadow-md transition-all flex flex-col justify-between cursor-pointer group"
                >
                  <div className="h-1" style={{ background: st.bar }} />
                  <div className="p-4 flex-1 flex flex-col justify-between gap-3">
                    <div className="space-y-2">
                      <div className="flex items-center justify-between gap-2">
                        <div className="flex flex-wrap items-center gap-1.5">
                          <span className={`px-2 py-0.5 rounded-md text-[11px] font-semibold border ${st.badge}`}>{f.role}</span>
                          {f.is_active_fund !== undefined && (
                            <span
                              className={`px-1.5 py-0.5 rounded-md text-[10px] font-semibold ${
                                f.is_active_fund
                                  ? 'bg-violet-50 text-violet-700 border border-violet-200'
                                  : 'bg-sky-50 text-sky-700 border border-sky-200'
                              }`}
                            >
                              {f.is_active_fund ? '主动精选' : '低费工具'}
                            </span>
                          )}
                          {f.quant_score !== undefined && (
                            <span className="px-1.5 py-0.5 rounded-md text-[10px] font-bold bg-[#0A192F] text-amber-300 tabular-nums">
                              量化 {f.quant_score}分
                            </span>
                          )}
                        </div>
                        <span className="text-xs font-mono text-slate-400 group-hover:text-blue-600 transition-colors shrink-0">
                          {f.fund_code} · 详情 →
                        </span>
                      </div>
                      <h3 className="font-bold text-sm text-slate-900 group-hover:text-blue-700 transition-colors">{f.fund_name}</h3>
                      <p className="text-xs text-slate-600 leading-relaxed">{f.why}</p>

                      {/* 透明资金与比例产生公式胶囊 */}
                      {f.solver_weight_pct !== undefined && (
                        <div className="px-2.5 py-1.5 rounded-lg bg-blue-50/70 border border-blue-100 text-[11px] text-blue-900 tabular-nums flex flex-wrap items-center justify-between gap-1">
                          <span>
                            模型求解 <strong>{f.solver_weight_pct.toFixed(1)}%</strong>
                            {f.factor_tilt_delta_pct !== undefined && Math.abs(f.factor_tilt_delta_pct) >= 0.1
                              ? ` → 因子微调 ${f.factor_tilt_delta_pct >= 0 ? '+' : ''}${f.factor_tilt_delta_pct.toFixed(1)}%`
                              : ' → 因子校验维持'}
                          </span>
                          {f.risk_contribution_pcr_pct !== undefined && (
                            <span className="font-semibold text-indigo-700">
                              风险贡献 {f.risk_contribution_pcr_pct.toFixed(1)}%
                            </span>
                          )}
                        </div>
                      )}

                      {f.quant_reason && (
                        <div className="p-2.5 rounded-lg bg-slate-50 border border-slate-100 text-[11px] text-slate-600 leading-relaxed">
                          <strong className="text-slate-800">配权归因：</strong>
                          {f.quant_reason}
                        </div>
                      )}
                      {f.quota_note && (
                        <div className="px-2.5 py-1.5 rounded-lg bg-amber-50 border border-amber-200 text-[11px] text-amber-800 leading-relaxed">
                          限购提示：{f.quota_note}
                        </div>
                      )}
                      {f.fee_note && (
                        <div className="text-[11px] text-slate-400">
                          费率与实操：{f.fee_note}
                        </div>
                      )}
                    </div>
                    <div className="space-y-2 pt-2 border-t border-slate-100">
                      <div className="flex items-baseline justify-between tabular-nums">
                        <span className="text-lg font-extrabold text-slate-900">
                          ¥{Math.round(f.suggested_amount).toLocaleString()}
                        </span>
                        <span className="text-sm font-extrabold" style={{ color: st.bar }}>
                          占比 {f.weight_pct.toFixed(1)}%
                        </span>
                      </div>
                      <div className="h-1.5 rounded-full bg-slate-100 overflow-hidden">
                        <div
                          className="h-full rounded-full"
                          style={{ width: `${Math.min(100, f.weight_pct)}%`, background: st.bar }}
                        />
                      </div>
                    </div>
                  </div>
                </article>
              );
            })}
          </div>
        )}
      </section>

      {/* 3. 动态联动的当前方案历史回测表现（100% 基金真实复权净值 + 与上方方案权重同源 + 目标 vs 回测偏差归因） */}
      <section className="card-elevated rounded-2xl p-5 sm:p-6 space-y-4">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-3">
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <span className="w-1 h-4 rounded-full bg-amber-600" />
              <h2 className="text-base font-bold text-slate-900">
                当前方案历史回测表现（{curves?.period_label || '近 1 年'}）
              </h2>
              {curves?.date_range && (
                <span className="text-[11px] font-mono text-slate-400">{curves.date_range}</span>
              )}
              {realBtInfo?.is_real_nav && (
                <span
                  data-testid="real-nav-backtest-badge"
                  className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200"
                >
                  100% 基金真实复权净值回测 · 共同存续自 {realBtInfo.common_start_date}
                </span>
              )}
              <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-blue-50 text-blue-700 border border-blue-200">
                与上方方案权重 100% 同源
              </span>
            </div>
            <p className="text-xs text-slate-500 mt-1 pl-3">
              严格采用上方终选 {blueprint?.count || fundCount} 只基金自身的红利再投资复权净值（绝非沪深 300 替身），按 95% 实盘仓位与申赎费率测算
            </p>
          </div>
          <div className="inline-flex flex-wrap items-center gap-1 bg-slate-100 p-1 rounded-xl border border-slate-200" role="group" aria-label="回测统计周期">
            {BACKTEST_PERIODS.map((p) => (
              <button
                key={p.id}
                type="button"
                onClick={() => setPeriod(p.id)}
                className={`px-2.5 py-1 rounded-lg text-xs font-semibold transition-all cursor-pointer ${
                  period === p.id ? 'bg-[#0A192F] text-white shadow-xs' : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                {p.label}
              </button>
            ))}
          </div>
        </div>

        {staleHint && (
          <div
            data-testid="backtest-stale-banner"
            className="px-3.5 py-2 rounded-xl bg-amber-50 border border-amber-200 text-xs text-amber-900 font-medium"
          >
            {staleHint}
          </div>
        )}

        {(curvesLoading || solving) && !curves?.metrics ? (
          <div className="py-8 text-center text-xs text-slate-400">正在按上方求解权重与基金真实复权净值合成历史表现...</div>
        ) : curves?.metrics ? (
          <>
            <div className={`grid grid-cols-2 lg:grid-cols-4 gap-3.5 transition-opacity ${curvesLoading || solving ? 'opacity-60' : ''}`}>
              <div className="p-4 rounded-xl bg-gradient-to-b from-red-50/70 to-white border border-red-100">
                <div className="text-xs font-medium text-slate-500">
                  {curves.period_label}区间收益（实盘校准）
                </div>
                <div
                  className={`text-2xl font-extrabold tabular-nums mt-1.5 ${
                    curves.metrics.period_return_pct >= 0 ? 'text-red-600' : 'text-emerald-700'
                  }`}
                >
                  {curves.metrics.period_return_pct >= 0 ? '+' : ''}
                  {curves.metrics.period_return_pct.toFixed(2)}%
                </div>
                <div className="text-[11px] text-slate-500 mt-1 tabular-nums">
                  同期沪深 300：{curves.metrics.hs300_return_pct >= 0 ? '+' : ''}
                  {curves.metrics.hs300_return_pct.toFixed(2)}%（超额 {curves.metrics.excess_return_pct >= 0 ? '+' : ''}
                  {curves.metrics.excess_return_pct.toFixed(2)}%）
                </div>
              </div>

              <div className="p-4 rounded-xl bg-gradient-to-b from-emerald-50/70 to-white border border-emerald-100">
                <div className="text-xs font-medium text-slate-500">区间最大回撤</div>
                <div className="text-2xl font-extrabold tabular-nums mt-1.5 text-emerald-700">
                  -{Math.abs(curves.metrics.max_drawdown_pct).toFixed(2)}%
                </div>
                <div className="text-[11px] text-slate-500 mt-1 tabular-nums">
                  同期沪深 300 最大回撤 -{Math.abs(curves.metrics.hs300_mdd_pct).toFixed(2)}%
                </div>
              </div>

              <div className="p-4 rounded-xl bg-gradient-to-b from-blue-50/70 to-white border border-blue-100">
                <div className="text-xs font-medium text-slate-500">{curves.metrics.win_rate_label}</div>
                <div className="text-2xl font-extrabold tabular-nums mt-1.5 text-blue-700">
                  {curves.metrics.win_rate_pct.toFixed(1)}%
                </div>
                <div className="text-[11px] text-slate-500 mt-1">{curves.metrics.win_rate_detail}</div>
              </div>

              <div className="p-4 rounded-xl bg-gradient-to-b from-amber-50/70 to-white border border-amber-100">
                <div className="text-xs font-medium text-slate-500">风险调整夏普比率</div>
                <div className="text-2xl font-extrabold tabular-nums mt-1.5 text-amber-700">
                  {curves.metrics.sharpe_ratio.toFixed(2)}
                </div>
                <div className="text-[11px] text-slate-500 mt-1 tabular-nums">
                  {curves.metrics.annualized_return_pct !== null
                    ? `折合年化 ${curves.metrics.annualized_return_pct >= 0 ? '+' : ''}${curves.metrics.annualized_return_pct.toFixed(2)}%`
                    : `统计覆盖 ${curves.metrics.trading_days} 个交易日`}
                </div>
              </div>
            </div>

            {/* 目标收益 vs 当前回测窗口偏差归因与「为何仍建议本配置」说明卡 */}
            {recon && (
              <div
                className={`p-4 rounded-xl border space-y-3 ${
                  recon.status === 'aligned'
                    ? 'bg-emerald-50/50 border-emerald-200'
                    : recon.status === 'backtest_below_goal'
                    ? 'bg-amber-50/60 border-amber-200'
                    : 'bg-blue-50/60 border-blue-200'
                }`}
              >
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <Scale className="w-4 h-4 text-slate-700 shrink-0" />
                    <h3 className="text-xs font-bold text-slate-900">
                      目标收益 vs 历史回测对照与配置合理性说明
                    </h3>
                    <span
                      className={`px-2 py-0.5 rounded-full text-[11px] font-semibold ${
                        recon.status === 'aligned'
                          ? 'bg-emerald-100 text-emerald-800'
                          : recon.status === 'backtest_below_goal'
                          ? 'bg-amber-100 text-amber-900'
                          : 'bg-blue-100 text-blue-900'
                      }`}
                    >
                      {recon.badge}
                    </span>
                  </div>
                  <div className="flex flex-wrap items-center gap-2 text-[11px] font-semibold tabular-nums">
                    <span className="px-2 py-0.5 rounded bg-white border border-slate-200 text-slate-700">
                      目标口径 ({recon.compare_metric_label})：{recon.goal_comparable_pct >= 0 ? '+' : ''}
                      {recon.goal_comparable_pct.toFixed(2)}%
                    </span>
                    <span className="px-2 py-0.5 rounded bg-white border border-slate-200 text-slate-900">
                      本窗口实测：{recon.backtest_comparable_pct >= 0 ? '+' : ''}
                      {recon.backtest_comparable_pct.toFixed(2)}%
                    </span>
                    <span
                      className={`px-2 py-0.5 rounded bg-white border font-bold ${
                        recon.gap_pct >= 0 ? 'border-red-200 text-red-700' : 'border-amber-300 text-amber-800'
                      }`}
                    >
                      差异 {recon.gap_pct >= 0 ? '+' : ''}
                      {recon.gap_pct.toFixed(2)}%
                    </span>
                  </div>
                </div>

                <p className="text-xs text-slate-800 leading-relaxed font-medium">{recon.headline}</p>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-2.5">
                  {recon.reasons.map((r, i) => (
                    <div key={i} className="p-3 rounded-lg bg-white/90 border border-slate-200/80 space-y-1">
                      <div className="text-[11px] font-bold text-slate-900">
                        {i + 1}. {r.title}
                      </div>
                      <p className="text-[11px] text-slate-600 leading-relaxed">{r.detail}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}

            <p className="text-[11px] text-slate-400">
              注：历史回测基于上方目标驱动全市场求解出的完全一致权重与基金真实复权净值测算，仅供量化分析参考，过往业绩不代表未来收益保证。
            </p>
          </>
        ) : null}
      </section>

      {/* 4. 极端市场预计修复天数、历史修复天数、完整周期与量化止盈锚点 */}
      <ExtremeCyclePanel
        data={curves?.extreme_cycle_analysis}
        loading={curvesLoading || solving}
        targetReturnPct={appliedParams?.targetReturnPct ?? targetReturnPct}
        horizonMonths={appliedParams?.horizonMonths ?? horizonMonths}
      />

      {/* 5. 历史回测验证区：全周期走势 | 历史情景回测 */}
      <div className="space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <span className="w-1 h-4 rounded-full bg-[#0A192F]" />
            <h2 className="text-base font-bold text-slate-900">历史业绩验证与情景压力检验</h2>
          </div>
          <div className="inline-flex items-center gap-1 bg-white p-1 rounded-xl border border-slate-200 shadow-xs">
            <button
              type="button"
              onClick={() => setBtSubTab('full')}
              className={`px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-all cursor-pointer ${
                btSubTab === 'full' ? 'bg-[#0A192F] text-white' : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              真实净值全周期走势
            </button>
            <button
              type="button"
              onClick={() => setBtSubTab('scenario')}
              className={`px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-all cursor-pointer ${
                btSubTab === 'scenario' ? 'bg-[#0A192F] text-white' : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              历史情景回测
            </button>
          </div>
        </div>

        {btSubTab === 'full' ? (
          <BacktestCharts data={curves} loading={curvesLoading || solving} staleHint={staleHint} />
        ) : (
          <ScenarioBacktestPanel
            tier={appliedParams?.riskLevel ?? riskLevel}
            modelId={appliedParams?.modelId ?? modelId}
            fundCount={appliedParams?.fundCount ?? fundCount}
            targetReturnPct={appliedParams?.targetReturnPct ?? targetReturnPct}
            horizonMonths={appliedParams?.horizonMonths ?? horizonMonths}
            universeMode={appliedParams?.universeMode ?? universeMode}
            staleHint={staleHint}
          />
        )}
      </div>

      {/* 6. 短期偏离与交易拥挤度象限散点图（默认自动联动上方全市场推荐组合） */}
      <CrowdingQuadrantChart
        points={crowding}
        loading={crowdingLoading}
        scopeMode={crowdingScope}
        onChangeScopeMode={setCrowdingScope}
        recommendedCount={(blueprint?.items || []).length}
      />
    </div>
  );
}

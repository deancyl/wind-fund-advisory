import { useMemo, useState } from 'react';
import {
  Play,
  RefreshCw,
  PanelLeftClose,
  PanelLeftOpen,
  BookmarkPlus,
  Download,
  FileJson,
  AlertTriangle,
  ChevronDown,
  ChevronRight,
  Lock,
  Ban,
  ArrowUpDown,
  X,
  Cpu,
} from 'lucide-react';
import { useWorkbench } from '../context/WorkbenchContext';
import type { UniverseMode } from '../api/client';
import { MetricTooltip } from '../components/MetricTooltip';
import { BacktestCharts } from '../components/charts/BacktestCharts';
import { ScenarioBacktestPanel } from '../components/charts/ScenarioBacktestPanel';
import { ExtremeCyclePanel } from '../components/charts/ExtremeCyclePanel';
import { SnapshotCompareView } from '../components/SnapshotCompareView';
import { buildQuantResearchMarkdown, triggerFileDownload } from '../utils/exportReport';

type LabSubTab = 'matrix' | 'backtest' | 'extreme' | 'compare';
type SortKey = 'weight_pct' | 'risk_contribution_pcr_pct' | 'quant_score' | 'bias_20';

const RISK_LEVELS = [
  { id: 'C1', label: 'C1 稳健' },
  { id: 'C2', label: 'C2 偏稳' },
  { id: 'C3', label: 'C3 均衡' },
  { id: 'C4', label: 'C4 进取' },
  { id: 'C5', label: 'C5 积极' },
];

const FUND_COUNTS = [3, 4, 5, 6, 8];

const HORIZON_OPTIONS = [
  { months: 6, label: '6月' },
  { months: 12, label: '1年' },
  { months: 24, label: '2年' },
  { months: 36, label: '3年' },
];

const BACKTEST_PERIODS = [
  { id: '3m', label: '近3月' },
  { id: '6m', label: '近6月' },
  { id: '1y', label: '近1年' },
  { id: '2y', label: '近2年' },
  { id: 'all', label: '全周期' },
];

const UNIVERSE_MODES: Array<{ id: UniverseMode; label: string; hint: string }> = [
  {
    id: 'index_only',
    label: '低费指数核心',
    hint: '低费透明·无风格漂移，适合多数场外投资者拿稳；注：海外被动指数偶有限购。',
  },
  {
    id: 'full_market',
    label: '全市场含主动',
    hint: '含绩优主动/固收+及高限额全球基，弹性更强；注：费率略高且需防风格漂移。',
  },
];

const SOLVE_STAGES = [
  { threshold: 10, label: '① 真净值湖仓' },
  { threshold: 30, label: '② 去冗余入围' },
  { threshold: 52, label: '③ SLSQP/HRP寻优' },
  { threshold: 82, label: '④ 真回测&万次MC' },
];

export function QuantLabPage() {
  const {
    sidebarCollapsed,
    setSidebarCollapsed,
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
    openInspector,
    pushToast,
  } = useWorkbench();

  const [subTab, setSubTab] = useState<LabSubTab>('matrix');
  const [btMode, setBtMode] = useState<'full' | 'scenario'>('full');
  const [showAuditDetail, setShowAuditDetail] = useState(false);
  const [sortKey, setSortKey] = useState<SortKey>('weight_pct');
  const [sortAsc, setSortAsc] = useState(false);

  const liveCapital = Math.max(1000, amount || 50000);

  const sortedItems = useMemo(() => {
    const raw = (blueprint?.items || []).map((f) => ({
      ...f,
      suggested_amount: Math.round((liveCapital * f.weight_pct) / 100),
    }));
    return raw.sort((a, b) => {
      const av = Number(a[sortKey] ?? -999);
      const bv = Number(b[sortKey] ?? -999);
      return sortAsc ? av - bv : bv - av;
    });
  }, [blueprint, liveCapital, sortKey, sortAsc]);

  const handleSort = (key: SortKey) => {
    if (sortKey === key) setSortAsc((v) => !v);
    else {
      setSortKey(key);
      setSortAsc(false);
    }
  };

  const handleExportMd = () => {
    if (!blueprint) return;
    const md = buildQuantResearchMarkdown(blueprint, curves, appliedParams, liveCapital);
    const fname = `agy2_quant_report_${blueprint.risk_level}_${blueprint.model}_${new Date().toISOString().slice(0, 10)}.md`;
    triggerFileDownload(fname, md, 'text/markdown;charset=utf-8;');
    pushToast(`已导出投研报告：${fname}`, 'success');
  };

  const handleExportJson = () => {
    if (!blueprint) return;
    const payload = {
      exported_at: new Date().toISOString(),
      applied_params: appliedParams,
      capital: liveCapital,
      blueprint,
      backtest_metrics: curves?.metrics,
      benchmark_horizons: curves?.benchmark_horizons,
    };
    const fname = `agy2_quant_solution_${blueprint.risk_level}_${blueprint.model}_${new Date().toISOString().slice(0, 10)}.json`;
    triggerFileDownload(fname, JSON.stringify(payload, null, 2), 'application/json;charset=utf-8;');
    pushToast(`已导出结构化 JSON：${fname}`, 'success');
  };

  const solverAudit = blueprint?.solver_audit;
  const funnelAudit = blueprint?.funnel_audit || curves?.funnel_audit;
  const realBtInfo = curves?.real_bt_info || blueprint?.real_bt_info;
  const allocLogic = blueprint?.allocation_logic_summary;
  const recon = curves?.goal_reconciliation;
  const constraintWarnings = blueprint?.constraint_audit?.warnings || [];

  const effModelName =
    blueprint?.all_models?.find((m) => m.id === modelId)?.name || blueprint?.model_meta?.name || modelId;

  return (
    <div className="fade-in">
      {/* 当左侧控制台折叠时，顶部浮现紧凑单行参数摘要控制条（方案二宽屏形态） */}
      {sidebarCollapsed && (
        <div
          data-testid="collapsed-param-bar"
          className="inst-panel rounded-lg px-3.5 py-2.5 mb-4 flex flex-wrap items-center justify-between gap-2.5 text-xs"
        >
          <div className="flex flex-wrap items-center gap-2">
            <button
              type="button"
              onClick={() => setSidebarCollapsed(false)}
              data-testid="btn-expand-sidebar"
              className="h-7 px-2.5 rounded-md bg-slate-100 hover:bg-slate-200 text-slate-800 font-semibold inline-flex items-center gap-1.5 cursor-pointer"
            >
              <PanelLeftOpen className="w-3.5 h-3.5" />
              <span>展开参数台</span>
            </button>
            <span className="text-slate-300">|</span>
            <span className="font-semibold text-slate-900">
              {universeMode === 'full_market' ? '全市场含主动' : '低费指数核心'}
            </span>
            <span className="px-1.5 py-0.5 rounded bg-slate-100 text-slate-800 font-bold">{riskLevel}</span>
            <span className="text-slate-700 font-medium">{effModelName}</span>
            <span className="text-slate-500 tabular-nums">
              {fundCount}只 · {horizonMonths}月+{targetReturnPct}% · ¥{liveCapital.toLocaleString()}
            </span>
            {(excludeCodes.length > 0 || includeCodes.length > 0) && (
              <span className="px-1.5 py-0.5 rounded bg-amber-50 border border-amber-200 text-amber-800 font-medium">
                排除{excludeCodes.length}/锁{includeCodes.length}
              </span>
            )}
          </div>

          <button
            type="button"
            onClick={() => void runAsyncQuantSolve(undefined, !isDirty)}
            disabled={solving}
            data-testid="btn-start-quant-solve-compact"
            className={`h-7 px-3 rounded-md text-xs font-bold inline-flex items-center gap-1.5 cursor-pointer disabled:opacity-50 ${
              isDirty ? 'bg-blue-700 text-white hover:bg-blue-800' : 'bg-[#0A1628] text-white hover:bg-slate-800'
            }`}
          >
            {solving ? <RefreshCw className="w-3 h-3 animate-spin" /> : <Play className="w-3 h-3 fill-current" />}
            <span>{solving ? `求解中 ${solveProgress}%` : isDirty ? '启动全市场量化求解' : '重新求解'}</span>
          </button>
        </div>
      )}

      {/* 主容器：左侧可折叠 268px 参数台 + 右侧单屏子视图工作区 */}
      <div className="flex flex-col xl:flex-row items-start gap-4">
        {!sidebarCollapsed && (
          <aside
            aria-label="量化求解参数台"
            data-testid="lab-param-sidebar"
            className="w-full xl:w-[266px] shrink-0 inst-panel rounded-lg p-3.5 space-y-3 xl:sticky xl:top-[92px]"
          >
            <div className="flex items-center justify-between pb-2 border-b border-slate-100">
              <div className="text-xs font-bold text-slate-900 tracking-tight">量化求解控制台</div>
              <button
                type="button"
                onClick={() => setSidebarCollapsed(true)}
                data-testid="btn-collapse-sidebar"
                title="收起参数台以获得 100% 满宽视野"
                aria-label="收起参数台"
                className="p-1 rounded text-slate-400 hover:text-slate-700 hover:bg-slate-100 cursor-pointer"
              >
                <PanelLeftClose className="w-4 h-4" />
              </button>
            </div>

            {/* 选基范围 */}
            <div className="space-y-1.5">
              <div className="flex items-center justify-between text-[11px] font-semibold text-slate-500">
                <span className="inline-flex items-center">
                  选基池范围
                  <MetricTooltip specKey="universe_mode" />
                </span>
                <span className="text-[10px] font-normal text-slate-400">100% 场外基金</span>
              </div>
              <div className="grid grid-cols-2 gap-1 bg-slate-100 p-0.5 rounded-md border border-slate-200" role="group" aria-label="选基范围模式">
                {UNIVERSE_MODES.map((u) => (
                  <button
                    key={u.id}
                    type="button"
                    onClick={() => setUniverseMode(u.id)}
                    className={`py-1.5 rounded text-[11px] font-semibold transition-colors cursor-pointer ${
                      universeMode === u.id ? 'bg-[#0A1628] text-white' : 'text-slate-600 hover:text-slate-900'
                    }`}
                  >
                    {u.label}
                  </button>
                ))}
              </div>
              <p className="text-[10px] leading-snug text-slate-500">
                {UNIVERSE_MODES.find((u) => u.id === universeMode)?.hint}
              </p>
            </div>

            {/* 风险偏好 C1~C5 */}
            <div className="space-y-1.5">
              <div className="text-[11px] font-semibold text-slate-500">风险偏好与回撤红线</div>
              <div className="grid grid-cols-5 gap-1" role="group" aria-label="风险偏好档位">
                {RISK_LEVELS.map((r) => (
                  <button
                    key={r.id}
                    type="button"
                    title={r.label}
                    onClick={() => setRiskLevel(r.id)}
                    className={`py-1.5 rounded text-[11px] font-bold border transition-colors cursor-pointer ${
                      riskLevel === r.id
                        ? 'bg-[#0A1628] text-white border-[#0A1628]'
                        : 'bg-white text-slate-600 border-slate-200 hover:border-slate-400'
                    }`}
                  >
                    {r.id}
                  </button>
                ))}
              </div>
              {blueprint?.all_risk_levels?.[riskLevel]?.drawdown_hint && (
                <div className="text-[10px] text-slate-400">
                  {blueprint.all_risk_levels[riskLevel].label} · {blueprint.all_risk_levels[riskLevel].drawdown_hint}
                </div>
              )}
            </div>

            {/* 量化优化模型 */}
            <div className="space-y-1.5">
              <div className="text-[11px] font-semibold text-slate-500">量化优化模型</div>
              <div className="space-y-1">
                {(
                  blueprint?.all_models || [
                    { id: 'all_weather', name: '全天候动态均衡模型', tag: 'ERC+胜率', scenario: '均衡跨资产配置' },
                    { id: 'risk_parity', name: '风险平价抗跌模型', tag: 'HRP+CVaR', scenario: '严控最大回撤与尾部风险' },
                    { id: 'dividend_defense', name: '红利防御稳健模型', tag: '核心-卫星', scenario: '高股息底仓复利' },
                    { id: 'barbell_growth', name: '哑铃增强进取模型', tag: 'SLSQP+凯利', scenario: '底仓防守+成长进攻' },
                  ]
                ).map((m) => {
                  const active = m.id === modelId;
                  return (
                    <button
                      key={m.id}
                      type="button"
                      onClick={() => setModelId(m.id)}
                      className={`w-full text-left px-2.5 py-2 rounded-md border transition-colors cursor-pointer ${
                        active
                          ? 'bg-blue-50/70 border-blue-600 text-blue-950'
                          : 'bg-white border-slate-200 text-slate-700 hover:border-slate-300'
                      }`}
                    >
                      <div className="flex items-center justify-between gap-1.5">
                        <span className="text-xs font-bold truncate">{m.name}</span>
                        <span
                          className={`text-[10px] px-1.5 py-0.2 rounded font-medium shrink-0 ${
                            active ? 'bg-blue-700 text-white' : 'bg-slate-100 text-slate-500'
                          }`}
                        >
                          {m.tag}
                        </span>
                      </div>
                    </button>
                  );
                })}
              </div>
            </div>

            {/* 投资目标：周期 × 期望收益 */}
            <div className="space-y-2 pt-1 border-t border-slate-100">
              <div className="text-[11px] font-semibold text-slate-500">投资目标（周期 × 期望收益）</div>
              <div className="grid grid-cols-4 gap-1" role="group" aria-label="目标持有周期">
                {HORIZON_OPTIONS.map((h) => (
                  <button
                    key={h.months}
                    type="button"
                    onClick={() => setGoal(targetReturnPct, h.months)}
                    className={`py-1 rounded text-[11px] font-semibold border cursor-pointer ${
                      horizonMonths === h.months
                        ? 'bg-[#0A1628] text-white border-[#0A1628]'
                        : 'bg-white text-slate-600 border-slate-200 hover:border-slate-400'
                    }`}
                  >
                    {h.label}
                  </button>
                ))}
              </div>

              <div className="grid grid-cols-2 gap-2">
                <label className="space-y-1 text-[11px]">
                  <span className="text-slate-500 font-medium">期望收益 (%)</span>
                  <input
                    type="number"
                    min={2}
                    max={60}
                    step={1}
                    value={targetReturnPct}
                    onChange={(e) => setGoal(Number(e.target.value) || 10, horizonMonths)}
                    aria-label="目标收益率百分比"
                    className="w-full h-8 px-2.5 rounded-md bg-slate-50 border border-slate-300 text-blue-700 font-bold tabular-nums focus:bg-white focus:border-blue-600 focus:outline-none"
                  />
                </label>

                <label className="space-y-1 text-[11px]">
                  <span className="text-slate-500 font-medium">拟投金额 (¥)</span>
                  <input
                    type="number"
                    min={1000}
                    step={5000}
                    value={amount}
                    onChange={(e) => setAmount(Number(e.target.value))}
                    aria-label="拟投金额"
                    className="w-full h-8 px-2.5 rounded-md bg-slate-50 border border-slate-300 text-slate-900 font-bold tabular-nums focus:bg-white focus:border-blue-600 focus:outline-none"
                  />
                </label>
              </div>
            </div>

            {/* 组合只数 */}
            <div className="space-y-1.5">
              <div className="text-[11px] font-semibold text-slate-500">组合持仓只数</div>
              <div className="grid grid-cols-5 gap-1" role="group" aria-label="基金数量">
                {FUND_COUNTS.map((n) => (
                  <button
                    key={n}
                    type="button"
                    onClick={() => setFundCount(n)}
                    className={`py-1 rounded text-[11px] font-semibold border cursor-pointer ${
                      fundCount === n
                        ? 'bg-blue-700 text-white border-blue-700'
                        : 'bg-white text-slate-600 border-slate-200 hover:border-slate-400'
                    }`}
                  >
                    {n}只
                  </button>
                ))}
              </div>
            </div>

            {/* 单基约束管理（排除 / 锁定） */}
            {(excludeCodes.length > 0 || includeCodes.length > 0) && (
              <div className="p-2.5 rounded-md bg-slate-50 border border-slate-200 space-y-2 text-[11px]">
                <div className="flex items-center justify-between">
                  <span className="font-semibold text-slate-700">自定义标的约束</span>
                  <button
                    type="button"
                    onClick={() => clearConstraints(false)}
                    className="text-[10px] text-blue-700 hover:underline cursor-pointer"
                  >
                    全部清空
                  </button>
                </div>
                {includeCodes.length > 0 && (
                  <div className="flex flex-wrap gap-1">
                    {includeCodes.map((c) => (
                      <span
                        key={`in-${c}`}
                        className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded bg-blue-50 border border-blue-200 text-blue-800 font-mono text-[10px]"
                      >
                        <Lock className="w-2.5 h-2.5" />
                        {c}
                        <button
                          type="button"
                          onClick={() => toggleIncludeCode(c, false)}
                          aria-label={`取消锁定 ${c}`}
                          className="hover:text-red-600 cursor-pointer"
                        >
                          <X className="w-2.5 h-2.5" />
                        </button>
                      </span>
                    ))}
                  </div>
                )}
                {excludeCodes.length > 0 && (
                  <div className="flex flex-wrap gap-1">
                    {excludeCodes.map((c) => (
                      <span
                        key={`ex-${c}`}
                        className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded bg-rose-50 border border-rose-200 text-rose-800 font-mono text-[10px]"
                      >
                        <Ban className="w-2.5 h-2.5" />
                        {c}
                        <button
                          type="button"
                          onClick={() => toggleExcludeCode(c, false)}
                          aria-label={`取消排除 ${c}`}
                          className="hover:text-slate-900 cursor-pointer"
                        >
                          <X className="w-2.5 h-2.5" />
                        </button>
                      </span>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* 显式主求解 CTA */}
            <button
              type="button"
              onClick={() => void runAsyncQuantSolve(undefined, !isDirty)}
              disabled={solving}
              data-testid="btn-start-quant-solve"
              className={`w-full h-9 rounded-md text-xs font-bold inline-flex items-center justify-center gap-1.5 transition-all cursor-pointer disabled:opacity-60 ${
                isDirty
                  ? 'bg-blue-700 text-white hover:bg-blue-800 ring-2 ring-blue-600/25'
                  : 'bg-[#0A1628] text-white hover:bg-slate-800'
              }`}
            >
              {solving ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Play className="w-3.5 h-3.5 fill-current" />}
              <span>
                {solving ? `求解中 ${solveProgress}%` : isDirty ? '启动全市场量化求解' : '重新全市场量化求解'}
              </span>
            </button>
          </aside>
        )}

        {/* 右侧主工作区：统一下划线 Sub-Tabs（单屏聚焦，零瀑布流堆叠） */}
        <div className="flex-1 min-w-0 w-full space-y-4">
          {/* 顶部 Sub-Tab 栏 + 工具按钮 */}
          <div className="inst-panel rounded-lg px-4 flex flex-wrap items-center justify-between gap-2 border-b border-slate-200">
            <div className="flex items-center gap-5 overflow-x-auto no-scrollbar" role="tablist" aria-label="量化实验室子视图">
              {[
                { id: 'matrix', label: `组合方案矩阵${blueprint?.count ? ` (${blueprint.count})` : ''}` },
                { id: 'backtest', label: '净值与情景回测' },
                { id: 'extreme', label: '极端周期与止盈' },
                { id: 'compare', label: `A/B 方案对比${snapshots.length ? ` (${snapshots.length})` : ''}` },
              ].map((t) => (
                <button
                  key={t.id}
                  type="button"
                  role="tab"
                  aria-selected={subTab === t.id}
                  data-active={subTab === t.id}
                  onClick={() => setSubTab(t.id as LabSubTab)}
                  className="inst-subtab"
                >
                  {t.label}
                </button>
              ))}
            </div>

            <div className="flex items-center gap-1.5 py-1.5 shrink-0">
              <button
                type="button"
                onClick={() => saveCurrentSnapshot()}
                disabled={!blueprint}
                data-testid="btn-save-snapshot"
                title="保存当前方案至 A/B 对比槽"
                className="h-7 px-2.5 rounded-md text-[11px] font-semibold bg-slate-100 text-slate-700 hover:bg-slate-200 inline-flex items-center gap-1 cursor-pointer disabled:opacity-40"
              >
                <BookmarkPlus className="w-3.5 h-3.5" />
                <span className="hidden sm:inline">存快照</span>
              </button>
              <button
                type="button"
                onClick={handleExportMd}
                disabled={!blueprint}
                title="导出完整 Markdown 量化投研报告"
                className="h-7 px-2.5 rounded-md text-[11px] font-semibold bg-white border border-slate-200 text-slate-700 hover:bg-slate-50 inline-flex items-center gap-1 cursor-pointer disabled:opacity-40"
              >
                <Download className="w-3.5 h-3.5" />
                <span className="hidden sm:inline">报告 MD</span>
              </button>
              <button
                type="button"
                onClick={handleExportJson}
                disabled={!blueprint}
                title="导出结构化 JSON 数据"
                className="h-7 px-2 rounded-md text-[11px] font-semibold bg-white border border-slate-200 text-slate-600 hover:bg-slate-50 inline-flex items-center gap-1 cursor-pointer disabled:opacity-40"
              >
                <FileJson className="w-3.5 h-3.5" />
                <span className="hidden md:inline">JSON</span>
              </button>
            </div>
          </div>

          {/* 实时 4 阶段异步求解进度条（求解中显示） */}
          {solving && (
            <div
              data-testid="quant-solve-progress"
              className="inst-panel rounded-lg p-3.5 border-l-4 border-l-blue-700 space-y-2.5"
            >
              <div className="flex flex-wrap items-center justify-between gap-2 text-xs">
                <div className="flex items-center gap-2 font-semibold text-slate-900">
                  <Cpu className="w-4 h-4 text-blue-700 animate-pulse shrink-0" />
                  <span>{solveStage || '正在本地真实复权净值湖仓运行全市场量化求解...'}</span>
                </div>
                <span className="font-mono font-bold text-blue-700 tabular-nums">
                  {solveProgress}% · {(solveElapsedMs / 1000).toFixed(1)}s
                </span>
              </div>
              <div className="h-1.5 rounded-full bg-slate-100 overflow-hidden">
                <div
                  className="h-full bg-blue-700 transition-all duration-300"
                  style={{ width: `${Math.max(6, Math.min(100, solveProgress))}%` }}
                />
              </div>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-1.5 text-[10px]">
                {SOLVE_STAGES.map((st) => {
                  const done = solveProgress >= st.threshold + 20;
                  const current = solveProgress >= st.threshold && !done;
                  return (
                    <div
                      key={st.label}
                      className={`px-2 py-1 rounded border font-medium ${
                        done
                          ? 'bg-emerald-50 border-emerald-200 text-emerald-800'
                          : current
                          ? 'bg-blue-700 border-blue-700 text-white'
                          : 'bg-slate-50 border-slate-200 text-slate-400'
                      }`}
                    >
                      {st.label}
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* 求解报错提示 */}
          {solveError && (
            <div className="inst-panel rounded-lg px-4 py-2.5 border-l-4 border-l-red-600 text-xs text-red-800 flex items-center justify-between gap-2">
              <span>求解提示：{solveError}</span>
              <button
                type="button"
                onClick={() => void runAsyncQuantSolve(undefined, false)}
                className="px-2.5 py-1 rounded bg-red-600 text-white font-semibold hover:bg-red-700 cursor-pointer"
              >
                重试求解
              </button>
            </div>
          )}

          {/* 永不隐藏的硬告警 1：参数脏状态 Stale 条 */}
          {staleHint && !solving && (
            <div
              data-testid="backtest-stale-banner"
              className="inst-panel rounded-lg px-4 py-2.5 border-l-4 border-l-amber-500 bg-amber-50/40 text-xs text-amber-950 flex flex-wrap items-center justify-between gap-2"
            >
              <span>{staleHint}</span>
              <button
                type="button"
                onClick={() => void runAsyncQuantSolve(undefined, false)}
                className="px-2.5 py-1 rounded bg-blue-700 text-white font-semibold hover:bg-blue-800 shrink-0 cursor-pointer"
              >
                立即重算对齐
              </button>
            </div>
          )}

          {/* 永不隐藏的硬告警 2：目标与档位冲突提示 */}
          {blueprint?.goal_analysis?.has_collision && subTab === 'matrix' && (
            <div className="inst-panel rounded-lg px-4 py-2.5 border-l-4 border-l-amber-500 text-xs text-slate-800 flex flex-wrap items-center justify-between gap-2">
              <span className="flex items-start gap-2 leading-relaxed">
                <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
                <span>{blueprint.goal_analysis.collision_message}</span>
              </span>
              <button
                type="button"
                onClick={() => {
                  const nextTier = blueprint.goal_analysis!.suggested_tier;
                  const nextModel = blueprint.goal_analysis!.recommended_model;
                  setRiskLevel(nextTier);
                  setModelId(nextModel);
                  void runAsyncQuantSolve({ riskLevel: nextTier, modelId: nextModel }, false);
                }}
                className="px-2.5 py-1 rounded bg-[#0A1628] text-white text-[11px] font-semibold hover:bg-slate-800 shrink-0 cursor-pointer"
              >
                对齐至 {blueprint.goal_analysis.suggested_tier} 并重算
              </button>
            </div>
          )}

          {/* 永不隐藏的硬告警 3：自定义约束自动调解提示 */}
          {constraintWarnings.length > 0 && subTab === 'matrix' && (
            <div className="inst-panel rounded-lg px-4 py-2 border-l-4 border-l-blue-600 text-xs text-slate-700 space-y-1">
              {constraintWarnings.map((w, i) => (
                <div key={i}>约束提示：{w}</div>
              ))}
            </div>
          )}

          {/* ==================== 子视图 1：组合方案矩阵 ==================== */}
          {subTab === 'matrix' && (
            <div className="space-y-4 fade-in">
              {/* 4 列极简无彩虹底纯排版 KPI 带 */}
              <section className="inst-panel rounded-lg grid grid-cols-2 lg:grid-cols-4 divide-y lg:divide-y-0 lg:divide-x divide-slate-200 tabular-nums">
                <div className="p-4">
                  <div className="flex items-center justify-between text-[11px] text-slate-500">
                    <span>{curves?.period_label || '近1年'}实盘校准收益</span>
                    <select
                      value={period}
                      onChange={(e) => setPeriod(e.target.value)}
                      aria-label="回测统计周期"
                      className="text-[10px] font-semibold text-slate-600 bg-slate-100 border border-slate-200 rounded px-1.5 py-0.5 cursor-pointer"
                    >
                      {BACKTEST_PERIODS.map((p) => (
                        <option key={p.id} value={p.id}>
                          {p.label}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div
                    className={`text-2xl font-extrabold mt-1 ${
                      (curves?.metrics?.period_return_pct ?? 0) >= 0 ? 'text-red-600' : 'text-emerald-700'
                    }`}
                  >
                    {curves?.metrics
                      ? `${curves.metrics.period_return_pct >= 0 ? '+' : ''}${curves.metrics.period_return_pct.toFixed(2)}%`
                      : '--'}
                  </div>
                  <div className="text-[11px] text-slate-500 mt-1">
                    {curves?.metrics
                      ? `沪深300 ${curves.metrics.hs300_return_pct >= 0 ? '+' : ''}${curves.metrics.hs300_return_pct.toFixed(2)}% · 超额 ${
                          curves.metrics.excess_return_pct >= 0 ? '+' : ''
                        }${curves.metrics.excess_return_pct.toFixed(2)}%`
                      : '等待真实复权净值回测'}
                  </div>
                </div>

                <div className="p-4">
                  <div className="text-[11px] text-slate-500">
                    区间最大回撤
                    <MetricTooltip specKey="cvar99" />
                  </div>
                  <div className="text-2xl font-extrabold mt-1 text-emerald-700">
                    {curves?.metrics ? `-${Math.abs(curves.metrics.max_drawdown_pct).toFixed(2)}%` : '--'}
                  </div>
                  <div className="text-[11px] text-slate-500 mt-1">
                    {curves?.metrics
                      ? `沪深300 -${Math.abs(curves.metrics.hs300_mdd_pct).toFixed(2)}% · 波动 ${
                          solverAudit?.portfolio_vol_annual_pct?.toFixed(1) ?? '--'
                        }%`
                      : '--'}
                  </div>
                </div>

                <div className="p-4">
                  <div className="text-[11px] text-slate-500">
                    滚动目标触达率
                    <MetricTooltip specKey="rolling_hit" />
                  </div>
                  <div className="text-2xl font-extrabold mt-1 text-slate-900">
                    {blueprint?.goal_analysis ? `${blueprint.goal_analysis.historical_hit_rate_pct.toFixed(1)}%` : '--'}
                  </div>
                  <div className="text-[11px] text-slate-500 mt-1">
                    同温层 {(blueprint?.goal_analysis?.conditional_win_rate_pct ?? 0).toFixed(1)}%
                    <MetricTooltip specKey="cond_winrate" />
                    <span className="mx-1 text-slate-300">·</span>
                    MC {(blueprint?.goal_analysis?.monte_carlo_prob_pct ?? 0).toFixed(1)}%
                    <MetricTooltip specKey="mc_prob" align="right" />
                  </div>
                </div>

                <div className="p-4">
                  <div className="text-[11px] text-slate-500">
                    风险调整夏普 / OOS 胜率
                    <MetricTooltip specKey="sharpe" align="right" />
                  </div>
                  <div className="text-2xl font-extrabold mt-1 text-slate-900">
                    {curves?.metrics ? curves.metrics.sharpe_ratio.toFixed(2) : '--'}
                    <span className="text-sm font-semibold text-slate-400 mx-1.5">/</span>
                    <span className="text-lg font-bold text-blue-700">
                      {solverAudit ? `${solverAudit.oos_conditional_win_rate_pct.toFixed(1)}%` : '--'}
                    </span>
                  </div>
                  <div className="text-[11px] text-slate-500 mt-1">
                    OOS 样本外核验
                    <MetricTooltip specKey="oos_winrate" align="right" />
                    <span className="mx-1 text-slate-300">·</span>
                    最大 PCR {solverAudit?.max_risk_pcr_pct?.toFixed(1) ?? '--'}%
                  </div>
                </div>
              </section>

              {/* 高密度专业组合配置矩阵表（替代臃肿 6 卡片） */}
              <section className="inst-panel rounded-lg overflow-hidden" data-testid="portfolio-matrix-table">
                <div className="px-4 py-2.5 border-b border-slate-200 bg-slate-50/70 flex flex-wrap items-center justify-between gap-2 text-xs">
                  <div className="flex flex-wrap items-center gap-2">
                    <h2 className="font-bold text-slate-900">
                      组合配置与风险预算矩阵（{sortedItems.length} 只
                      {sortedItems.length > 0
                        ? ` · 权重 ${sortedItems.reduce((acc, it) => acc + Number(it.weight_pct || 0), 0).toFixed(1)}%`
                        : ' · 暂无可用方案'}
                      ）
                    </h2>
                    {realBtInfo?.is_real_nav && (
                      <span
                        data-testid="real-nav-backtest-badge"
                        className="px-2 py-0.5 rounded bg-emerald-50 text-emerald-700 border border-emerald-200 text-[10px] font-semibold"
                      >
                        100% 基金真实复权净值 · 存续自 {realBtInfo.common_start_date}
                      </span>
                    )}
                  </div>
                  <span className="text-[11px] text-slate-500 tabular-nums">
                    拟投本金 <strong className="text-slate-900">¥{liveCapital.toLocaleString()}</strong> · 点击任意行打开右侧检查器
                  </span>
                </div>

                {solving && !blueprint ? (
                  <div className="py-12 text-center text-xs text-slate-400">
                    正在本地真净值湖仓执行全市场量化寻优...
                  </div>
                ) : (
                  <div className="table-wrapper">
                    <table className="text-left text-xs tabular-nums">
                      <thead>
                        <tr className="border-b border-slate-200 bg-white text-slate-500">
                          <th scope="col" className="py-2.5 px-4 font-semibold whitespace-nowrap">基金标的</th>
                          <th scope="col" className="py-2.5 px-3 font-semibold whitespace-nowrap">风格桶 / 属性</th>
                          <th scope="col" className="py-2.5 px-3 font-semibold text-right whitespace-nowrap">
                            <button type="button" onClick={() => handleSort('weight_pct')} className="inline-flex items-center gap-1 hover:text-slate-900 cursor-pointer">
                              <span>目标权重</span>
                              <ArrowUpDown className="w-3 h-3" />
                            </button>
                          </th>
                          <th scope="col" className="py-2.5 px-3 font-semibold text-right whitespace-nowrap">建议金额</th>
                          <th scope="col" className="py-2.5 px-3 font-semibold text-right whitespace-nowrap">
                            <button type="button" onClick={() => handleSort('risk_contribution_pcr_pct')} className="inline-flex items-center gap-1 hover:text-slate-900 cursor-pointer">
                              <span>风险贡献 PCR</span>
                              <ArrowUpDown className="w-3 h-3" />
                            </button>
                            <MetricTooltip specKey="pcr" align="right" />
                          </th>
                          <th scope="col" className="py-2.5 px-3 font-semibold text-right whitespace-nowrap">
                            <button type="button" onClick={() => handleSort('quant_score')} className="inline-flex items-center gap-1 hover:text-slate-900 cursor-pointer">
                              <span>量化分</span>
                              <ArrowUpDown className="w-3 h-3" />
                            </button>
                          </th>
                          <th scope="col" className="py-2.5 px-3 font-semibold text-right whitespace-nowrap">
                            <button type="button" onClick={() => handleSort('bias_20')} className="inline-flex items-center gap-1 hover:text-slate-900 cursor-pointer">
                              <span>MA20乖离 / 温度</span>
                              <ArrowUpDown className="w-3 h-3" />
                            </button>
                            <MetricTooltip specKey="bias20" align="right" />
                          </th>
                          <th scope="col" className="py-2.5 px-3 font-semibold whitespace-nowrap">限购与费率</th>
                          <th scope="col" className="py-2.5 px-4 font-semibold text-right whitespace-nowrap">约束操作</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-100">
                        {sortedItems.map((f) => {
                          const pcr = f.risk_contribution_pcr_pct ?? f.weight_pct;
                          const isLocked = includeCodes.includes(f.fund_code);
                          const b20 = f.bias_20;
                          const hot = b20 !== null && b20 !== undefined && b20 > 3.5;
                          const cool = b20 !== null && b20 !== undefined && b20 < -1.5;

                          return (
                            <tr
                              key={f.fund_code}
                              onClick={() => openInspector(f.fund_code)}
                              className={`hover:bg-blue-50/40 transition-colors cursor-pointer ${solving ? 'opacity-60' : ''}`}
                            >
                              <th scope="row" className="py-2.5 px-4 font-normal">
                                <div className="flex items-center gap-1.5">
                                  <span className="font-semibold text-slate-900 hover:text-blue-700 whitespace-nowrap">
                                    {f.fund_name}
                                  </span>
                                  {isLocked && (
                                    <span className="px-1 py-0.2 rounded bg-blue-50 text-blue-700 border border-blue-200 text-[10px] font-semibold">
                                      已锁
                                    </span>
                                  )}
                                </div>
                                <div className="text-[11px] font-mono text-slate-400">
                                  {f.fund_code}
                                  {f.real_scale_yi ? ` · ${Number(f.real_scale_yi).toFixed(1)}亿` : ''}
                                </div>
                              </th>
                              <td className="py-2.5 px-3 whitespace-nowrap">
                                <div className="text-slate-700 font-medium">{f.bucket_label || f.role}</div>
                                <div className="text-[10px] text-slate-400">
                                  {f.is_active_fund ? '主动精选' : '低费指数/工具'}
                                </div>
                              </td>
                              <td className="py-2.5 px-3 text-right whitespace-nowrap">
                                <div className="font-bold text-slate-900">{f.weight_pct.toFixed(1)}%</div>
                                <div className="w-16 h-1 rounded-full bg-slate-100 ml-auto mt-1 overflow-hidden">
                                  <div className="h-full bg-blue-700" style={{ width: `${Math.min(100, f.weight_pct * 2.2)}%` }} />
                                </div>
                              </td>
                              <td className="py-2.5 px-3 text-right font-semibold text-slate-800 whitespace-nowrap">
                                ¥{Math.round(f.suggested_amount).toLocaleString()}
                              </td>
                              <td className="py-2.5 px-3 text-right whitespace-nowrap">
                                <span
                                  className={`font-semibold ${
                                    pcr < 0 ? 'text-emerald-700' : pcr >= 32 ? 'text-amber-700' : 'text-slate-700'
                                  }`}
                                >
                                  {pcr.toFixed(1)}%
                                </span>
                                <div
                                  className={`text-[10px] ${pcr < 0 ? 'text-emerald-700 font-medium' : 'text-slate-400'}`}
                                  title={
                                    pcr < 0
                                      ? '与组合权益主风险呈负相关，起到天然波动对冲作用'
                                      : undefined
                                  }
                                >
                                  {pcr < 0
                                    ? '负相关对冲'
                                    : f.factor_tilt_delta_pct !== undefined && Math.abs(f.factor_tilt_delta_pct) >= 0.1
                                    ? `因子 ${f.factor_tilt_delta_pct >= 0 ? '+' : ''}${f.factor_tilt_delta_pct.toFixed(1)}%`
                                    : '均衡'}
                                </div>
                              </td>
                              <td className="py-2.5 px-3 text-right font-bold text-slate-900 whitespace-nowrap">
                                {f.quant_score ?? '--'}
                              </td>
                              <td className="py-2.5 px-3 text-right whitespace-nowrap">
                                {b20 !== null && b20 !== undefined ? (
                                  <div>
                                    <span
                                      className={`font-mono font-semibold ${
                                        hot ? 'text-amber-700' : cool ? 'text-emerald-700' : 'text-slate-700'
                                      }`}
                                    >
                                      {b20 >= 0 ? '+' : ''}
                                      {b20.toFixed(1)}%
                                    </span>
                                    <div className="text-[10px] text-slate-400">
                                      {f.quadrant_tag || (hot ? '短线偏热' : cool ? '冷清低吸' : '温和区间')}
                                    </div>
                                  </div>
                                ) : (
                                  <span className="text-slate-300">--</span>
                                )}
                              </td>
                              <td className="py-2.5 px-3 whitespace-nowrap">
                                <div>
                                  {f.quota_note ? (
                                    <span
                                      title={f.quota_note}
                                      className="px-1.5 py-0.5 rounded bg-amber-50 border border-amber-200 text-amber-800 text-[10px] font-semibold"
                                    >
                                      限购 ¥{Math.round(f.daily_limit).toLocaleString()}
                                    </span>
                                  ) : (
                                    <span className="text-[11px] text-slate-500">
                                      不限购 · 费率 {(f.factor_profile?.total_fee_pct ?? 0.6).toFixed(2)}%
                                    </span>
                                  )}
                                </div>
                                {horizonMonths <= 12 && f.share_class_tip && (
                                  <div
                                    title={f.share_class_tip}
                                    className="text-[10px] text-blue-700 font-medium mt-0.5"
                                  >
                                    {f.c_share_code && f.c_share_code !== f.fund_code
                                      ? `≤1年省费：可看 C 类 ${f.c_share_code}`
                                      : '≤1年建议关注同基 C 类'}
                                  </div>
                                )}
                              </td>
                              <td
                                className="py-2.5 px-4 text-right whitespace-nowrap"
                                onClick={(e) => e.stopPropagation()}
                              >
                                <div className="inline-flex items-center gap-1">
                                  <button
                                    type="button"
                                    onClick={() => toggleIncludeCode(f.fund_code, true)}
                                    title={isLocked ? '解除锁定并重算' : '锁定必选并重算'}
                                    className={`px-2 py-1 rounded text-[11px] font-medium border inline-flex items-center gap-1 cursor-pointer ${
                                      isLocked
                                        ? 'bg-blue-700 text-white border-blue-700'
                                        : 'bg-white text-slate-600 border-slate-200 hover:border-blue-500 hover:text-blue-700'
                                    }`}
                                  >
                                    <Lock className="w-3 h-3" />
                                    <span>{isLocked ? '解锁' : '锁定'}</span>
                                  </button>
                                  <button
                                    type="button"
                                    data-testid={`btn-exclude-${f.fund_code}`}
                                    onClick={() => toggleExcludeCode(f.fund_code, true)}
                                    title="排除此基金并立即全市场重算"
                                    className="px-2 py-1 rounded text-[11px] font-medium bg-white border border-slate-200 text-slate-600 hover:border-red-500 hover:text-red-600 inline-flex items-center gap-1 cursor-pointer"
                                  >
                                    <Ban className="w-3 h-3" />
                                    <span>排除</span>
                                  </button>
                                </div>
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                )}
              </section>

              {/* 底部 1 行极简可展开量化审计条（替代原来黑/黄/蓝三条叠罗汉横幅） */}
              {blueprint && (
                <section className="inst-panel rounded-lg overflow-hidden" data-testid="full-market-funnel-bar">
                  <button
                    type="button"
                    onClick={() => setShowAuditDetail((v) => !v)}
                    className="w-full px-4 py-2.5 flex flex-wrap items-center justify-between gap-2 text-xs text-slate-700 hover:bg-slate-50 transition-colors cursor-pointer tabular-nums"
                  >
                    <div className="flex flex-wrap items-center gap-2">
                      {showAuditDetail ? <ChevronDown className="w-3.5 h-3.5 text-slate-400" /> : <ChevronRight className="w-3.5 h-3.5 text-slate-400" />}
                      <span className="font-bold text-slate-900">选基漏斗与求解审计</span>
                      {funnelAudit && (
                        <span className="text-slate-500">
                          {funnelAudit.total_market_funds.toLocaleString()} 全市场 → {funnelAudit.compliant_screened_funds.toLocaleString()} 合规 →{' '}
                          <strong className="text-slate-800">{funnelAudit.elite_lakehouse_funds}</strong> 真净值湖仓 →{' '}
                          {funnelAudit.shortlisted_candidates} 去冗余入围 → <strong className="text-blue-700">{funnelAudit.final_selected_funds}</strong> 终选
                        </span>
                      )}
                    </div>
                    <span className="text-[11px] font-mono text-slate-400">
                      {solverAudit?.from_cache ? `缓存 (${solverAudit.compute_ms}ms)` : `实算 ${solverAudit?.compute_ms ?? '--'}ms`} ·{' '}
                      {showAuditDetail ? '收起详情' : '展开配权推导 & 目标偏差归因'}
                    </span>
                  </button>

                  {showAuditDetail && (
                    <div className="px-4 py-3.5 border-t border-slate-200 bg-slate-50/50 space-y-4 text-xs">
                      {allocLogic && (
                        <div className="space-y-2">
                          <div className="font-bold text-slate-900">1. 求解算法与资金配权推导</div>
                          <p className="text-slate-600 leading-relaxed">{allocLogic.headline}</p>
                          <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                            {allocLogic.steps.map((s, idx) => (
                              <div key={idx} className="p-2.5 rounded-md bg-white border border-slate-200 text-[11px] text-slate-600 leading-relaxed">
                                {s}
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      {recon && (
                        <div className="space-y-2 pt-2 border-t border-slate-200">
                          <div className="flex flex-wrap items-center justify-between gap-2">
                            <span className="font-bold text-slate-900">
                              2. 目标收益 vs 历史回测对照（{recon.badge}）
                            </span>
                            <span className="font-mono text-[11px] text-slate-600 tabular-nums">
                              目标口径 {recon.goal_comparable_pct >= 0 ? '+' : ''}
                              {recon.goal_comparable_pct.toFixed(2)}% vs 实测 {recon.backtest_comparable_pct >= 0 ? '+' : ''}
                              {recon.backtest_comparable_pct.toFixed(2)}%（差值 {recon.gap_pct >= 0 ? '+' : ''}
                              {recon.gap_pct.toFixed(2)}%）
                            </span>
                          </div>
                          <p className="text-slate-700 leading-relaxed">{recon.headline}</p>
                          <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
                            {recon.reasons.map((r, i) => (
                              <div key={i} className="p-2.5 rounded-md bg-white border border-slate-200 space-y-1">
                                <div className="text-[11px] font-bold text-slate-900">
                                  {i + 1}. {r.title}
                                </div>
                                <p className="text-[11px] text-slate-600 leading-relaxed">{r.detail}</p>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                      {(blueprint?.walk_forward_audit?.splits?.length || blueprint?.survivorship_bias_disclaimer || solverAudit?.survivorship_bias_disclaimer) && (
                        <div className="space-y-1.5 pt-2 border-t border-slate-200 text-[11px] text-slate-600">
                          {blueprint?.walk_forward_audit?.splits && blueprint.walk_forward_audit.splits.length > 0 && (
                            <div className="flex flex-wrap items-center gap-3 tabular-nums">
                              <span className="font-bold text-slate-800">3. 严格 Walk-Forward 盲测摘要：</span>
                              <span>
                                正收益窗口占比 <strong className="text-slate-900">{blueprint.walk_forward_audit.wf_oos_positive_rate_pct.toFixed(0)}%</strong>
                              </span>
                              <span>
                                盲测均收益 <strong className="text-slate-900">{blueprint.walk_forward_audit.wf_avg_return_pct >= 0 ? '+' : ''}{blueprint.walk_forward_audit.wf_avg_return_pct.toFixed(2)}%</strong>
                              </span>
                              <span>
                                盲测最差回撤 <strong className="text-emerald-700">{blueprint.walk_forward_audit.wf_worst_mdd_pct.toFixed(2)}%</strong>
                              </span>
                            </div>
                          )}
                          {(blueprint?.survivorship_bias_disclaimer || solverAudit?.survivorship_bias_disclaimer) && (
                            <p className="text-[10px] text-slate-500 leading-relaxed">
                              {blueprint?.survivorship_bias_disclaimer || solverAudit?.survivorship_bias_disclaimer}
                            </p>
                          )}
                        </div>
                      )}
                    </div>
                  )}
                </section>
              )}
            </div>
          )}

          {/* ==================== 子视图 2：净值与情景回测 ==================== */}
          {subTab === 'backtest' && (
            <div className="space-y-4 fade-in">
              <div className="inst-panel rounded-lg px-4 py-2.5 flex flex-wrap items-center justify-between gap-2">
                <div className="inline-flex items-center gap-1 bg-slate-100 p-0.5 rounded-md border border-slate-200">
                  <button
                    type="button"
                    onClick={() => setBtMode('full')}
                    className={`px-3 py-1 rounded text-xs font-semibold cursor-pointer ${
                      btMode === 'full' ? 'bg-white text-slate-900 shadow-2xs' : 'text-slate-600 hover:text-slate-900'
                    }`}
                  >
                    真实净值与风险贡献
                  </button>
                  <button
                    type="button"
                    onClick={() => setBtMode('scenario')}
                    className={`px-3 py-1 rounded text-xs font-semibold cursor-pointer ${
                      btMode === 'scenario' ? 'bg-white text-slate-900 shadow-2xs' : 'text-slate-600 hover:text-slate-900'
                    }`}
                  >
                    历史情景压力回测
                  </button>
                </div>

                {btMode === 'full' && (
                  <div className="inline-flex items-center gap-1 bg-slate-100 p-0.5 rounded-md border border-slate-200" role="group" aria-label="回测区间">
                    {BACKTEST_PERIODS.map((p) => (
                      <button
                        key={p.id}
                        type="button"
                        onClick={() => setPeriod(p.id)}
                        className={`px-2.5 py-1 rounded text-xs font-semibold cursor-pointer ${
                          period === p.id ? 'bg-[#0A1628] text-white' : 'text-slate-600 hover:text-slate-900'
                        }`}
                      >
                        {p.label}
                      </button>
                    ))}
                  </div>
                )}
              </div>

              {btMode === 'full' ? (
                <BacktestCharts data={curves} loading={curvesLoading || solving} staleHint="" />
              ) : (
                <ScenarioBacktestPanel
                  tier={appliedParams?.riskLevel ?? riskLevel}
                  modelId={appliedParams?.modelId ?? modelId}
                  fundCount={appliedParams?.fundCount ?? fundCount}
                  targetReturnPct={appliedParams?.targetReturnPct ?? targetReturnPct}
                  horizonMonths={appliedParams?.horizonMonths ?? horizonMonths}
                  universeMode={appliedParams?.universeMode ?? universeMode}
                  excludeCodes={appliedParams?.excludeCodes ?? excludeCodes}
                  includeCodes={appliedParams?.includeCodes ?? includeCodes}
                  staleHint=""
                />
              )}
            </div>
          )}

          {/* ==================== 子视图 3：极端周期与三阶止盈 ==================== */}
          {subTab === 'extreme' && (
            <ExtremeCyclePanel
              data={curves?.extreme_cycle_analysis}
              loading={curvesLoading || solving}
              targetReturnPct={appliedParams?.targetReturnPct ?? targetReturnPct}
              horizonMonths={appliedParams?.horizonMonths ?? horizonMonths}
            />
          )}

          {/* ==================== 子视图 4：A/B 方案对比 ==================== */}
          {subTab === 'compare' && <SnapshotCompareView />}
        </div>
      </div>
    </div>
  );
}

import { useEffect, useId, useMemo, useState } from 'react';
import {
  Trash2,
  Plus,
  ArrowRight,
  Search,
  AlertTriangle,
  Download,
  Pencil,
  Check,
  X,
  Scale,
  ShieldAlert,
  Layers,
  ArrowUpDown,
  ReceiptText,
  FileCheck2,
} from 'lucide-react';
import {
  api,
  type CashflowSummaryResponse,
  type ExposureResponse,
  type HoldingRow,
  type RiskCheckResponse,
  type TakeProfitSummary,
} from '../api/client';
import { useWorkbench } from '../context/WorkbenchContext';
import { ExposureCharts } from '../components/charts/ExposureCharts';
import { MetricTooltip } from '../components/MetricTooltip';
import { CashflowModal } from '../components/CashflowModal';

type HoldingSubTab = 'list' | 'exposure' | 'stress';
type SortField = 'market_value' | 'day_chg' | 'floating_pnl_pct' | 'holding_days';

export function HoldingsPage() {
  const {
    overview,
    activeLedgerId,
    currentLedger,
    refreshTick,
    openDataCenter,
    setActiveTab,
    notifyDataMutated,
    openInspector,
    openConfirm,
    pushToast,
  } = useWorkbench();

  const isDemoLedger = Boolean(currentLedger?.is_demo);
  const ledgerName = currentLedger?.name || activeLedgerId;
  const tableCaptionId = useId();

  const [subTab, setSubTab] = useState<HoldingSubTab>('list');
  const [holdings, setHoldings] = useState<HoldingRow[]>([]);
  const [tpSummary, setTpSummary] = useState<TakeProfitSummary | null>(null);
  const [cashflowSummary, setCashflowSummary] = useState<CashflowSummaryResponse | null>(null);
  const [cashflowModalOpen, setCashflowModalOpen] = useState(false);
  const [loading, setLoading] = useState(true);
  const [exposure, setExposure] = useState<ExposureResponse | null>(null);
  const [expLoading, setExpLoading] = useState(true);
  const [riskCheck, setRiskCheck] = useState<RiskCheckResponse | null>(null);
  const [overlap, setOverlap] = useState<Record<string, unknown>>({});
  const [stress, setStress] = useState<Record<string, unknown>>({});
  const [shadowComp, setShadowComp] = useState<Record<string, unknown>>({});
  const [forwardAudit, setForwardAudit] = useState<Record<string, unknown>>({});
  const [recentAuditLogs, setRecentAuditLogs] = useState<Array<Record<string, unknown>>>([]);
  const [freezing, setFreezing] = useState(false);

  const [tableView, setTableView] = useState<'holdings' | 'reconcile'>('holdings');
  const [query, setQuery] = useState('');
  const [tierFilter, setTierFilter] = useState<'all' | 'core' | 'tail'>('all');
  const [sortField, setSortField] = useState<SortField>('market_value');
  const [sortAsc, setSortAsc] = useState(false);

  // 行内编辑状态
  const [editingCode, setEditingCode] = useState<string | null>(null);
  const [editShares, setEditShares] = useState('');
  const [editCost, setEditCost] = useState('');
  const [savingEdit, setSavingEdit] = useState(false);

  useEffect(() => {
    if (!activeLedgerId) return;
    let alive = true;
    setLoading(true);
    setExpLoading(true);
    api
      .getHoldings(activeLedgerId)
      .then((res) => {
        if (alive) {
          setHoldings(res.items || []);
          setTpSummary(res.take_profit_summary || null);
        }
      })
      .catch(() => {})
      .finally(() => {
        if (alive) setLoading(false);
      });
    api
      .getLedgerCashflows(activeLedgerId)
      .then((res) => {
        if (alive) setCashflowSummary(res);
      })
      .catch(() => {});
    api
      .getDiagnoseExposure(activeLedgerId)
      .then((res) => {
        if (alive) setExposure(res);
      })
      .catch(() => {})
      .finally(() => {
        if (alive) setExpLoading(false);
      });
    api
      .getDiagnoseRiskCheck(activeLedgerId)
      .then((res) => {
        if (alive) setRiskCheck(res);
      })
      .catch(() => {});
    api
      .getDiagnoseOverlap(activeLedgerId)
      .then((res) => {
        if (alive) setOverlap(res || {});
      })
      .catch(() => {});
    api
      .getDiagnoseStress(activeLedgerId)
      .then((res) => {
        if (alive) setStress(res || {});
      })
      .catch(() => {});
    api
      .getAuditTrackers(activeLedgerId)
      .then((res) => {
        if (alive) {
          setShadowComp((res?.shadow_tracker || {}) as Record<string, unknown>);
          setForwardAudit((res?.forward_audit || {}) as Record<string, unknown>);
          setRecentAuditLogs(Array.isArray(res?.recent_logs) ? res.recent_logs : []);
        }
      })
      .catch(() => {});
    return () => {
      alive = false;
    };
  }, [activeLedgerId, refreshTick]);

  const tailCount = useMemo(() => holdings.filter((h) => Number(h.market_value ?? 0) < 200).length, [holdings]);

  const getDayChg = (h: HoldingRow) =>
    Number(
      h.is_official_nav && h.official_chg_pct !== null && h.official_chg_pct !== undefined
        ? h.official_chg_pct
        : (h.est_chg_pct ?? 0)
    );

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    const list = holdings.filter((h) => {
      const mv = Number(h.market_value ?? 0);
      if (tierFilter === 'core' && mv < 500) return false;
      if (tierFilter === 'tail' && mv >= 200) return false;
      if (q && !h.fund_code.toLowerCase().includes(q) && !h.fund_name.toLowerCase().includes(q)) return false;
      return true;
    });
    return [...list].sort((a, b) => {
      let av = 0;
      let bv = 0;
      if (sortField === 'market_value') {
        av = Number(a.market_value ?? 0);
        bv = Number(b.market_value ?? 0);
      } else if (sortField === 'day_chg') {
        av = getDayChg(a);
        bv = getDayChg(b);
      } else if (sortField === 'floating_pnl_pct') {
        av = Number(a.floating_pnl_pct ?? 0);
        bv = Number(b.floating_pnl_pct ?? 0);
      } else {
        av = Number(a.holding_days ?? 0);
        bv = Number(b.holding_days ?? 0);
      }
      return sortAsc ? av - bv : bv - av;
    });
  }, [holdings, query, tierFilter, sortField, sortAsc]);

  const toggleSort = (f: SortField) => {
    if (sortField === f) setSortAsc((v) => !v);
    else {
      setSortField(f);
      setSortAsc(false);
    }
  };

  const handleEditCash = () => {
    const cur = overview?.available_cash ?? 0;
    openConfirm({
      title: '更新账本可用现金',
      description: `当前账本【${ledgerName}】每次变更都会自动生成不可变冷备快照，随时可在数据中心还原。`,
      confirmLabel: '保存现金金额',
      input: {
        label: '可用现金金额 (¥)',
        type: 'number',
        min: 0,
        step: 100,
        defaultValue: String(cur),
        placeholder: '例如 10000',
      },
      onConfirm: async (rawVal) => {
        const val = Number(rawVal);
        if (Number.isNaN(val) || val < 0) throw new Error('请输入大于等于 0 的有效金额');
        await api.updateCash(val, activeLedgerId);
        await notifyDataMutated(`可用现金已更新为 ¥${val.toLocaleString()}（已自动冷备）`);
      },
    });
  };

  const handleStartEdit = (h: HoldingRow) => {
    setEditingCode(h.fund_code);
    setEditShares(String(h.shares ?? 0));
    setEditCost(String(h.cost_price ?? 1));
  };

  const handleSaveEdit = async (h: HoldingRow) => {
    const sh = Number(editShares);
    const cp = Number(editCost);
    if (Number.isNaN(sh) || sh < 0 || Number.isNaN(cp) || cp <= 0) {
      pushToast('请输入有效的份额与持仓成本净值', 'warning');
      return;
    }
    setSavingEdit(true);
    try {
      await api.reconcileManual(
        [{ fund_code: h.fund_code, fund_name: h.fund_name, shares: sh, cost_price: cp, current_nav: h.current_nav }],
        activeLedgerId
      );
      setEditingCode(null);
      await notifyDataMutated(`已更新 ${h.fund_name} (${h.fund_code}) 份额与成本（已自动冷备）`);
    } catch (e) {
      pushToast(e instanceof Error ? e.message : '保存失败', 'error');
    } finally {
      setSavingEdit(false);
    }
  };

  const handleDelete = (h: HoldingRow) => {
    openConfirm({
      title: `删除持仓：${h.fund_name}`,
      description: `确认从当前账本【${ledgerName}】删除 ${h.fund_name} (${h.fund_code})？\n系统会在删除前自动生成冷备快照，随时可在「数据与账本」还原。`,
      confirmLabel: '确认删除',
      tone: 'danger',
      onConfirm: async () => {
        await api.deleteHolding(h.fund_code, activeLedgerId);
        await notifyDataMutated(`已删除 ${h.fund_name} (${h.fund_code})`);
      },
    });
  };

  const handleExportCsv = () => {
    const header = ['基金代码', '基金名称', '资产大类', '持有份额', '成本净值', '最新净值', '当前市值', '今日涨跌(%)', '累计盈亏(%)', '持有天数', '赎回费状态'];
    const lines = [header.join(',')];
    for (const h of holdings) {
      lines.push(
        [
          `"${h.fund_code}"`,
          `"${(h.fund_name || '').replace(/"/g, '""')}"`,
          `"${h.asset_class || ''}"`,
          Number(h.shares ?? 0).toFixed(4),
          Number(h.cost_price ?? 0).toFixed(4),
          Number(h.current_nav ?? 0).toFixed(4),
          Number(h.market_value ?? 0).toFixed(2),
          getDayChg(h).toFixed(2),
          Number(h.floating_pnl_pct ?? 0).toFixed(2),
          h.holding_days ?? 0,
          `"${h.redemption_fee_status?.label || ''}"`,
        ].join(',')
      );
    }
    const blob = new Blob(['\uFEFF' + lines.join('\n')], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `agy2_holdings_${activeLedgerId}_${new Date().toISOString().slice(0, 10)}.csv`;
    a.click();
    URL.revokeObjectURL(url);
    pushToast('持仓明细 CSV 已导出', 'success');
  };

  const handleFreezeShadow = async () => {
    setFreezing(true);
    try {
      const res = await api.freezeShadowBaseline(activeLedgerId, `${ledgerName} 调整前基准`);
      await notifyDataMutated(`已冻结「${res.baseline_name}」（${res.frozen_date}），后续持续跟踪调仓超额`);
    } catch (e) {
      pushToast(e instanceof Error ? e.message : '冻结基准失败', 'error');
    } finally {
      setFreezing(false);
    }
  };

  if (!loading && holdings.length === 0) {
    return (
      <section className="inst-panel rounded-lg p-12 text-center space-y-4 fade-in">
        <div className="w-12 h-12 rounded-lg bg-slate-100 border border-slate-200 text-slate-700 mx-auto flex items-center justify-center">
          <Plus className="w-6 h-6" />
        </div>
        <div className="space-y-1 max-w-md mx-auto">
          <h1 className="text-base font-bold text-slate-900">当前账本【{ledgerName}】尚无持仓记录</h1>
          <p className="text-xs text-slate-500 leading-relaxed">
            支持粘贴文本、截图离线 OCR（带预览核对表）或手动录入持仓，导入后立即执行资产缺口、申万行业穿透与极端尾部风险压测。
          </p>
        </div>
        <div>
          <button
            type="button"
            onClick={() => openDataCenter('import')}
            className="px-4 py-2 rounded-md text-xs font-semibold bg-[#0A1628] text-white hover:bg-slate-800 cursor-pointer"
          >
            打开数据中心导入持仓
          </button>
        </div>
      </section>
    );
  }

  const alerts = riskCheck?.active_sentry?.alerts || [];
  const hasShadow = Boolean(shadowComp.has_baseline);
  const shadowExcessPct = Number(shadowComp.excess_return_pct ?? 0);
  const stressModel = (stress.stress_model || {}) as Record<string, unknown>;
  const cvar = (stress.cvar_bootstrap || {}) as Record<string, unknown>;
  const totalEq = Number(overview?.total_equity ?? 0);

  const rawScenarios = Array.isArray(cvar.scenarios) ? (cvar.scenarios as Array<Record<string, unknown>>) : [];
  const portBeta = Number(stressModel.portfolio_weighted_beta ?? stressModel.portfolio_beta ?? 0.6);
  const stressScenarios =
    rawScenarios.length > 0
      ? rawScenarios.slice(0, 4).map((sc) => ({
          name: String(sc.name || '历史极端情景'),
          period: String(sc.period || ''),
          estDrop: -Math.abs(Number(sc.predicted_mdd_pct ?? 0)),
          estLoss: Math.abs(Number(sc.predicted_loss_amount ?? 0)),
        }))
      : [
          { name: '2018 去杠杆熊市情景', period: '2018', estDrop: -(25.3 * Math.min(1.1, Math.max(0.25, portBeta))), estLoss: (totalEq * 25.3 * Math.min(1.1, Math.max(0.25, portBeta))) / 100 },
          { name: '2020 流动性冲击情景', period: '2020', estDrop: -(16.1 * Math.min(1.1, Math.max(0.25, portBeta))), estLoss: (totalEq * 16.1 * Math.min(1.1, Math.max(0.25, portBeta))) / 100 },
          { name: '2022 全球加息杀估值情景', period: '2022', estDrop: -(21.6 * Math.min(1.1, Math.max(0.25, portBeta))), estLoss: (totalEq * 21.6 * Math.min(1.1, Math.max(0.25, portBeta))) / 100 },
        ];
  const cvar99 = cvar.overall_cvar_99 !== undefined ? Number(cvar.overall_cvar_99) : null;
  const overlapPairs = Array.isArray(overlap.overlap_pairs)
    ? (overlap.overlap_pairs as Array<Record<string, unknown>>)
    : Array.isArray(overlap.top_overlapping_stocks)
    ? (overlap.top_overlapping_stocks as Array<Record<string, unknown>>)
    : [];

  return (
    <div className="space-y-4 fade-in" data-testid="holdings-page">
      {isDemoLedger && (
        <div className="inst-panel rounded-lg px-4 py-2 border-l-4 border-l-blue-600 flex flex-wrap items-center justify-between gap-2 text-xs">
          <span className="text-slate-700">
            当前正在查看 <strong className="text-slate-900">示例账本 · {ledgerName}</strong>，可在右上角「数据与账本」新建个人空白账本并导入真实持仓。
          </span>
          <button
            type="button"
            onClick={() => openDataCenter('ledgers')}
            className="text-blue-700 font-semibold hover:underline cursor-pointer"
          >
            管理账本 / 导入持仓 →
          </button>
        </div>
      )}

      {/* 顶部 4 列无彩虹底机构级资产 KPI 带（含真实年化 XIRR 与记流水入口） */}
      <section className="inst-panel rounded-xl grid grid-cols-2 lg:grid-cols-4 divide-y lg:divide-y-0 lg:divide-x divide-slate-200 tabular-nums">
        <div className="p-4">
          <div className="flex items-center justify-between text-[11px] font-medium text-slate-500">
            <span>组合总资产（含现金）</span>
            <button type="button" onClick={handleEditCash} className="text-blue-700 font-semibold hover:underline cursor-pointer">
              改现金
            </button>
          </div>
          <div className="inst-kpi-val text-slate-900 mt-1.5">
            ¥{totalEq.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </div>
          <div className="text-[11px] text-slate-500 mt-1">
            可用现金 ¥{(overview?.available_cash ?? 0).toLocaleString('zh-CN', { minimumFractionDigits: 2 })}
          </div>
        </div>

        <div className="p-4">
          <div className="text-[11px] font-medium text-slate-500">今日估算盈亏</div>
          <div
            className={`inst-kpi-val mt-1.5 ${
              (overview?.today_est_pnl ?? 0) >= 0 ? 'text-[#C81E1E]' : 'text-[#047857]'
            }`}
          >
            {(overview?.today_est_pnl ?? 0) >= 0 ? '+' : '-'}¥
            {Math.abs(overview?.today_est_pnl ?? 0).toLocaleString('zh-CN', { minimumFractionDigits: 2 })}
          </div>
          <div className="text-[11px] text-slate-500 mt-1">
            当日 {(overview?.today_est_pnl_pct ?? 0) >= 0 ? '+' : ''}
            {(overview?.today_est_pnl_pct ?? 0).toFixed(2)}% · {overview?.is_official_nav ? '官方净值' : '盘中估值'}
          </div>
        </div>

        <div className="p-4">
          <div className="flex items-center justify-between text-[11px] font-medium text-slate-500">
            <span className="inline-flex items-center">
              累计盈亏 / 年化 XIRR
              <MetricTooltip specKey="xirr" />
            </span>
            <button
              type="button"
              onClick={() => setCashflowModalOpen(true)}
              data-testid="btn-open-cashflow-modal"
              className="text-blue-700 font-semibold hover:underline inline-flex items-center gap-0.5 cursor-pointer"
            >
              <ReceiptText className="w-3 h-3" />
              <span>记流水</span>
            </button>
          </div>
          <div
            className={`inst-kpi-val mt-1.5 ${
              (overview?.cumulative_pnl ?? 0) >= 0 ? 'text-[#C81E1E]' : 'text-[#047857]'
            }`}
          >
            {(overview?.cumulative_pnl ?? 0) >= 0 ? '+' : '-'}¥
            {Math.abs(overview?.cumulative_pnl ?? 0).toLocaleString('zh-CN', { minimumFractionDigits: 2 })}
          </div>
          <div className="text-[11px] text-slate-500 mt-1 flex flex-wrap items-center gap-x-1.5">
            <span>
              简单 {(overview?.cumulative_pnl_pct ?? 0) >= 0 ? '+' : ''}
              {(overview?.cumulative_pnl_pct ?? 0).toFixed(2)}%
            </span>
            <span className="text-slate-300">·</span>
            <span
              title={cashflowSummary?.source_label || '资金加权年化收益率'}
              className={`font-semibold ${
                cashflowSummary?.xirr_pct === null || cashflowSummary?.xirr_pct === undefined
                  ? 'text-slate-400'
                  : cashflowSummary.xirr_pct >= 0
                  ? 'text-[#C81E1E]'
                  : 'text-[#047857]'
              }`}
            >
              XIRR{' '}
              {cashflowSummary?.xirr_pct !== null && cashflowSummary?.xirr_pct !== undefined
                ? `${cashflowSummary.xirr_pct >= 0 ? '+' : ''}${cashflowSummary.xirr_pct.toFixed(1)}%`
                : '--'}
            </span>
          </div>
        </div>

        <div className="p-4">
          <div className="text-[11px] font-medium text-slate-500">
            风控状态 / 极端 CVaR99
            <MetricTooltip specKey="cvar99" align="right" />
          </div>
          <div className="inst-kpi-val text-slate-900 mt-1.5">
            {cvar99 !== null ? <span className="text-[#047857]">-{Math.abs(cvar99).toFixed(1)}%</span> : `${alerts.length} 预警`}
          </div>
          <div className="text-[11px] text-slate-500 mt-1 flex items-center justify-between gap-2">
            <span>
              {tpSummary && tpSummary.lock_count > 0
                ? `${tpSummary.lock_count} 只触发移动止盈`
                : tailCount > 0
                ? `含 ${tailCount} 只 <¥200 尾仓`
                : '无碎片尾仓'}
            </span>
            <button
              type="button"
              onClick={() => setActiveTab('rebalance')}
              className="text-blue-700 font-semibold hover:underline inline-flex items-center gap-0.5 cursor-pointer"
            >
              去调仓 <ArrowRight className="w-3 h-3" />
            </button>
          </div>
        </div>
      </section>

      {/* 统一下划线子视图切换（彻底避免 4 屏混排） */}
      <div className="inst-panel rounded-lg px-4 flex flex-wrap items-center justify-between gap-2 border-b border-slate-200">
        <div className="flex items-center gap-5 overflow-x-auto no-scrollbar" role="tablist" aria-label="实盘与风控子视图">
          {[
            { id: 'list', label: `持仓明细与净值对账 (${holdings.length})` },
            { id: 'exposure', label: '大类缺口 · 行业穿透 · 重仓重叠' },
            { id: 'stress', label: '极端压测与影子追踪' },
          ].map((t) => (
            <button
              key={t.id}
              type="button"
              role="tab"
              aria-selected={subTab === t.id}
              data-active={subTab === t.id}
              onClick={() => setSubTab(t.id as HoldingSubTab)}
              className="inst-subtab"
            >
              {t.label}
            </button>
          ))}
        </div>

        <span className="text-[11px] text-slate-400 py-1.5">
          发现 <strong className="text-slate-700">{alerts.length + (tailCount > 0 ? 1 : 0)}</strong> 项风控关注点
        </span>
      </div>

      {/* ==================== 子视图 1：持仓明细与净值对账 ==================== */}
      {subTab === 'list' && (
        <div className="space-y-4 fade-in">
          {/* 精炼风险关注条 */}
          {(tailCount > 0 || alerts.length > 0) && (
            <section className="inst-panel rounded-lg p-3.5 border-l-4 border-l-amber-500 space-y-2 text-xs">
              <div className="flex items-center justify-between gap-2">
                <div className="flex items-center gap-1.5 font-bold text-slate-900">
                  <AlertTriangle className="w-3.5 h-3.5 text-amber-600" />
                  <span>持仓风控体检（{alerts.length + (tailCount > 0 ? 1 : 0)} 项）</span>
                </div>
                <button
                  type="button"
                  onClick={() => setActiveTab('rebalance')}
                  className="text-blue-700 font-semibold hover:underline cursor-pointer"
                >
                  前往调仓执行台处理 →
                </button>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                {tailCount > 0 && (
                  <div className="px-3 py-2 rounded bg-slate-50 border border-slate-200 text-slate-700">
                    <span className="font-bold text-amber-800 mr-1.5">[碎片尾仓]</span>
                    持有 <strong>{tailCount} 只</strong>不足 ¥200 的尾仓，建议在调仓页一键清扫归拢。
                  </div>
                )}
                {alerts.slice(0, 3).map((a, idx) => (
                  <div key={idx} className="px-3 py-2 rounded bg-slate-50 border border-slate-200 text-slate-700">
                    <span className="font-bold text-red-700 mr-1.5">[{a.dimension || '风控'}]</span>
                    <span>{a.title || a.message}</span>
                  </div>
                ))}
              </div>
            </section>
          )}

          {/* 持仓明细 / 净值对账高密度表 */}
          <section className="inst-panel rounded-lg overflow-hidden">
            <div className="px-4 py-3 border-b border-slate-200 bg-slate-50/70 flex flex-wrap items-center justify-between gap-2.5">
              <div className="flex flex-wrap items-center gap-3">
                <h2 id={tableCaptionId} className="text-xs font-bold text-slate-900">
                  {tableView === 'holdings' ? `持仓明细（${filtered.length} / ${holdings.length} 只）` : `净值估值对账（${filtered.length} 只）`}
                </h2>
                <div className="inline-flex items-center gap-0.5 bg-slate-200/70 p-0.5 rounded-md">
                  <button
                    type="button"
                    onClick={() => setTableView('holdings')}
                    className={`px-2.5 py-1 rounded text-[11px] font-semibold cursor-pointer ${
                      tableView === 'holdings' ? 'bg-white text-slate-900 shadow-2xs' : 'text-slate-600'
                    }`}
                  >
                    持仓明细
                  </button>
                  <button
                    type="button"
                    onClick={() => setTableView('reconcile')}
                    className={`px-2.5 py-1 rounded text-[11px] font-semibold cursor-pointer ${
                      tableView === 'reconcile' ? 'bg-white text-slate-900 shadow-2xs' : 'text-slate-600'
                    }`}
                  >
                    净值对账
                  </button>
                </div>
              </div>

              <div className="flex flex-wrap items-center gap-2">
                <div className="relative">
                  <Search className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-1/2 -translate-y-1/2 pointer-events-none" />
                  <input
                    type="search"
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    placeholder="搜索代码或名称..."
                    aria-label="搜索持仓基金"
                    className="h-8 pl-8 pr-3 rounded-md text-xs bg-white border border-slate-200 focus:border-blue-600 focus:outline-none w-40"
                  />
                </div>
                <select
                  value={tierFilter}
                  onChange={(e) => setTierFilter(e.target.value as 'all' | 'core' | 'tail')}
                  aria-label="按市值筛选持仓"
                  className="h-8 px-2 rounded-md text-xs bg-white border border-slate-200 text-slate-700 cursor-pointer"
                >
                  <option value="all">全部持仓</option>
                  <option value="core">核心持仓 (≥¥500)</option>
                  <option value="tail">碎片尾仓 (&lt;¥200)</option>
                </select>
                <button
                  type="button"
                  onClick={handleExportCsv}
                  className="h-8 px-2.5 rounded-md text-xs font-medium border border-slate-200 bg-white text-slate-700 hover:bg-slate-50 inline-flex items-center gap-1 cursor-pointer"
                >
                  <Download className="w-3.5 h-3.5" />
                  <span>导出 CSV</span>
                </button>
              </div>
            </div>

            <div tabIndex={0} role="region" aria-labelledby={tableCaptionId} className="table-wrapper">
              {tableView === 'holdings' ? (
                <table className="text-left text-xs tabular-nums">
                  <thead>
                    <tr className="border-b border-slate-200 text-slate-500 bg-white">
                      <th scope="col" className="py-2.5 px-4 font-semibold whitespace-nowrap">基金名称 / 代码</th>
                      <th scope="col" className="py-2.5 px-3 font-semibold whitespace-nowrap">资产大类</th>
                      <th scope="col" className="py-2.5 px-3 font-semibold text-right whitespace-nowrap">
                        <button type="button" onClick={() => toggleSort('market_value')} className="inline-flex items-center gap-1 hover:text-slate-900 cursor-pointer">
                          <span>市值 / 份额</span>
                          <ArrowUpDown className="w-3 h-3" />
                        </button>
                      </th>
                      <th scope="col" className="py-2.5 px-3 font-semibold text-right whitespace-nowrap">
                        <button type="button" onClick={() => toggleSort('day_chg')} className="inline-flex items-center gap-1 hover:text-slate-900 cursor-pointer">
                          <span>今日涨跌</span>
                          <ArrowUpDown className="w-3 h-3" />
                        </button>
                      </th>
                      <th scope="col" className="py-2.5 px-3 font-semibold text-right whitespace-nowrap">
                        <button type="button" onClick={() => toggleSort('floating_pnl_pct')} className="inline-flex items-center gap-1 hover:text-slate-900 cursor-pointer">
                          <span>累计盈亏</span>
                          <ArrowUpDown className="w-3 h-3" />
                        </button>
                      </th>
                      <th scope="col" className="py-2.5 px-3 font-semibold whitespace-nowrap">
                        <button type="button" onClick={() => toggleSort('holding_days')} className="inline-flex items-center gap-1 hover:text-slate-900 cursor-pointer">
                          <span>持有天数 / 止盈守果</span>
                          <ArrowUpDown className="w-3 h-3" />
                        </button>
                        <MetricTooltip specKey="trailing_tp" align="right" />
                      </th>
                      <th scope="col" className="py-2.5 px-4 font-semibold text-right whitespace-nowrap">操作</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {loading ? (
                      <tr>
                        <td colSpan={7} className="py-10 text-center text-slate-400">
                          正在加载持仓明细与实时估值...
                        </td>
                      </tr>
                    ) : (
                      filtered.map((h) => {
                        const dayChg = getDayChg(h);
                        const cumPct = Number(h.floating_pnl_pct ?? 0);
                        const mv = Number(h.market_value ?? 0);
                        const isEditing = editingCode === h.fund_code;
                        const isPenalty = (h.holding_days ?? 0) < 7;

                        return (
                          <tr key={h.fund_code} data-testid="holding-row" className="hover:bg-blue-50/30 transition-colors">
                            <th scope="row" className="py-2.5 px-4 font-normal">
                              <button
                                type="button"
                                onClick={() => openInspector(h.fund_code)}
                                className="text-left group cursor-pointer"
                              >
                                <div className="font-semibold text-slate-900 group-hover:text-blue-700 group-hover:underline whitespace-nowrap">
                                  {h.fund_name}
                                </div>
                                <div className="text-slate-400 font-mono text-[11px]">{h.fund_code}</div>
                              </button>
                            </th>
                            <td className="py-2.5 px-3 whitespace-nowrap">
                              <span className="px-2 py-0.5 rounded bg-slate-100 text-slate-600 text-[11px]">
                                {h.asset_class || `${h.share_class || 'A'}类`}
                              </span>
                            </td>
                            <td className="py-2.5 px-3 text-right whitespace-nowrap">
                              {isEditing ? (
                                <div className="flex items-center justify-end gap-1">
                                  <input
                                    type="number"
                                    step="0.01"
                                    value={editShares}
                                    onChange={(e) => setEditShares(e.target.value)}
                                    aria-label="编辑持有份额"
                                    className="w-20 h-7 px-2 rounded border border-blue-500 text-right text-xs"
                                    placeholder="份额"
                                  />
                                  <input
                                    type="number"
                                    step="0.0001"
                                    value={editCost}
                                    onChange={(e) => setEditCost(e.target.value)}
                                    aria-label="编辑持仓成本"
                                    className="w-20 h-7 px-2 rounded border border-blue-500 text-right text-xs"
                                    placeholder="成本"
                                  />
                                </div>
                              ) : (
                                <>
                                  <div className="font-bold text-slate-900">
                                    ¥{mv.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                                  </div>
                                  <div className="text-[11px] text-slate-400">{Number(h.shares ?? 0).toFixed(2)} 份</div>
                                </>
                              )}
                            </td>
                            <td className={`py-2.5 px-3 text-right font-bold whitespace-nowrap ${dayChg >= 0 ? 'text-red-600' : 'text-emerald-700'}`}>
                              {dayChg >= 0 ? '+' : ''}
                              {dayChg.toFixed(2)}%
                            </td>
                            <td className={`py-2.5 px-3 text-right font-bold whitespace-nowrap ${cumPct >= 0 ? 'text-red-600' : 'text-emerald-700'}`}>
                              {cumPct >= 0 ? '+' : ''}
                              {cumPct.toFixed(2)}%
                            </td>
                            <td className="py-2.5 px-3 whitespace-nowrap">
                              <div className="flex items-center gap-1.5">
                                <span className="font-medium text-slate-800">{h.holding_days ?? 0}天</span>
                                <span
                                  className={`px-1.5 py-0.5 rounded text-[10px] font-semibold ${
                                    isPenalty
                                      ? 'bg-red-50 text-red-700 border border-red-200'
                                      : mv < 200
                                      ? 'bg-amber-50 text-amber-800 border border-amber-200'
                                      : 'bg-slate-100 text-slate-600'
                                  }`}
                                >
                                  {h.redemption_fee_status?.label || '正常'}
                                </span>
                              </div>
                              {h.take_profit && h.take_profit.status !== 'NORMAL' && (
                                <div className="mt-1">
                                  <span
                                    title={h.take_profit.action_tip}
                                    className={`inline-block px-1.5 py-0.5 rounded text-[10px] font-semibold border ${
                                      h.take_profit.status === 'LOCK_PARTIAL'
                                        ? 'bg-amber-50 text-amber-900 border-amber-300'
                                        : h.take_profit.status === 'TARGET_REACHED'
                                        ? 'bg-red-50 text-[#C81E1E] border-red-200'
                                        : h.take_profit.status === 'HOLD_PENALTY'
                                        ? 'bg-red-50 text-red-700 border-red-200'
                                        : 'bg-blue-50 text-blue-800 border-blue-200'
                                    }`}
                                  >
                                    {h.take_profit.label}
                                    {h.take_profit.drawdown_from_peak_pct < -0.5 && h.take_profit.status !== 'HOLD_PENALTY'
                                      ? ` (高点${h.take_profit.drawdown_from_peak_pct.toFixed(1)}%)`
                                      : ''}
                                  </span>
                                </div>
                              )}
                            </td>
                            <td className="py-2.5 px-4 text-right whitespace-nowrap">
                              {isEditing ? (
                                <div className="inline-flex items-center gap-1">
                                  <button
                                    type="button"
                                    disabled={savingEdit}
                                    onClick={() => void handleSaveEdit(h)}
                                    className="p-1 rounded bg-blue-700 text-white hover:bg-blue-800 cursor-pointer"
                                    aria-label="保存修改"
                                  >
                                    <Check className="w-3.5 h-3.5" />
                                  </button>
                                  <button
                                    type="button"
                                    onClick={() => setEditingCode(null)}
                                    className="p-1 rounded bg-slate-200 text-slate-700 hover:bg-slate-300 cursor-pointer"
                                    aria-label="取消修改"
                                  >
                                    <X className="w-3.5 h-3.5" />
                                  </button>
                                </div>
                              ) : (
                                <div className="inline-flex items-center gap-2.5">
                                  <button
                                    type="button"
                                    onClick={() => handleStartEdit(h)}
                                    aria-label={`编辑基金 ${h.fund_name}`}
                                    className="inline-flex items-center gap-1 text-slate-500 hover:text-blue-700 font-medium cursor-pointer"
                                  >
                                    <Pencil className="w-3.5 h-3.5" />
                                    <span>编辑</span>
                                  </button>
                                  <button
                                    type="button"
                                    onClick={() => handleDelete(h)}
                                    aria-label={`删除基金 ${h.fund_name}`}
                                    className="inline-flex items-center gap-1 text-slate-400 hover:text-red-600 font-medium cursor-pointer"
                                  >
                                    <Trash2 className="w-3.5 h-3.5" />
                                    <span>删除</span>
                                  </button>
                                </div>
                              )}
                            </td>
                          </tr>
                        );
                      })
                    )}
                  </tbody>
                </table>
              ) : (
                <table className="text-left text-xs tabular-nums">
                  <thead>
                    <tr className="border-b border-slate-200 text-slate-500 bg-white">
                      <th scope="col" className="py-2.5 px-4 font-semibold whitespace-nowrap">基金名称 / 代码</th>
                      <th scope="col" className="py-2.5 px-3 font-semibold text-right whitespace-nowrap">最新单位净值</th>
                      <th scope="col" className="py-2.5 px-3 font-semibold text-right whitespace-nowrap">盘中估算涨跌</th>
                      <th scope="col" className="py-2.5 px-3 font-semibold text-right whitespace-nowrap">官方公布涨跌</th>
                      <th scope="col" className="py-2.5 px-3 font-semibold text-right whitespace-nowrap">估值误差</th>
                      <th scope="col" className="py-2.5 px-4 font-semibold whitespace-nowrap">数据状态</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {filtered.map((h) => {
                      const est = Number(h.est_chg_pct ?? 0);
                      const hasOff = h.is_official_nav && h.official_chg_pct !== null && h.official_chg_pct !== undefined;
                      const off = hasOff ? Number(h.official_chg_pct) : null;
                      const diff = off !== null ? est - off : null;
                      return (
                        <tr key={h.fund_code} className="hover:bg-slate-50/70">
                          <th scope="row" className="py-2.5 px-4 font-normal">
                            <button type="button" onClick={() => openInspector(h.fund_code)} className="text-left hover:text-blue-700 cursor-pointer">
                              <div className="font-semibold text-slate-900 whitespace-nowrap">{h.fund_name}</div>
                              <div className="text-slate-400 font-mono text-[11px]">{h.fund_code}</div>
                            </button>
                          </th>
                          <td className="py-2.5 px-3 text-right font-mono text-slate-800">{Number(h.current_nav ?? 0).toFixed(4)}</td>
                          <td className={`py-2.5 px-3 text-right font-semibold ${est >= 0 ? 'text-red-600' : 'text-emerald-700'}`}>
                            {est >= 0 ? '+' : ''}
                            {est.toFixed(2)}%
                          </td>
                          <td className={`py-2.5 px-3 text-right font-bold ${off === null ? 'text-slate-400' : off >= 0 ? 'text-red-600' : 'text-emerald-700'}`}>
                            {off === null ? '待公布' : `${off >= 0 ? '+' : ''}${off.toFixed(2)}%`}
                          </td>
                          <td className="py-2.5 px-3 text-right text-slate-600">
                            {diff === null ? '--' : `${diff >= 0 ? '+' : ''}${diff.toFixed(2)}%`}
                          </td>
                          <td className="py-2.5 px-4 whitespace-nowrap">
                            <span
                              className={`px-2 py-0.5 rounded text-[10px] font-semibold ${
                                hasOff ? 'bg-emerald-50 text-emerald-700 border border-emerald-200' : 'bg-blue-50 text-blue-700 border border-blue-200'
                              }`}
                            >
                              {hasOff ? '官方净值已更新' : '盘中实时估算'}
                            </span>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              )}
            </div>
          </section>
        </div>
      )}

      {/* ==================== 子视图 2：大类缺口 + 行业穿透 + 重仓重叠（原抽屉归位） ==================== */}
      {subTab === 'exposure' && (
        <div className="space-y-4 fade-in">
          <ExposureCharts exposure={exposure} loading={expLoading} />

          <section className="inst-panel rounded-lg p-4 sm:p-5 space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Layers className="w-4 h-4 text-slate-700" />
                <h3 className="text-xs font-bold text-slate-900">底层重仓股交叉重叠穿透（防多基同买同一批重仓股）</h3>
              </div>
              <span className="text-[11px] text-slate-400">
                {String(overlap.summary || overlap.verdict || '季报前十大重仓穿透')}
              </span>
            </div>

            {overlapPairs.length === 0 ? (
              <div className="p-3 rounded-md bg-slate-50 border border-slate-200 text-xs text-slate-600">
                当前组合底层重仓股票交叉重叠度低，风格分散度良好。
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-xs text-left tabular-nums">
                  <thead>
                    <tr className="border-b border-slate-200 text-slate-500">
                      <th className="py-2 px-3 font-semibold">重仓股 / 基金对</th>
                      <th className="py-2 px-3 font-semibold text-right">重叠度 / 合计穿透占比</th>
                      <th className="py-2 px-3 font-semibold">涉及基金</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {overlapPairs.slice(0, 8).map((row, idx) => (
                      <tr key={idx} className="hover:bg-slate-50/70">
                        <td className="py-2 px-3 font-semibold text-slate-900">
                          {String(row.stock_name || row.pair_name || row.fund_a || `重叠项 ${idx + 1}`)}
                        </td>
                        <td className="py-2 px-3 text-right font-mono font-bold text-amber-700">
                          {Number(row.overlap_pct ?? row.total_weight_pct ?? row.similarity_pct ?? 0).toFixed(2)}%
                        </td>
                        <td className="py-2 px-3 text-slate-600">
                          {Array.isArray(row.funds) ? row.funds.join(' / ') : String(row.fund_b || row.detail || '--')}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>
        </div>
      )}

      {/* ==================== 子视图 3：极端行情压力测试 + 调仓影子追踪 + 前瞻实盘审计 ==================== */}
      {subTab === 'stress' && (
        <div className="space-y-4 fade-in">
          <section className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <div className="inst-panel rounded-xl p-4 sm:p-5 flex flex-col justify-between gap-4">
            <div className="space-y-2">
              <div className="flex items-center justify-between gap-2">
                <div className="flex items-center gap-2">
                  <Scale className="w-4 h-4 text-blue-700" />
                  <h3 className="text-xs font-bold text-slate-900">调仓效果追踪（调整前 vs 调整后）</h3>
                </div>
                <button
                  type="button"
                  disabled={freezing}
                  onClick={() => void handleFreezeShadow()}
                  className="px-2.5 py-1 rounded text-[11px] font-semibold bg-[#0A1628] text-white hover:bg-slate-800 cursor-pointer disabled:opacity-50"
                >
                  {hasShadow ? '重新冻结基准' : '记录调整前基准'}
                </button>
              </div>
              <p className="text-xs text-slate-500">
                冻结调整前持仓快照后，系统将按每日真实净值持续追踪实盘相对“原地不动基准”的超额 Alpha。
              </p>
            </div>

            {hasShadow ? (
              <div className="grid grid-cols-3 border border-slate-200 rounded-md divide-x divide-slate-200 text-xs tabular-nums">
                <div className="p-3">
                  <div className="text-[11px] text-slate-500">调整前基准</div>
                  <div className="text-base font-bold text-slate-800 mt-1">
                    {Number(shadowComp.shadow_return_pct ?? 0) >= 0 ? '+' : ''}
                    {Number(shadowComp.shadow_return_pct ?? 0).toFixed(2)}%
                  </div>
                </div>
                <div className="p-3">
                  <div className="text-[11px] text-slate-500">当前实盘</div>
                  <div className="text-base font-bold text-slate-800 mt-1">
                    {Number(shadowComp.live_return_pct ?? 0) >= 0 ? '+' : ''}
                    {Number(shadowComp.live_return_pct ?? 0).toFixed(2)}%
                  </div>
                </div>
                <div className="p-3 bg-slate-50/70">
                  <div className="text-[11px] text-slate-600 font-semibold">调仓超额 Alpha</div>
                  <div className={`text-base font-extrabold mt-1 ${shadowExcessPct >= 0 ? 'text-red-600' : 'text-emerald-700'}`}>
                    {shadowExcessPct >= 0 ? '+' : ''}
                    {shadowExcessPct.toFixed(2)}%
                  </div>
                </div>
              </div>
            ) : (
              <div className="p-3.5 rounded-md bg-slate-50 border border-dashed border-slate-300 text-xs text-slate-500">
                尚未记录对比基准。建议在参照「调仓执行」操作前先冻结一份调整前快照。
              </div>
            )}
          </div>

          <div className="inst-panel rounded-lg p-4 sm:p-5 space-y-3">
            <div className="flex items-center justify-between gap-2">
              <div className="flex items-center gap-1.5">
                <ShieldAlert className="w-4 h-4 text-red-600" />
                <h3 className="text-xs font-bold text-slate-900">极端行情压力测试（Block Bootstrap）</h3>
                <MetricTooltip specKey="cvar99" align="right" />
              </div>
              {cvar99 !== null && (
                <span className="text-[11px] font-mono font-bold px-2 py-0.5 rounded bg-red-50 text-red-700 border border-red-200 tabular-nums">
                  99% 极端尾部风险 CVaR -{Math.abs(cvar99).toFixed(1)}%
                </span>
              )}
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs tabular-nums">
                <thead>
                  <tr className="border-b border-slate-200 text-slate-500">
                    <th className="py-2 pr-2 font-semibold">历史极端情景</th>
                    <th className="py-2 px-2 text-right font-semibold">预估最大回撤</th>
                    <th className="py-2 pl-2 text-right font-semibold">预估最大浮亏</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {stressScenarios.map((sc) => (
                    <tr key={sc.name}>
                      <td className="py-2 pr-2">
                        <div className="font-semibold text-slate-800">{sc.name}</div>
                        {sc.period && <div className="text-[10px] text-slate-400">{sc.period}</div>}
                      </td>
                      <td className="py-2 px-2 text-right font-bold text-emerald-700">{sc.estDrop.toFixed(2)}%</td>
                      <td className="py-2 pl-2 text-right font-semibold text-slate-700">
                        -¥{Math.abs(sc.estLoss).toLocaleString('zh-CN', { maximumFractionDigits: 0 })}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
          </section>

          {/* 前瞻实盘审计日志（只读冻结验真） */}
          <section className="inst-panel rounded-xl overflow-hidden" data-testid="forward-audit-card">
            <div className="px-4 py-3 inst-panel-header flex flex-wrap items-center justify-between gap-2">
              <div className="flex items-center gap-2">
                <FileCheck2 className="w-4 h-4 text-blue-700" />
                <h3 className="text-xs font-bold text-slate-900">前瞻实盘审计日志（每日只读冻结 · 持续检验历史裁决真实表现）</h3>
              </div>
              <span className="text-[11px] font-mono text-slate-500 tabular-nums">
                已归档 {recentAuditLogs.length} 条快照
                {forwardAudit?.status ? ` · ${String(forwardAudit.status)}` : ''}
              </span>
            </div>
            {recentAuditLogs.length === 0 ? (
              <div className="p-4 text-xs text-slate-500">
                前瞻实盘审计已在系统启动与每日盘后自动开启（每日最多冻结 1 条不可篡改快照），后续将按 30/90/180 天自动对照沪深 300 验真。
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-xs text-left tabular-nums">
                  <thead>
                    <tr className="border-b border-slate-200 bg-white text-slate-500 text-[11px]">
                      <th className="py-2 px-4 font-semibold">冻结日期</th>
                      <th className="py-2 px-3 font-semibold">宏观状态</th>
                      <th className="py-2 px-3 font-semibold">定调动作</th>
                      <th className="py-2 px-3 font-semibold text-right">沪深300基准点位</th>
                      <th className="py-2 px-4 font-semibold text-right">跟踪基金数</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {[...recentAuditLogs].reverse().slice(0, 8).map((lg, i) => {
                      const tw = (lg.target_weights || {}) as Record<string, unknown>;
                      const pt = Number(lg.hs300_point ?? lg.c300_close ?? 0);
                      return (
                        <tr key={i} className="hover:bg-slate-50/70">
                          <td className="py-2 px-4 font-mono text-slate-800">{String(lg.date || lg.trade_date || '--')}</td>
                          <td className="py-2 px-3 font-medium text-slate-700">{String(lg.market_regime || 'NEUTRAL')}</td>
                          <td className="py-2 px-3">
                            <span className="px-2 py-0.5 rounded bg-slate-100 text-slate-700 text-[11px] font-semibold">
                              {String(lg.verdict_action || 'HOLD')}
                            </span>
                          </td>
                          <td className="py-2 px-3 text-right font-mono text-slate-700">
                            {pt > 0 ? pt.toLocaleString('zh-CN', { maximumFractionDigits: 1 }) : '--'}
                          </td>
                          <td className="py-2 px-4 text-right font-mono text-slate-600">{Object.keys(tw).length} 只</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </section>
        </div>
      )}

      <CashflowModal
        open={cashflowModalOpen}
        ledgerId={activeLedgerId}
        ledgerName={ledgerName}
        summary={cashflowSummary}
        onUpdated={(next) => setCashflowSummary(next)}
        onClose={() => setCashflowModalOpen(false)}
        onNotify={pushToast}
      />
    </div>
  );
}

import { useEffect, useId, useMemo, useState } from 'react';
import { Trash2, Plus, ArrowRight, Search, AlertTriangle, Download, Pencil, Check, X, Scale, ShieldAlert } from 'lucide-react';
import {
  api,
  type ExposureResponse,
  type HoldingRow,
  type OverviewResponse,
  type RiskCheckResponse,
} from '../api/client';
import { ExposureCharts } from '../components/charts/ExposureCharts';

interface HoldingsPageProps {
  overview: OverviewResponse | null;
  ledgerId: string;
  isDemoLedger: boolean;
  ledgerName: string;
  refreshTick: number;
  onOpenImport: () => void;
  onGoRebalance: () => void;
  onDataMutated: (msg: string) => void;
  onSelectFund: (code: string) => void;
}

export function HoldingsPage({
  overview,
  ledgerId,
  isDemoLedger,
  ledgerName,
  refreshTick,
  onOpenImport,
  onGoRebalance,
  onDataMutated,
  onSelectFund,
}: HoldingsPageProps) {
  const tableCaptionId = useId();
  const [holdings, setHoldings] = useState<HoldingRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [exposure, setExposure] = useState<ExposureResponse | null>(null);
  const [expLoading, setExpLoading] = useState(true);
  const [riskCheck, setRiskCheck] = useState<RiskCheckResponse | null>(null);
  const [stress, setStress] = useState<Record<string, unknown>>({});
  const [shadowComp, setShadowComp] = useState<Record<string, unknown>>({});
  const [freezing, setFreezing] = useState(false);

  const [tableView, setTableView] = useState<'holdings' | 'reconcile'>('holdings');
  const [query, setQuery] = useState('');
  const [tierFilter, setTierFilter] = useState<'all' | 'core' | 'tail'>('all');

  // 行内编辑状态
  const [editingCode, setEditingCode] = useState<string | null>(null);
  const [editShares, setEditShares] = useState('');
  const [editCost, setEditCost] = useState('');
  const [savingEdit, setSavingEdit] = useState(false);

  useEffect(() => {
    let alive = true;
    setLoading(true);
    setExpLoading(true);
    api
      .getHoldings(ledgerId)
      .then((res) => {
        if (alive) setHoldings(res.items || []);
      })
      .catch(() => {})
      .finally(() => {
        if (alive) setLoading(false);
      });
    api
      .getDiagnoseExposure(ledgerId)
      .then((res) => {
        if (alive) setExposure(res);
      })
      .catch(() => {})
      .finally(() => {
        if (alive) setExpLoading(false);
      });
    api
      .getDiagnoseRiskCheck(ledgerId)
      .then((res) => {
        if (alive) setRiskCheck(res);
      })
      .catch(() => {});
    api
      .getDiagnoseStress(ledgerId)
      .then((res) => {
        if (alive) setStress(res || {});
      })
      .catch(() => {});
    api
      .getAuditTrackers(ledgerId)
      .then((res) => {
        if (alive) setShadowComp((res?.shadow_tracker || {}) as Record<string, unknown>);
      })
      .catch(() => {});
    return () => {
      alive = false;
    };
  }, [ledgerId, refreshTick]);

  const tailCount = useMemo(() => holdings.filter((h) => Number(h.market_value ?? 0) < 200).length, [holdings]);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return holdings.filter((h) => {
      const mv = Number(h.market_value ?? 0);
      if (tierFilter === 'core' && mv < 500) return false;
      if (tierFilter === 'tail' && mv >= 200) return false;
      if (q && !h.fund_code.toLowerCase().includes(q) && !h.fund_name.toLowerCase().includes(q)) return false;
      return true;
    });
  }, [holdings, query, tierFilter]);

  const handleEditCash = async () => {
    const cur = overview?.available_cash ?? 0;
    const raw = window.prompt('请输入当前可用现金金额（元）：', String(cur));
    if (raw === null) return;
    const val = Number(raw);
    if (Number.isNaN(val) || val < 0) return;
    try {
      await api.updateCash(val, ledgerId);
      onDataMutated(`可用现金已更新为 ¥${val.toLocaleString()}（已自动冷备）`);
    } catch (e) {
      window.alert(e instanceof Error ? e.message : '更新现金失败');
    }
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
      window.alert('请输入有效的份额与持仓成本净值');
      return;
    }
    setSavingEdit(true);
    try {
      await api.reconcileManual(
        [{ fund_code: h.fund_code, fund_name: h.fund_name, shares: sh, cost_price: cp, current_nav: h.current_nav }],
        ledgerId
      );
      setEditingCode(null);
      onDataMutated(`已更新 ${h.fund_name} (${h.fund_code}) 份额与成本（已自动冷备）`);
    } catch (e) {
      window.alert(e instanceof Error ? e.message : '保存失败');
    } finally {
      setSavingEdit(false);
    }
  };

  const handleDelete = async (h: HoldingRow) => {
    if (!window.confirm(`确认从当前账本删除 ${h.fund_name} (${h.fund_code})？\n系统会在删除前自动生成冷备快照，随时可还原。`)) {
      return;
    }
    try {
      await api.deleteHolding(h.fund_code, ledgerId);
      onDataMutated(`已删除 ${h.fund_name} (${h.fund_code})`);
    } catch (e) {
      window.alert(e instanceof Error ? e.message : '删除失败');
    }
  };

  const handleExportCsv = () => {
    const header = ['基金代码', '基金名称', '资产大类', '持有份额', '成本净值', '最新净值', '当前市值', '今日涨跌(%)', '累计盈亏(%)', '持有天数', '赎回费状态'];
    const lines = [header.join(',')];
    for (const h of holdings) {
      const dayChg = Number(
        h.is_official_nav && h.official_chg_pct !== null && h.official_chg_pct !== undefined
          ? h.official_chg_pct
          : (h.est_chg_pct ?? 0)
      );
      lines.push(
        [
          `"${h.fund_code}"`,
          `"${(h.fund_name || '').replace(/"/g, '""')}"`,
          `"${h.asset_class || ''}"`,
          Number(h.shares ?? 0).toFixed(4),
          Number(h.cost_price ?? 0).toFixed(4),
          Number(h.current_nav ?? 0).toFixed(4),
          Number(h.market_value ?? 0).toFixed(2),
          dayChg.toFixed(2),
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
    a.download = `agy2_holdings_${ledgerId}_${new Date().toISOString().slice(0, 10)}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleFreezeShadow = async () => {
    setFreezing(true);
    try {
      const res = await api.freezeShadowBaseline(ledgerId, `${ledgerName} 调整前基准`);
      onDataMutated(`已记录「${res.baseline_name}」（${res.frozen_date}），后续将持续对比调仓前后收益差`);
    } catch (e) {
      window.alert(e instanceof Error ? e.message : '记录基准失败');
    } finally {
      setFreezing(false);
    }
  };

  if (!loading && holdings.length === 0) {
    return (
      <section className="card-elevated rounded-2xl p-10 sm:p-14 text-center space-y-4 fade-in">
        <div className="w-14 h-14 rounded-2xl bg-blue-50 border border-blue-200 text-blue-700 mx-auto flex items-center justify-center">
          <Plus className="w-7 h-7" />
        </div>
        <div className="space-y-1.5 max-w-md mx-auto">
          <h1 className="text-lg font-bold text-slate-900">当前账本【{ledgerName}】还没有持仓记录</h1>
          <p className="text-sm text-slate-500 leading-relaxed">
            导入你在支付宝 / 天天基金 / 券商持有的基金（支持截图离线 OCR、粘贴文本或手动录入），系统立刻为你做资产缺口、行业暴露与费率健康体检。
          </p>
        </div>
        <div className="pt-2">
          <button
            type="button"
            onClick={onOpenImport}
            className="px-5 py-2.5 rounded-xl text-sm font-semibold bg-[#0A192F] text-white hover:bg-[#132A4A] shadow-sm cursor-pointer"
          >
            立即导入我的持仓
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

  // 优先直接渲染后端 Block Bootstrap 真实极端危机情景表，零估算
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

  return (
    <div className="space-y-6 fade-in">
      {isDemoLedger && (
        <div className="px-4 py-2.5 rounded-xl bg-blue-50/80 border border-blue-200/80 flex flex-wrap items-center justify-between gap-2 text-xs">
          <span className="text-slate-700">
            当前正在查看 <strong className="text-slate-900">示例账本 · {ledgerName}</strong>。点击顶栏右上角文件夹图标可新建自己的空白账本并导入真实持仓。
          </span>
          <button type="button" onClick={onOpenImport} className="text-blue-700 font-semibold hover:underline cursor-pointer">
            导入 / 更新持仓 →
          </button>
        </div>
      )}

      {/* 3 项核心 KPI */}
      <section className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="hero-navy text-white rounded-2xl p-5 shadow-md">
          <div className="text-xs text-slate-300">组合总资产（含可用现金）</div>
          <div className="text-2xl font-extrabold tabular-nums mt-1.5 text-white">
            ¥{totalEq.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </div>
          <div className="text-xs text-slate-300 mt-2 flex items-center justify-between">
            <span>可用现金 ¥{(overview?.available_cash ?? 0).toLocaleString('zh-CN', { minimumFractionDigits: 2 })}</span>
            <button type="button" onClick={handleEditCash} className="text-amber-300 font-medium hover:underline cursor-pointer">
              修改现金
            </button>
          </div>
        </div>

        <div className="card-elevated rounded-2xl p-5">
          <div className="text-xs text-slate-500 font-medium">今日估算盈亏</div>
          <div
            className={`text-2xl font-extrabold tabular-nums mt-1.5 ${
              (overview?.today_est_pnl ?? 0) >= 0 ? 'text-red-600' : 'text-emerald-600'
            }`}
          >
            {(overview?.today_est_pnl ?? 0) >= 0 ? '+' : ''}¥
            {(overview?.today_est_pnl ?? 0).toLocaleString('zh-CN', { minimumFractionDigits: 2 })}{' '}
            <span className="text-base font-bold">
              ({(overview?.today_est_pnl_pct ?? 0) >= 0 ? '+' : ''}
              {(overview?.today_est_pnl_pct ?? 0).toFixed(2)}%)
            </span>
          </div>
          <div className="text-xs text-slate-400 mt-2">
            {overview?.is_official_nav ? '已按今日官方公布净值核算' : '盘中实时双轨估值核算'}
          </div>
        </div>

        <div className="card-elevated rounded-2xl p-5">
          <div className="text-xs text-slate-500 font-medium">累计持仓盈亏</div>
          <div
            className={`text-2xl font-extrabold tabular-nums mt-1.5 ${
              (overview?.cumulative_pnl ?? 0) >= 0 ? 'text-red-600' : 'text-emerald-600'
            }`}
          >
            {(overview?.cumulative_pnl ?? 0) >= 0 ? '+' : ''}¥
            {(overview?.cumulative_pnl ?? 0).toLocaleString('zh-CN', { minimumFractionDigits: 2 })}{' '}
            <span className="text-base font-bold">
              ({(overview?.cumulative_pnl_pct ?? 0) >= 0 ? '+' : ''}
              {(overview?.cumulative_pnl_pct ?? 0).toFixed(2)}%)
            </span>
          </div>
          <div className="text-xs text-slate-500 mt-2">
            共持有 {holdings.length} 只基金
            {tailCount > 0 && <span className="ml-1 text-amber-700 font-semibold">（含 {tailCount} 只 &lt;¥200 碎片尾仓）</span>}
          </div>
        </div>
      </section>

      {/* 体检核心预警卡 */}
      <section className="card-elevated rounded-2xl p-5 space-y-3.5">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-amber-600" />
            <h2 className="text-base font-bold text-slate-900">
              持仓健康体检结论（发现 {alerts.length + (tailCount > 0 ? 1 : 0)} 项关注点）
            </h2>
          </div>
          <button
            type="button"
            onClick={onGoRebalance}
            className="text-xs font-semibold text-blue-700 hover:underline inline-flex items-center gap-1 cursor-pointer"
          >
            <span>查看调仓参考方案</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-2.5">
          {tailCount > 0 && (
            <div className="p-3.5 rounded-xl bg-amber-50/75 border border-amber-200/75 flex items-start gap-2.5 text-xs">
              <span className="px-2 py-0.5 rounded-md text-[11px] font-bold bg-amber-500 text-white shrink-0">碎片尾仓</span>
              <span className="text-slate-700 leading-relaxed">
                当前有 <strong className="text-slate-900">{tailCount} 只基金市值不足 ¥200</strong>，分散注意力且对组合贡献微弱，建议在调仓页一键归拢。
              </span>
            </div>
          )}
          {alerts.slice(0, 5).map((a, idx) => (
            <div key={idx} className="p-3.5 rounded-xl bg-red-50/60 border border-red-200/70 flex items-start gap-2.5 text-xs">
              <span className="px-2 py-0.5 rounded-md text-[11px] font-bold bg-red-600 text-white shrink-0">
                {a.dimension || '风控预警'}
              </span>
              <div className="text-slate-700 leading-relaxed">
                <strong className="text-slate-900">{a.title || a.message}</strong>
                {a.action && <span className="block text-slate-500 mt-0.5">{a.action}</span>}
              </div>
            </div>
          ))}
          {tailCount === 0 && alerts.length === 0 && (
            <div className="p-3.5 rounded-xl bg-emerald-50/70 border border-emerald-200 text-xs text-emerald-800 md:col-span-2">
              当前持仓结构健康，未触发高危风控或高费率预警。
            </div>
          )}
        </div>
      </section>

      {/* 资产大类配比 + 行业穿透暴露双图 */}
      <ExposureCharts exposure={exposure} loading={expLoading} />

      {/* 调仓效果追踪（调整前 vs 调整后） + 极端行情压力测试 并排卡 */}
      <section className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* #4 调仓效果追踪 */}
        <div className="card-elevated rounded-2xl p-5 flex flex-col justify-between gap-4">
          <div className="space-y-2">
            <div className="flex items-center justify-between gap-2">
              <div className="flex items-center gap-2">
                <Scale className="w-4 h-4 text-blue-700" />
                <h3 className="text-sm font-bold text-slate-900">调仓效果追踪（调整前 vs 调整后）</h3>
              </div>
              <button
                type="button"
                disabled={freezing}
                onClick={handleFreezeShadow}
                className="px-2.5 py-1 rounded-lg text-[11px] font-semibold bg-blue-50 text-blue-700 hover:bg-blue-100 cursor-pointer disabled:opacity-50"
              >
                {hasShadow ? '重新设为对比基准' : '记录当前为调整前基准'}
              </button>
            </div>
            <p className="text-xs text-slate-500">
              在调仓前点一下「记录当前为调整前基准」，后续可长期直观验证：按建议调仓后的实盘表现，比原地不动多赚了多少或少亏了多少。
            </p>
          </div>

          {hasShadow ? (
            <div className="grid grid-cols-3 gap-2.5 text-xs tabular-nums">
              <div className="p-3 rounded-xl bg-slate-50 border border-slate-200">
                <div className="text-slate-500">调整前基准收益</div>
                <div className="text-base font-bold text-slate-800 mt-1">
                  {Number(shadowComp.shadow_return_pct ?? 0) >= 0 ? '+' : ''}
                  {Number(shadowComp.shadow_return_pct ?? 0).toFixed(2)}%
                </div>
              </div>
              <div className="p-3 rounded-xl bg-slate-50 border border-slate-200">
                <div className="text-slate-500">当前实盘收益</div>
                <div className="text-base font-bold text-slate-800 mt-1">
                  {Number(shadowComp.live_return_pct ?? 0) >= 0 ? '+' : ''}
                  {Number(shadowComp.live_return_pct ?? 0).toFixed(2)}%
                </div>
              </div>
              <div className="p-3 rounded-xl bg-blue-50/70 border border-blue-200">
                <div className="text-blue-800">调仓超额效果</div>
                <div className={`text-base font-extrabold mt-1 ${shadowExcessPct >= 0 ? 'text-red-600' : 'text-emerald-700'}`}>
                  {shadowExcessPct >= 0 ? '+' : ''}
                  {shadowExcessPct.toFixed(2)}%
                </div>
              </div>
            </div>
          ) : (
            <div className="p-3.5 rounded-xl bg-slate-50 border border-dashed border-slate-300 text-xs text-slate-500">
              尚未记录对比基准。建议在你准备参照「调仓参考方案」操作前，先点击右上角按钮留存一份调整前快照。
            </div>
          )}
        </div>

        {/* #5 极端行情压力测试 */}
        <div className="card-elevated rounded-2xl p-5 space-y-3">
          <div className="flex items-center justify-between gap-2">
            <div className="flex items-center gap-2">
              <ShieldAlert className="w-4 h-4 text-rose-600" />
              <h3 className="text-sm font-bold text-slate-900">极端行情压力测试（组合承压估算）</h3>
            </div>
            {cvar99 !== null && (
              <span className="text-[11px] font-semibold px-2 py-0.5 rounded-full bg-rose-50 text-rose-700 tabular-nums">
                99% 极端尾部风险 CVaR -{Math.abs(cvar99).toFixed(1)}%
              </span>
            )}
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs tabular-nums">
              <thead>
                <tr className="border-b border-slate-200 text-slate-500">
                  <th className="py-2 pr-2 font-semibold">历史极端情景</th>
                  <th className="py-2 px-2 text-right font-semibold">组合预估最大回撤</th>
                  <th className="py-2 pl-2 text-right font-semibold">预估最大浮亏金额</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {stressScenarios.map((sc) => (
                  <tr key={sc.name}>
                    <td className="py-2 pr-2">
                      <div className="font-medium text-slate-800">{sc.name}</div>
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

      {/* 持仓明细 / 净值估值对账表 */}
      <section className="card-elevated rounded-2xl overflow-hidden">
        <div className="p-4 sm:px-5 border-b border-slate-200 flex flex-wrap items-center justify-between gap-3">
          <div className="flex flex-wrap items-center gap-3">
            <div className="flex items-center gap-2">
              <span className="w-1 h-4 rounded-full bg-[#0A192F]" />
              <h2 id={tableCaptionId} className="text-base font-bold text-slate-900">
                {tableView === 'holdings' ? `持仓明细（${filtered.length} / ${holdings.length} 只）` : `净值估值对账（${filtered.length} 只）`}
              </h2>
            </div>
            <div className="inline-flex items-center gap-1 bg-slate-100 p-0.5 rounded-lg border border-slate-200">
              <button
                type="button"
                onClick={() => setTableView('holdings')}
                className={`px-2.5 py-1 rounded-md text-xs font-semibold cursor-pointer ${
                  tableView === 'holdings' ? 'bg-white text-slate-900 shadow-xs' : 'text-slate-500'
                }`}
              >
                持仓明细
              </button>
              <button
                type="button"
                onClick={() => setTableView('reconcile')}
                className={`px-2.5 py-1 rounded-md text-xs font-semibold cursor-pointer ${
                  tableView === 'reconcile' ? 'bg-white text-slate-900 shadow-xs' : 'text-slate-500'
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
                placeholder="搜索代码或基金名..."
                aria-label="搜索持仓基金"
                className="h-8 pl-8 pr-3 rounded-lg text-xs bg-slate-50 border border-slate-200 focus:border-blue-600 focus:bg-white focus:outline-none w-40 sm:w-44"
              />
            </div>
            <select
              value={tierFilter}
              onChange={(e) => setTierFilter(e.target.value as 'all' | 'core' | 'tail')}
              aria-label="按市值筛选持仓"
              className="h-8 px-2.5 rounded-lg text-xs bg-slate-50 border border-slate-200 text-slate-700 cursor-pointer"
            >
              <option value="all">全部持仓</option>
              <option value="core">核心持仓 (≥¥500)</option>
              <option value="tail">碎片尾仓 (&lt;¥200)</option>
            </select>
            <button
              type="button"
              onClick={handleExportCsv}
              className="h-8 px-2.5 rounded-lg text-xs font-medium border border-slate-200 bg-white text-slate-700 hover:bg-slate-50 inline-flex items-center gap-1 cursor-pointer"
            >
              <Download className="w-3.5 h-3.5" />
              <span>导出 CSV</span>
            </button>
          </div>
        </div>

        <div tabIndex={0} role="region" aria-labelledby={tableCaptionId} className="table-wrapper">
          {tableView === 'holdings' ? (
            <table className="text-left text-xs">
              <thead>
                <tr className="border-b border-slate-200 text-slate-500 bg-slate-50">
                  <th scope="col" className="py-3 px-4 font-semibold whitespace-nowrap">基金名称 / 代码</th>
                  <th scope="col" className="py-3 px-4 font-semibold whitespace-nowrap">资产大类</th>
                  <th scope="col" className="py-3 px-4 font-semibold text-right whitespace-nowrap">当前市值 / 份额</th>
                  <th scope="col" className="py-3 px-4 font-semibold text-right whitespace-nowrap">今日涨跌</th>
                  <th scope="col" className="py-3 px-4 font-semibold text-right whitespace-nowrap">累计盈亏</th>
                  <th scope="col" className="py-3 px-4 font-semibold whitespace-nowrap">持有天数 / 赎回费</th>
                  <th scope="col" className="py-3 px-4 font-semibold text-right whitespace-nowrap">操作</th>
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
                    const dayChg = Number(
                      h.is_official_nav && h.official_chg_pct !== null && h.official_chg_pct !== undefined
                        ? h.official_chg_pct
                        : (h.est_chg_pct ?? 0)
                    );
                    const cumPct = Number(h.floating_pnl_pct ?? 0);
                    const mv = Number(h.market_value ?? 0);
                    const isEditing = editingCode === h.fund_code;

                    return (
                      <tr key={h.fund_code} className="hover:bg-slate-50/80 transition-colors">
                        <th scope="row" className="py-3 px-4 font-normal">
                          <button
                            type="button"
                            onClick={() => onSelectFund(h.fund_code)}
                            className="text-left group cursor-pointer"
                          >
                            <div className="font-semibold text-slate-900 group-hover:text-blue-700 group-hover:underline whitespace-nowrap">
                              {h.fund_name}
                            </div>
                            <div className="text-slate-400 font-mono text-[11px]">{h.fund_code}</div>
                          </button>
                        </th>
                        <td className="py-3 px-4 whitespace-nowrap">
                          <span className="px-2 py-0.5 rounded-md bg-slate-100 text-slate-600 text-[11px]">
                            {h.asset_class || `${h.share_class || 'A'}类基金`}
                          </span>
                        </td>
                        <td className="py-3 px-4 text-right tabular-nums whitespace-nowrap">
                          {isEditing ? (
                            <div className="flex items-center justify-end gap-1.5">
                              <input
                                type="number"
                                step="0.01"
                                value={editShares}
                                onChange={(e) => setEditShares(e.target.value)}
                                aria-label="编辑持有份额"
                                className="w-20 h-7 px-2 rounded border border-blue-400 text-right text-xs"
                                placeholder="份额"
                              />
                              <input
                                type="number"
                                step="0.0001"
                                value={editCost}
                                onChange={(e) => setEditCost(e.target.value)}
                                aria-label="编辑持仓成本"
                                className="w-20 h-7 px-2 rounded border border-blue-400 text-right text-xs"
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
                        <td
                          className={`py-3 px-4 text-right font-bold tabular-nums whitespace-nowrap ${
                            dayChg >= 0 ? 'text-red-600' : 'text-emerald-600'
                          }`}
                        >
                          {dayChg >= 0 ? '+' : ''}
                          {dayChg.toFixed(2)}%
                        </td>
                        <td
                          className={`py-3 px-4 text-right font-bold tabular-nums whitespace-nowrap ${
                            cumPct >= 0 ? 'text-red-600' : 'text-emerald-600'
                          }`}
                        >
                          {cumPct >= 0 ? '+' : ''}
                          {cumPct.toFixed(2)}%
                        </td>
                        <td className="py-3 px-4 whitespace-nowrap">
                          <span className="font-medium text-slate-800">{h.holding_days ?? 0}天</span>
                          <span
                            className={`ml-1.5 px-2 py-0.5 rounded-full text-[11px] ${
                              mv < 200 ? 'bg-amber-50 text-amber-700' : 'bg-slate-100 text-slate-600'
                            }`}
                          >
                            {h.redemption_fee_status?.label || '正常'}
                          </span>
                        </td>
                        <td className="py-3 px-4 text-right whitespace-nowrap">
                          {isEditing ? (
                            <div className="inline-flex items-center gap-1.5">
                              <button
                                type="button"
                                disabled={savingEdit}
                                onClick={() => handleSaveEdit(h)}
                                className="p-1 rounded bg-blue-600 text-white hover:bg-blue-700 cursor-pointer"
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
                <tr className="border-b border-slate-200 text-slate-500 bg-slate-50">
                  <th scope="col" className="py-3 px-4 font-semibold whitespace-nowrap">基金名称 / 代码</th>
                  <th scope="col" className="py-3 px-4 font-semibold text-right whitespace-nowrap">最新单位净值</th>
                  <th scope="col" className="py-3 px-4 font-semibold text-right whitespace-nowrap">盘中估算涨跌</th>
                  <th scope="col" className="py-3 px-4 font-semibold text-right whitespace-nowrap">官方公布涨跌</th>
                  <th scope="col" className="py-3 px-4 font-semibold text-right whitespace-nowrap">估值误差</th>
                  <th scope="col" className="py-3 px-4 font-semibold whitespace-nowrap">数据状态</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {filtered.map((h) => {
                  const est = Number(h.est_chg_pct ?? 0);
                  const hasOff = h.is_official_nav && h.official_chg_pct !== null && h.official_chg_pct !== undefined;
                  const off = hasOff ? Number(h.official_chg_pct) : null;
                  const diff = off !== null ? est - off : null;
                  return (
                    <tr key={h.fund_code} className="hover:bg-slate-50/80">
                      <th scope="row" className="py-3 px-4 font-normal">
                        <div className="font-semibold text-slate-900 whitespace-nowrap">{h.fund_name}</div>
                        <div className="text-slate-400 font-mono text-[11px]">{h.fund_code}</div>
                      </th>
                      <td className="py-3 px-4 text-right font-mono text-slate-800">{Number(h.current_nav ?? 0).toFixed(4)}</td>
                      <td className={`py-3 px-4 text-right font-semibold ${est >= 0 ? 'text-red-600' : 'text-emerald-600'}`}>
                        {est >= 0 ? '+' : ''}
                        {est.toFixed(2)}%
                      </td>
                      <td className={`py-3 px-4 text-right font-bold ${off === null ? 'text-slate-400' : off >= 0 ? 'text-red-600' : 'text-emerald-600'}`}>
                        {off === null ? '待公布' : `${off >= 0 ? '+' : ''}${off.toFixed(2)}%`}
                      </td>
                      <td className="py-3 px-4 text-right text-slate-600">
                        {diff === null ? '--' : `${diff >= 0 ? '+' : ''}${diff.toFixed(2)}%`}
                      </td>
                      <td className="py-3 px-4 whitespace-nowrap">
                        <span
                          className={`px-2 py-0.5 rounded-full text-[11px] font-medium ${
                            hasOff ? 'bg-emerald-50 text-emerald-700' : 'bg-blue-50 text-blue-700'
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
  );
}

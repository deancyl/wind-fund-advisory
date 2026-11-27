import { useEffect, useMemo, useState } from 'react';
import { Copy, Check, RefreshCw, ChevronDown, ChevronRight, CalendarClock, Coins, Calculator, Clock, ShieldCheck } from 'lucide-react';
import { api, type CutoffQuickBriefResponse, type DividendAdviceResponse, type RebalanceItem, type RebalanceResponse } from '../api/client';
import { useWorkbench } from '../context/WorkbenchContext';

export function RebalancePage() {
  const {
    activeLedgerId,
    currentLedger,
    refreshTick,
    targetReturnPct,
    horizonMonths,
    setGoal,
    setActiveTab,
    solvedContext,
    openDataCenter,
    openInspector,
    pushToast,
  } = useWorkbench();

  const [data, setData] = useState<RebalanceResponse | null>(null);
  const [cutoffBrief, setCutoffBrief] = useState<CutoffQuickBriefResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [targetSource, setTargetSource] = useState<'ledger_smooth' | 'full_market_solved'>('ledger_smooth');
  const [checkedSet, setCheckedSet] = useState<Set<string>>(new Set());
  const [saveStatus, setSaveStatus] = useState<'idle' | 'saving' | 'saved' | 'error'>('idle');
  const [lastSavedTime, setLastSavedTime] = useState('');
  const [copied, setCopied] = useState(false);
  const [showHold, setShowHold] = useState(false);
  const [showTails, setShowTails] = useState(false);

  // 增量定投（DCA）
  const [dcaAmount, setDcaAmount] = useState(3000);
  const [dcaSummary, setDcaSummary] = useState('');
  const [dcaLoading, setDcaLoading] = useState(false);
  const [dcaItems, setDcaItems] = useState<Array<{ fund_code: string; fund_name: string; amount: number; weight_pct?: number; reason?: string }>>([]);
  const [divAdvice, setDivAdvice] = useState<DividendAdviceResponse | null>(null);

  // A/C 类份额费率精算器（从原 ProAnalysisDrawer 正式归位至调仓执行台）
  const [acAmount, setAcAmount] = useState(50000);
  const [acDays, setAcDays] = useState(180);
  const [acSubFee, setAcSubFee] = useState(0.15);
  const [acSalesFee, setAcSalesFee] = useState(0.4);

  const effTier = solvedContext.riskLevel || 'C3';
  const effModel = solvedContext.modelId || 'all_weather';
  const effFundCount = solvedContext.fundCount || 6;
  const effUniverse = solvedContext.universeMode || 'full_market';
  const exKey = (solvedContext.excludeCodes || []).join(',');
  const inKey = (solvedContext.includeCodes || []).join(',');

  useEffect(() => {
    if (!activeLedgerId) return;
    let alive = true;
    setLoading(true);
    Promise.all([
      api.getRebalance(activeLedgerId, targetReturnPct, horizonMonths, {
        tier: effTier,
        targetSource,
        model: effModel,
        fundCount: effFundCount,
        universeMode: effUniverse,
        excludeCodes: exKey ? exKey.split(',') : undefined,
        includeCodes: inKey ? inKey.split(',') : undefined,
      }),
      api.getCheckin(),
      api.getDividendAdvice(activeLedgerId).catch(() => null),
      api.getCutoffBrief(activeLedgerId, targetReturnPct).catch(() => null),
    ])
      .then(([reb, chk, divRes, briefRes]) => {
        if (!alive) return;
        setData(reb);
        if (divRes) setDivAdvice(divRes);
        if (briefRes) setCutoffBrief(briefRes);
        const codes = new Set<string>();
        const rawMap = chk?.checked_codes || {};
        for (const [k, v] of Object.entries(rawMap)) {
          if (v === true || (typeof v === 'object' && v !== null && v.checked !== false)) {
            codes.add(k);
          }
        }
        setCheckedSet(codes);
      })
      .catch(() => {})
      .finally(() => {
        if (alive) setLoading(false);
      });
    return () => {
      alive = false;
    };
  }, [activeLedgerId, refreshTick, targetReturnPct, horizonMonths, effTier, targetSource, effModel, effFundCount, effUniverse, exKey, inKey]);

  useEffect(() => {
    if (!activeLedgerId) return;
    let alive = true;
    const t = setTimeout(() => {
      setDcaLoading(true);
      api
        .planCashflow(Math.max(500, dcaAmount || 3000), activeLedgerId)
        .then((res) => {
          if (!alive) return;
          const raw = (res.dca_plan || {}) as Record<string, unknown>;
          setDcaSummary(String(raw.summary_text || raw.advice_summary || ''));
          const list = (raw.allocations || raw.monthly_allocations || raw.items || []) as Array<Record<string, unknown>>;
          setDcaItems(
            list.slice(0, 6).map((x) => {
              const code = String(x.fund_code || x['基金代码'] || x.code || '');
              const name = String(x.fund_name || x['基金名称'] || x.name || code);
              const amt = Number(x.monthly_amount ?? x['每月定投金额(元)'] ?? x.amount ?? x.buy_amount ?? 0);
              const pctRaw = x.target_weight_pct ?? x['目标配置占比'] ?? x.weight_pct;
              const pct = pctRaw !== undefined ? Number(String(pctRaw).replace('%', '')) : undefined;
              return {
                fund_code: code,
                fund_name: name,
                amount: amt,
                weight_pct: Number.isFinite(pct) ? pct : undefined,
                reason: String(x.reason || x.note || '优先补齐低配核心底仓'),
              };
            })
          );
        })
        .catch(() => {})
        .finally(() => {
          if (alive) setDcaLoading(false);
        });
    }, 180);
    return () => {
      alive = false;
      clearTimeout(t);
    };
  }, [dcaAmount, activeLedgerId, refreshTick]);

  const actionableList = useMemo(() => {
    if (!data) return [];
    const out: Array<{ group: string; item: RebalanceItem; code: string; name: string; amount: number }> = [];
    const pushGroup = (gName: string, items: RebalanceItem[]) => {
      for (const it of items || []) {
        const code = String(it.fund_code || it.code || '');
        const name = String(it.fund_name || it.name || code);
        const amt = Number(it.diff_amount ?? it.amount ?? 0);
        out.push({ group: gName, item: it, code, name, amount: amt });
      }
    };
    pushGroup('C转A省费', data.c_replace?.items || []);
    pushGroup('核心调仓', data.core_trades?.items || []);
    pushGroup('清理尾仓', data.tail_sweep?.items || []);
    return out;
  }, [data]);

  const toggleCheck = async (code: string, amount: number) => {
    const prev = new Set(checkedSet);
    const next = new Set(checkedSet);
    const nextChecked = !next.has(code);
    if (nextChecked) next.add(code);
    else next.delete(code);
    setCheckedSet(next);
    setSaveStatus('saving');
    try {
      const action = amount > 0 ? 'BUY' : 'SELL';
      await api.saveCheckinItem(code, action, Math.abs(amount), nextChecked);
      const nowStr = new Date().toLocaleTimeString('zh-CN', { hour12: false });
      setLastSavedTime(nowStr);
      setSaveStatus('saved');
      pushToast(nextChecked ? `已勾选 ${code} 并保存至本机（${nowStr}）` : `已取消勾选 ${code}`, 'success');
    } catch (e) {
      setCheckedSet(prev);
      setSaveStatus('error');
      pushToast(e instanceof Error ? `保存失败：${e.message}` : '保存勾选状态失败', 'error');
    }
  };

  const handleCopy = async () => {
    const text = data?.cheat_sheet_text || '今日无需买卖操作。';
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      pushToast('已复制调仓参考清单到剪贴板', 'success');
      setTimeout(() => setCopied(false), 2000);
    } catch {
      pushToast('复制失败，请手动选中复制', 'warning');
    }
  };

  if (loading) {
    return <div className="inst-panel rounded-lg p-10 text-center text-xs text-slate-400">正在测算调仓参考方案...</div>;
  }

  if (data?.is_empty || (currentLedger && currentLedger.holding_count === 0)) {
    return (
      <div className="inst-panel rounded-lg p-8 sm:p-10 text-center space-y-4 fade-in" data-testid="rebalance-empty-state">
        <div className="space-y-1.5 max-w-md mx-auto">
          <h2 className="text-sm font-bold text-slate-900">
            当前账本「{currentLedger?.name || activeLedgerId}」暂无实盘持仓
          </h2>
          <p className="text-xs text-slate-500 leading-relaxed">
            调仓执行台需要基于您当前的真实持仓测算偏差、清理碎片尾仓与 C 转 A 省费。请先导入已有持仓，或直接前往量化实验室生成新资金配置蓝图。
          </p>
        </div>
        <div className="flex flex-wrap items-center justify-center gap-2.5">
          <button
            type="button"
            onClick={() => openDataCenter('import')}
            className="h-8 px-4 rounded-md text-xs font-semibold bg-[#0A1628] text-white hover:bg-slate-800 cursor-pointer"
          >
            导入实盘持仓（文本 / 截图 OCR）
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('quant_lab')}
            className="h-8 px-4 rounded-md text-xs font-semibold bg-white border border-slate-300 text-slate-700 hover:bg-slate-50 cursor-pointer"
          >
            前往量化实验室建仓
          </button>
        </div>
      </div>
    );
  }

  const tailCount = data?.tail_sweep?.count || 0;
  const tailCash = data?.tail_sweep?.recovered_cash || 0;
  const cCount = data?.c_replace?.count || 0;
  const coreCount = data?.core_trades?.count || 0;
  const holdCount = data?.buffer_hold?.count || 0;
  const doneCount = actionableList.filter((x) => checkedSet.has(x.code)).length;

  const breakEvenDays = acSalesFee > 0 ? Math.round((acSubFee / acSalesFee) * 365) : 365;
  const costA = (acAmount * acSubFee) / 100;
  const costC = (acAmount * (acSalesFee / 100) * acDays) / 365;
  const recommendA = acDays >= breakEvenDays;

  return (
    <div className="space-y-4 fade-in" data-testid="rebalance-page">
      {/* 0. 14:30 尾盘实盘速决条（单行极简，复用 TradingClock 15:00 申赎生死线 + Top 3 动作） */}
      {cutoffBrief && (
        <section
          data-testid="cutoff-quick-brief-bar"
          className={`inst-panel rounded-xl px-4 py-3 border-l-4 flex flex-col lg:flex-row lg:items-center justify-between gap-3 text-xs ${
            cutoffBrief.is_golden_window
              ? 'border-l-amber-500 bg-amber-50/40'
              : cutoffBrief.is_after_market || !cutoffBrief.is_trade_day
              ? 'border-l-slate-400'
              : 'border-l-blue-600'
          }`}
        >
          <div className="flex flex-wrap items-center gap-2.5 min-w-0">
            <span
              className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-md text-[11px] font-bold shrink-0 ${
                cutoffBrief.is_golden_window
                  ? 'bg-amber-500 text-[#0B192C]'
                  : cutoffBrief.is_after_market || !cutoffBrief.is_trade_day
                  ? 'bg-slate-800 text-white'
                  : 'bg-[#0B192C] text-white'
              }`}
            >
              <Clock className="w-3.5 h-3.5" />
              <span>{cutoffBrief.window_label}</span>
              {cutoffBrief.countdown_str && cutoffBrief.countdown_str !== '00:00' && cutoffBrief.countdown_str !== '--:--' && (
                <span className="font-mono ml-1 opacity-90">距15:00 {cutoffBrief.countdown_str}</span>
              )}
            </span>
            <span className="text-slate-700 leading-snug">
              生效成交日 <strong className="font-mono text-slate-900">{cutoffBrief.effective_trade_date}</strong> · {cutoffBrief.message}
            </span>
          </div>

          <div className="flex flex-wrap items-center gap-1.5 shrink-0">
            {cutoffBrief.priority_actions.length === 0 ? (
              <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md bg-emerald-50 border border-emerald-200 text-emerald-800 text-[11px] font-semibold">
                <ShieldCheck className="w-3.5 h-3.5" />
                今日无紧急动作，安心持有
              </span>
            ) : (
              cutoffBrief.priority_actions.map((act, idx) => (
                <button
                  key={`${act.tag}-${idx}`}
                  type="button"
                  onClick={() => act.fund_code && openInspector(act.fund_code)}
                  title={act.summary}
                  className={`px-2 py-1 rounded-md text-[11px] font-semibold border cursor-pointer transition-colors ${
                    act.tone === 'profit_lock'
                      ? 'bg-amber-50 border-amber-300 text-amber-900 hover:bg-amber-100'
                      : act.tone === 'buy'
                      ? 'bg-red-50 border-red-200 text-[#C81E1E] hover:bg-red-100'
                      : act.tone === 'sell'
                      ? 'bg-emerald-50 border-emerald-200 text-[#047857] hover:bg-emerald-100'
                      : 'bg-blue-50 border-blue-200 text-blue-800 hover:bg-blue-100'
                  }`}
                >
                  {act.tag}：{act.fund_name}
                </button>
              ))
            )}
          </div>
        </section>
      )}

      {/* 1. 顶部目标基准切换 + 一键复制 + 次日同步 */}
      <section className="inst-panel rounded-xl px-4 py-3.5 flex flex-col lg:flex-row lg:items-center justify-between gap-3">
        <div className="space-y-1">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-xs font-bold text-slate-900">调仓目标组合来源</span>
            <span className="px-1.5 py-0.5 rounded bg-slate-100 border border-slate-200 text-[10px] font-semibold text-slate-600">
              纯量化参考 · 本地不连券商
            </span>
          </div>
          <p className="text-xs text-slate-500">
            {data?.target_summary || '默认采用稳健低换手模式保护存量核心基金；可一键切换对齐量化实验室最新全市场方案。'}
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2 shrink-0">
          <div className="inline-flex items-center gap-0.5 bg-slate-100 p-0.5 rounded-md border border-slate-200" role="group" aria-label="调仓目标来源">
            <button
              type="button"
              onClick={() => setTargetSource('ledger_smooth')}
              className={`px-2.5 py-1.5 rounded text-xs font-semibold cursor-pointer ${
                targetSource === 'ledger_smooth' ? 'bg-[#0A1628] text-white' : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              稳健低换手（平滑调优·默认）
            </button>
            <button
              type="button"
              onClick={() => setTargetSource('full_market_solved')}
              data-testid="btn-rebalance-align-fullmarket"
              className={`px-2.5 py-1.5 rounded text-xs font-semibold cursor-pointer ${
                targetSource === 'full_market_solved' ? 'bg-blue-700 text-white' : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              对齐实验室方案（{effTier}·{effFundCount}只）
            </button>
          </div>

          <button
            type="button"
            onClick={() => void handleCopy()}
            className="h-8 px-3 rounded-md text-xs font-semibold bg-amber-500 text-[#0A1628] hover:bg-amber-400 inline-flex items-center gap-1.5 cursor-pointer"
          >
            {copied ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
            <span>{copied ? '已复制清单' : '复制参考清单'}</span>
          </button>
          <button
            type="button"
            onClick={() => openDataCenter('import')}
            className="h-8 px-3 rounded-md text-xs font-medium bg-white border border-slate-300 text-slate-700 hover:bg-slate-50 inline-flex items-center gap-1.5 cursor-pointer"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            <span>次日更新持仓</span>
          </button>
        </div>
      </section>

      {/* 2. 目标收益达成概率改善对比 + 3 步重构摘要（统一纯白硬边分栏） */}
      {data?.goal_comparison && (
        <section className="inst-panel rounded-lg overflow-hidden">
          <div className="px-4 py-3 border-b border-slate-200 bg-slate-50/70 flex flex-wrap items-center justify-between gap-2">
            <div className="text-xs font-bold text-slate-900">
              目标达成概率对比（调仓前 vs 调仓后 · {effTier} 档）
            </div>
            <div className="flex items-center gap-2 text-xs">
              <select
                value={horizonMonths}
                onChange={(e) => setGoal(targetReturnPct, Number(e.target.value))}
                aria-label="调仓目标周期"
                className="h-7 px-2 rounded bg-white border border-slate-300 font-semibold text-slate-700"
              >
                <option value={6}>6 个月</option>
                <option value={12}>1 年</option>
                <option value={24}>2 年</option>
                <option value={36}>3 年</option>
              </select>
              <label className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-white border border-slate-300 font-semibold text-slate-700">
                <span>目标</span>
                <input
                  type="number"
                  min={2}
                  max={60}
                  step={1}
                  value={targetReturnPct}
                  onChange={(e) => setGoal(Number(e.target.value) || 10, horizonMonths)}
                  aria-label="调仓目标收益率百分比"
                  className="w-12 h-5 text-center font-bold text-blue-700 tabular-nums focus:outline-none"
                />
                <span>%</span>
              </label>
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 divide-y sm:divide-y-0 sm:divide-x divide-slate-200 text-xs tabular-nums">
            <div className="p-4">
              <div className="text-[11px] text-slate-500">调仓前 · 历史达标概率</div>
              <div className="text-xl font-extrabold text-slate-800 mt-1">
                {data.goal_comparison.before.historical_hit_rate_pct.toFixed(1)}%
              </div>
              <div className="text-[11px] text-slate-400 mt-0.5">
                P05 最差情景：{data.goal_comparison.before.p05_worst_return_pct.toFixed(2)}%
              </div>
            </div>
            <div className="p-4">
              <div className="text-[11px] text-slate-500">调仓后 · 历史达标概率</div>
              <div className="text-xl font-extrabold text-blue-700 mt-1">
                {data.goal_comparison.after.historical_hit_rate_pct.toFixed(1)}%
              </div>
              <div className="text-[11px] text-slate-500 mt-0.5">
                P05 最差情景：{data.goal_comparison.after.p05_worst_return_pct.toFixed(2)}%
              </div>
            </div>
            <div className="p-4 bg-slate-50/40">
              <div className="text-[11px] text-slate-500">调仓量化改善幅度</div>
              <div
                className={`text-xl font-extrabold mt-1 ${
                  data.goal_comparison.hit_rate_delta_pct >= 0 ? 'text-red-600' : 'text-emerald-700'
                }`}
              >
                {data.goal_comparison.hit_rate_delta_pct >= 0 ? '+' : ''}
                {data.goal_comparison.hit_rate_delta_pct.toFixed(1)}%
              </div>
              <div className="text-[11px] text-slate-500 mt-0.5">
                底线改善 {data.goal_comparison.worst_return_delta_pct >= 0 ? '+' : ''}
                {data.goal_comparison.worst_return_delta_pct.toFixed(2)}%
              </div>
            </div>
          </div>

          {data.goal_comparison.hit_rate_delta_pct < 0 && (
            <div
              data-testid="rebalance-tradeoff-note"
              className="px-4 py-2.5 border-t border-slate-200 bg-amber-50/50 flex flex-wrap items-center justify-between gap-2 text-[11px] text-amber-950"
            >
              <span>
                <strong>归因说明：</strong>
                {targetSource === 'ledger_smooth'
                  ? '当前「稳健低换手」模式优先压缩交易摩擦、清理尾仓并控制回撤底线（P05 改善），因此历史达标率略低于原高弹性持仓；若追求更高达标率，可一键切换对齐量化实验室全市场方案。'
                  : '新目标方案以风控均衡与回撤底线为优先约束，降低了高波动单一赛道的弹性暴露，历史达标率小幅收敛属风控取舍。'}
              </span>
              {targetSource === 'ledger_smooth' && (
                <button
                  type="button"
                  onClick={() => setTargetSource('full_market_solved')}
                  className="px-2.5 py-1 rounded bg-blue-700 text-white font-semibold hover:bg-blue-800 shrink-0 cursor-pointer"
                >
                  切换对齐实验室方案
                </button>
              )}
            </div>
          )}
        </section>
      )}

      {/* 3 步重构摘要条 */}
      <section className="inst-panel rounded-lg grid grid-cols-1 md:grid-cols-3 divide-y md:divide-y-0 md:divide-x divide-slate-200 tabular-nums">
        <div className="p-4">
          <div className="flex items-center justify-between text-[11px] text-slate-500">
            <span className="font-bold text-slate-700">STEP 01 · 清理碎片尾仓</span>
            <span className="font-mono font-semibold">{tailCount} 只</span>
          </div>
          <div className="text-base font-extrabold text-slate-900 mt-1">
            {tailCount > 0 ? `回收 ¥${tailCash.toLocaleString('zh-CN', { minimumFractionDigits: 2 })}` : '暂无碎片尾仓'}
          </div>
          <p className="text-[11px] text-slate-500 mt-0.5">
            {tailCount > 0 ? '单只不足 ¥200 且满免赎期，清仓归拢' : '持仓精简整洁，无需清理'}
          </p>
        </div>

        <div className="p-4">
          <div className="flex items-center justify-between text-[11px] text-slate-500">
            <span className="font-bold text-slate-700">STEP 02 · C 转 A 省管理费</span>
            <span className="font-mono font-semibold">{cCount} 笔</span>
          </div>
          <div className="text-base font-extrabold text-slate-900 mt-1">
            {cCount > 0 ? '年省 0.40% 服务费' : '暂无高费 C 类置换'}
          </div>
          <p className="text-[11px] text-slate-500 mt-0.5">
            {cCount > 0 ? '满 30 天免赎回费置换同款 A 类' : '当前份额类别结构合理'}
          </p>
        </div>

        <div className="p-4">
          <div className="flex items-center justify-between text-[11px] text-slate-500">
            <span className="font-bold text-slate-700">STEP 03 · 核心仓位再平衡</span>
            <span className="font-mono font-semibold">{coreCount} 笔</span>
          </div>
          <div className="text-base font-extrabold text-slate-900 mt-1">
            {coreCount > 0 ? '对齐今日目标仓位' : '核心仓位在安全缓冲内'}
          </div>
          <p className="text-[11px] text-slate-500 mt-0.5">
            {coreCount > 0 ? '高抛超配、低吸欠配，控制偏离' : `其余 ${holdCount} 只核心标的安心持有`}
          </p>
        </div>
      </section>

      {/* 3. 执行清单主表（带本地勾选持久化） */}
      <section className="inst-panel rounded-lg overflow-hidden">
        <div className="px-4 py-3 border-b border-slate-200 bg-slate-50/70 flex flex-wrap items-center justify-between gap-2">
          <div>
            <h2 className="text-xs font-bold text-slate-900">建议调整执行清单（勾选记录已在 App 手动完成的笔数）</h2>
          </div>
          <div className="flex items-center gap-2 text-xs">
            {saveStatus === 'saving' && <span className="text-slate-500">正在保存...</span>}
            {saveStatus === 'saved' && (
              <span className="text-[11px] font-semibold px-2 py-0.5 rounded bg-emerald-50 text-emerald-700 border border-emerald-200 inline-flex items-center gap-1">
                <Check className="w-3 h-3" />
                已保存至本机 {lastSavedTime}
              </span>
            )}
            {saveStatus === 'error' && (
              <span className="text-[11px] font-semibold px-2 py-0.5 rounded bg-red-50 text-red-700 border border-red-200">
                保存失败
              </span>
            )}
            <span className="text-[11px] font-mono font-semibold px-2.5 py-0.5 rounded bg-white border border-slate-200 text-slate-700 tabular-nums">
              已打卡 {doneCount} / {actionableList.length}
            </span>
          </div>
        </div>

        {actionableList.length === 0 ? (
          <div className="p-8 text-center text-xs text-slate-500">当前组合处于目标安全缓冲区内，今日无需买卖操作。</div>
        ) : (
          <div className="divide-y divide-slate-100">
            {actionableList
              .filter((x) => x.group !== '清理尾仓')
              .map(({ group, item, code, name, amount }) => {
                const isBuy = amount > 0;
                const done = checkedSet.has(code);
                return (
                  <label
                    key={`${group}-${code}`}
                    className={`px-4 py-3 flex items-start gap-3 cursor-pointer hover:bg-blue-50/30 transition-colors ${
                      done ? 'opacity-55 bg-slate-50/60' : ''
                    }`}
                  >
                    <input
                      type="checkbox"
                      checked={done}
                      onChange={() => void toggleCheck(code, amount)}
                      className="mt-0.5 w-4 h-4 accent-[#0A1628]"
                    />
                    <div className="flex-1 min-w-0 space-y-1">
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <div className="flex flex-wrap items-center gap-1.5">
                          <span className="px-1.5 py-0.5 rounded text-[10px] font-semibold bg-slate-100 text-slate-600">{group}</span>
                          <span
                            className={`px-1.5 py-0.5 rounded text-[10px] font-bold border ${
                              isBuy ? 'bg-red-50 text-red-700 border-red-200' : 'bg-emerald-50 text-emerald-700 border-emerald-200'
                            }`}
                          >
                            {isBuy ? '买入增配' : '卖出减仓'}
                          </span>
                          <button
                            type="button"
                            onClick={(e) => {
                              e.preventDefault();
                              openInspector(code);
                            }}
                            className={`font-bold text-xs text-slate-900 hover:text-blue-700 hover:underline cursor-pointer ${done ? 'line-through' : ''}`}
                          >
                            {name} <span className="font-mono text-[11px] text-slate-400">({code})</span>
                          </button>
                        </div>
                        <span className="font-extrabold text-sm text-slate-900 tabular-nums">
                          ¥{Math.abs(amount).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                        </span>
                      </div>
                      <p className="text-[11px] text-slate-500">
                        {item.reason || (isBuy ? '当前权重低于量化目标，建议补齐' : '当前权重偏高或风格重叠，建议适度减配')}
                      </p>
                    </div>
                  </label>
                );
              })}

            {tailCount > 0 && (
              <div>
                <button
                  type="button"
                  onClick={() => setShowTails(!showTails)}
                  className="w-full px-4 py-2.5 flex items-center justify-between text-xs font-semibold text-amber-900 bg-amber-50/40 hover:bg-amber-50 cursor-pointer"
                >
                  <span className="inline-flex items-center gap-1.5">
                    {showTails ? <ChevronDown className="w-3.5 h-3.5" /> : <ChevronRight className="w-3.5 h-3.5" />}
                    展开 {tailCount} 只碎片尾仓清理清单（回收 ¥{tailCash.toLocaleString('zh-CN', { minimumFractionDigits: 2 })}）
                  </span>
                  <span className="text-[11px] text-amber-800">均满 7 天免惩罚费</span>
                </button>
                {showTails && (
                  <div className="divide-y divide-slate-100 bg-slate-50/40">
                    {actionableList
                      .filter((x) => x.group === '清理尾仓')
                      .map(({ code, name, amount }) => {
                        const done = checkedSet.has(code);
                        return (
                          <label
                            key={`tail-${code}`}
                            className={`px-4 py-2 flex items-center justify-between gap-3 cursor-pointer text-xs hover:bg-slate-100/70 ${
                              done ? 'opacity-50 line-through' : ''
                            }`}
                          >
                            <span className="flex items-center gap-2.5">
                              <input
                                type="checkbox"
                                checked={done}
                                onChange={() => void toggleCheck(code, amount)}
                                className="w-3.5 h-3.5 accent-[#0A1628]"
                              />
                              <span className="font-medium text-slate-800">{name}</span>
                              <span className="font-mono text-[11px] text-slate-400">{code}</span>
                            </span>
                            <span className="font-mono font-semibold text-emerald-700 tabular-nums">
                              卖出 ¥{Math.abs(amount).toFixed(2)}
                            </span>
                          </label>
                        );
                      })}
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {holdCount > 0 && (
          <div className="border-t border-slate-200">
            <button
              type="button"
              onClick={() => setShowHold(!showHold)}
              className="w-full px-4 py-2.5 flex items-center justify-between text-xs text-slate-500 hover:bg-slate-50 cursor-pointer"
            >
              <span className="inline-flex items-center gap-1.5">
                {showHold ? <ChevronDown className="w-3.5 h-3.5" /> : <ChevronRight className="w-3.5 h-3.5" />}
                维持不动的核心持仓（{holdCount} 只，偏差在安全缓冲内）
              </span>
            </button>
            {showHold && (
              <div className="px-4 pb-3 flex flex-wrap gap-1.5">
                {(data?.buffer_hold?.items || []).map((it, idx) => (
                  <button
                    key={idx}
                    type="button"
                    onClick={() => openInspector(String(it.fund_code || it.code || ''))}
                    className="px-2 py-1 rounded bg-slate-100 hover:bg-blue-50 text-xs text-slate-700 cursor-pointer"
                  >
                    {it.fund_name || it.name} <span className="font-mono text-slate-400">{it.fund_code || it.code}</span>
                  </button>
                ))}
              </div>
            )}
          </div>
        )}
      </section>

      {/* 4. 增量新钱定投方案（DCA） */}
      <section className="inst-panel rounded-lg p-4 sm:p-5 space-y-3.5">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2.5">
          <div>
            <h2 className="text-xs font-bold text-slate-900">增量新钱补齐偏离（不卖老基金 · 智能定投）</h2>
            <p className="text-[11px] text-slate-500 mt-0.5">{dcaSummary || '输入本月新增资金，自动优先分配至低配核心底仓'}</p>
          </div>
          <label className="flex items-center gap-2 text-xs font-medium text-slate-600 shrink-0">
            <span>本月新增资金 (¥)</span>
            <input
              type="number"
              min={500}
              step={500}
              value={dcaAmount}
              onChange={(e) => setDcaAmount(Number(e.target.value))}
              className="w-28 h-8 px-2.5 rounded-md bg-white border border-slate-300 text-slate-900 font-bold tabular-nums text-xs focus:border-blue-600 focus:outline-none"
            />
          </label>
        </div>

        {dcaLoading && dcaItems.length === 0 ? (
          <div className="text-xs text-slate-400 py-2">正在计算增量定投分配方案...</div>
        ) : (
          <div className="overflow-x-auto border border-slate-200 rounded-md">
            <table className="w-full text-xs text-left tabular-nums">
              <thead>
                <tr className="border-b border-slate-200 bg-slate-50 text-slate-500">
                  <th className="py-2 px-3 font-semibold">补齐标的</th>
                  <th className="py-2 px-3 font-semibold text-right">建议定投金额</th>
                  <th className="py-2 px-3 font-semibold text-right">目标占比</th>
                  <th className="py-2 px-3 font-semibold">分配理由</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {dcaItems.map((d) => (
                  <tr
                    key={d.fund_code}
                    onClick={() => openInspector(d.fund_code)}
                    className="hover:bg-blue-50/30 cursor-pointer"
                  >
                    <td className="py-2 px-3">
                      <span className="font-semibold text-slate-900 hover:text-blue-700">{d.fund_name}</span>{' '}
                      <span className="font-mono text-[11px] text-slate-400">{d.fund_code}</span>
                    </td>
                    <td className="py-2 px-3 text-right font-bold text-slate-900">
                      ¥{d.amount.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                    </td>
                    <td className="py-2 px-3 text-right text-blue-700 font-semibold">
                      {d.weight_pct !== undefined ? `${d.weight_pct.toFixed(1)}%` : '--'}
                    </td>
                    <td className="py-2 px-3 text-slate-500">{d.reason}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {/* 5. 交易摩擦三合一：大额限购拆单 + 分红方式 + A/C 类份额费率精算器 */}
      <section className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* 大额限购拆单 */}
        <div className="inst-panel rounded-lg p-4 space-y-2.5">
          <div className="flex items-center gap-1.5">
            <CalendarClock className="w-4 h-4 text-slate-700" />
            <h2 className="text-xs font-bold text-slate-900">大额限购分批买入计划</h2>
          </div>
          {(data?.quota_split_plans || []).length === 0 ? (
            <p className="text-xs text-slate-500">当前买入清单暂无限购拆单需求，可单日完成配置。</p>
          ) : (
            <div className="space-y-2 text-xs">
              {(data?.quota_split_plans || []).map((q) => (
                <div key={q.fund_code} className="p-2.5 rounded bg-slate-50 border border-slate-200 space-y-1">
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-bold text-slate-900 truncate">{q.fund_name}</span>
                    <span
                      className={`px-1.5 py-0.5 rounded text-[10px] font-semibold shrink-0 ${
                        q.needs_split ? 'bg-amber-50 text-amber-800 border border-amber-200' : 'bg-emerald-50 text-emerald-700'
                      }`}
                    >
                      {q.needs_split ? `分 ${q.days_needed} 日` : '单日买完'}
                    </span>
                  </div>
                  <div className="text-[11px] text-slate-500 tabular-nums">
                    ¥{Number(q.total_amount || 0).toLocaleString()}
                    {q.daily_limit ? ` · 限额 ¥${Number(q.daily_limit).toLocaleString()}` : ''}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* 宏观分红方式建议 */}
        <div className="inst-panel rounded-lg p-4 space-y-2.5">
          <div className="flex items-center justify-between gap-2">
            <div className="flex items-center gap-1.5">
              <Coins className="w-4 h-4 text-slate-700" />
              <h2 className="text-xs font-bold text-slate-900">基金分红方式建议</h2>
            </div>
            {divAdvice && (
              <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-amber-50 text-amber-800 border border-amber-200">
                {divAdvice.recommended_label}
              </span>
            )}
          </div>
          <p className="text-xs text-slate-600 leading-relaxed">
            {divAdvice?.summary || '低估区间优先选择「红利再投资」免申购费滚份额，高估区间选择「现金分红」落袋为安。'}
          </p>
        </div>

        {/* A/C 类份额费率精算器（原抽屉归位） */}
        <div className="inst-panel rounded-lg p-4 space-y-2.5 text-xs">
          <div className="flex items-center justify-between gap-2">
            <div className="flex items-center gap-1.5">
              <Calculator className="w-4 h-4 text-blue-700" />
              <h2 className="text-xs font-bold text-slate-900">A / C 类份额费率对比器</h2>
            </div>
            <span className="text-[10px] font-mono text-slate-500">盈亏平衡点 {breakEvenDays} 天</span>
          </div>
          <div className="grid grid-cols-2 gap-2 tabular-nums">
            <label className="space-y-0.5">
              <span className="text-[10px] text-slate-500">投入金额 (¥)</span>
              <input
                type="number"
                value={acAmount}
                min={1000}
                step={5000}
                onChange={(e) => setAcAmount(Math.max(1000, Number(e.target.value) || 10000))}
                className="w-full h-7 px-2 rounded bg-slate-50 border border-slate-200 text-xs font-semibold"
              />
            </label>
            <label className="space-y-0.5">
              <span className="text-[10px] text-slate-500">预计持有 (天)</span>
              <input
                type="number"
                value={acDays}
                min={7}
                step={30}
                onChange={(e) => setAcDays(Math.max(7, Number(e.target.value) || 30))}
                className="w-full h-7 px-2 rounded bg-slate-50 border border-slate-200 text-xs font-semibold"
              />
            </label>
            <label className="space-y-0.5">
              <span className="text-[10px] text-slate-500">A类申购费 (%)</span>
              <input
                type="number"
                value={acSubFee}
                min={0}
                max={2}
                step={0.05}
                onChange={(e) => setAcSubFee(Math.max(0, Number(e.target.value) || 0))}
                className="w-full h-7 px-2 rounded bg-slate-50 border border-slate-200 text-xs font-semibold"
              />
            </label>
            <label className="space-y-0.5">
              <span className="text-[10px] text-slate-500">C类年服务费 (%)</span>
              <input
                type="number"
                value={acSalesFee}
                min={0}
                max={2}
                step={0.05}
                onChange={(e) => setAcSalesFee(Math.max(0, Number(e.target.value) || 0))}
                className="w-full h-7 px-2 rounded bg-slate-50 border border-slate-200 text-xs font-semibold"
              />
            </label>
          </div>
          <div className="p-2 rounded bg-slate-50 border border-slate-200 flex items-center justify-between tabular-nums">
            <span className="text-slate-600">
              A类 <strong>¥{costA.toFixed(1)}</strong> vs C类 <strong>¥{costC.toFixed(1)}</strong>
            </span>
            <span className="font-bold text-blue-700">
              {recommendA ? `优选 A类（省 ¥${(costC - costA).toFixed(1)}）` : `优选 C类（省 ¥${(costA - costC).toFixed(1)}）`}
            </span>
          </div>
        </div>
      </section>
    </div>
  );
}

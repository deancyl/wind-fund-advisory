import { useEffect, useMemo, useState } from 'react';
import type * as echarts from 'echarts';
import { X, Maximize2, Lock, Ban } from 'lucide-react';
import { api, type FundDetailResponse } from '../api/client';
import { useWorkbench } from '../context/WorkbenchContext';
import { EChartBox } from './EChartBox';

export function FundInspectorDrawer() {
  const {
    inspectorFundCode,
    inspectorFundMeta,
    closeInspector,
    openFullDetail,
    excludeCodes,
    includeCodes,
    toggleExcludeCode,
    toggleIncludeCode,
  } = useWorkbench();

  const [detail, setDetail] = useState<FundDetailResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState('');

  useEffect(() => {
    if (!inspectorFundCode) {
      setDetail(null);
      return;
    }
    let alive = true;
    setLoading(true);
    setErr('');
    api
      .getFundDetail(inspectorFundCode, 1000)
      .then((res) => {
        if (alive) setDetail(res);
      })
      .catch((e) => {
        if (alive) setErr(e instanceof Error ? e.message : '加载基金档案失败');
      })
      .finally(() => {
        if (alive) setLoading(false);
      });
    return () => {
      alive = false;
    };
  }, [inspectorFundCode]);

  useEffect(() => {
    if (!inspectorFundCode) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') closeInspector();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [inspectorFundCode, closeInspector]);

  const miniChartOption = useMemo<echarts.EChartsCoreOption>(() => {
    if (!detail?.charts?.dates?.length) return {};
    const { dates, ac_nav } = detail.charts;
    const total = dates.length;
    const lastTs = new Date(dates[total - 1]).getTime();
    const cutoff = lastTs - 365 * 86400 * 1000;
    let start = dates.findIndex((d) => new Date(d).getTime() >= cutoff);
    if (start < 0) start = 0;
    const sDates = dates.slice(start);
    const sAc = ac_nav.slice(start);
    const base = sAc[0] > 0 ? sAc[0] : 1;
    const sRet = sAc.map((v) => Number((((v / base) - 1) * 100).toFixed(2)));
    const last = sRet[sRet.length - 1] ?? 0;
    const color = last >= 0 ? '#DC2626' : '#059669';
    return {
      tooltip: {
        trigger: 'axis',
        backgroundColor: 'rgba(10,22,40,0.92)',
        borderWidth: 0,
        textStyle: { color: '#F8FAFC', fontSize: 11 },
        valueFormatter: (v: unknown) => `${Number(v) >= 0 ? '+' : ''}${Number(v).toFixed(2)}%`,
      },
      grid: { top: 14, left: 42, right: 12, bottom: 22 },
      xAxis: {
        type: 'category',
        data: sDates,
        boundaryGap: false,
        axisLabel: { color: '#64748B', fontSize: 10, formatter: (v: string) => v.slice(2, 7) },
      },
      yAxis: {
        type: 'value',
        scale: true,
        axisLabel: { color: '#64748B', fontSize: 10, formatter: '{value}%' },
        splitLine: { lineStyle: { color: '#F1F5F9' } },
      },
      series: [
        {
          type: 'line',
          data: sRet,
          showSymbol: false,
          lineStyle: { color, width: 2 },
          areaStyle: { color: last >= 0 ? 'rgba(220,38,38,0.08)' : 'rgba(5,150,105,0.08)' },
        },
      ],
    };
  }, [detail]);

  if (!inspectorFundCode) return null;

  const isLocked = includeCodes.includes(inspectorFundCode);
  const isExcluded = excludeCodes.includes(inspectorFundCode);
  const dayUp = (detail?.daily_return_pct ?? 0) >= 0;

  return (
    <div className="fixed inset-0 z-40 flex justify-end" data-testid="fund-inspector-drawer">
      <div
        className="fixed inset-0 bg-slate-900/35 backdrop-blur-[1px]"
        onClick={closeInspector}
        aria-hidden="true"
      />
      <aside
        aria-label="基金量化检查器"
        className="relative z-50 h-full w-full max-w-[520px] bg-white border-l border-slate-200 shadow-2xl flex flex-col slide-in-right"
      >
        {/* 头部 */}
        <div className="px-4 py-3.5 topbar-navy text-white flex items-start justify-between gap-2 shrink-0">
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <h2 className="font-bold text-sm text-white truncate">
                {detail?.fund_name || inspectorFundMeta?.fund_name || `基金 ${inspectorFundCode}`}
              </h2>
              <span className="font-mono text-xs text-slate-300 shrink-0">{inspectorFundCode}</span>
            </div>
            <div className="text-[11px] text-slate-300 mt-0.5 flex flex-wrap items-center gap-2">
              <span>{detail?.fund_type || inspectorFundMeta?.bucket_label || '公募基金'}</span>
              {detail?.profile?.scale_yi !== null && detail?.profile?.scale_yi !== undefined && (
                <span>· 规模 ¥{detail.profile.scale_yi} 亿</span>
              )}
              {detail?.profile?.company && <span>· {detail.profile.company}</span>}
            </div>
          </div>

          <div className="flex items-center gap-1 shrink-0">
            <button
              type="button"
              onClick={() => openFullDetail(inspectorFundCode)}
              data-testid="btn-inspector-fullscreen"
              title="展开完整 5 维基金档案"
              className="h-7 px-2 rounded text-[11px] font-semibold bg-white/10 hover:bg-white/20 text-slate-100 inline-flex items-center gap-1 cursor-pointer"
            >
              <Maximize2 className="w-3 h-3" />
              <span>完整档案</span>
            </button>
            <button
              type="button"
              onClick={closeInspector}
              aria-label="关闭基金检查器"
              className="w-7 h-7 rounded flex items-center justify-center text-slate-300 hover:text-white hover:bg-white/15 cursor-pointer"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* 快捷实验室约束操作条 */}
        <div className="px-4 py-2 border-b border-slate-200 bg-slate-50 flex flex-wrap items-center justify-between gap-2 text-xs shrink-0">
          <span className="text-[11px] text-slate-500">实验室约束控制（点击后立即重算）</span>
          <div className="flex items-center gap-1.5">
            <button
              type="button"
              onClick={() => toggleIncludeCode(inspectorFundCode, true)}
              className={`px-2.5 py-1 rounded text-[11px] font-semibold border inline-flex items-center gap-1 cursor-pointer ${
                isLocked
                  ? 'bg-blue-700 text-white border-blue-700'
                  : 'bg-white text-slate-700 border-slate-300 hover:border-blue-600 hover:text-blue-700'
              }`}
            >
              <Lock className="w-3 h-3" />
              <span>{isLocked ? '已锁定 · 取消' : '锁定必选'}</span>
            </button>
            <button
              type="button"
              onClick={() => toggleExcludeCode(inspectorFundCode, true)}
              className={`px-2.5 py-1 rounded text-[11px] font-semibold border inline-flex items-center gap-1 cursor-pointer ${
                isExcluded
                  ? 'bg-red-600 text-white border-red-600'
                  : 'bg-white text-slate-700 border-slate-300 hover:border-red-600 hover:text-red-600'
              }`}
            >
              <Ban className="w-3 h-3" />
              <span>{isExcluded ? '已排除 · 恢复' : '排除重算'}</span>
            </button>
          </div>
        </div>

        {/* 内容滚动区 */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-[#F8FAFC] text-xs">
          {/* 若在当前实验室方案中：直接展示量化配权归因公式 */}
          {inspectorFundMeta && (
            <section className="inst-panel rounded-lg p-3.5 space-y-2 border-l-4 border-l-blue-700">
              <div className="flex items-center justify-between">
                <span className="font-bold text-slate-900">当前实验室方案配权归因</span>
                <span className="font-mono text-[11px] font-bold text-blue-700 tabular-nums">
                  权重 {inspectorFundMeta.weight_pct.toFixed(1)}% · PCR {(inspectorFundMeta.risk_contribution_pcr_pct ?? inspectorFundMeta.weight_pct).toFixed(1)}%
                </span>
              </div>
              {inspectorFundMeta.allocation_breakdown?.allocation_formula_text && (
                <div className="px-2.5 py-1.5 rounded bg-slate-50 border border-slate-200 font-mono text-[11px] text-slate-700">
                  {inspectorFundMeta.allocation_breakdown.allocation_formula_text}
                </div>
              )}
              <p className="text-slate-600 leading-relaxed">{inspectorFundMeta.quant_reason || inspectorFundMeta.why}</p>
              {inspectorFundMeta.quota_note && (
                <div className="px-2.5 py-1.5 rounded bg-amber-50 border border-amber-200 text-[11px] text-amber-900">
                  限购提示：{inspectorFundMeta.quota_note}
                </div>
              )}
            </section>
          )}

          {loading && <div className="py-10 text-center text-slate-400">正在实时拉取基金净值、指标与前十大重仓...</div>}
          {err && <div className="p-3 rounded-md bg-red-50 border border-red-200 text-red-700">{err}</div>}

          {!loading && detail && (
            <>
              {/* 最新净值带 */}
              <section className="inst-panel rounded-lg grid grid-cols-3 divide-x divide-slate-200 tabular-nums">
                <div className="p-3">
                  <div className="text-[10px] text-slate-400">单位净值 ({detail.nav_date || '--'})</div>
                  <div className="text-base font-extrabold text-slate-900 mt-0.5">{detail.latest_nav.toFixed(4)}</div>
                </div>
                <div className="p-3">
                  <div className="text-[10px] text-slate-400">日涨跌幅</div>
                  <div className={`text-base font-extrabold mt-0.5 ${dayUp ? 'text-red-600' : 'text-emerald-700'}`}>
                    {dayUp ? '+' : ''}
                    {detail.daily_return_pct.toFixed(2)}%
                  </div>
                </div>
                <div className="p-3">
                  <div className="text-[10px] text-slate-400">累计净值</div>
                  <div className="text-base font-bold text-slate-700 mt-0.5">{detail.latest_ac_nav.toFixed(4)}</div>
                </div>
              </section>

              {/* 近 1 年收益走势图 */}
              <section className="inst-panel rounded-lg p-3.5 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="font-bold text-slate-900">近 1 年累计收益走势</span>
                  <span className="text-[10px] text-slate-400">{detail.risk_level}</span>
                </div>
                <EChartBox option={miniChartOption} height={190} />
              </section>

              {/* 关键历史业绩 */}
              {detail.historical_performance?.length > 0 && (
                <section className="inst-panel rounded-lg overflow-hidden">
                  <div className="px-3.5 py-2 border-b border-slate-200 bg-slate-50 font-bold text-slate-900">
                    阶段收益对比（vs 沪深 300）
                  </div>
                  <table className="w-full text-xs text-left tabular-nums">
                    <thead>
                      <tr className="border-b border-slate-100 text-slate-400 text-[11px]">
                        <th className="py-1.5 px-3 font-medium">区间</th>
                        <th className="py-1.5 px-3 font-medium text-right">本基金</th>
                        <th className="py-1.5 px-3 font-medium text-right">沪深300</th>
                        <th className="py-1.5 px-3 font-medium text-right">超额</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                      {detail.historical_performance.slice(0, 6).map((p) => (
                        <tr key={p.period}>
                          <td className="py-1.5 px-3 font-medium text-slate-700">{p.period}</td>
                          <td className={`py-1.5 px-3 text-right font-bold ${p.fund_return_pct >= 0 ? 'text-red-600' : 'text-emerald-700'}`}>
                            {p.fund_return_pct >= 0 ? '+' : ''}
                            {p.fund_return_pct.toFixed(2)}%
                          </td>
                          <td className="py-1.5 px-3 text-right text-slate-500">
                            {p.benchmark_return_pct !== null ? `${p.benchmark_return_pct >= 0 ? '+' : ''}${p.benchmark_return_pct.toFixed(2)}%` : '--'}
                          </td>
                          <td className="py-1.5 px-3 text-right font-semibold text-slate-700">
                            {p.excess_return_pct !== null ? `${p.excess_return_pct >= 0 ? '+' : ''}${p.excess_return_pct.toFixed(2)}%` : '--'}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </section>
              )}

              {/* 十大重仓前 6 */}
              {detail.holdings_distribution?.top_stocks?.length > 0 && (
                <section className="inst-panel rounded-lg overflow-hidden">
                  <div className="px-3.5 py-2 border-b border-slate-200 bg-slate-50 flex items-center justify-between">
                    <span className="font-bold text-slate-900">前十大重仓股票</span>
                    <span className="text-[10px] text-slate-400">{detail.holdings_distribution.quarter_label}</span>
                  </div>
                  <div className="divide-y divide-slate-100">
                    {detail.holdings_distribution.top_stocks.slice(0, 6).map((s) => (
                      <div key={s.stock_code} className="px-3.5 py-1.5 flex items-center justify-between tabular-nums">
                        <span className="text-slate-800 font-medium">
                          {s.stock_name} <span className="font-mono text-[10px] text-slate-400">{s.stock_code}</span>
                        </span>
                        <span className="font-mono font-bold text-slate-900">{s.weight_pct.toFixed(2)}%</span>
                      </div>
                    ))}
                  </div>
                </section>
              )}

              {/* 费率与交易规则摘要 */}
              <section className="inst-panel rounded-lg p-3.5 space-y-1.5 text-[11px] text-slate-600">
                <div className="font-bold text-xs text-slate-900">申赎状态与运作费率</div>
                <div className="grid grid-cols-2 gap-1.5">
                  <div>申购状态：<strong className="text-slate-900">{detail.trading_rules.purchase_status}</strong></div>
                  <div>赎回状态：<strong className="text-slate-900">{detail.trading_rules.redemption_status}</strong></div>
                  <div>管理费：<strong className="text-slate-900">{detail.trading_rules.management_fee}</strong></div>
                  <div>托管费：<strong className="text-slate-900">{detail.trading_rules.custody_fee}</strong></div>
                  <div>销售服务费：<strong className="text-slate-900">{detail.trading_rules.sales_service_fee}</strong></div>
                  <div>申购折扣：<strong className="text-slate-900">{detail.trading_rules.discount_rate}</strong></div>
                </div>
              </section>
            </>
          )}
        </div>
      </aside>
    </div>
  );
}

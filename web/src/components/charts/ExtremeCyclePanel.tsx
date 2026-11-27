import { useMemo, useState } from 'react';
import type * as echarts from 'echarts';
import type { ExtremeCycleAnalysis } from '../../api/client';
import { EChartBox } from '../EChartBox';
import { MetricTooltip } from '../MetricTooltip';

interface ExtremeCyclePanelProps {
  data?: ExtremeCycleAnalysis | null;
  loading?: boolean;
  targetReturnPct: number;
  horizonMonths: number;
}

export function ExtremeCyclePanel({
  data,
  loading,
  targetReturnPct,
  horizonMonths,
}: ExtremeCyclePanelProps) {
  const [subTab, setSubTab] = useState<'recovery' | 'cycles' | 'take_profit'>('recovery');

  const recoveryBarOption = useMemo<echarts.EChartsCoreOption>(() => {
    if (!data || data.status !== 'ready') return {};
    const events = data.historical_recovery.events || [];
    const labels = [
      ...events.map((e) => e.name.replace('贸易摩擦与去杠杆熊市', '去杠杆熊市').replace('全球疫情流动性冲击', '疫情冲击').replace('杀估值与加息熊市', '杀估值熊市').replace('年初微盘流动性危机', '微盘危机')),
      'MC 预计中位',
    ];
    const portDays = [
      ...events.map((e) => e.total_underwater_tdays),
      data.expected_recovery.peak_to_recovery_tdays.normal_median ?? data.expected_recovery.peak_to_recovery_tdays.median,
    ];
    const hs300Days = [
      ...events.map((e) => e.h300_total_underwater_tdays),
      data.expected_recovery.hs300_peak_to_recovery_median_tdays,
    ];

    return {
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'shadow' },
        backgroundColor: 'rgba(15,23,42,0.92)',
        borderWidth: 0,
        textStyle: { color: '#F8FAFC', fontSize: 12 },
        formatter: (params: unknown) => {
          const list = Array.isArray(params) ? params : [];
          if (!list.length) return '';
          const title = String((list[0] as { axisValue?: string }).axisValue || '');
          const lines = list.map((it) => {
            const item = it as { marker?: string; seriesName?: string; value?: number };
            const d = Number(item.value || 0);
            return `${item.marker || ''}${item.seriesName}: <strong>${d} 交易日</strong>（约 ${(d / 21).toFixed(1)} 个月）`;
          });
          return `<div style="font-weight:700;margin-bottom:4px">${title}</div>${lines.join('<br/>')}`;
        },
      },
      legend: { top: 0, right: 0, textStyle: { fontSize: 11, color: '#475569' } },
      grid: { top: 38, left: 52, right: 18, bottom: 38 },
      xAxis: {
        type: 'category',
        data: labels,
        axisLabel: { color: '#475569', fontSize: 11, interval: 0 },
      },
      yAxis: {
        type: 'value',
        name: '交易日',
        nameTextStyle: { color: '#64748B', fontSize: 11 },
        axisLabel: { color: '#64748B', fontSize: 11 },
        splitLine: { lineStyle: { color: '#F1F5F9' } },
      },
      series: [
        {
          name: '当前方案总水下修复天数',
          type: 'bar',
          barMaxWidth: 26,
          data: portDays,
          itemStyle: { color: '#1D4ED8', borderRadius: [5, 5, 0, 0] },
        },
        {
          name: '沪深 300 总水下修复天数',
          type: 'bar',
          barMaxWidth: 26,
          data: hs300Days,
          itemStyle: { color: '#94A3B8', borderRadius: [5, 5, 0, 0] },
        },
      ],
    };
  }, [data]);

  const cycleChartOption = useMemo<echarts.EChartsCoreOption>(() => {
    if (!data || data.status !== 'ready') return {};
    const items = (data.full_cycles.items || []).filter((c) => c.recovered);
    if (!items.length) return {};
    return {
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'shadow' },
        backgroundColor: 'rgba(15,23,42,0.92)',
        borderWidth: 0,
        textStyle: { color: '#F8FAFC', fontSize: 12 },
      },
      legend: { top: 0, left: 'center', textStyle: { fontSize: 11, color: '#475569' } },
      grid: { top: 48, left: 48, right: 54, bottom: 34 },
      xAxis: {
        type: 'category',
        data: items.map((c) => `${c.peak1_date.slice(0, 7)}→${c.next_peak_date.slice(0, 7)}`),
        axisLabel: { color: '#475569', fontSize: 10 },
      },
      yAxis: [
        {
          type: 'value',
          name: '收益率 (%)',
          nameTextStyle: { color: '#64748B', fontSize: 11 },
          axisLabel: { color: '#64748B', fontSize: 11, formatter: '{value}%' },
          splitLine: { lineStyle: { color: '#F1F5F9' } },
        },
        {
          type: 'value',
          name: '周期(月)',
          nameTextStyle: { color: '#64748B', fontSize: 11 },
          axisLabel: { color: '#64748B', fontSize: 11, formatter: '{value}月' },
          splitLine: { show: false },
        },
      ],
      series: [
        {
          name: '前高→新高净收益 (%)',
          type: 'bar',
          barMaxWidth: 22,
          data: items.map((c) => c.peak_to_next_peak_return_pct),
          itemStyle: { color: '#1D4ED8', borderRadius: [4, 4, 0, 0] },
        },
        {
          name: '低点→新高反弹收益 (%)',
          type: 'bar',
          barMaxWidth: 22,
          data: items.map((c) => c.trough_to_next_peak_return_pct),
          itemStyle: { color: '#DC2626', borderRadius: [4, 4, 0, 0] },
        },
        {
          name: '完整周期时长 (月)',
          type: 'line',
          yAxisIndex: 1,
          data: items.map((c) => c.full_cycle_months),
          lineStyle: { color: '#D97706', width: 2.5 },
          itemStyle: { color: '#D97706' },
          symbolSize: 7,
        },
      ],
    };
  }, [data]);

  if (loading && !data) {
    return (
      <section className="inst-panel rounded-lg p-8 text-center text-xs text-slate-400">
        正在基于 10,000 次蒙特卡洛与 2018–2026 历史极端行情测算修复天数、完整周期与止盈锚点...
      </section>
    );
  }

  if (!data || data.status !== 'ready') {
    return null;
  }

  const exp = data.expected_recovery;
  const hist = data.historical_recovery;
  const cycSum = data.full_cycles.summary;
  const tp = data.take_profit_plan;
  const pos = tp.current_cycle_position;
  const normalPeakRec = exp.peak_to_recovery_tdays.normal_median ?? exp.peak_to_recovery_tdays.median;
  const normalPeakRecM = exp.peak_to_recovery_tdays.normal_median_months ?? exp.peak_to_recovery_tdays.median_months;
  const normalTroughRec = exp.trough_to_recovery_tdays.normal_median ?? exp.trough_to_recovery_tdays.median;

  return (
    <section className="inst-panel rounded-lg overflow-hidden space-y-0">
      {/* 头部标题 + 统一下划线子页签 */}
      <div className="px-4 sm:px-5 pt-4 border-b border-slate-200 flex flex-col lg:flex-row lg:items-end justify-between gap-3">
        <div className="pb-3">
          <div className="flex flex-wrap items-center gap-2">
            <h2 className="text-sm font-bold text-slate-900">极端行情修复天数、完整周期与量化止盈锚点</h2>
            <span className="text-[11px] font-mono text-slate-400 tabular-nums">
              {data.date_range} · {exp.n_simulations.toLocaleString()} 次 MC
            </span>
            <MetricTooltip specKey="mc_prob" />
          </div>
        </div>

        <div className="flex items-center gap-5 shrink-0">
          {[
            { id: 'recovery', label: '预计与历史修复天数' },
            { id: 'cycles', label: '完整周期拆解' },
            { id: 'take_profit', label: '三阶量化止盈锚点' },
          ].map((t) => (
            <button
              key={t.id}
              type="button"
              data-active={subTab === t.id}
              onClick={() => setSubTab(t.id as 'recovery' | 'cycles' | 'take_profit')}
              className="inst-subtab"
            >
              {t.label}
            </button>
          ))}
        </div>
      </div>

      {/* 顶部 4 列无彩虹底纯排版指标带 */}
      <div className="grid grid-cols-2 lg:grid-cols-4 divide-y lg:divide-y-0 lg:divide-x divide-slate-200 border-b border-slate-200 bg-slate-50/40 tabular-nums">
        <div className="p-4">
          <div className="text-[11px] text-slate-500">前瞻 MC 预计修复</div>
          <div className="text-xl font-extrabold text-slate-900 mt-1">
            {normalPeakRec} <span className="text-xs font-medium text-slate-500">交易日</span>
          </div>
          <div className="text-[11px] text-slate-500 mt-0.5">
            约 {normalPeakRecM} 月（谷底回本 {normalTroughRec} 天） · VaR95 -{exp.extreme_shock_var95_pct.toFixed(1)}%
          </div>
        </div>

        <div className="p-4">
          <div className="text-[11px] text-slate-500">历史极端真实修复</div>
          <div className="text-xl font-extrabold text-emerald-700 mt-1">
            均 {hist.avg_underwater_tdays} <span className="text-xs font-medium text-slate-500">交易日</span>
          </div>
          <div className="text-[11px] text-slate-500 mt-0.5">
            约 {hist.avg_underwater_months} 月 · 最长 {hist.max_underwater_tdays} 天
            {hist.days_faster_than_hs300 > 0 ? ` · 比300快${hist.days_faster_than_hs300}天` : ''}
          </div>
        </div>

        <div className="p-4">
          <div className="text-[11px] text-slate-500">历史完整周期（高→低→新高）</div>
          <div className="text-xl font-extrabold text-slate-900 mt-1">
            约 {cycSum.avg_full_cycle_months} <span className="text-xs font-medium text-slate-500">个月</span>
          </div>
          <div className="text-[11px] text-slate-500 mt-0.5">
            前高→新高均 <strong className="text-red-600">+{cycSum.avg_peak_to_next_peak_return_pct.toFixed(1)}%</strong> · {cycSum.completed_cycles_count} 轮完整样本
          </div>
        </div>

        <div className="p-4">
          <div className="text-[11px] text-slate-500">量化建议止盈区间</div>
          <div className="text-xl font-extrabold text-red-600 mt-1">
            +{tp.recommended_zone_pct[0].toFixed(1)}% ~ +{tp.recommended_zone_pct[1].toFixed(1)}%
          </div>
          <div className="text-[11px] text-slate-500 mt-0.5">
            移动锁盈 -{tp.trailing_stop_drawdown_pct.toFixed(1)}% · 当下 <strong className="text-slate-800">{pos.tag}</strong>
          </div>
        </div>
      </div>

      <div className="p-4 sm:p-5">
      {/* 子视图 1：预计修复天数 vs 历史四大极端行情真实修复天数 */}
      {subTab === 'recovery' && (
        <div className="space-y-4">
          <div className="px-3.5 py-2 rounded-md bg-slate-50 border border-slate-200 text-xs text-slate-600 leading-relaxed tabular-nums">
            <strong className="text-slate-800">口径摘要：</strong>
            历史均水下 {hist.avg_underwater_tdays} 交易日；前瞻 MC（CVaR99 -{exp.extreme_shock_cvar99_pct.toFixed(1)}%）常规中位{' '}
            <strong>{normalPeakRec} 天</strong> / 保守中位 {exp.peak_to_recovery_tdays.median} 天 / P90 极端 {exp.peak_to_recovery_tdays.p90} 天。
          </div>

          <EChartBox option={recoveryBarOption} height={260} />

          {hist.events.some((e) => e.is_proxy_simulated) && (
            <div className="px-3.5 py-2 rounded-md bg-amber-50/60 border-l-4 border-l-amber-500 text-[11px] text-amber-950 leading-relaxed">
              <strong>透明口径声明：</strong>共同存续期内的事件 100% 采用终选基金真实复权净值；标有「同风格基准参考」的早期历史事件（早于组合中最年轻基金成立日）采用风格桶基准指数作压力参考。
            </div>
          )}

          <div className="overflow-x-auto rounded-xl border border-slate-200">
            <table className="w-full text-xs text-left">
              <thead className="bg-slate-50 text-slate-500 border-b border-slate-200">
                <tr>
                  <th className="py-2.5 px-3 font-semibold">历史极端市场事件</th>
                  <th className="py-2.5 px-3 font-semibold text-right">本方案最大回撤</th>
                  <th className="py-2.5 px-3 font-semibold text-right">沪深 300 回撤</th>
                  <th className="py-2.5 px-3 font-semibold text-right">下跌天数</th>
                  <th className="py-2.5 px-3 font-semibold text-right">谷底→回本</th>
                  <th className="py-2.5 px-3 font-semibold text-right">总水下时长</th>
                  <th className="py-2.5 px-3 font-semibold text-right">沪深 300 水下</th>
                  <th className="py-2.5 px-3 font-semibold">解套日期</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 tabular-nums">
                {hist.events.map((ev) => (
                  <tr key={ev.id} className="hover:bg-slate-50/70">
                    <td className="py-2.5 px-3">
                      <div className="flex flex-wrap items-center gap-1.5">
                        <span className="font-semibold text-slate-900">{ev.name}</span>
                        {ev.is_proxy_simulated && (
                          <span
                            title={ev.proxy_note || '早于共同成立日，按同风格基准指数参考测算'}
                            className="px-1.5 py-0.5 rounded text-[10px] font-semibold bg-amber-100 text-amber-800 border border-amber-200"
                          >
                            同风格基准参考
                          </span>
                        )}
                      </div>
                      <div className="text-[11px] text-slate-400">{ev.desc}</div>
                      {ev.is_proxy_simulated && ev.proxy_note && (
                        <div className="text-[10px] text-amber-700 mt-0.5">{ev.proxy_note}</div>
                      )}
                    </td>
                    <td className="py-2.5 px-3 text-right font-bold text-emerald-700">{ev.max_dd_pct.toFixed(2)}%</td>
                    <td className="py-2.5 px-3 text-right text-slate-500">{ev.h300_mdd_pct.toFixed(2)}%</td>
                    <td className="py-2.5 px-3 text-right text-slate-700">{ev.fall_tdays} 天</td>
                    <td className="py-2.5 px-3 text-right font-semibold text-blue-700">
                      {ev.trough_to_recovery_tdays} 天（{ev.trough_to_recovery_months}月）
                    </td>
                    <td className="py-2.5 px-3 text-right font-bold text-slate-900">
                      {ev.total_underwater_tdays} 天（{ev.total_underwater_months}月）
                    </td>
                    <td className="py-2.5 px-3 text-right text-slate-500">
                      {ev.h300_total_underwater_tdays} 天（{ev.h300_total_underwater_months}月）
                    </td>
                    <td className="py-2.5 px-3 font-mono text-[11px] text-slate-600">{ev.recovery_date}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* 子视图 2：高点→低点→回本→下一轮高点 完整极端周期拆解 */}
      {subTab === 'cycles' && (
        <div className="space-y-4">
          <div className="p-4 rounded-xl bg-amber-50/60 border border-amber-200 text-xs text-amber-950 leading-relaxed space-y-1">
            <div>
              <strong>完整极端周期实测结论（2018–2026）：</strong>本方案共经历 <strong>{cycSum.completed_cycles_count} 轮</strong>显著极端回撤并创出新高的完整周期（回撤门槛 ≥ {cycSum.dd_threshold_pct.toFixed(1)}%）。
            </div>
            <div>
              • <strong>一般耗时多久：</strong>从高点跌至谷底再冲至下一轮高点，完整周期平均约 <strong>{cycSum.avg_full_cycle_months} 个月（{cycSum.avg_full_cycle_tdays} 交易日）</strong>，分布区间 {cycSum.full_cycle_months_range[0]} ~ {cycSum.full_cycle_months_range[1]} 个月（其中水下回本阶段平均 {cycSum.avg_underwater_months} 个月）。
            </div>
            <div>
              • <strong>大致有多少收益：</strong>即便不幸买在上一轮高点、熬过完整周期拿到下一轮高点，平均净收益 <strong className="text-red-700">+{cycSum.avg_peak_to_next_peak_return_pct.toFixed(1)}%</strong>（区间 +{cycSum.peak_to_next_peak_range_pct[0].toFixed(1)}% ~ +{cycSum.peak_to_next_peak_range_pct[1].toFixed(1)}%）；若在谷底分批布局拿到下一轮高点，平均波段收益达 <strong className="text-red-700">+{cycSum.avg_trough_to_next_peak_return_pct.toFixed(1)}%</strong>（区间 +{cycSum.trough_to_next_peak_range_pct[0].toFixed(1)}% ~ +{cycSum.trough_to_next_peak_range_pct[1].toFixed(1)}%）。
            </div>
          </div>

          <EChartBox option={cycleChartOption} height={270} />

          <div className="overflow-x-auto rounded-xl border border-slate-200">
            <table className="w-full text-xs text-left">
              <thead className="bg-slate-50 text-slate-500 border-b border-slate-200">
                <tr>
                  <th className="py-2.5 px-3 font-semibold">完整周期</th>
                  <th className="py-2.5 px-3 font-semibold">前高 → 谷底 → 回本 → 新高</th>
                  <th className="py-2.5 px-3 font-semibold text-right">期间回撤</th>
                  <th className="py-2.5 px-3 font-semibold text-right">水下解套</th>
                  <th className="py-2.5 px-3 font-semibold text-right">完整周期总长</th>
                  <th className="py-2.5 px-3 font-semibold text-right">前高→新高净赚</th>
                  <th className="py-2.5 px-3 font-semibold text-right">谷底→新高收益</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 tabular-nums">
                {data.full_cycles.items.map((cy) => (
                  <tr key={cy.cycle_id} className="hover:bg-slate-50/70">
                    <td className="py-2.5 px-3 font-semibold text-slate-900">{cy.cycle_label}</td>
                    <td className="py-2.5 px-3 font-mono text-[11px] text-slate-500">
                      {cy.peak1_date} → {cy.trough_date} → {cy.recovery_date} → {cy.next_peak_date}
                    </td>
                    <td className="py-2.5 px-3 text-right font-semibold text-emerald-700">{cy.drawdown_pct.toFixed(2)}%</td>
                    <td className="py-2.5 px-3 text-right text-slate-700">
                      {cy.underwater_tdays} 天（{cy.underwater_months}月）
                    </td>
                    <td className="py-2.5 px-3 text-right font-bold text-slate-900">
                      {cy.full_cycle_tdays} 天（{cy.full_cycle_months}月）
                    </td>
                    <td
                      className={`py-2.5 px-3 text-right font-bold ${
                        cy.peak_to_next_peak_return_pct >= 0 ? 'text-red-600' : 'text-emerald-700'
                      }`}
                    >
                      {cy.peak_to_next_peak_return_pct >= 0 ? '+' : ''}
                      {cy.peak_to_next_peak_return_pct.toFixed(2)}%
                    </td>
                    <td className="py-2.5 px-3 text-right font-bold text-rose-600">
                      +{cy.trough_to_next_peak_return_pct.toFixed(2)}%
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* 子视图 3：三阶量化建议止盈点与当下周期定位 */}
      {subTab === 'take_profit' && (
        <div className="space-y-4">
          <div
            className={`p-4 rounded-xl border text-xs leading-relaxed ${
              pos.level === 'take_profit'
                ? 'bg-rose-50/80 border-rose-200 text-rose-950'
                : pos.level === 'accumulate'
                ? 'bg-emerald-50/70 border-emerald-200 text-emerald-950'
                : 'bg-blue-50/70 border-blue-200 text-blue-950'
            }`}
          >
            <div className="flex flex-wrap items-center justify-between gap-2 mb-1">
              <strong className="text-sm">当前宏观周期定位：{pos.tag}</strong>
              <span className="font-mono text-[11px] opacity-80">
                全市场 ERP 估值分位 {pos.erp_percentile.toFixed(1)}% · MA20 乖离 {pos.bias_20 >= 0 ? '+' : ''}
                {pos.bias_20.toFixed(2)}%
              </span>
            </div>
            <p>{pos.advice}</p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {tp.anchors.map((a) => (
              <div
                key={a.code}
                className="p-4 rounded-xl bg-white border border-slate-200 shadow-2xs space-y-2.5 flex flex-col justify-between"
              >
                <div className="space-y-2">
                  <div className="flex items-center justify-between gap-2">
                    <span className="px-2 py-0.5 rounded-md text-[11px] font-bold bg-[#0A192F] text-amber-300">
                      STEP 0{a.step}
                    </span>
                    <span className="text-[11px] text-slate-400">
                      联动目标 {horizonMonths}月 +{targetReturnPct}%
                    </span>
                  </div>
                  <h3 className="text-sm font-bold text-slate-900">{a.title}</h3>
                  <div className="text-lg font-extrabold text-rose-600 tabular-nums">{a.trigger_label}</div>
                  <div className="p-2.5 rounded-lg bg-slate-50 border border-slate-100 text-xs text-slate-800 font-medium">
                    建议动作：{a.action}
                  </div>
                </div>
                <p className="text-[11px] text-slate-500 leading-relaxed pt-2 border-t border-slate-100">{a.rationale}</p>
              </div>
            ))}
          </div>
        </div>
      )}
      </div>
    </section>
  );
}

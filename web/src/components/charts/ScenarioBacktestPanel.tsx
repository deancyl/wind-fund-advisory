import { useEffect, useMemo, useState } from 'react';
import type * as echarts from 'echarts';
import { api, type ScenarioBacktestResponse, type ScenarioKpi, type UniverseMode } from '../../api/client';
import { EChartBox } from '../EChartBox';
import { ChartReadingGuide } from '../ChartReadingGuide';

interface ScenarioBacktestPanelProps {
  tier: string;
  modelId?: string;
  fundCount?: number;
  targetReturnPct?: number;
  horizonMonths?: number;
  universeMode?: UniverseMode;
  staleHint?: string;
}

const SCENARIO_PRESETS = [
  { id: '2021-02-18', label: '2021-02 核心资产高位', hint: '检验高点建仓的抗跌与回本能力' },
  { id: '2022-04-26', label: '2022-04 底部反弹期', hint: '检验震荡筑底阶段的修复节奏' },
  { id: '2024-09-18', label: '2024-09 政策转向期', hint: '检验行情快速反转时的跟涨效率' },
  { id: '2025-11-25', label: '近 1 年区间', hint: '检验最近一年的实盘适应性' },
];

export function ScenarioBacktestPanel({
  tier,
  modelId,
  fundCount,
  targetReturnPct,
  horizonMonths,
  universeMode,
  staleHint,
}: ScenarioBacktestPanelProps) {
  const [startDate, setStartDate] = useState('2024-09-18');
  const [dynamicRebal, setDynamicRebal] = useState(true);
  const [data, setData] = useState<ScenarioBacktestResponse | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let alive = true;
    setLoading(true);
    api
      .getScenarioBacktest(
        startDate,
        tier,
        dynamicRebal,
        modelId
          ? {
              model: modelId,
              fundCount,
              targetReturnPct,
              horizonMonths,
              universeMode,
            }
          : undefined
      )
      .then((res) => {
        if (alive) setData(res);
      })
      .catch(() => {})
      .finally(() => {
        if (alive) setLoading(false);
      });
    return () => {
      alive = false;
    };
  }, [startDate, tier, dynamicRebal, modelId, fundCount, targetReturnPct, horizonMonths, universeMode]);

  const chartOption = useMemo<echarts.EChartsCoreOption>(() => {
    if (!data || !data.dates.length) return {};
    const series: Array<Record<string, unknown>> = [
      {
        name: `${data.portfolio_name || '当前方案'}真实到手净值（全扣费）`,
        type: 'line',
        data: data.strategy_nav,
        showSymbol: false,
        lineStyle: { color: '#1D4ED8', width: 2.5 },
        itemStyle: { color: '#1D4ED8' },
      },
      {
        name: '沪深 300 基准',
        type: 'line',
        data: data.hs300_nav,
        showSymbol: false,
        lineStyle: { color: '#64748B', width: 1.5, type: 'dashed' },
        itemStyle: { color: '#64748B' },
      },
    ];
    if (data.balanced_nav?.length) {
      series.push({
        name: '股债 50/50 平衡基准',
        type: 'line',
        data: data.balanced_nav,
        showSymbol: false,
        lineStyle: { color: '#10B981', width: 1.5, type: 'dotted' },
        itemStyle: { color: '#10B981' },
      });
    }
    return {
      tooltip: { trigger: 'axis', backgroundColor: 'rgba(15,23,42,0.92)', borderWidth: 0, textStyle: { color: '#F8FAFC', fontSize: 12 } },
      legend: { top: 0, right: 0, type: 'scroll', textStyle: { fontSize: 11, color: '#475569' } },
      grid: { top: 40, left: 46, right: 16, bottom: 28 },
      xAxis: {
        type: 'category',
        data: data.dates,
        boundaryGap: false,
        axisLabel: { color: '#64748B', fontSize: 11, formatter: (v: string) => v.slice(0, 7) },
      },
      yAxis: {
        type: 'value',
        scale: true,
        axisLabel: { color: '#64748B', fontSize: 11 },
        splitLine: { lineStyle: { color: '#F1F5F9' } },
      },
      series,
    };
  }, [data]);

  const kpiCards: Array<{ title: string; item?: ScenarioKpi | null }> = [
    { title: '持有 3 个月', item: data?.kpis?.m3 },
    { title: '持有 6 个月', item: data?.kpis?.m6 },
    { title: '持有 1 年', item: data?.kpis?.y1 },
    { title: '持有至今', item: data?.kpis?.all },
  ];

  return (
    <div className="card-elevated rounded-2xl p-5 sm:p-6 space-y-5">
      {staleHint && (
        <div className="px-3.5 py-2 rounded-xl bg-amber-50 border border-amber-200 text-xs text-amber-900 font-medium">
          {staleHint}
        </div>
      )}

      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-3">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <h3 className="text-base font-bold text-slate-900">历史情景回测（严格零未来函数 · 全真申赎扣费）</h3>
            {data?.portfolio_name && (
              <span
                data-testid="scenario-portfolio-badge"
                className="px-2 py-0.5 rounded-full text-[11px] font-semibold bg-blue-50 text-blue-700 border border-blue-200"
              >
                联动当前方案：{data.portfolio_name}
              </span>
            )}
          </div>
          <p className="text-xs text-slate-500 mt-0.5">
            严格按上方已求解出的精确基金与权重，任选历史代表性市场节点作为买入起点，检验高位建仓、底部震荡或政策反转后的真实到手表现
          </p>
        </div>
        <label className="inline-flex items-center gap-2 text-xs font-medium text-slate-700 cursor-pointer shrink-0">
          <input
            type="checkbox"
            checked={dynamicRebal}
            onChange={(e) => setDynamicRebal(e.target.checked)}
            className="w-4 h-4 accent-[#1D4ED8]"
          />
          <span>启用月频 3% 偏离动态再平衡</span>
        </label>
      </div>

      {data?.used_proxy_early && data.proxy_note && (
        <div
          data-testid="scenario-proxy-notice"
          className="px-3.5 py-2 rounded-xl bg-amber-50/80 border border-amber-200 text-xs text-amber-900 leading-relaxed"
        >
          <strong>透明衔接提示：</strong>
          {data.proxy_note}
        </div>
      )}

      {/* 情景预设按钮 + 自定义日期 */}
      <div className="flex flex-wrap items-center gap-2">
        {SCENARIO_PRESETS.map((p) => {
          const active = startDate === p.id;
          return (
            <button
              key={p.id}
              type="button"
              onClick={() => setStartDate(p.id)}
              title={p.hint}
              className={`px-3 py-1.5 rounded-xl text-xs font-semibold border transition-all cursor-pointer ${
                active
                  ? 'bg-[#0A192F] text-white border-[#0A192F] shadow-xs'
                  : 'bg-slate-50 text-slate-700 border-slate-200 hover:bg-white hover:border-slate-300'
              }`}
            >
              {p.label}
            </button>
          );
        })}
        <label className="inline-flex items-center gap-2 ml-auto text-xs text-slate-600">
          <span>自定义起点</span>
          <input
            type="date"
            value={startDate}
            min="2018-01-02"
            max="2026-10-01"
            onChange={(e) => {
              if (e.target.value) setStartDate(e.target.value);
            }}
            className="h-8 px-2.5 rounded-lg bg-slate-50 border border-slate-200 text-slate-900 font-mono text-xs focus:border-blue-600 focus:bg-white focus:outline-none"
          />
        </label>
      </div>

      {/* 4 周期绩效卡 */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        {kpiCards.map(({ title, item }) => {
          if (!item) {
            return (
              <div key={title} className="p-3.5 rounded-xl bg-slate-50 border border-slate-200 text-xs text-slate-400">
                <div className="font-semibold text-slate-600">{title}</div>
                <div className="mt-2">区间样本不足</div>
              </div>
            );
          }
          const pos = item.net_return_pct >= 0;
          return (
            <div key={title} className="p-3.5 rounded-xl bg-slate-50/80 border border-slate-200 space-y-1">
              <div className="text-xs font-semibold text-slate-700">
                {title} <span className="text-slate-400 font-normal">({item.days}天)</span>
              </div>
              <div className={`text-xl font-extrabold tabular-nums ${pos ? 'text-red-600' : 'text-emerald-700'}`}>
                {pos ? '+' : ''}
                {item.net_return_pct.toFixed(2)}%
              </div>
              <div className="text-[11px] text-slate-500 space-y-0.5 tabular-nums">
                <div>
                  同期沪深 300：<strong>{item.h300_return_pct >= 0 ? '+' : ''}{item.h300_return_pct.toFixed(2)}%</strong>
                </div>
                <div>
                  最大回撤：<strong>{item.mdd_pct.toFixed(2)}%</strong>（基准 {item.h300_mdd_pct.toFixed(2)}%）
                </div>
              </div>
            </div>
          );
        })}
      </div>

      <ChartReadingGuide
        howToRead="蓝线为扣除申赎费与资金到账摩擦后的策略真实到手净值，灰虚线为同期沪深 300 基准，绿点线为股债 50/50 基准。"
        actionSignal="即使在 2021-02 核心资产高位发车，若蓝线最大回撤显著浅于沪深 300 且更快修复，说明策略具备跨周期抗跌能力。"
      />

      {loading ? (
        <div className="py-12 text-center text-xs text-slate-400">正在按所选起点重演历史情景回测...</div>
      ) : (
        <EChartBox option={chartOption} height={320} />
      )}
    </div>
  );
}

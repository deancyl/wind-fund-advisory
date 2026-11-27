import { useEffect, useMemo, useState } from 'react';
import type * as echarts from 'echarts';
import { api, type ScenarioBacktestResponse, type ScenarioKpi, type UniverseMode } from '../../api/client';
import { EChartBox } from '../EChartBox';

interface ScenarioBacktestPanelProps {
  tier: string;
  modelId?: string;
  fundCount?: number;
  targetReturnPct?: number;
  horizonMonths?: number;
  universeMode?: UniverseMode;
  excludeCodes?: string[];
  includeCodes?: string[];
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
  excludeCodes,
  includeCodes,
  staleHint,
}: ScenarioBacktestPanelProps) {
  const [startDate, setStartDate] = useState('2024-09-18');
  const [dynamicRebal, setDynamicRebal] = useState(true);
  const [data, setData] = useState<ScenarioBacktestResponse | null>(null);
  const [loading, setLoading] = useState(true);

  const exKey = (excludeCodes || []).join(',');
  const inKey = (includeCodes || []).join(',');

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
              excludeCodes: exKey ? exKey.split(',') : undefined,
              includeCodes: inKey ? inKey.split(',') : undefined,
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
  }, [startDate, tier, dynamicRebal, modelId, fundCount, targetReturnPct, horizonMonths, universeMode, exKey, inKey]);

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
    <div className="inst-panel rounded-lg p-4 sm:p-5 space-y-4">
      {staleHint && (
        <div className="px-3.5 py-2 rounded-md bg-amber-50 border-l-4 border-l-amber-500 text-xs text-amber-900 font-medium">
          {staleHint}
        </div>
      )}

      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-2.5">
        <div className="flex flex-wrap items-center gap-2">
          <h3 className="text-sm font-bold text-slate-900">历史情景压力回测（零未来函数 · 全真申赎扣费）</h3>
          {data?.portfolio_name && (
            <span
              data-testid="scenario-portfolio-badge"
              className="px-2 py-0.5 rounded text-[10px] font-semibold bg-slate-100 text-slate-700 border border-slate-200"
            >
              {data.portfolio_name}
            </span>
          )}
        </div>
        <label className="inline-flex items-center gap-2 text-xs font-medium text-slate-700 cursor-pointer shrink-0">
          <input
            type="checkbox"
            checked={dynamicRebal}
            onChange={(e) => setDynamicRebal(e.target.checked)}
            className="w-3.5 h-3.5 accent-blue-700"
          />
          <span>月频 3% 偏离动态再平衡</span>
        </label>
      </div>

      {/* 永不隐藏的数据口径提示：早于共同成立日采用同风格基准衔接 */}
      {data?.used_proxy_early && data.proxy_note && (
        <div
          data-testid="scenario-proxy-notice"
          className="px-3.5 py-2 rounded-md bg-amber-50/60 border-l-4 border-l-amber-500 text-xs text-amber-950 leading-relaxed"
        >
          <strong>透明衔接声明：</strong>
          {data.proxy_note}
        </div>
      )}

      {/* 情景预设按钮 + 自定义日期 */}
      <div className="flex flex-wrap items-center gap-1.5">
        {SCENARIO_PRESETS.map((p) => {
          const active = startDate === p.id;
          return (
            <button
              key={p.id}
              type="button"
              onClick={() => setStartDate(p.id)}
              title={p.hint}
              className={`px-2.5 py-1.5 rounded-md text-xs font-semibold border transition-colors cursor-pointer ${
                active
                  ? 'bg-[#0A1628] text-white border-[#0A1628]'
                  : 'bg-white text-slate-700 border-slate-200 hover:border-slate-400'
              }`}
            >
              {p.label}
            </button>
          );
        })}
        <label className="inline-flex items-center gap-2 ml-auto text-xs text-slate-500">
          <span>自定义起点</span>
          <input
            type="date"
            value={startDate}
            min="2018-01-02"
            max="2026-10-01"
            onChange={(e) => {
              if (e.target.value) setStartDate(e.target.value);
            }}
            className="h-8 px-2 rounded-md bg-white border border-slate-300 text-slate-900 font-mono text-xs focus:border-blue-600 focus:outline-none"
          />
        </label>
      </div>

      {/* 4 周期绩效带（极简无彩虹底） */}
      <div className="grid grid-cols-2 lg:grid-cols-4 border border-slate-200 rounded-lg divide-y lg:divide-y-0 lg:divide-x divide-slate-200 bg-slate-50/40 tabular-nums">
        {kpiCards.map(({ title, item }) => {
          if (!item) {
            return (
              <div key={title} className="p-3 text-xs text-slate-400">
                <div className="font-semibold text-slate-600">{title}</div>
                <div className="mt-1.5">区间样本不足</div>
              </div>
            );
          }
          const pos = item.net_return_pct >= 0;
          return (
            <div key={title} className="p-3 space-y-0.5">
              <div className="text-[11px] font-medium text-slate-500">
                {title} <span className="text-slate-400">({item.days}天)</span>
              </div>
              <div className={`text-lg font-extrabold ${pos ? 'text-red-600' : 'text-emerald-700'}`}>
                {pos ? '+' : ''}
                {item.net_return_pct.toFixed(2)}%
              </div>
              <div className="text-[11px] text-slate-500">
                沪深300 {item.h300_return_pct >= 0 ? '+' : ''}
                {item.h300_return_pct.toFixed(2)}% · 回撤 {item.mdd_pct.toFixed(1)}%
              </div>
            </div>
          );
        })}
      </div>

      {loading ? (
        <div className="py-12 text-center text-xs text-slate-400">正在按所选起点重演历史情景回测...</div>
      ) : (
        <EChartBox option={chartOption} height={330} />
      )}
    </div>
  );
}

import { useMemo } from 'react';
import type * as echarts from 'echarts';
import type { ExposureResponse } from '../../api/client';
import { EChartBox } from '../EChartBox';
import { ChartReadingGuide } from '../ChartReadingGuide';

interface ExposureChartsProps {
  exposure: ExposureResponse | null;
  loading: boolean;
}

export function ExposureCharts({ exposure, loading }: ExposureChartsProps) {
  const assetOption = useMemo<echarts.EChartsCoreOption>(() => {
    if (!exposure) return {};
    const cur = exposure.asset_classes || {};
    const tgt = exposure.target_classes || {};
    const keys = Array.from(new Set([...Object.keys(cur), ...Object.keys(tgt)]));
    if (!keys.length) return {};

    keys.sort((a, b) => Math.max(cur[a] || 0, tgt[a] || 0) - Math.max(cur[b] || 0, tgt[b] || 0));

    return {
      tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' }, valueFormatter: (v: unknown) => `${Number(v).toFixed(1)}%` },
      legend: { top: 0, right: 0, textStyle: { fontSize: 11, color: '#475569' } },
      grid: { top: 36, left: 108, right: 20, bottom: 26 },
      xAxis: {
        type: 'value',
        axisLabel: { color: '#64748B', fontSize: 11, formatter: '{value}%' },
        splitLine: { lineStyle: { color: '#F1F5F9' } },
      },
      yAxis: {
        type: 'category',
        data: keys,
        axisLabel: { color: '#334155', fontSize: 11 },
      },
      series: [
        {
          name: '我的当前占比',
          type: 'bar',
          barMaxWidth: 12,
          itemStyle: { color: '#0EA5E9', borderRadius: [0, 4, 4, 0] },
          data: keys.map((k) => Number(((cur[k] || 0) * 100).toFixed(1))),
        },
        {
          name: 'AI 今日目标占比',
          type: 'bar',
          barMaxWidth: 12,
          itemStyle: { color: '#10B981', borderRadius: [0, 4, 4, 0] },
          data: keys.map((k) => Number(((tgt[k] || 0) * 100).toFixed(1))),
        },
      ],
    };
  }, [exposure]);

  const industryOption = useMemo<echarts.EChartsCoreOption>(() => {
    if (!exposure || !exposure.top_industries) return {};
    const entries = Object.entries(exposure.top_industries)
      .filter(([, v]) => v > 0)
      .sort((a, b) => a[1] - b[1]);
    if (!entries.length) return {};

    return {
      tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' }, valueFormatter: (v: unknown) => `${Number(v).toFixed(2)}%` },
      grid: { top: 18, left: 110, right: 24, bottom: 26 },
      xAxis: {
        type: 'value',
        axisLabel: { color: '#64748B', fontSize: 11, formatter: '{value}%' },
        splitLine: { lineStyle: { color: '#F1F5F9' } },
      },
      yAxis: {
        type: 'category',
        data: entries.map(([k]) => k),
        axisLabel: { color: '#334155', fontSize: 11 },
      },
      series: [
        {
          name: '行业穿透暴露',
          type: 'bar',
          barMaxWidth: 14,
          data: entries.map(([, v]) => Number((v * 100).toFixed(2))),
          itemStyle: {
            borderRadius: [0, 4, 4, 0],
            color: (params: { dataIndex: number }) => {
              const ratio = params.dataIndex / Math.max(1, entries.length - 1);
              if (ratio > 0.75) return '#D97706';
              if (ratio > 0.45) return '#0D9488';
              return '#3B82F6';
            },
          },
        },
      ],
    };
  }, [exposure]);

  if (loading) {
    return <div className="card-elevated rounded-2xl p-6 text-center text-xs text-slate-500">正在穿透计算资产大类缺口与底层申万行业暴露...</div>;
  }
  if (!exposure || exposure.status === 'empty') return null;

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
      <div className="card-elevated rounded-2xl p-5 space-y-3">
        <div className="flex items-center gap-2">
          <span className="w-1 h-4 rounded-full bg-sky-500" />
          <h3 className="text-sm font-bold text-slate-900">资产大类配比（当前 vs AI 目标缺口）</h3>
        </div>
        <ChartReadingGuide
          howToRead="对比天蓝色（我的当前持仓占比）与翠绿色（AI 今日目标占比）之间的长短差距。"
          actionSignal="蓝条明显长于绿条的大类需在调仓页减配，蓝条短于绿条的低配大类优先用新增资金补齐。"
        />
        <EChartBox option={assetOption} height={300} />
      </div>

      <div className="card-elevated rounded-2xl p-5 space-y-3">
        <div className="flex items-center gap-2">
          <span className="w-1 h-4 rounded-full bg-teal-600" />
          <h3 className="text-sm font-bold text-slate-900">行业穿透暴露（底层持仓汇总）</h3>
        </div>
        <ChartReadingGuide
          howToRead="将所有持仓基金拆解到底层股票后，按申万行业汇总的真实资金暴露比例。"
          actionSignal="若单一行业暴露超过 25% 说明存在赛道集中风险，应适度分散至宽基或红利底仓。"
        />
        <EChartBox option={industryOption} height={300} />
      </div>
    </div>
  );
}

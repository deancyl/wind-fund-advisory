import { useMemo } from 'react';
import type * as echarts from 'echarts';
import type { ExposureResponse } from '../../api/client';
import { EChartBox } from '../EChartBox';

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
    return <div className="inst-panel rounded-lg p-6 text-center text-xs text-slate-400">正在穿透计算资产大类缺口与底层申万行业暴露...</div>;
  }
  if (!exposure || exposure.status === 'empty') return null;

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
      <div className="inst-panel rounded-lg p-4 sm:p-5 space-y-2.5">
        <div className="flex items-center justify-between">
          <h3 className="text-xs font-bold text-slate-900">资产大类配比（当前持仓 vs AI 目标）</h3>
          <span className="text-[11px] text-slate-400">大类缺口定位</span>
        </div>
        <EChartBox option={assetOption} height={290} />
      </div>

      <div className="inst-panel rounded-lg p-4 sm:p-5 space-y-2.5">
        <div className="flex items-center justify-between">
          <h3 className="text-xs font-bold text-slate-900">申万行业穿透暴露（底层股票汇总）</h3>
          <span className="text-[11px] text-slate-400">单行业红线 25%</span>
        </div>
        <EChartBox option={industryOption} height={290} />
      </div>
    </div>
  );
}

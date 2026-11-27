import { useMemo } from 'react';
import type * as echarts from 'echarts';
import type { CrowdingPoint } from '../../api/client';
import { EChartBox } from '../EChartBox';
import { MetricTooltip } from '../MetricTooltip';

interface CrowdingQuadrantChartProps {
  points: CrowdingPoint[];
  loading: boolean;
  scopeMode?: 'recommended' | 'holdings';
  onChangeScopeMode?: (mode: 'recommended' | 'holdings') => void;
  recommendedCount?: number;
}

export function CrowdingQuadrantChart({
  points,
  loading,
  scopeMode = 'recommended',
  onChangeScopeMode,
  recommendedCount = 0,
}: CrowdingQuadrantChartProps) {
  const option = useMemo<echarts.EChartsCoreOption>(() => {
    if (!points.length) return {};

    const groups: Record<string, { color: string; data: Array<Record<string, unknown>> }> = {
      低估布局区: { color: '#10B981', data: [] },
      温和修复区: { color: '#0EA5E9', data: [] },
      分歧避险区: { color: '#F43F5E', data: [] },
      高位偏热区: { color: '#F59E0B', data: [] },
    };

    for (const p of points) {
      let key = '温和修复区';
      if (p.bias_20 <= 0 && p.crowding_score < 50) key = '低估布局区';
      else if (p.bias_20 <= 0 && p.crowding_score >= 50) key = '分歧避险区';
      else if (p.bias_20 > 0 && p.crowding_score >= 50) key = '高位偏热区';

      groups[key].data.push({
        name: p.short_name,
        value: [p.bias_20, p.crowding_score],
        meta: p,
      });
    }

    const xVals = points.map((p) => p.bias_20);
    const minX = Math.min(-6, Math.floor(Math.min(...xVals) - 2));
    const maxX = Math.max(6, Math.ceil(Math.max(...xVals) + 2));

    return {
      tooltip: {
        trigger: 'item',
        backgroundColor: 'rgba(15,23,42,0.94)',
        borderWidth: 0,
        textStyle: { color: '#F8FAFC', fontSize: 12 },
        formatter: (params: unknown) => {
          const item = (params as { data?: { meta?: CrowdingPoint } })?.data?.meta;
          if (!item) return '';
          return `
            <div style="font-weight:700;margin-bottom:4px;">${item.fund_name} (${item.fund_code})</div>
            <div>MA20 乖离率：<b>${item.bias_20 >= 0 ? '+' : ''}${item.bias_20}%</b></div>
            <div>交易拥挤热力：<b>${item.crowding_score}</b> / 100</div>
            <div>近20日涨跌：<b>${item.ret_20d >= 0 ? '+' : ''}${item.ret_20d}%</b></div>
            <div style="margin-top:4px;color:#CBD5E1;max-width:240px;white-space:normal;">${item.advisory_tip}</div>
          `;
        },
      },
      legend: { top: 0, right: 0, textStyle: { fontSize: 11, color: '#475569' } },
      grid: { top: 44, left: 48, right: 24, bottom: 40 },
      xAxis: {
        type: 'value',
        name: 'MA20 均线乖离率 Bias20 (%)',
        nameLocation: 'middle',
        nameGap: 25,
        nameTextStyle: { color: '#64748B', fontSize: 11 },
        min: minX,
        max: maxX,
        splitLine: { lineStyle: { color: '#F1F5F9' } },
      },
      yAxis: {
        type: 'value',
        name: '交易拥挤度热力 (0~100)',
        nameTextStyle: { color: '#64748B', fontSize: 11 },
        min: 15,
        max: 90,
        splitLine: { lineStyle: { color: '#F1F5F9' } },
      },
      series: Object.entries(groups).map(([name, g], idx) => ({
        name,
        type: 'scatter',
        symbolSize: 20,
        itemStyle: { color: g.color, opacity: 0.88, borderColor: '#FFFFFF', borderWidth: 1.5 },
        label: {
          show: true,
          position: 'top',
          distance: 4,
          formatter: '{b}',
          color: '#1E293B',
          fontSize: 11,
          fontWeight: 600,
        },
        labelLayout: { hideOverlap: true },
        data: g.data,
        ...(idx === 0
          ? {
              markLine: {
                silent: true,
                symbol: 'none',
                lineStyle: { type: 'dashed', color: '#CBD5E1', width: 1.5 },
                data: [{ xAxis: 0 }, { yAxis: 50 }],
              },
              markArea: {
                silent: true,
                data: [
                  [{ coord: [minX, 15], itemStyle: { color: 'rgba(16, 185, 129, 0.04)' }, label: { show: true, position: 'insideBottomLeft', formatter: '低估布局区（适合分批低吸）', color: '#059669', fontSize: 11 } }, { coord: [0, 50] }],
                  [{ coord: [0, 50], itemStyle: { color: 'rgba(245, 158, 11, 0.04)' }, label: { show: true, position: 'insideTopRight', formatter: '高位偏热区（忌盲目追高）', color: '#D97706', fontSize: 11 } }, { coord: [maxX, 90] }],
                  [{ coord: [minX, 50], itemStyle: { color: 'rgba(244, 63, 94, 0.03)' }, label: { show: true, position: 'insideTopLeft', formatter: '分歧避险区（观望防守）', color: '#E11D48', fontSize: 11 } }, { coord: [0, 90] }],
                  [{ coord: [0, 15], itemStyle: { color: 'rgba(14, 165, 233, 0.03)' }, label: { show: true, position: 'insideBottomRight', formatter: '温和修复区（稳健持有）', color: '#0284C7', fontSize: 11 } }, { coord: [maxX, 50] }],
                ],
              },
            }
          : {}),
      })),
    };
  }, [points]);

  if (loading) {
    return <div className="inst-panel rounded-lg p-6 text-center text-xs text-slate-400">正在测算核心标的 MA20 乖离率与拥挤度象限...</div>;
  }
  if (!points.length) return null;

  return (
    <div className="inst-panel rounded-lg p-4 sm:p-5 space-y-3" data-testid="crowding-quadrant-section">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex flex-wrap items-center gap-1.5">
          <h3 className="text-sm font-bold text-slate-900">短期偏离与交易拥挤度象限（MA20 乖离 × 拥挤热力）</h3>
          <MetricTooltip specKey="bias20" />
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {onChangeScopeMode && (
            <div className="inline-flex items-center gap-1 bg-slate-100 p-0.5 rounded-md border border-slate-200 text-[11px]" role="group" aria-label="拥挤度象限标的来源">
              <button
                type="button"
                onClick={() => onChangeScopeMode('recommended')}
                className={`px-2.5 py-1 rounded font-semibold transition-colors cursor-pointer ${
                  scopeMode === 'recommended' ? 'bg-[#0A1628] text-white' : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                实验室推荐方案{recommendedCount > 0 ? ` (${recommendedCount}只)` : ''}
              </button>
              <button
                type="button"
                onClick={() => onChangeScopeMode('holdings')}
                className={`px-2.5 py-1 rounded font-semibold transition-colors cursor-pointer ${
                  scopeMode === 'holdings' ? 'bg-[#0A1628] text-white' : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                当前账本持仓
              </button>
            </div>
          )}
        </div>
      </div>
      <EChartBox option={option} height={330} />
    </div>
  );
}

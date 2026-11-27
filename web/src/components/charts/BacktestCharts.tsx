import { useMemo } from 'react';
import type * as echarts from 'echarts';
import type { BacktestCurvesResponse } from '../../api/client';
import { EChartBox } from '../EChartBox';
import { MetricTooltip } from '../MetricTooltip';

interface BacktestChartsProps {
  data: BacktestCurvesResponse | null;
  loading: boolean;
  staleHint?: string;
}

export function BacktestCharts({ data, loading, staleHint }: BacktestChartsProps) {
  const navOption = useMemo<echarts.EChartsCoreOption>(() => {
    if (!data || !data.dates.length) return {};
    const fmtCagr = (v: number | null) => (v !== null && v !== undefined ? `${v >= 0 ? '+' : ''}${v.toFixed(2)}%` : '');

    const markAreaData = (data.slices || []).map((s) => [
      {
        name: s.label,
        xAxis: s.start,
        itemStyle: { color: s.color },
        label: {
          show: true,
          position: 'insideTopLeft',
          color: '#64748B',
          fontSize: 10,
          distance: 6,
        },
      },
      { xAxis: s.end },
    ]);

    const series: Array<Record<string, unknown>> = [
      {
        name: `${data.primary_name} (${fmtCagr(data.cagr.primary)})`,
        type: 'line',
        data: data.nav.primary,
        showSymbol: false,
        lineStyle: { color: '#DC2626', width: 2.4 },
        itemStyle: { color: '#DC2626' },
        markArea: { silent: true, data: markAreaData },
      },
    ];

    if (data.nav.secondary?.length) {
      series.push({
        name: `${data.secondary_name || '对照组合'} (${fmtCagr(data.cagr.secondary)})`,
        type: 'line',
        data: data.nav.secondary,
        showSymbol: false,
        lineStyle: { color: '#0F223D', width: 2.0 },
        itemStyle: { color: '#0F223D' },
      });
    } else if (data.nav.primary_otc?.length) {
      series.push({
        name: `场外实盘95%仓位校准 (${fmtCagr(data.cagr.primary_otc)})`,
        type: 'line',
        data: data.nav.primary_otc,
        showSymbol: false,
        lineStyle: { color: '#1D4ED8', width: 1.8, type: 'dotted' },
        itemStyle: { color: '#1D4ED8' },
      });
    }

    if (data.nav.hs300?.length) {
      series.push({
        name: `沪深300 (${fmtCagr(data.cagr.hs300)})`,
        type: 'line',
        data: data.nav.hs300,
        showSymbol: false,
        lineStyle: { color: '#94A3B8', width: 1.4, type: 'dashed' },
        itemStyle: { color: '#94A3B8' },
      });
    }
    if (data.nav.dividend?.length) {
      series.push({
        name: `红利低波 (${fmtCagr(data.cagr.dividend)})`,
        type: 'line',
        data: data.nav.dividend,
        showSymbol: false,
        lineStyle: { color: '#10B981', width: 1.4, type: 'dashed' },
        itemStyle: { color: '#10B981' },
      });
    }
    if (data.nav.bond?.length) {
      series.push({
        name: `纯债指数 (${fmtCagr(data.cagr.bond)})`,
        type: 'line',
        data: data.nav.bond,
        showSymbol: false,
        lineStyle: { color: '#3B82F6', width: 1.4, type: 'dashed' },
        itemStyle: { color: '#3B82F6' },
      });
    }

    return {
      tooltip: { trigger: 'axis', backgroundColor: 'rgba(15,23,42,0.92)', borderWidth: 0, textStyle: { color: '#F8FAFC', fontSize: 12 } },
      legend: { top: 0, right: 0, type: 'scroll', textStyle: { fontSize: 11, color: '#475569' } },
      grid: { top: 44, left: 46, right: 16, bottom: 28 },
      xAxis: {
        type: 'category',
        data: data.dates,
        boundaryGap: false,
        axisLine: { lineStyle: { color: '#CBD5E1' } },
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

  const ddOption = useMemo<echarts.EChartsCoreOption>(() => {
    if (!data || !data.dates.length) return {};
    const series: Array<Record<string, unknown>> = [
      {
        name: `${data.primary_name}回撤`,
        type: 'line',
        data: data.drawdown.primary,
        showSymbol: false,
        lineStyle: { color: '#059669', width: 1.8 },
        areaStyle: { color: 'rgba(16, 185, 129, 0.14)' },
      },
    ];
    if (data.drawdown.secondary?.length) {
      series.push({
        name: `${data.secondary_name || '对照'}回撤`,
        type: 'line',
        data: data.drawdown.secondary,
        showSymbol: false,
        lineStyle: { color: '#0F223D', width: 1.5 },
      });
    }
    if (data.drawdown.hs300?.length) {
      series.push({
        name: '沪深300回撤',
        type: 'line',
        data: data.drawdown.hs300,
        showSymbol: false,
        lineStyle: { color: '#94A3B8', width: 1.2, type: 'dotted' },
      });
    }
    return {
      tooltip: { trigger: 'axis', valueFormatter: (v: unknown) => `${Number(v).toFixed(2)}%` },
      legend: { top: 0, right: 0, type: 'scroll', textStyle: { fontSize: 11, color: '#475569' } },
      grid: { top: 36, left: 46, right: 14, bottom: 26 },
      xAxis: {
        type: 'category',
        data: data.dates,
        boundaryGap: false,
        axisLabel: { color: '#64748B', fontSize: 10, formatter: (v: string) => v.slice(0, 7) },
      },
      yAxis: {
        type: 'value',
        max: 0,
        axisLabel: { color: '#64748B', fontSize: 10, formatter: '{value}%' },
        splitLine: { lineStyle: { color: '#F1F5F9' } },
      },
      series,
    };
  }, [data]);

  const allocOption = useMemo<echarts.EChartsCoreOption>(() => {
    if (!data || !data.dates.length) return {};
    return {
      tooltip: { trigger: 'axis', valueFormatter: (v: unknown) => `${Number(v).toFixed(1)}%` },
      legend: { top: 0, right: 0, type: 'scroll', textStyle: { fontSize: 11, color: '#475569' } },
      grid: { top: 36, left: 42, right: 14, bottom: 26 },
      xAxis: {
        type: 'category',
        data: data.dates,
        boundaryGap: false,
        axisLabel: { color: '#64748B', fontSize: 10, formatter: (v: string) => v.slice(0, 7) },
      },
      yAxis: {
        type: 'value',
        min: 0,
        max: 100,
        axisLabel: { color: '#64748B', fontSize: 10, formatter: '{value}%' },
        splitLine: { lineStyle: { color: '#F1F5F9' } },
      },
      series: [
        { name: 'A股权益仓位', type: 'line', stack: 'alloc', showSymbol: false, lineStyle: { width: 0.5 }, areaStyle: { color: 'rgba(248, 113, 113, 0.35)' }, itemStyle: { color: '#F87171' }, data: data.allocation.ashare },
        { name: '纯债避风港', type: 'line', stack: 'alloc', showSymbol: false, lineStyle: { width: 0.5 }, areaStyle: { color: 'rgba(59, 130, 246, 0.55)' }, itemStyle: { color: '#3B82F6' }, data: data.allocation.bond },
        { name: '黄金对冲气垫', type: 'line', stack: 'alloc', showSymbol: false, lineStyle: { width: 0.5 }, areaStyle: { color: 'rgba(245, 158, 11, 0.65)' }, itemStyle: { color: '#F59E0B' }, data: data.allocation.gold },
        { name: '海外标普对冲', type: 'line', stack: 'alloc', showSymbol: false, lineStyle: { width: 0.5 }, areaStyle: { color: 'rgba(139, 92, 246, 0.60)' }, itemStyle: { color: '#8B5CF6' }, data: data.allocation.spx },
      ],
    };
  }, [data]);

  const pcrCompareOption = useMemo<echarts.EChartsCoreOption>(() => {
    const rows = data?.weight_vs_pcr || [];
    if (!rows.length) return {};
    return {
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'shadow' },
        backgroundColor: 'rgba(15,23,42,0.94)',
        borderWidth: 0,
        textStyle: { color: '#F8FAFC', fontSize: 12 },
        formatter: (params: unknown) => {
          const list = Array.isArray(params) ? params : [];
          if (!list.length) return '';
          const idx = Number((list[0] as { dataIndex?: number }).dataIndex ?? 0);
          const item = rows[idx];
          if (!item) return '';
          const pcrColor = item.pcr_pct < 0 ? '#34D399' : '#FBBF24';
          const pcrNote = item.pcr_pct < 0 ? '（负相关对冲）' : '';
          return `
            <div style="font-weight:700;margin-bottom:4px;">${item.fund_name} (${item.fund_code})</div>
            <div style="color:#94A3B8;font-size:11px;margin-bottom:4px;">风格桶：${item.bucket_label}</div>
            <div>资金配置占比：<strong>${item.weight_pct.toFixed(1)}%</strong></div>
            <div>真实风险贡献 (PCR)：<strong style="color:${pcrColor};">${item.pcr_pct.toFixed(1)}%${pcrNote}</strong></div>
          `;
        },
      },
      legend: { top: 0, right: 0, textStyle: { fontSize: 11, color: '#475569' } },
      grid: { top: 38, left: 42, right: 14, bottom: 52 },
      xAxis: {
        type: 'category',
        data: rows.map((r) => r.short_name),
        axisLabel: { color: '#475569', fontSize: 10, interval: 0, rotate: rows.length >= 6 ? 18 : 0 },
      },
      yAxis: {
        type: 'value',
        axisLabel: { color: '#64748B', fontSize: 10, formatter: '{value}%' },
        splitLine: { lineStyle: { color: '#F1F5F9' } },
      },
      series: [
        {
          name: '资金占比 (%)',
          type: 'bar',
          barMaxWidth: 20,
          data: rows.map((r) => r.weight_pct),
          itemStyle: { color: '#1D4ED8', borderRadius: [4, 4, 0, 0] },
        },
        {
          name: '风险贡献 PCR (%)',
          type: 'bar',
          barMaxWidth: 20,
          data: rows.map((r) => ({
            value: r.pcr_pct,
            itemStyle:
              r.pcr_pct < 0
                ? { color: '#059669', borderRadius: [0, 0, 4, 4] }
                : { color: '#D97706', borderRadius: [4, 4, 0, 0] },
          })),
        },
      ],
    };
  }, [data]);

  const hasPcrChart = Boolean(data?.weight_vs_pcr && data.weight_vs_pcr.length > 0);

  if (loading) {
    return (
      <div className="inst-panel rounded-lg p-8 text-center text-xs text-slate-400">
        正在加载真实复权净值、动态回撤与风险贡献结构图...
      </div>
    );
  }
  if (!data || !data.dates.length) return null;

  return (
    <div className="space-y-4">
      {staleHint && (
        <div className="inst-panel rounded-lg px-3.5 py-2 border-l-4 border-l-amber-500 text-xs text-amber-900 font-medium">
          {staleHint}
        </div>
      )}

      {/* 累计净值对比 */}
      <div className="inst-panel rounded-lg p-4 sm:p-5 space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex flex-wrap items-center gap-2">
            <h3 className="text-sm font-bold text-slate-900">
              {data.period_label || '所选周期'}累计净值对比（起始归一化 1.000）
            </h3>
            <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-slate-100 text-slate-700 border border-slate-200">
              {data.primary_name}
            </span>
          </div>
          <span className="text-[11px] font-mono text-slate-400">{data.date_range}</span>
        </div>
        <EChartBox option={navOption} height={350} />
      </div>

      {/* 下方双图：动态回撤对比 + 资金占比 vs 真实风险贡献(PCR)对照 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="inst-panel rounded-lg p-4 sm:p-5 space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="text-xs font-bold text-slate-900">动态回撤对比（水下深度）</h3>
            <span className="text-[11px] text-slate-400">95% 实盘校准口径</span>
          </div>
          <EChartBox option={ddOption} height={260} />
        </div>

        <div className="inst-panel rounded-lg p-4 sm:p-5 space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="text-xs font-bold text-slate-900">
              {hasPcrChart ? '资金占比 vs 真实风险贡献 (PCR)' : '资产仓位变迁（大类配比）'}
              {hasPcrChart && <MetricTooltip specKey="pcr" align="right" />}
            </h3>
            <span className="text-[11px] text-slate-400">Ledoit-Wolf 协方差分解</span>
          </div>
          <EChartBox option={hasPcrChart ? pcrCompareOption : allocOption} height={260} />
        </div>
      </div>
    </div>
  );
}

import { useMemo } from 'react';
import type * as echarts from 'echarts';
import type { BacktestCurvesResponse } from '../../api/client';
import { EChartBox } from '../EChartBox';
import { ChartReadingGuide } from '../ChartReadingGuide';

interface BacktestChartsProps {
  data: BacktestCurvesResponse | null;
  loading: boolean;
}

export function BacktestCharts({ data, loading }: BacktestChartsProps) {
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
        axisLabel: { color: '#64748B', fontSize: 10, formatter: (v: string) => v.slice(0, 4) },
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
        axisLabel: { color: '#64748B', fontSize: 10, formatter: (v: string) => v.slice(0, 4) },
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

  if (loading) {
    return (
      <div className="card-elevated rounded-2xl p-6 text-center text-xs text-slate-500">
        正在加载 2018–2026 全周期净值、动态回撤与资产仓位变迁曲线...
      </div>
    );
  }
  if (!data || !data.dates.length) return null;

  return (
    <div className="space-y-4">
      {/* 累计净值对比 */}
      <div className="card-elevated rounded-2xl p-5 space-y-3.5">
        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <span className="w-1 h-4 rounded-full bg-red-600" />
            <h3 className="text-base font-bold text-slate-900">
              {data.period_label || '所选周期'}累计净值对比（起始归一化 1.000）
            </h3>
          </div>
          <span className="text-[11px] text-slate-400">{data.date_range || '支持鼠标悬停对比各阶段净值'}</span>
        </div>
        <ChartReadingGuide
          howToRead="对比 2018 至今跨越牛熊周期的累计净值增长（背景色块对应 7 大宏观牛熊风格切片与样本外盲测金库）。"
          actionSignal="若策略曲线斜率更稳、熊市切片期跌幅显著小于沪深300基准，可安心按目标权重长期持有。"
        />
        <EChartBox option={navOption} height={350} />
      </div>

      {/* 下方双图：动态回撤对比 + 资产仓位变迁 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="card-elevated rounded-2xl p-5 space-y-3">
          <div className="flex items-center gap-2">
            <span className="w-1 h-4 rounded-full bg-emerald-600" />
            <h3 className="text-sm font-bold text-slate-900">动态回撤对比（水下深度）</h3>
          </div>
          <ChartReadingGuide
            howToRead="曲线越贴近 0% 说明抗跌能力越强，深坑越浅越容易拿得住。"
            actionSignal="若当前回撤明显小于沪深300且处于修复期，坚持持有不轻易割肉。"
          />
          <EChartBox option={ddOption} height={260} />
        </div>

        <div className="card-elevated rounded-2xl p-5 space-y-3">
          <div className="flex items-center gap-2">
            <span className="w-1 h-4 rounded-full bg-indigo-600" />
            <h3 className="text-sm font-bold text-slate-900">资产仓位变迁（高抛低吸验证）</h3>
          </div>
          <ChartReadingGuide
            howToRead="观察高位时权益色块是否自动收缩、低位时是否自动放大。"
            actionSignal="用于验证策略是否真正做到动态风控与多元分散，而非满仓死扛。"
          />
          <EChartBox option={allocOption} height={260} />
        </div>
      </div>
    </div>
  );
}

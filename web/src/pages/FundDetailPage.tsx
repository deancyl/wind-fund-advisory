import { useEffect, useMemo, useState } from 'react';
import type * as echarts from 'echarts';
import {
  ArrowLeft,
  TrendingUp,
  BarChart3,
  PieChart,
  Users,
  FileText,
  ExternalLink,
  ShieldCheck,
} from 'lucide-react';
import { api, type FundDetailResponse } from '../api/client';
import { EChartBox } from '../components/EChartBox';

interface FundDetailPageProps {
  fundCode: string;
  onBack: () => void;
}

type DetailTab = 'trend' | 'analytics' | 'holdings' | 'managers' | 'archive';
type ChartKind = 'return' | 'nav';
type RangeKey = '3m' | '6m' | '1y' | '3y' | 'all';

const DETAIL_TABS: Array<{ id: DetailTab; label: string; icon: typeof TrendingUp }> = [
  { id: 'trend', label: '走势与定投', icon: TrendingUp },
  { id: 'analytics', label: '量化分析指标', icon: BarChart3 },
  { id: 'holdings', label: '持仓与行业分布', icon: PieChart },
  { id: 'managers', label: '基金经理', icon: Users },
  { id: 'archive', label: '档案 · 公告 · 规则', icon: FileText },
];

const RANGE_OPTIONS: Array<{ id: RangeKey; label: string; ratio: number }> = [
  { id: '3m', label: '近3月', ratio: 0.08 },
  { id: '6m', label: '近6月', ratio: 0.16 },
  { id: '1y', label: '近1年', ratio: 0.3 },
  { id: '3y', label: '近3年', ratio: 0.7 },
  { id: 'all', label: '成立以来', ratio: 1.0 },
];

export function FundDetailPage({ fundCode, onBack }: FundDetailPageProps) {
  const [data, setData] = useState<FundDetailResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [tab, setTab] = useState<DetailTab>('trend');
  const [chartKind, setChartKind] = useState<ChartKind>('return');
  const [rangeKey, setRangeKey] = useState<RangeKey>('1y');
  const [dcaMonthly, setDcaMonthly] = useState(1000);

  useEffect(() => {
    let alive = true;
    setLoading(true);
    setError('');
    api
      .getFundDetail(fundCode, dcaMonthly)
      .then((res) => {
        if (alive) setData(res);
      })
      .catch((e) => {
        if (alive) setError(e instanceof Error ? e.message : '加载基金详情失败');
      })
      .finally(() => {
        if (alive) setLoading(false);
      });
    return () => {
      alive = false;
    };
  }, [fundCode, dcaMonthly]);

  const slicedChart = useMemo(() => {
    if (!data || !data.charts.dates.length) return null;
    const { dates, unit_nav, ac_nav } = data.charts;
    const total = dates.length;
    const daysMap: Record<RangeKey, number> = { '3m': 90, '6m': 180, '1y': 365, '3y': 1095, all: 99999 };
    const lastTs = new Date(dates[total - 1]).getTime();
    const cutoff = lastTs - daysMap[rangeKey] * 86400 * 1000;
    let startIdx = 0;
    if (rangeKey !== 'all') {
      startIdx = dates.findIndex((d) => new Date(d).getTime() >= cutoff);
      if (startIdx < 0) startIdx = 0;
    }
    const sDates = dates.slice(startIdx);
    const sUnit = unit_nav.slice(startIdx);
    const sAc = ac_nav.slice(startIdx);
    const baseAc = sAc[0] > 0 ? sAc[0] : 1;
    const sRet = sAc.map((v) => Number((((v / baseAc) - 1) * 100).toFixed(2)));
    return { dates: sDates, unit: sUnit, ac: sAc, ret: sRet };
  }, [data, rangeKey]);

  const mainChartOption = useMemo<echarts.EChartsCoreOption>(() => {
    if (!slicedChart) return {};
    if (chartKind === 'return') {
      const lastRet = slicedChart.ret[slicedChart.ret.length - 1] ?? 0;
      const color = lastRet >= 0 ? '#DC2626' : '#059669';
      return {
        tooltip: { trigger: 'axis', valueFormatter: (v: unknown) => `${Number(v) >= 0 ? '+' : ''}${Number(v).toFixed(2)}%` },
        grid: { top: 28, left: 50, right: 18, bottom: 28 },
        xAxis: {
          type: 'category',
          data: slicedChart.dates,
          boundaryGap: false,
          axisLabel: { color: '#64748B', fontSize: 11, formatter: (v: string) => v.slice(0, 7) },
        },
        yAxis: {
          type: 'value',
          scale: true,
          axisLabel: { color: '#64748B', fontSize: 11, formatter: '{value}%' },
          splitLine: { lineStyle: { color: '#F1F5F9' } },
        },
        series: [
          {
            name: '累计收益率',
            type: 'line',
            data: slicedChart.ret,
            showSymbol: false,
            lineStyle: { color, width: 2.2 },
            areaStyle: { color: lastRet >= 0 ? 'rgba(220, 38, 38, 0.10)' : 'rgba(5, 150, 105, 0.10)' },
          },
        ],
      };
    }
    return {
      tooltip: { trigger: 'axis' },
      legend: { top: 0, right: 0, textStyle: { fontSize: 11, color: '#475569' } },
      grid: { top: 36, left: 50, right: 18, bottom: 28 },
      xAxis: {
        type: 'category',
        data: slicedChart.dates,
        boundaryGap: false,
        axisLabel: { color: '#64748B', fontSize: 11, formatter: (v: string) => v.slice(0, 7) },
      },
      yAxis: {
        type: 'value',
        scale: true,
        axisLabel: { color: '#64748B', fontSize: 11 },
        splitLine: { lineStyle: { color: '#F1F5F9' } },
      },
      series: [
        { name: '单位净值', type: 'line', data: slicedChart.unit, showSymbol: false, lineStyle: { color: '#1D4ED8', width: 2.2 } },
        { name: '累计净值', type: 'line', data: slicedChart.ac, showSymbol: false, lineStyle: { color: '#D97706', width: 1.8, type: 'dashed' } },
      ],
    };
  }, [slicedChart, chartKind]);

  const radarOption = useMemo<echarts.EChartsCoreOption>(() => {
    const cats = data?.analytics?.categories || [];
    if (!cats.length) return {};
    return {
      tooltip: {},
      radar: {
        indicator: cats.map((c) => ({ name: c.name, max: 100 })),
        radius: '68%',
        axisName: { color: '#334155', fontSize: 12, fontWeight: 600 },
      },
      series: [
        {
          type: 'radar',
          data: [
            {
              value: cats.map((c) => c.score),
              name: data?.fund_name || '综合能力',
              areaStyle: { color: 'rgba(29, 78, 216, 0.18)' },
              lineStyle: { color: '#1D4ED8', width: 2 },
              itemStyle: { color: '#1D4ED8' },
            },
          ],
        },
      ],
    };
  }, [data]);

  const industryOption = useMemo<echarts.EChartsCoreOption>(() => {
    const list = (data?.holdings_distribution?.industry_distribution || []).slice().reverse();
    if (!list.length) return {};
    return {
      tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' }, valueFormatter: (v: unknown) => `${Number(v).toFixed(2)}%` },
      grid: { top: 12, left: 95, right: 24, bottom: 24 },
      xAxis: { type: 'value', axisLabel: { color: '#64748B', fontSize: 11, formatter: '{value}%' } },
      yAxis: { type: 'category', data: list.map((x) => x.industry), axisLabel: { color: '#334155', fontSize: 11 } },
      series: [
        {
          type: 'bar',
          barMaxWidth: 14,
          data: list.map((x) => x.weight_pct),
          itemStyle: { color: '#0D9488', borderRadius: [0, 4, 4, 0] },
        },
      ],
    };
  }, [data]);

  if (loading && !data) {
    return (
      <div className="space-y-4 fade-in">
        <button type="button" onClick={onBack} className="inline-flex items-center gap-1.5 text-xs font-semibold text-blue-700 hover:underline cursor-pointer">
          <ArrowLeft className="w-4 h-4" /> 返回上一页
        </button>
        <div className="card-elevated rounded-2xl p-12 text-center text-sm text-slate-500">
          正在实时拉取基金 {fundCode} 的历史净值、量化指标、持仓与档案数据...
        </div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="space-y-4 fade-in">
        <button type="button" onClick={onBack} className="inline-flex items-center gap-1.5 text-xs font-semibold text-blue-700 hover:underline cursor-pointer">
          <ArrowLeft className="w-4 h-4" /> 返回上一页
        </button>
        <div className="card-elevated rounded-2xl p-8 text-center text-sm text-red-600">{error || '未能获取基金详情'}</div>
      </div>
    );
  }

  const dayUp = data.daily_return_pct >= 0;

  return (
    <div className="space-y-6 fade-in">
      {/* 顶部返回 + 深海墨蓝基金档案头 */}
      <div className="hero-navy text-white rounded-2xl p-5 sm:p-6 shadow-lg border border-[#1E3A5F] space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <button
            type="button"
            onClick={onBack}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-white/10 border border-white/15 text-slate-100 hover:bg-white/20 cursor-pointer"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            <span>返回工作台</span>
          </button>
          <div className="flex flex-wrap items-center gap-2 text-xs">
            <span className="px-2.5 py-0.5 rounded-full bg-white/10 border border-white/15 text-slate-200">{data.fund_type}</span>
            <span className="px-2.5 py-0.5 rounded-full bg-amber-400/20 text-amber-300 border border-amber-400/30 font-semibold">
              {data.risk_level}
            </span>
            {data.is_fallback && (
              <span className="px-2.5 py-0.5 rounded-full bg-rose-500/20 text-rose-200">离线快照</span>
            )}
          </div>
        </div>

        <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
          <div>
            <div className="flex items-baseline gap-2.5">
              <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-white">{data.fund_name}</h1>
              <span className="font-mono text-sm text-slate-300">{data.fund_code}</span>
            </div>
            <p className="text-xs text-slate-300 mt-1">
              {data.profile.company} · 成立日 {data.profile.establish_date}
              {data.profile.scale_yi !== null ? ` · 最新规模 ¥${data.profile.scale_yi} 亿` : ''}
            </p>
          </div>

          <div className="flex items-end gap-6 tabular-nums">
            <div>
              <div className="text-[11px] text-slate-300">最新单位净值 ({data.nav_date || '--'})</div>
              <div className="text-2xl font-extrabold text-white mt-0.5">{data.latest_nav.toFixed(4)}</div>
            </div>
            <div>
              <div className="text-[11px] text-slate-300">日涨跌幅</div>
              <div className={`text-2xl font-extrabold mt-0.5 ${dayUp ? 'text-rose-400' : 'text-emerald-400'}`}>
                {dayUp ? '+' : ''}
                {data.daily_return_pct.toFixed(2)}%
              </div>
            </div>
            <div className="hidden sm:block">
              <div className="text-[11px] text-slate-300">累计净值</div>
              <div className="text-lg font-bold text-slate-200 mt-0.5">{data.latest_ac_nav.toFixed(4)}</div>
            </div>
          </div>
        </div>
      </div>

      {/* 5 大详情标签导航 */}
      <div className="flex flex-wrap items-center gap-1.5 bg-white p-1.5 rounded-2xl border border-slate-200 shadow-xs">
        {DETAIL_TABS.map(({ id, label, icon: Icon }) => {
          const active = tab === id;
          return (
            <button
              key={id}
              type="button"
              onClick={() => setTab(id)}
              className={`flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-semibold transition-all cursor-pointer ${
                active ? 'bg-[#0A192F] text-white shadow-xs' : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900'
              }`}
            >
              <Icon className="w-3.5 h-3.5" />
              <span>{label}</span>
            </button>
          );
        })}
      </div>

      {/* ==================== Tab 1: 走势与定投 ==================== */}
      {tab === 'trend' && (
        <div className="space-y-6 fade-in">
          {/* 业绩走势 & 单位净值双图 */}
          <section className="card-elevated rounded-2xl p-5 space-y-4">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div className="inline-flex items-center gap-1 bg-slate-100 p-1 rounded-xl border border-slate-200">
                <button
                  type="button"
                  onClick={() => setChartKind('return')}
                  className={`px-3 py-1 rounded-lg text-xs font-semibold cursor-pointer ${
                    chartKind === 'return' ? 'bg-white text-slate-900 shadow-xs' : 'text-slate-600'
                  }`}
                >
                  业绩走势（累计收益）
                </button>
                <button
                  type="button"
                  onClick={() => setChartKind('nav')}
                  className={`px-3 py-1 rounded-lg text-xs font-semibold cursor-pointer ${
                    chartKind === 'nav' ? 'bg-white text-slate-900 shadow-xs' : 'text-slate-600'
                  }`}
                >
                  单位净值 / 累计净值
                </button>
              </div>

              <div className="inline-flex items-center gap-1 bg-slate-100 p-1 rounded-xl border border-slate-200">
                {RANGE_OPTIONS.map((r) => (
                  <button
                    key={r.id}
                    type="button"
                    onClick={() => setRangeKey(r.id)}
                    className={`px-2.5 py-1 rounded-lg text-xs font-semibold cursor-pointer ${
                      rangeKey === r.id ? 'bg-[#0A192F] text-white' : 'text-slate-600 hover:text-slate-900'
                    }`}
                  >
                    {r.label}
                  </button>
                ))}
              </div>
            </div>
            <EChartBox option={mainChartOption} height={320} />
          </section>

          {/* 历史业绩 + 定投收益测算 并排/上下 */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
            {/* 历史业绩表 */}
            <section className="card-elevated rounded-2xl p-5 space-y-3">
              <h2 className="text-base font-bold text-slate-900">历史业绩表现</h2>
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs tabular-nums">
                  <thead>
                    <tr className="border-b border-slate-200 text-slate-500">
                      <th className="py-2 pr-2 font-semibold">统计区间</th>
                      <th className="py-2 px-2 text-right font-semibold">本基金</th>
                      <th className="py-2 px-2 text-right font-semibold">同期沪深300</th>
                      <th className="py-2 pl-2 text-right font-semibold">超额收益</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {data.historical_performance.map((r) => (
                      <tr key={r.period}>
                        <td className="py-2.5 pr-2 font-medium text-slate-800">{r.period}</td>
                        <td className={`py-2.5 px-2 text-right font-bold ${r.fund_return_pct >= 0 ? 'text-red-600' : 'text-emerald-600'}`}>
                          {r.fund_return_pct >= 0 ? '+' : ''}
                          {r.fund_return_pct.toFixed(2)}%
                        </td>
                        <td className="py-2.5 px-2 text-right text-slate-500">
                          {r.benchmark_return_pct === null ? '--' : `${r.benchmark_return_pct >= 0 ? '+' : ''}${r.benchmark_return_pct.toFixed(2)}%`}
                        </td>
                        <td className={`py-2.5 pl-2 text-right font-semibold ${(r.excess_return_pct ?? 0) >= 0 ? 'text-red-600' : 'text-emerald-600'}`}>
                          {r.excess_return_pct === null ? '--' : `${r.excess_return_pct >= 0 ? '+' : ''}${r.excess_return_pct.toFixed(2)}%`}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>

            {/* 定投收益测算表 */}
            <section className="card-elevated rounded-2xl p-5 space-y-3">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <h2 className="text-base font-bold text-slate-900">历史定投收益测算</h2>
                <div className="flex items-center gap-1.5 text-xs">
                  <span className="text-slate-500">每月定投</span>
                  {[500, 1000, 2000, 5000].map((v) => (
                    <button
                      key={v}
                      type="button"
                      onClick={() => setDcaMonthly(v)}
                      className={`px-2 py-0.5 rounded-lg font-semibold tabular-nums cursor-pointer ${
                        dcaMonthly === v ? 'bg-blue-600 text-white' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                      }`}
                    >
                      ¥{v}
                    </button>
                  ))}
                </div>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs tabular-nums">
                  <thead>
                    <tr className="border-b border-slate-200 text-slate-500">
                      <th className="py-2 pr-2 font-semibold">定投周期</th>
                      <th className="py-2 px-2 text-right font-semibold">累计投入</th>
                      <th className="py-2 px-2 text-right font-semibold">期末市值</th>
                      <th className="py-2 px-2 text-right font-semibold">定投收益率</th>
                      <th className="py-2 pl-2 text-right font-semibold">近似年化</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {data.dca_simulation.map((d) => (
                      <tr key={d.period}>
                        <td className="py-2.5 pr-2 font-medium text-slate-800">
                          {d.period} <span className="text-slate-400">({d.periods}期)</span>
                        </td>
                        <td className="py-2.5 px-2 text-right text-slate-600">¥{d.total_invested.toLocaleString()}</td>
                        <td className="py-2.5 px-2 text-right font-bold text-slate-900">¥{d.final_value.toLocaleString()}</td>
                        <td className={`py-2.5 px-2 text-right font-bold ${d.return_pct >= 0 ? 'text-red-600' : 'text-emerald-600'}`}>
                          {d.return_pct >= 0 ? '+' : ''}
                          {d.return_pct.toFixed(2)}%
                        </td>
                        <td className="py-2.5 pl-2 text-right font-semibold text-slate-700">
                          {d.annualized_pct >= 0 ? '+' : ''}
                          {d.annualized_pct.toFixed(2)}%
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <p className="text-[11px] text-slate-400">按历史每月首个交易日真实净值模拟扣款测算，不含申购费优惠差异，仅供参考。</p>
            </section>
          </div>

          {/* 历史净值明细表 */}
          <section className="card-elevated rounded-2xl overflow-hidden">
            <div className="p-4 sm:px-5 border-b border-slate-200">
              <h2 className="text-base font-bold text-slate-900">历史净值明细（最近 30 个交易日）</h2>
            </div>
            <div className="table-wrapper">
              <table className="text-left text-xs tabular-nums">
                <thead>
                  <tr className="border-b border-slate-200 bg-slate-50 text-slate-500">
                    <th className="py-2.5 px-4 font-semibold">净值日期</th>
                    <th className="py-2.5 px-4 text-right font-semibold">单位净值</th>
                    <th className="py-2.5 px-4 text-right font-semibold">累计净值</th>
                    <th className="py-2.5 px-4 text-right font-semibold">日涨跌幅</th>
                    <th className="py-2.5 px-4 font-semibold">分红送配</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {data.historical_nav.map((r) => (
                    <tr key={r.date} className="hover:bg-slate-50/80">
                      <td className="py-2.5 px-4 font-mono text-slate-700">{r.date}</td>
                      <td className="py-2.5 px-4 text-right font-semibold text-slate-900">{r.unit_nav.toFixed(4)}</td>
                      <td className="py-2.5 px-4 text-right text-slate-600">{r.ac_nav.toFixed(4)}</td>
                      <td className={`py-2.5 px-4 text-right font-bold ${r.daily_return_pct >= 0 ? 'text-red-600' : 'text-emerald-600'}`}>
                        {r.daily_return_pct >= 0 ? '+' : ''}
                        {r.daily_return_pct.toFixed(2)}%
                      </td>
                      <td className="py-2.5 px-4 text-slate-500">{r.dividend || '--'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        </div>
      )}

      {/* ==================== Tab 2: 量化分析指标 ==================== */}
      {tab === 'analytics' && (
        <div className="space-y-6 fade-in">
          {/* 大类四维能力评估 + 雷达图 */}
          <section className="grid grid-cols-1 lg:grid-cols-5 gap-5">
            <div className="lg:col-span-2 card-elevated rounded-2xl p-5 flex flex-col justify-between">
              <div>
                <h2 className="text-base font-bold text-slate-900">四维综合能力画像</h2>
                <p className="text-xs text-slate-500 mt-0.5">统计窗口：{data.analytics?.window_label || '近 3 年'}</p>
              </div>
              <EChartBox option={radarOption} height={260} />
            </div>

            <div className="lg:col-span-3 card-elevated rounded-2xl p-5 space-y-4">
              <h2 className="text-base font-bold text-slate-900">大类评估（跟踪性价比 · 抗下跌 · 抗波动 · 跟踪误差）</h2>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5">
                {(data.analytics?.categories || []).map((c) => (
                  <div key={c.key} className="p-4 rounded-xl bg-slate-50 border border-slate-200 space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="font-bold text-sm text-slate-900">{c.name}</span>
                      <span className="px-2 py-0.5 rounded-full text-xs font-bold bg-blue-50 text-blue-700">
                        {c.score} 分 · {c.grade}
                      </span>
                    </div>
                    <div className="h-2 rounded-full bg-slate-200 overflow-hidden">
                      <div className="h-full rounded-full bg-blue-600" style={{ width: `${c.score}%` }} />
                    </div>
                    <p className="text-xs text-slate-500">{c.desc}</p>
                  </div>
                ))}
              </div>
            </div>
          </section>

          {/* 小类四组 8 项专业量化指标 */}
          {data.analytics?.sub_metrics && (
            <section className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {[
                { title: '收益能力', color: 'border-t-red-500', items: data.analytics.sub_metrics.return_ability },
                { title: '风险控制', color: 'border-t-emerald-600', items: data.analytics.sub_metrics.risk_control },
                { title: '跟踪能力', color: 'border-t-indigo-600', items: data.analytics.sub_metrics.tracking_ability },
                { title: '风险收益性价比', color: 'border-t-amber-500', items: data.analytics.sub_metrics.cost_performance },
              ].map((grp) => (
                <div key={grp.title} className={`card-elevated rounded-2xl p-5 border-t-4 ${grp.color} space-y-3`}>
                  <h3 className="text-sm font-bold text-slate-900">{grp.title}</h3>
                  <div className="space-y-2.5">
                    {grp.items.map((m) => (
                      <div key={m.name} className="p-3 rounded-xl bg-slate-50 border border-slate-100">
                        <div className="flex items-baseline justify-between gap-2">
                          <span className="text-xs font-semibold text-slate-700">{m.name}</span>
                          <span className="text-base font-extrabold text-slate-900 tabular-nums">{m.value}</span>
                        </div>
                        <p className="text-[11px] text-slate-500 mt-1">{m.hint}</p>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </section>
          )}
        </div>
      )}

      {/* ==================== Tab 3: 持仓与行业分布 ==================== */}
      {tab === 'holdings' && (
        <div className="space-y-6 fade-in">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
            {/* 资产配置占比 */}
            <section className="card-elevated rounded-2xl p-5 space-y-3.5">
              <h2 className="text-base font-bold text-slate-900">资产配置结构（股票 / 债券 / 现金）</h2>
              {data.holdings_distribution.asset_allocation.length === 0 ? (
                <p className="text-xs text-slate-500">该基金暂未披露最新季报大类配置明细。</p>
              ) : (
                <div className="space-y-3 pt-1">
                  {data.holdings_distribution.asset_allocation.map((a) => (
                    <div key={a.name} className="space-y-1">
                      <div className="flex justify-between text-xs">
                        <span className="font-medium text-slate-700">{a.name}</span>
                        <span className="font-bold text-slate-900 tabular-nums">{a.pct.toFixed(2)}%</span>
                      </div>
                      <div className="h-2 rounded-full bg-slate-100 overflow-hidden">
                        <div className="h-full rounded-full bg-[#1D4ED8]" style={{ width: `${Math.min(100, Math.max(0, a.pct))}%` }} />
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </section>

            {/* 行业分布 */}
            <section className="card-elevated rounded-2xl p-5 space-y-3">
              <h2 className="text-base font-bold text-slate-900">行业分布透视</h2>
              {data.holdings_distribution.industry_distribution.length === 0 ? (
                <p className="text-xs text-slate-500">纯债或联接基金以债券/底层ETF为主，无直接申万股票行业分布。</p>
              ) : (
                <EChartBox option={industryOption} height={240} />
              )}
            </section>
          </div>

          {/* 前十大重仓股票 */}
          <section className="card-elevated rounded-2xl overflow-hidden">
            <div className="p-4 sm:px-5 border-b border-slate-200 flex items-center justify-between">
              <h2 className="text-base font-bold text-slate-900">前十大重仓股票</h2>
              <span className="text-xs text-slate-400">{data.holdings_distribution.quarter_label}</span>
            </div>
            {data.holdings_distribution.top_stocks.length === 0 ? (
              <div className="p-6 text-xs text-slate-500">该基金为债券型/黄金型/ETF联接基金，最新季报未直接持有个股。</div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs tabular-nums">
                  <thead>
                    <tr className="border-b border-slate-200 bg-slate-50 text-slate-500">
                      <th className="py-2.5 px-4 font-semibold">股票代码</th>
                      <th className="py-2.5 px-4 font-semibold">股票名称</th>
                      <th className="py-2.5 px-4 text-right font-semibold">占净值比例</th>
                      <th className="py-2.5 px-4 text-right font-semibold">持股数 (万股)</th>
                      <th className="py-2.5 px-4 text-right font-semibold">持仓市值 (万元)</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {data.holdings_distribution.top_stocks.map((s) => (
                      <tr key={s.stock_code} className="hover:bg-slate-50/80">
                        <td className="py-2.5 px-4 font-mono text-slate-500">{s.stock_code}</td>
                        <td className="py-2.5 px-4 font-semibold text-slate-900">{s.stock_name}</td>
                        <td className="py-2.5 px-4 text-right font-bold text-blue-700">{s.weight_pct.toFixed(2)}%</td>
                        <td className="py-2.5 px-4 text-right text-slate-600">{s.shares_wan || '--'}</td>
                        <td className="py-2.5 px-4 text-right text-slate-600">{s.value_wan || '--'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>
        </div>
      )}

      {/* ==================== Tab 4: 基金经理（含历任） ==================== */}
      {tab === 'managers' && (
        <section className="card-elevated rounded-2xl overflow-hidden fade-in">
          <div className="p-4 sm:px-5 border-b border-slate-200">
            <h2 className="text-base font-bold text-slate-900">基金经理介绍与历任变动记录（共 {data.managers.length} 任）</h2>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs tabular-nums">
              <thead>
                <tr className="border-b border-slate-200 bg-slate-50 text-slate-500">
                  <th className="py-3 px-4 font-semibold">状态</th>
                  <th className="py-3 px-4 font-semibold">基金经理</th>
                  <th className="py-3 px-4 font-semibold">任职起始</th>
                  <th className="py-3 px-4 font-semibold">任职截止</th>
                  <th className="py-3 px-4 text-right font-semibold">任职天数</th>
                  <th className="py-3 px-4 text-right font-semibold">任职回报</th>
                  <th className="py-3 px-4 font-semibold">从业资历 / 在管规模</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {data.managers.map((m, idx) => (
                  <tr key={`${m.name}-${idx}`} className={m.is_current ? 'bg-blue-50/40' : ''}>
                    <td className="py-3 px-4">
                      <span
                        className={`px-2 py-0.5 rounded-full text-[11px] font-semibold ${
                          m.is_current ? 'bg-blue-600 text-white' : 'bg-slate-100 text-slate-500'
                        }`}
                      >
                        {m.is_current ? '现任' : '历任'}
                      </span>
                    </td>
                    <td className="py-3 px-4 font-bold text-slate-900">{m.name}</td>
                    <td className="py-3 px-4 font-mono text-slate-600">{m.start_date}</td>
                    <td className="py-3 px-4 font-mono text-slate-600">{m.end_date}</td>
                    <td className="py-3 px-4 text-right text-slate-700">{m.days} 天</td>
                    <td className={`py-3 px-4 text-right font-bold ${(m.return_pct ?? 0) >= 0 ? 'text-red-600' : 'text-emerald-600'}`}>
                      {m.return_pct === null ? '--' : `${m.return_pct >= 0 ? '+' : ''}${m.return_pct.toFixed(2)}%`}
                    </td>
                    <td className="py-3 px-4 text-slate-500">
                      {m.work_time || m.fund_size ? `${m.work_time} ${m.fund_size}` : '--'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {/* ==================== Tab 5: 档案 · 公告 · 概要 · 交易规则 ==================== */}
      {tab === 'archive' && (
        <div className="space-y-6 fade-in">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
            {/* 基金档案 & 产品概要 */}
            <section className="card-elevated rounded-2xl p-5 space-y-3">
              <div className="flex items-center justify-between">
                <h2 className="text-base font-bold text-slate-900">基金档案与产品概要</h2>
                <a
                  href={data.product_summary.official_summary_url}
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex items-center gap-1 text-xs font-semibold text-blue-700 hover:underline"
                >
                  官方档案原文 <ExternalLink className="w-3.5 h-3.5" />
                </a>
              </div>
              <dl className="grid grid-cols-1 sm:grid-cols-2 gap-x-4 gap-y-2.5 text-xs">
                {[
                  ['基金全称', data.profile.full_name],
                  ['基金代码', data.profile.fund_code],
                  ['基金类型', data.profile.fund_type],
                  ['成立日期', data.profile.establish_date],
                  ['最新规模', data.profile.scale_yi !== null ? `${data.profile.scale_yi} 亿元` : '--'],
                  ['基金管理人', data.profile.company],
                  ['基金托管人', data.profile.custodian],
                  ['风险等级', data.profile.risk_level],
                  ['跟踪标的', data.profile.tracking_target],
                  ['分红政策', data.product_summary.dividend_policy],
                ].map(([k, v]) => (
                  <div key={k} className="p-2.5 rounded-lg bg-slate-50">
                    <dt className="text-slate-400">{k}</dt>
                    <dd className="font-semibold text-slate-800 mt-0.5 break-all">{v || '--'}</dd>
                  </div>
                ))}
              </dl>
              <div className="p-3 rounded-xl bg-slate-50 text-xs">
                <div className="text-slate-400">业绩比较基准</div>
                <div className="font-medium text-slate-700 mt-0.5">{data.profile.benchmark}</div>
              </div>
            </section>

            {/* 交易规则与费率 */}
            <section className="card-elevated rounded-2xl p-5 space-y-3.5">
              <div className="flex items-center gap-2">
                <ShieldCheck className="w-4 h-4 text-blue-700" />
                <h2 className="text-base font-bold text-slate-900">交易规则与费率明细</h2>
              </div>
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-2.5 text-xs">
                <div className="p-2.5 rounded-lg bg-slate-50">
                  <div className="text-slate-400">申购 / 赎回状态</div>
                  <div className="font-semibold text-slate-800 mt-0.5">
                    {data.trading_rules.purchase_status} / {data.trading_rules.redemption_status}
                  </div>
                </div>
                <div className="p-2.5 rounded-lg bg-slate-50">
                  <div className="text-slate-400">起购 / 定投起点</div>
                  <div className="font-semibold text-slate-800 mt-0.5">
                    {data.trading_rules.min_purchase} / {data.trading_rules.min_dca}
                  </div>
                </div>
                <div className="p-2.5 rounded-lg bg-slate-50">
                  <div className="text-slate-400">申购折后费率</div>
                  <div className="font-semibold text-blue-700 mt-0.5">
                    {data.trading_rules.discount_rate} <span className="text-slate-400 font-normal">(原 {data.trading_rules.source_rate})</span>
                  </div>
                </div>
                <div className="p-2.5 rounded-lg bg-slate-50">
                  <div className="text-slate-400">年管理费</div>
                  <div className="font-semibold text-slate-800 mt-0.5">{data.trading_rules.management_fee}</div>
                </div>
                <div className="p-2.5 rounded-lg bg-slate-50">
                  <div className="text-slate-400">年托管费</div>
                  <div className="font-semibold text-slate-800 mt-0.5">{data.trading_rules.custody_fee}</div>
                </div>
                <div className="p-2.5 rounded-lg bg-slate-50">
                  <div className="text-slate-400">销售服务费</div>
                  <div className="font-semibold text-slate-800 mt-0.5">{data.trading_rules.sales_service_fee}</div>
                </div>
              </div>

              {data.trading_rules.redemption_tiers.length > 0 && (
                <div className="space-y-1.5">
                  <div className="text-xs font-semibold text-slate-700">阶梯赎回费率</div>
                  <div className="divide-y divide-slate-100 rounded-xl border border-slate-200 overflow-hidden text-xs">
                    {data.trading_rules.redemption_tiers.map((t, i) => (
                      <div key={i} className="px-3 py-2 flex justify-between bg-white">
                        <span className="text-slate-600">{t.condition}</span>
                        <span className="font-bold text-slate-900 tabular-nums">{t.rate}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              <p className="text-[11px] text-slate-500 leading-relaxed bg-amber-50/70 border border-amber-200 rounded-xl p-3">
                {data.trading_rules.settlement_note}
              </p>
            </section>
          </div>

          {/* 基金公告列表 */}
          <section className="card-elevated rounded-2xl overflow-hidden">
            <div className="p-4 sm:px-5 border-b border-slate-200 flex items-center justify-between">
              <h2 className="text-base font-bold text-slate-900">最新官方基金公告（{data.notices.length} 条）</h2>
              <a
                href={`https://fundf10.eastmoney.com/jjgg_${data.fund_code}.html`}
                target="_blank"
                rel="noreferrer"
                className="text-xs font-semibold text-blue-700 hover:underline inline-flex items-center gap-1"
              >
                全部公告 <ExternalLink className="w-3.5 h-3.5" />
              </a>
            </div>
            <div className="divide-y divide-slate-100">
              {data.notices.map((n, idx) => (
                <a
                  key={`${n.id}-${idx}`}
                  href={n.url}
                  target="_blank"
                  rel="noreferrer"
                  className="px-5 py-3 flex items-center justify-between gap-4 hover:bg-slate-50 transition-colors text-xs"
                >
                  <span className="font-medium text-slate-800 hover:text-blue-700 truncate">{n.title}</span>
                  <span className="font-mono text-slate-400 shrink-0">{n.date}</span>
                </a>
              ))}
            </div>
          </section>
        </div>
      )}
    </div>
  );
}

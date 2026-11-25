import { useEffect, useState } from 'react';
import { ArrowRight, Sparkles } from 'lucide-react';
import {
  api,
  type BacktestCurvesResponse,
  type BlueprintResponse,
  type CrowdingPoint,
  type OverviewResponse,
} from '../api/client';
import { BacktestCharts } from '../components/charts/BacktestCharts';
import { ScenarioBacktestPanel } from '../components/charts/ScenarioBacktestPanel';
import { CrowdingQuadrantChart } from '../components/charts/CrowdingQuadrantChart';

interface SignalPageProps {
  overview: OverviewResponse | null;
  ledgerId: string;
  onGoHoldings: () => void;
  onOpenProDrawer: () => void;
}

const ROLE_STYLES = [
  { bar: '#D97706', badge: 'bg-amber-50 text-amber-800 border-amber-200' },
  { bar: '#1D4ED8', badge: 'bg-blue-50 text-blue-800 border-blue-200' },
  { bar: '#0D9488', badge: 'bg-teal-50 text-teal-800 border-teal-200' },
  { bar: '#6366F1', badge: 'bg-indigo-50 text-indigo-800 border-indigo-200' },
  { bar: '#E11D48', badge: 'bg-rose-50 text-rose-800 border-rose-200' },
  { bar: '#B45309', badge: 'bg-orange-50 text-orange-800 border-orange-200' },
];

const RISK_LEVELS = [
  { id: 'C1', label: 'C1 稳健' },
  { id: 'C2', label: 'C2 偏稳' },
  { id: 'C3', label: 'C3 均衡' },
  { id: 'C4', label: 'C4 进取' },
  { id: 'C5', label: 'C5 积极' },
];

const FUND_COUNTS = [3, 4, 5, 6, 8];

const BACKTEST_PERIODS = [
  { id: '3m', label: '近 3 个月' },
  { id: '6m', label: '近 6 个月' },
  { id: '1y', label: '近 1 年' },
  { id: '2y', label: '近 2 年' },
  { id: 'all', label: '全周期' },
];

export function SignalPage({ overview, ledgerId, onGoHoldings, onOpenProDrawer }: SignalPageProps) {
  const [riskLevel, setRiskLevel] = useState('C3');
  const [amount, setAmount] = useState(50000);
  const [fundCount, setFundCount] = useState(6);
  const [modelId, setModelId] = useState('all_weather');
  const [period, setPeriod] = useState('1y');
  const [btSubTab, setBtSubTab] = useState<'full' | 'scenario'>('full');
  const [blueprint, setBlueprint] = useState<BlueprintResponse | null>(null);
  const [bpLoading, setBpLoading] = useState(false);

  const [curves, setCurves] = useState<BacktestCurvesResponse | null>(null);
  const [curvesLoading, setCurvesLoading] = useState(true);
  const [crowding, setCrowding] = useState<CrowdingPoint[]>([]);
  const [crowdingLoading, setCrowdingLoading] = useState(true);

  useEffect(() => {
    let alive = true;
    const timer = setTimeout(() => {
      setBpLoading(true);
      api
        .getBlueprint(riskLevel, Math.max(1000, amount || 50000), fundCount, modelId)
        .then((res) => {
          if (alive) setBlueprint(res);
        })
        .catch(() => {})
        .finally(() => {
          if (alive) setBpLoading(false);
        });
    }, 150);
    return () => {
      alive = false;
      clearTimeout(timer);
    };
  }, [riskLevel, amount, fundCount, modelId]);

  useEffect(() => {
    let alive = true;
    setCurvesLoading(true);
    api
      .getBacktestCurves(riskLevel, modelId, fundCount, period, 'model_live')
      .then((res) => {
        if (alive) setCurves(res);
      })
      .catch(() => {})
      .finally(() => {
        if (alive) setCurvesLoading(false);
      });
    return () => {
      alive = false;
    };
  }, [riskLevel, modelId, fundCount, period]);

  useEffect(() => {
    let alive = true;
    setCrowdingLoading(true);
    api
      .getCrowdingQuadrant(ledgerId)
      .then((res) => {
        if (alive) setCrowding(res.points || []);
      })
      .catch(() => {})
      .finally(() => {
        if (alive) setCrowdingLoading(false);
      });
    return () => {
      alive = false;
    };
  }, [ledgerId]);

  const verdict = overview?.market_verdict;
  const indices = overview?.indices || {};
  const indexCards = [
    { key: 'sh000300', fallbackName: '沪深 300', note: 'A股核心大盘风向标' },
    { key: 'sh000688', fallbackName: '科创 50', note: '硬核科技弹性指标' },
    { key: 'sh000922', fallbackName: '中证红利', note: '高股息防御底仓锚' },
  ];

  return (
    <div className="space-y-6 fade-in">
      {/* 1. 深海墨蓝投研英雄看板 */}
      <section className="hero-navy text-white rounded-2xl p-5 sm:p-7 shadow-lg border border-[#1E3A5F] space-y-5">
        <div className="flex flex-col md:flex-row md:items-start justify-between gap-5">
          <div className="space-y-2.5 max-w-3xl">
            <div className="flex flex-wrap items-center gap-2.5">
              <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-amber-400/15 text-amber-300 border border-amber-400/30">
                <span className="w-1.5 h-1.5 rounded-full bg-amber-400" />
                {verdict?.short_label || '市场信号加载中'} · {verdict?.action_tag || '量化研判'}
              </span>
              <span className="text-xs text-slate-300/85">
                {overview?.is_official_nav ? '已同步盘后官方净值' : '实时行情与估值已连接'}
              </span>
            </div>
            <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-white leading-snug">
              {verdict?.detail_explanation || '正在根据十维量化模型与宏观估值信号生成今日大势定调...'}
            </h1>
            <p className="text-xs sm:text-sm text-slate-300 leading-relaxed">
              空仓 / 新钱用户可直接在下方输入拟投金额生成选基参考；已有持仓的用户请切至「我的持仓与体检」一键诊断。
            </p>
          </div>
          <div className="flex flex-col sm:flex-row md:flex-col gap-2 shrink-0">
            <button
              type="button"
              onClick={onGoHoldings}
              className="px-4 py-2.5 rounded-xl text-xs font-semibold bg-white text-[#0A192F] hover:bg-slate-100 transition-colors shadow-sm inline-flex items-center justify-center gap-1.5 cursor-pointer"
            >
              <span>我有持仓，去体检</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
            <button
              type="button"
              onClick={onOpenProDrawer}
              className="px-4 py-2 rounded-xl text-xs font-medium bg-white/10 text-slate-200 border border-white/15 hover:bg-white/15 transition-colors cursor-pointer"
            >
              查看十维量化投票
            </button>
          </div>
        </div>

        {/* 3 大核心指数毛玻璃行情条 */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3.5 pt-4 border-t border-white/10">
          {indexCards.map(({ key, fallbackName, note }) => {
            const q = indices[key];
            const chg = q?.change_pct ?? null;
            const up = chg !== null && chg >= 0;
            return (
              <div
                key={key}
                className="px-4 py-3 rounded-xl bg-white/[0.06] border border-white/10 flex items-center justify-between gap-2"
              >
                <div>
                  <div className="text-xs text-slate-300 font-medium">{q?.name || fallbackName}</div>
                  <div className="text-base font-bold tabular-nums text-white mt-0.5">
                    {q?.point ? Number(q.point).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : '--'}
                  </div>
                  <div className="text-[11px] text-slate-400 mt-0.5">{note}</div>
                </div>
                <div className="text-right">
                  <div className={`text-sm font-bold tabular-nums ${chg === null ? 'text-slate-300' : up ? 'text-rose-400' : 'text-emerald-400'}`}>
                    {chg === null ? '--' : `${up ? '+' : ''}${Number(chg).toFixed(2)}%`}
                  </div>
                  <div className="text-[10px] text-slate-400 mt-1">{q?.is_fallback ? '缓存快照' : '实时行情'}</div>
                </div>
              </div>
            );
          })}
        </div>
      </section>

      {/* 2. 交互式空仓选基方案生成器（支持模型选择、基金数量、风险档位与动态入选理由） */}
      <section className="card-elevated rounded-2xl p-5 sm:p-6 space-y-5">
        <div className="flex flex-col xl:flex-row xl:items-end justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <span className="w-1 h-4 rounded-full bg-[#1D4ED8]" />
              <h2 className="text-base font-bold text-slate-900">空仓 / 新钱选基方案生成器</h2>
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-medium bg-blue-50 text-blue-700">
                <Sparkles className="w-3 h-3" />
                实时量化配权
              </span>
            </div>
            <p className="text-xs text-slate-500 mt-1 pl-3">
              <strong>两步分工（互补不冲突）：</strong>① <strong>C1~C5 风险档位</strong>决定总股债仓位上限；② <strong>配置模型</strong>决定在该风险预算内如何分配各资产风格与权重
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <label className="flex items-center gap-2 text-xs font-medium text-slate-600">
              <span>拟投金额 (¥)</span>
              <input
                type="number"
                min={1000}
                step={5000}
                value={amount}
                onChange={(e) => setAmount(Number(e.target.value))}
                className="w-28 h-9 px-3 rounded-lg bg-slate-50 border border-slate-200 text-slate-900 font-bold tabular-nums text-sm focus:border-[#1D4ED8] focus:bg-white focus:outline-none"
              />
            </label>

            <div className="flex items-center gap-1 bg-slate-100 p-1 rounded-xl border border-slate-200" role="group" aria-label="基金数量">
              <span className="px-2 text-[11px] text-slate-500 font-medium">只数</span>
              {FUND_COUNTS.map((n) => (
                <button
                  key={n}
                  type="button"
                  onClick={() => setFundCount(n)}
                  className={`px-2.5 py-1 rounded-lg text-xs font-semibold transition-all cursor-pointer ${
                    fundCount === n ? 'bg-[#1D4ED8] text-white shadow-xs' : 'text-slate-600 hover:text-slate-900'
                  }`}
                >
                  {n}只
                </button>
              ))}
            </div>

            <div className="flex items-center gap-1 bg-slate-100 p-1 rounded-xl border border-slate-200" role="group" aria-label="风险偏好档位">
              {RISK_LEVELS.map((r) => (
                <button
                  key={r.id}
                  type="button"
                  onClick={() => setRiskLevel(r.id)}
                  className={`px-2.5 py-1 rounded-lg text-xs font-semibold transition-all cursor-pointer ${
                    riskLevel === r.id ? 'bg-[#0A192F] text-white shadow-xs' : 'text-slate-600 hover:text-slate-900'
                  }`}
                >
                  {r.label}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* 4 套量化模型选择卡（清晰展示模型名称 + 适用场景 + 核心原理） */}
        {blueprint?.all_models && blueprint.all_models.length > 0 && (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
            {blueprint.all_models.map((m) => {
              const active = m.id === modelId;
              return (
                <button
                  key={m.id}
                  type="button"
                  onClick={() => setModelId(m.id)}
                  className={`text-left p-3.5 rounded-xl border transition-all cursor-pointer ${
                    active
                      ? 'bg-blue-50/80 border-blue-600 shadow-xs ring-1 ring-blue-600/20'
                      : 'bg-slate-50/70 border-slate-200 hover:border-slate-300 hover:bg-white'
                  }`}
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className={`font-bold text-xs ${active ? 'text-blue-900' : 'text-slate-800'}`}>{m.name}</span>
                    <span
                      className={`px-1.5 py-0.5 rounded text-[10px] font-semibold shrink-0 ${
                        active ? 'bg-blue-600 text-white' : 'bg-slate-200/80 text-slate-600'
                      }`}
                    >
                      {m.tag}
                    </span>
                  </div>
                  <p className="text-[11px] text-slate-600 mt-1.5 leading-relaxed">{m.scenario}</p>
                </button>
              );
            })}
          </div>
        )}

        {blueprint && (
          <div className="px-4 py-2.5 rounded-xl bg-blue-50/70 border border-blue-100 text-xs text-slate-700 flex flex-wrap items-center justify-between gap-2">
            <span>
              当前方案：<strong className="text-slate-900">{blueprint.model_meta?.name}</strong> ·{' '}
              <strong className="text-slate-900">{blueprint.risk_meta.label}</strong>（{blueprint.risk_meta.drawdown_hint}）·{' '}
              {blueprint.model_meta?.principle}
            </span>
            <span className="font-bold text-blue-800 tabular-nums">
              合计配置：¥{blueprint.total_amount.toLocaleString()}（严格精选 {blueprint.count} 只核心基金 · 权重和 100.0%）
            </span>
          </div>
        )}

        {bpLoading && !blueprint ? (
          <div className="py-10 text-center text-xs text-slate-500">正在根据所选模型与今日信号生成选基组合...</div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {(blueprint?.items || []).map((f, idx) => {
              const st = ROLE_STYLES[idx % ROLE_STYLES.length];
              return (
                <article
                  key={f.fund_code}
                  className="rounded-xl bg-white border border-slate-200 overflow-hidden hover:border-slate-300 hover:shadow-md transition-all flex flex-col justify-between"
                >
                  <div className="h-1" style={{ background: st.bar }} />
                  <div className="p-4 flex-1 flex flex-col justify-between gap-3">
                    <div className="space-y-2">
                      <div className="flex items-center justify-between gap-2">
                        <span className={`px-2 py-0.5 rounded-md text-[11px] font-semibold border ${st.badge}`}>{f.role}</span>
                        <span className="text-xs font-mono text-slate-400">{f.fund_code}</span>
                      </div>
                      <h3 className="font-bold text-sm text-slate-900">{f.fund_name}</h3>
                      <p className="text-xs text-slate-600 leading-relaxed">{f.why}</p>
                      {f.quant_reason && (
                        <div className="p-2.5 rounded-lg bg-slate-50 border border-slate-100 text-[11px] text-slate-600 leading-relaxed">
                          <strong className="text-slate-800">为什么选它：</strong>
                          {f.quant_reason}
                        </div>
                      )}
                      {f.quota_note && (
                        <div className="px-2.5 py-1.5 rounded-lg bg-amber-50 border border-amber-200 text-[11px] text-amber-800 leading-relaxed">
                          限购提示：{f.quota_note}
                        </div>
                      )}
                      {f.fee_note && (
                        <div className="text-[11px] text-slate-400">
                          费率与实操：{f.fee_note}
                        </div>
                      )}
                    </div>
                    <div className="space-y-2 pt-2 border-t border-slate-100">
                      <div className="flex items-baseline justify-between tabular-nums">
                        <span className="text-lg font-extrabold text-slate-900">
                          ¥{Math.round(f.suggested_amount).toLocaleString()}
                        </span>
                        <span className="text-sm font-extrabold" style={{ color: st.bar }}>
                          占比 {f.weight_pct.toFixed(1)}%
                        </span>
                      </div>
                      <div className="h-1.5 rounded-full bg-slate-100 overflow-hidden">
                        <div
                          className="h-full rounded-full"
                          style={{ width: `${Math.min(100, f.weight_pct)}%`, background: st.bar }}
                        />
                      </div>
                    </div>
                  </div>
                </article>
              );
            })}
          </div>
        )}
      </section>

      {/* 3. 动态联动的当前方案历史回测表现（多周期切换 + 客观克制口径） */}
      <section className="card-elevated rounded-2xl p-5 sm:p-6 space-y-4">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-3">
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <span className="w-1 h-4 rounded-full bg-amber-600" />
              <h2 className="text-base font-bold text-slate-900">
                当前方案历史回测表现（{curves?.period_label || '近 1 年'}）
              </h2>
              {curves?.date_range && (
                <span className="text-[11px] font-mono text-slate-400">{curves.date_range}</span>
              )}
            </div>
            <p className="text-xs text-slate-500 mt-1 pl-3">
              与上方所选「{blueprint?.model_meta?.name || '当前模型'} · {riskLevel} · {fundCount} 只基金」实时联动，按 95% 实盘仓位与申赎费率测算
            </p>
          </div>
          <div className="inline-flex flex-wrap items-center gap-1 bg-slate-100 p-1 rounded-xl border border-slate-200" role="group" aria-label="回测统计周期">
            {BACKTEST_PERIODS.map((p) => (
              <button
                key={p.id}
                type="button"
                onClick={() => setPeriod(p.id)}
                className={`px-2.5 py-1 rounded-lg text-xs font-semibold transition-all cursor-pointer ${
                  period === p.id ? 'bg-[#0A192F] text-white shadow-xs' : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                {p.label}
              </button>
            ))}
          </div>
        </div>

        {curvesLoading && !curves?.metrics ? (
          <div className="py-8 text-center text-xs text-slate-400">正在按所选模型与周期重算历史表现...</div>
        ) : curves?.metrics ? (
          <>
            <div className={`grid grid-cols-2 lg:grid-cols-4 gap-3.5 transition-opacity ${curvesLoading ? 'opacity-60' : ''}`}>
              <div className="p-4 rounded-xl bg-gradient-to-b from-red-50/70 to-white border border-red-100">
                <div className="text-xs font-medium text-slate-500">
                  {curves.period_label}区间收益（实盘校准）
                </div>
                <div
                  className={`text-2xl font-extrabold tabular-nums mt-1.5 ${
                    curves.metrics.period_return_pct >= 0 ? 'text-red-600' : 'text-emerald-700'
                  }`}
                >
                  {curves.metrics.period_return_pct >= 0 ? '+' : ''}
                  {curves.metrics.period_return_pct.toFixed(2)}%
                </div>
                <div className="text-[11px] text-slate-500 mt-1 tabular-nums">
                  同期沪深 300：{curves.metrics.hs300_return_pct >= 0 ? '+' : ''}
                  {curves.metrics.hs300_return_pct.toFixed(2)}%（超额 {curves.metrics.excess_return_pct >= 0 ? '+' : ''}
                  {curves.metrics.excess_return_pct.toFixed(2)}%）
                </div>
              </div>

              <div className="p-4 rounded-xl bg-gradient-to-b from-emerald-50/70 to-white border border-emerald-100">
                <div className="text-xs font-medium text-slate-500">区间最大回撤</div>
                <div className="text-2xl font-extrabold tabular-nums mt-1.5 text-emerald-700">
                  -{Math.abs(curves.metrics.max_drawdown_pct).toFixed(2)}%
                </div>
                <div className="text-[11px] text-slate-500 mt-1 tabular-nums">
                  同期沪深 300 最大回撤 -{Math.abs(curves.metrics.hs300_mdd_pct).toFixed(2)}%
                </div>
              </div>

              <div className="p-4 rounded-xl bg-gradient-to-b from-blue-50/70 to-white border border-blue-100">
                <div className="text-xs font-medium text-slate-500">{curves.metrics.win_rate_label}</div>
                <div className="text-2xl font-extrabold tabular-nums mt-1.5 text-blue-700">
                  {curves.metrics.win_rate_pct.toFixed(1)}%
                </div>
                <div className="text-[11px] text-slate-500 mt-1">{curves.metrics.win_rate_detail}</div>
              </div>

              <div className="p-4 rounded-xl bg-gradient-to-b from-amber-50/70 to-white border border-amber-100">
                <div className="text-xs font-medium text-slate-500">风险调整夏普比率</div>
                <div className="text-2xl font-extrabold tabular-nums mt-1.5 text-amber-700">
                  {curves.metrics.sharpe_ratio.toFixed(2)}
                </div>
                <div className="text-[11px] text-slate-500 mt-1 tabular-nums">
                  {curves.metrics.annualized_return_pct !== null
                    ? `折合年化 ${curves.metrics.annualized_return_pct >= 0 ? '+' : ''}${curves.metrics.annualized_return_pct.toFixed(2)}%`
                    : `统计覆盖 ${curves.metrics.trading_days} 个交易日`}
                </div>
              </div>
            </div>
            <p className="text-[11px] text-slate-400">
              注：历史回测基于当前所选模型权重与交易费率测算，仅供量化分析参考，过往业绩不代表未来收益保证。
            </p>
          </>
        ) : null}
      </section>

      {/* 4. 历史回测验证区：全周期走势 | 历史情景回测 */}
      <div className="space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <span className="w-1 h-4 rounded-full bg-[#0A192F]" />
            <h2 className="text-base font-bold text-slate-900">历史业绩验证与情景压力检验</h2>
          </div>
          <div className="inline-flex items-center gap-1 bg-white p-1 rounded-xl border border-slate-200 shadow-xs">
            <button
              type="button"
              onClick={() => setBtSubTab('full')}
              className={`px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-all cursor-pointer ${
                btSubTab === 'full' ? 'bg-[#0A192F] text-white' : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              2018–2026 全周期走势
            </button>
            <button
              type="button"
              onClick={() => setBtSubTab('scenario')}
              className={`px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-all cursor-pointer ${
                btSubTab === 'scenario' ? 'bg-[#0A192F] text-white' : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              历史情景回测
            </button>
          </div>
        </div>

        {btSubTab === 'full' ? (
          <BacktestCharts data={curves} loading={curvesLoading} />
        ) : (
          <ScenarioBacktestPanel tier={riskLevel} />
        )}
      </div>

      {/* 5. 短期偏离与交易拥挤度象限散点图 */}
      <CrowdingQuadrantChart points={crowding} loading={crowdingLoading} />
    </div>
  );
}

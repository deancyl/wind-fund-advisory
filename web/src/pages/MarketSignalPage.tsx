import { useEffect, useState } from 'react';
import { Plus, Trash2, Radio, Activity, Eye } from 'lucide-react';
import { api, type CrowdingPoint, type EtfPremiumItem } from '../api/client';
import { useWorkbench } from '../context/WorkbenchContext';
import { CrowdingQuadrantChart } from '../components/charts/CrowdingQuadrantChart';

function localizeSignal(raw: unknown): { label: string; tone: 'bull' | 'bear' | 'neutral' } {
  const s = String(raw || '').toUpperCase().trim();
  if (s.includes('BULL') || s.includes('偏多') || s.includes('进攻') || s.includes('低估') || s === 'BUY') {
    return { label: '偏多进攻', tone: 'bull' };
  }
  if (s.includes('BEAR') || s.includes('偏空') || s.includes('防守') || s.includes('高估') || s === 'SELL') {
    return { label: '偏空防守', tone: 'bear' };
  }
  return { label: '中性观望', tone: 'neutral' };
}

export function MarketSignalPage() {
  const {
    overview,
    activeLedgerId,
    refreshTick,
    solvedContext,
    openInspector,
    pushToast,
  } = useWorkbench();

  const [loading, setLoading] = useState(true);
  const [votes, setVotes] = useState<Array<Record<string, unknown>>>([]);
  const [watchlist, setWatchlist] = useState<Array<{ code: string; name: string; change_pct: number }>>([]);
  const [etfPremiums, setEtfPremiums] = useState<EtfPremiumItem[]>([]);
  const [etfMeta, setEtfMeta] = useState<{ isOffline: boolean; timestamp: string; sourceLabel: string }>({
    isOffline: false,
    timestamp: '',
    sourceLabel: '',
  });
  const [searchQ, setSearchQ] = useState('');
  const [searchHits, setSearchHits] = useState<Array<{ code: string; name: string; sector: string }>>([]);

  const [crowdingScope, setCrowdingScope] = useState<'recommended' | 'holdings'>('recommended');
  const [crowding, setCrowding] = useState<CrowdingPoint[]>([]);
  const [crowdingLoading, setCrowdingLoading] = useState(true);

  useEffect(() => {
    if (!activeLedgerId) return;
    let alive = true;
    setLoading(true);
    Promise.allSettled([
      api.getTenDimVotes(activeLedgerId),
      api.getWatchlist(),
      api.getEtfPremiums(),
    ]).then(([v, w, ep]) => {
      if (!alive) return;
      if (v.status === 'fulfilled') setVotes(v.value.votes || []);
      if (w.status === 'fulfilled') setWatchlist(w.value.items || []);
      if (ep.status === 'fulfilled') {
        setEtfPremiums(ep.value.items || []);
        setEtfMeta({
          isOffline: Boolean(ep.value.is_offline_snapshot),
          timestamp: String(ep.value.snapshot_timestamp || ''),
          sourceLabel: String(ep.value.source_label || ''),
        });
      }
      setLoading(false);
    });
    return () => {
      alive = false;
    };
  }, [activeLedgerId, refreshTick]);

  const recCodesKey = (solvedContext.fundCodes || []).join(',');
  useEffect(() => {
    if (!activeLedgerId && !recCodesKey) return;
    let alive = true;
    const recCodes = recCodesKey ? recCodesKey.split(',').filter(Boolean) : [];
    const effScope = crowdingScope === 'recommended' && recCodes.length > 0 ? 'recommended' : 'holdings';
    setCrowdingLoading(true);
    api
      .getCrowdingQuadrant(activeLedgerId, effScope === 'recommended' ? recCodes : undefined)
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
  }, [activeLedgerId, crowdingScope, recCodesKey]);

  useEffect(() => {
    const q = searchQ.trim();
    if (!q) {
      setSearchHits([]);
      return;
    }
    const t = setTimeout(() => {
      api
        .searchFunds(q, 6)
        .then((res) => setSearchHits(res.items || []))
        .catch(() => {});
    }, 220);
    return () => clearTimeout(t);
  }, [searchQ]);

  const handleAddWatch = async (code: string, name: string) => {
    try {
      const res = await api.addWatchlistItem(code, name);
      setWatchlist(res.items || []);
      setSearchQ('');
      setSearchHits([]);
      pushToast(`已将「${name} (${code})」加入自选观察`, 'success');
    } catch (e) {
      pushToast(e instanceof Error ? e.message : '添加自选失败', 'error');
    }
  };

  const handleRemoveWatch = async (code: string) => {
    try {
      const res = await api.removeWatchlistItem(code);
      setWatchlist(res.items || []);
      pushToast(`已移除自选 ${code}`, 'default');
    } catch (e) {
      pushToast(e instanceof Error ? e.message : '移除自选失败', 'error');
    }
  };

  const verdict = overview?.market_verdict;
  const indices = overview?.indices || {};
  const indexSpecs = [
    { key: 'sh000300', name: '沪深 300', role: 'A股核心大盘' },
    { key: 'sh000688', name: '科创 50', role: '硬核科技弹性' },
    { key: 'sh000922', name: '中证红利', role: '高股息底仓锚' },
  ];

  const bullCount = votes.filter((v) => localizeSignal(v.signal ?? v.vote).tone === 'bull').length;
  const bearCount = votes.filter((v) => localizeSignal(v.signal ?? v.vote).tone === 'bear').length;
  const neutralCount = Math.max(0, votes.length - bullCount - bearCount);

  return (
    <div className="space-y-4 fade-in" data-testid="market-signal-page">
      {/* 1. 顶部宏观定调与核心指数极简信息带（零大块广告牌） */}
      <section className="inst-panel rounded-xl overflow-hidden">
        <div className="px-4 sm:px-5 py-3.5 inst-panel-header flex flex-col lg:flex-row lg:items-center justify-between gap-3">
          <div className="space-y-1">
            <div className="flex flex-wrap items-center gap-2">
              <span className="px-2.5 py-0.5 rounded-md bg-[#0B192C] text-white text-[11px] font-bold">
                {verdict?.short_label || '大势信号研判中'}
              </span>
              {verdict?.action_tag && (
                <span className="px-2 py-0.5 rounded-md bg-blue-50 text-blue-800 border border-blue-200 text-[11px] font-semibold">
                  {verdict.action_tag}
                </span>
              )}
              <span className="text-[11px] text-slate-500">
                {overview?.is_official_nav ? '已同步盘后官方净值' : '盘中实时行情已连接'}
              </span>
            </div>
            <h1 className="text-sm sm:text-[15px] font-bold text-slate-900 leading-snug">
              {verdict?.detail_explanation || '正在根据十维量化投票与宏观估值水位汇总今日市场定调...'}
            </h1>
          </div>

          <div className="flex items-center gap-2 text-xs tabular-nums shrink-0">
            <div className="px-3 py-1.5 rounded-lg bg-red-50/70 border border-red-200/70 text-center min-w-[54px]">
              <div className="text-[10px] font-medium text-red-700">偏多</div>
              <div className="font-extrabold text-[#C81E1E] text-base leading-tight">{bullCount}</div>
            </div>
            <div className="px-3 py-1.5 rounded-lg bg-slate-100/80 border border-slate-200 text-center min-w-[54px]">
              <div className="text-[10px] font-medium text-slate-500">中性</div>
              <div className="font-extrabold text-slate-700 text-base leading-tight">{neutralCount}</div>
            </div>
            <div className="px-3 py-1.5 rounded-lg bg-emerald-50/70 border border-emerald-200/70 text-center min-w-[54px]">
              <div className="text-[10px] font-medium text-emerald-800">偏空</div>
              <div className="font-extrabold text-[#047857] text-base leading-tight">{bearCount}</div>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 divide-y sm:divide-y-0 sm:divide-x divide-slate-200 bg-slate-50/40 tabular-nums">
          {indexSpecs.map(({ key, name, role }) => {
            const q = indices[key];
            const chg = q?.change_pct ?? null;
            const up = chg !== null && chg >= 0;
            return (
              <div key={key} className="px-4 sm:px-5 py-3 flex items-center justify-between gap-2">
                <div>
                  <div className="text-xs font-bold text-slate-800">{q?.name || name}</div>
                  <div className="text-[11px] text-slate-400">{role}</div>
                </div>
                <div className="text-right">
                  <div className="text-sm font-extrabold font-mono text-slate-900">
                    {q?.point ? Number(q.point).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : '--'}
                  </div>
                  <div className={`text-xs font-bold font-mono ${chg === null ? 'text-slate-400' : up ? 'text-red-600' : 'text-emerald-600'}`}>
                    {chg === null ? '--' : `${up ? '+' : ''}${Number(chg).toFixed(2)}%`}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </section>

      {/* 2. 主双栏：左十维量化投票矩阵 | 右自选观察 + 场内 ETF 溢价监控 */}
      <section className="grid grid-cols-1 lg:grid-cols-12 gap-4 items-start">
        {/* 左 7 列：十维量化投票矩阵 */}
        <div className="lg:col-span-7 inst-panel rounded-lg overflow-hidden">
          <div className="px-4 py-3 border-b border-slate-200 bg-slate-50/70 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Activity className="w-4 h-4 text-blue-700" />
              <h2 className="text-xs font-bold text-slate-900">十维量化宏观投票矩阵（中债/美债/ERP/动量/量能）</h2>
            </div>
            <span className="text-[11px] text-slate-400 tabular-nums">{votes.length} 维度实算</span>
          </div>

          {loading ? (
            <div className="p-8 text-center text-xs text-slate-400">正在加载十维量化宏观投票...</div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-xs text-left">
                <thead>
                  <tr className="border-b border-slate-200 bg-white text-slate-500">
                    <th className="py-2 px-4 font-semibold whitespace-nowrap">量化维度</th>
                    <th className="py-2 px-3 font-semibold whitespace-nowrap">信号裁决</th>
                    <th className="py-2 px-4 font-semibold">量化观测依据</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {votes.map((v, idx) => {
                    const sig = localizeSignal(v.signal ?? v.vote);
                    const name = String(v.dimension || v.name || `维度 ${idx + 1}`);
                    const reason = String(v.reason || v.detail || v.indicator || '--');
                    return (
                      <tr key={idx} className="hover:bg-slate-50/70">
                        <td className="py-2 px-4 font-semibold text-slate-900 whitespace-nowrap">{name}</td>
                        <td className="py-2 px-3 whitespace-nowrap">
                          <span
                            className={`px-2 py-0.5 rounded text-[11px] font-bold ${
                              sig.tone === 'bull'
                                ? 'bg-red-50 text-red-700 border border-red-200'
                                : sig.tone === 'bear'
                                ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                                : 'bg-slate-100 text-slate-600 border border-slate-200'
                            }`}
                          >
                            {sig.label}
                          </span>
                        </td>
                        <td className="py-2 px-4 text-slate-600 leading-relaxed">{reason}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* 右 5 列：自选与行业观察 + 热门场内 ETF 溢价预警 */}
        <div className="lg:col-span-5 space-y-4">
          {/* 自选观察 */}
          <div className="inst-panel rounded-lg p-4 space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Eye className="w-4 h-4 text-slate-700" />
                <h2 className="text-xs font-bold text-slate-900">自选与行业板块监控</h2>
              </div>
              <span className="text-[11px] text-slate-400">支持拼音/代码添加</span>
            </div>

            <div className="relative">
              <input
                type="search"
                value={searchQ}
                onChange={(e) => setSearchQ(e.target.value)}
                placeholder="输入代码或拼音检索添加（如 hldb、红利低波、513100）"
                aria-label="搜索基金或行业添加自选"
                className="w-full h-8 px-3 rounded-md bg-slate-50 border border-slate-200 focus:border-blue-600 focus:bg-white focus:outline-none text-xs"
              />
              {searchHits.length > 0 && (
                <div className="mt-1 rounded-md border border-slate-200 bg-white shadow-md divide-y divide-slate-100 max-h-40 overflow-y-auto">
                  {searchHits.map((it) => (
                    <button
                      key={it.code}
                      type="button"
                      onClick={() => void handleAddWatch(it.code, it.name)}
                      className="w-full px-3 py-2 text-left hover:bg-blue-50 flex items-center justify-between gap-2 text-xs cursor-pointer"
                    >
                      <span className="truncate text-slate-800">
                        <strong>{it.name}</strong> <span className="font-mono text-slate-400">{it.code}</span>
                      </span>
                      <Plus className="w-3.5 h-3.5 text-blue-700 shrink-0" />
                    </button>
                  ))}
                </div>
              )}
            </div>

            <div className="divide-y divide-slate-100 text-xs tabular-nums">
              {watchlist.length === 0 ? (
                <div className="py-4 text-center text-slate-400">暂无自选标的</div>
              ) : (
                watchlist.map((w) => (
                  <div key={w.code} className="flex justify-between items-center py-2 gap-2">
                    <button
                      type="button"
                      onClick={() => openInspector(w.code)}
                      className="text-left truncate text-slate-800 hover:text-blue-700 cursor-pointer"
                    >
                      <span className="font-semibold">{w.name}</span>{' '}
                      <span className="font-mono text-[11px] text-slate-400">{w.code}</span>
                    </button>
                    <div className="flex items-center gap-2 shrink-0">
                      <span
                        className={`font-mono font-bold ${
                          w.change_pct > 0 ? 'text-red-600' : w.change_pct < 0 ? 'text-emerald-700' : 'text-slate-500'
                        }`}
                      >
                        {w.change_pct > 0 ? '+' : ''}
                        {Number(w.change_pct || 0).toFixed(2)}%
                      </span>
                      <button
                        type="button"
                        onClick={() => void handleRemoveWatch(w.code)}
                        aria-label={`移除自选 ${w.name}`}
                        className="text-slate-400 hover:text-red-600 cursor-pointer"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>

          {/* 热门场内 ETF 溢价预警（紧凑吸顶滚动表，杜绝长列表撑爆页面） */}
          <div className="inst-panel rounded-lg overflow-hidden">
            <div className="px-4 py-3 border-b border-slate-200 bg-slate-50/70 flex flex-wrap items-center justify-between gap-2">
              <div className="flex flex-wrap items-center gap-1.5">
                <Radio className="w-4 h-4 text-red-600" />
                <h2 className="text-xs font-bold text-slate-900">热门场内 ETF 溢价预警（红线 0.8%）</h2>
                {etfMeta.isOffline && (
                  <span
                    data-testid="etf-offline-badge"
                    title={etfMeta.sourceLabel || '当前展示本地离线截面快照，非盘中实时行情'}
                    className="px-1.5 py-0.5 rounded bg-amber-50 border border-amber-300 text-amber-800 text-[10px] font-semibold"
                  >
                    离线快照{etfMeta.timestamp ? ` · ${etfMeta.timestamp}` : ''}
                  </span>
                )}
              </div>
              <span className="text-[11px] font-mono text-slate-500 tabular-nums">
                {etfPremiums.length} 只超红线
              </span>
            </div>
            {etfPremiums.length === 0 ? (
              <div className="p-4">
                <div className="px-3 py-2.5 rounded-md bg-emerald-50/70 border border-emerald-200 text-xs text-emerald-800">
                  当前监控的核心场内 ETF 溢价率均处于安全区间（≤ 0.8%），无高位接盘风险。
                </div>
              </div>
            ) : (
              <div>
                <div className="px-4 py-1.5 bg-amber-50/60 border-b border-amber-200/70 text-[11px] text-amber-900">
                  以下场内 ETF 溢价超 0.8% 安全线，建议优先用场外联接基金或等待溢价回落，防高位接盘。
                </div>
                <div className="max-h-[260px] overflow-y-auto">
                  <table className="w-full text-xs text-left tabular-nums">
                    <thead className="sticky top-0 bg-white border-b border-slate-200 text-slate-500 z-10">
                      <tr>
                        <th className="py-2 px-3 font-semibold">场内 ETF</th>
                        <th className="py-2 px-2 font-semibold text-right">现价 / IOPV</th>
                        <th className="py-2 px-3 font-semibold text-right">溢价率</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                      {[...etfPremiums]
                        .sort((a, b) => b.premium_pct - a.premium_pct)
                        .map((e) => (
                          <tr key={e.code} className="hover:bg-slate-50/70">
                            <td className="py-1.5 px-3">
                              <div className="font-semibold text-slate-900 truncate max-w-[160px]" title={e.name}>
                                {e.name}
                              </div>
                              <div className="font-mono text-[10px] text-slate-400">{e.code}</div>
                            </td>
                            <td className="py-1.5 px-2 text-right font-mono text-[11px] text-slate-600">
                              {e.price.toFixed(3)} / {e.iopv.toFixed(3)}
                            </td>
                            <td className="py-1.5 px-3 text-right font-mono font-bold text-red-600">
                              +{e.premium_pct.toFixed(2)}%
                            </td>
                          </tr>
                        ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>
        </div>
      </section>

      {/* 3. 全市场/组合交易拥挤度四象限全景 */}
      <CrowdingQuadrantChart
        points={crowding}
        loading={crowdingLoading}
        scopeMode={crowdingScope}
        onChangeScopeMode={setCrowdingScope}
        recommendedCount={(solvedContext.fundCodes || []).length}
      />
    </div>
  );
}

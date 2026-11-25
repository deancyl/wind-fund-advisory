import { useEffect, useState } from 'react';
import { X, RotateCcw, Activity, Eye, Layers, ShieldAlert, Plus, Trash2, Calculator, Radio } from 'lucide-react';
import { api, type EtfPremiumItem } from '../api/client';

interface ProAnalysisDrawerProps {
  open: boolean;
  ledgerId: string;
  onClose: () => void;
  onRestored: () => void;
}

export function ProAnalysisDrawer({ open, ledgerId, onClose, onRestored }: ProAnalysisDrawerProps) {
  const [loading, setLoading] = useState(false);
  const [votes, setVotes] = useState<Array<Record<string, unknown>>>([]);
  const [watchlist, setWatchlist] = useState<Array<{ code: string; name: string; change_pct: number }>>([]);
  const [overlap, setOverlap] = useState<Record<string, unknown>>({});
  const [stress, setStress] = useState<Record<string, unknown>>({});
  const [backups, setBackups] = useState<Array<{ snapshot_id: string; created_at?: string; reason?: string }>>([]);
  const [etfPremiums, setEtfPremiums] = useState<EtfPremiumItem[]>([]);
  const [msg, setMsg] = useState('');

  // 自选检索添加
  const [searchQ, setSearchQ] = useState('');
  const [searchHits, setSearchHits] = useState<Array<{ code: string; name: string; sector: string }>>([]);

  // A/C 费率对比计算器（即时响应，零延迟）
  const [acAmount, setAcAmount] = useState(50000);
  const [acDays, setAcDays] = useState(180);
  const [acSubFee, setAcSubFee] = useState(0.15); // A类申购费(%)
  const [acSalesFee, setAcSalesFee] = useState(0.4); // C类年化销售服务费(%)

  useEffect(() => {
    if (!open) return;
    let alive = true;
    setLoading(true);
    setMsg('');
    Promise.allSettled([
      api.getTenDimVotes(ledgerId),
      api.getWatchlist(),
      api.getDiagnoseOverlap(ledgerId),
      api.getDiagnoseStress(ledgerId),
      api.getBackups(),
      api.getEtfPremiums(),
    ]).then(([v, w, o, s, b, ep]) => {
      if (!alive) return;
      if (v.status === 'fulfilled') setVotes(v.value.votes || []);
      if (w.status === 'fulfilled') setWatchlist(w.value.items || []);
      if (o.status === 'fulfilled') setOverlap(o.value || {});
      if (s.status === 'fulfilled') setStress(s.value || {});
      if (b.status === 'fulfilled') setBackups((b.value.snapshots || []).slice(0, 6));
      if (ep.status === 'fulfilled') setEtfPremiums(ep.value.items || []);
      setLoading(false);
    });
    return () => {
      alive = false;
    };
  }, [open, ledgerId]);

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
      setMsg(`已将「${name} (${code})」加入自选观察`);
    } catch (e) {
      setMsg(e instanceof Error ? e.message : '添加自选失败');
    }
  };

  const handleRemoveWatch = async (code: string) => {
    try {
      const res = await api.removeWatchlistItem(code);
      setWatchlist(res.items || []);
      setMsg(`已移除自选 ${code}`);
    } catch (e) {
      setMsg(e instanceof Error ? e.message : '移除自选失败');
    }
  };

  const handleRestore = async (snapshotId: string) => {
    if (!window.confirm(`确认将账本还原至快照 ${snapshotId}？`)) return;
    try {
      await api.restoreBackup(snapshotId);
      setMsg('账本已还原，正在刷新数据...');
      onRestored();
    } catch (e) {
      setMsg(e instanceof Error ? e.message : '还原失败');
    }
  };

  if (!open) return null;

  const pen = (stress.penetration_risk || {}) as Record<string, unknown>;
  const cvar = (stress.cvar_bootstrap || {}) as Record<string, unknown>;

  // A/C 费率精算（A类=一次性前端申购费；C类=按日计提年化销售服务费）
  const breakEvenDays = acSalesFee > 0 ? Math.round((acSubFee / acSalesFee) * 365) : 365;
  const costA = (acAmount * acSubFee) / 100;
  const costC = (acAmount * (acSalesFee / 100) * acDays) / 365;
  const recommendA = acDays >= breakEvenDays;

  return (
    <div className="fixed inset-0 z-40 flex justify-end">
      <div className="fixed inset-0 bg-slate-900/50 backdrop-blur-xs" onClick={onClose} aria-hidden="true" />
      <aside
        aria-label="专业量化分析工具箱"
        className="relative z-50 h-full w-full max-w-md bg-white border-l border-slate-200 shadow-2xl flex flex-col fade-in"
      >
        <div className="px-5 py-4 topbar-navy text-white flex items-center justify-between shrink-0">
          <div>
            <h2 className="font-semibold text-base">专业量化分析工具箱</h2>
            <p className="text-xs text-slate-300 mt-0.5">进阶投研指标、自选管理、费率测算与冷备还原</p>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="关闭专业分析抽屉"
            className="w-8 h-8 rounded-lg flex items-center justify-center text-slate-300 hover:text-white hover:bg-white/10 cursor-pointer"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="p-4 sm:p-5 overflow-y-auto space-y-4 flex-1 text-xs bg-[#F3F6FA]">
          {loading && <div className="text-center py-8 text-slate-500">正在加载进阶量化数据...</div>}

          {msg && (
            <div className="p-3 rounded-xl bg-blue-50 border border-blue-200 text-blue-800 font-medium">{msg}</div>
          )}

          {!loading && (
            <>
              {/* #8 自选观察管理（支持搜索添加与删除） */}
              <div className="card-elevated p-4 rounded-xl space-y-2.5">
                <div className="flex items-center gap-2 font-bold text-sm text-slate-900">
                  <Eye className="w-4 h-4 text-amber-600" />
                  <span>自选与行业板块观察</span>
                </div>
                <div className="relative">
                  <input
                    type="search"
                    value={searchQ}
                    onChange={(e) => setSearchQ(e.target.value)}
                    placeholder="搜索代码/拼音/名称添加（如 hldb、红利低波、513100）"
                    aria-label="搜索基金或行业添加自选"
                    className="w-full h-8 px-3 rounded-lg bg-slate-50 border border-slate-200 focus:border-blue-600 focus:bg-white focus:outline-none text-xs"
                  />
                  {searchHits.length > 0 && (
                    <div className="mt-1 rounded-lg border border-slate-200 bg-white shadow-md divide-y divide-slate-100 max-h-40 overflow-y-auto">
                      {searchHits.map((it) => (
                        <button
                          key={it.code}
                          type="button"
                          onClick={() => handleAddWatch(it.code, it.name)}
                          className="w-full px-3 py-2 text-left hover:bg-blue-50 flex items-center justify-between gap-2 cursor-pointer"
                        >
                          <span className="truncate text-slate-800">
                            <strong>{it.name}</strong> <span className="font-mono text-slate-400">{it.code}</span>
                          </span>
                          <Plus className="w-3.5 h-3.5 text-blue-600 shrink-0" />
                        </button>
                      ))}
                    </div>
                  )}
                </div>

                <div className="divide-y divide-slate-100 tabular-nums">
                  {watchlist.map((w) => (
                    <div key={w.code} className="flex justify-between items-center py-1.5 gap-2">
                      <span className="text-slate-700 truncate">
                        {w.name} <span className="font-mono text-slate-400">({w.code})</span>
                      </span>
                      <div className="flex items-center gap-2 shrink-0">
                        <span
                          className={`px-2 py-0.5 rounded font-bold ${
                            w.change_pct > 0
                              ? 'bg-red-50 text-red-600'
                              : w.change_pct < 0
                              ? 'bg-emerald-50 text-emerald-700'
                              : 'bg-slate-100 text-slate-600'
                          }`}
                        >
                          {w.change_pct > 0 ? '+' : ''}
                          {Number(w.change_pct || 0).toFixed(2)}%
                        </span>
                        <button
                          type="button"
                          onClick={() => handleRemoveWatch(w.code)}
                          aria-label={`移除自选 ${w.name}`}
                          className="text-slate-400 hover:text-red-600 cursor-pointer"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* #10 海外/热门场内 ETF 溢价预警 */}
              <div className="card-elevated p-4 rounded-xl space-y-2.5">
                <div className="flex items-center gap-2 font-bold text-sm text-slate-900">
                  <Radio className="w-4 h-4 text-rose-600" />
                  <span>热门场内 ETF 溢价预警（红线 0.8%）</span>
                </div>
                {etfPremiums.length === 0 ? (
                  <div className="p-2.5 rounded-lg bg-emerald-50 border border-emerald-200 text-emerald-800">
                    当前监控的核心场内 ETF 溢价率均处于安全区间（≤ 0.8%），无高位接盘风险。
                  </div>
                ) : (
                  <div className="space-y-2">
                    {etfPremiums.map((e) => (
                      <div key={e.code} className="p-2.5 rounded-lg bg-amber-50 border border-amber-200 space-y-1">
                        <div className="flex justify-between font-semibold text-slate-900 tabular-nums">
                          <span>
                            {e.name} ({e.code})
                          </span>
                          <span className="text-red-600">溢价 +{e.premium_pct.toFixed(2)}%</span>
                        </div>
                        <p className="text-[11px] text-slate-600">{e.advice}</p>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* #9 A/C 类份额费率对比器 */}
              <div className="card-elevated p-4 rounded-xl space-y-3">
                <div className="flex items-center gap-2 font-bold text-sm text-slate-900">
                  <Calculator className="w-4 h-4 text-blue-700" />
                  <span>A / C 类份额费率对比器</span>
                </div>
                <div className="grid grid-cols-2 gap-2.5">
                  <label className="space-y-1">
                    <span className="text-slate-500">拟投金额 (¥)</span>
                    <input
                      type="number"
                      step={5000}
                      min={1000}
                      value={acAmount}
                      onChange={(e) => setAcAmount(Math.max(1000, Number(e.target.value) || 1000))}
                      className="w-full h-8 px-2.5 rounded-lg bg-slate-50 border border-slate-200 font-semibold tabular-nums"
                    />
                  </label>
                  <label className="space-y-1">
                    <span className="text-slate-500">计划持有天数</span>
                    <input
                      type="number"
                      step={10}
                      min={7}
                      value={acDays}
                      onChange={(e) => setAcDays(Math.max(7, Number(e.target.value) || 30))}
                      className="w-full h-8 px-2.5 rounded-lg bg-slate-50 border border-slate-200 font-semibold tabular-nums"
                    />
                  </label>
                  <label className="space-y-1">
                    <span className="text-slate-500">A 类申购费 (%)</span>
                    <input
                      type="number"
                      step={0.01}
                      min={0}
                      value={acSubFee}
                      onChange={(e) => setAcSubFee(Math.max(0, Number(e.target.value) || 0))}
                      className="w-full h-8 px-2.5 rounded-lg bg-slate-50 border border-slate-200 tabular-nums"
                    />
                  </label>
                  <label className="space-y-1">
                    <span className="text-slate-500">C 类年服务费 (%)</span>
                    <input
                      type="number"
                      step={0.05}
                      min={0.05}
                      value={acSalesFee}
                      onChange={(e) => setAcSalesFee(Math.max(0.05, Number(e.target.value) || 0.4))}
                      className="w-full h-8 px-2.5 rounded-lg bg-slate-50 border border-slate-200 tabular-nums"
                    />
                  </label>
                </div>
                <div className="p-3 rounded-xl bg-blue-50/70 border border-blue-200 space-y-1 tabular-nums">
                  <div className="font-bold text-slate-900">
                    结论：持有 {acDays} 天，建议选【{recommendA ? 'A 类份额' : 'C 类份额'}】
                    （省 ¥{Math.abs(costA - costC).toFixed(2)}）
                  </div>
                  <div className="text-[11px] text-slate-600">
                    盈亏平衡点约 <strong>{breakEvenDays} 天</strong> · A 类预估 ¥{costA.toFixed(2)} vs C 类预估 ¥{costC.toFixed(2)}
                  </div>
                </div>
              </div>

              {/* 十维量化投票 */}
              <div className="card-elevated p-4 rounded-xl space-y-2.5">
                <div className="flex items-center gap-2 font-bold text-sm text-slate-900">
                  <Activity className="w-4 h-4 text-blue-700" />
                  <span>十维量化投票明细</span>
                </div>
                <div className="grid grid-cols-1 gap-1.5">
                  {votes.slice(0, 10).map((v, idx) => {
                    const label = String(v.name || v.dimension || v.indicator || `维度 ${idx + 1}`);
                    const stance = String(v.signal || v.stance || v.vote || v.status || '中性');
                    const isPos = stance.includes('多') || stance.includes('进攻') || stance.includes('低估') || stance.includes('买');
                    const isNeg = stance.includes('空') || stance.includes('防守') || stance.includes('谨慎') || stance.includes('高估');
                    return (
                      <div key={idx} className="flex items-center justify-between py-1.5 px-2.5 rounded-lg bg-slate-50">
                        <span className="text-slate-700 truncate pr-2">{label}</span>
                        <span
                          className={`px-2 py-0.5 rounded font-semibold shrink-0 ${
                            isPos
                              ? 'bg-red-50 text-red-700'
                              : isNeg
                              ? 'bg-emerald-50 text-emerald-700'
                              : 'bg-slate-200/70 text-slate-700'
                          }`}
                        >
                          {stance}
                        </span>
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* 重仓重叠度 */}
              <div className="card-elevated p-4 rounded-xl space-y-2">
                <div className="flex items-center gap-2 font-bold text-sm text-slate-900">
                  <Layers className="w-4 h-4 text-indigo-600" />
                  <span>重仓股重叠度与穿透风险</span>
                </div>
                <div className="grid grid-cols-2 gap-2.5 pt-1 tabular-nums">
                  <div className="p-2.5 rounded-lg bg-slate-50">
                    <div className="text-slate-500">最高基金重仓重叠</div>
                    <div className="text-base font-bold text-slate-900 mt-0.5">
                      {(Number(overlap.max_total_overlap || 0) * 100).toFixed(1)}%
                    </div>
                  </div>
                  <div className="p-2.5 rounded-lg bg-slate-50">
                    <div className="text-slate-500">穿透风险评级</div>
                    <div className="text-base font-bold text-slate-900 mt-0.5">{String(pen.risk_level || '稳健可控')}</div>
                  </div>
                </div>
                {cvar.cvar_95_pct !== undefined && (
                  <p className="text-slate-600 leading-relaxed pt-1 flex items-center gap-1.5">
                    <ShieldAlert className="w-3.5 h-3.5 text-amber-600 shrink-0" />
                    <span>
                      95% 置信度尾部风险 CVaR：<strong className="text-emerald-700">{Number(cvar.cvar_95_pct).toFixed(2)}%</strong>
                    </span>
                  </p>
                )}
              </div>

              {/* 账本冷备快照还原 */}
              <div className="card-elevated p-4 rounded-xl space-y-2.5">
                <div className="flex items-center gap-2 font-bold text-sm text-slate-900">
                  <RotateCcw className="w-4 h-4 text-slate-700" />
                  <span>账本冷备快照（一键撤回）</span>
                </div>
                {backups.length === 0 ? (
                  <p className="text-slate-500">暂无可用冷备快照</p>
                ) : (
                  <div className="space-y-2">
                    {backups.map((b) => (
                      <div key={b.snapshot_id} className="flex items-center justify-between gap-2 p-2 rounded-lg bg-slate-50">
                        <div className="min-w-0">
                          <div className="font-mono text-[11px] text-slate-700 truncate">{b.snapshot_id}</div>
                          <div className="text-[11px] text-slate-400 truncate">{b.reason || b.created_at || '自动冷备'}</div>
                        </div>
                        <button
                          type="button"
                          onClick={() => handleRestore(b.snapshot_id)}
                          className="px-2.5 py-1 rounded-lg bg-blue-50 text-blue-700 font-semibold hover:bg-blue-100 shrink-0 cursor-pointer"
                        >
                          还原
                        </button>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </>
          )}
        </div>
      </aside>
    </div>
  );
}

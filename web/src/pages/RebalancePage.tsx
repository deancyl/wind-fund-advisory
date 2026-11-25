import { useEffect, useMemo, useState } from 'react';
import { Copy, Check, RefreshCw, ChevronDown, ChevronRight, CalendarClock, Coins } from 'lucide-react';
import { api, type DividendAdviceResponse, type RebalanceItem, type RebalanceResponse } from '../api/client';

interface RebalancePageProps {
  ledgerId: string;
  refreshTick: number;
  onOpenImport: () => void;
  onToast: (msg: string) => void;
}

export function RebalancePage({ ledgerId, refreshTick, onOpenImport, onToast }: RebalancePageProps) {
  const [data, setData] = useState<RebalanceResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [checkedSet, setCheckedSet] = useState<Set<string>>(new Set());
  const [saveStatus, setSaveStatus] = useState<'idle' | 'saving' | 'saved' | 'error'>('idle');
  const [lastSavedTime, setLastSavedTime] = useState('');
  const [copied, setCopied] = useState(false);
  const [showHold, setShowHold] = useState(false);
  const [showTails, setShowTails] = useState(false);

  const [dcaAmount, setDcaAmount] = useState(3000);
  const [dcaSummary, setDcaSummary] = useState('');
  const [dcaLoading, setDcaLoading] = useState(false);
  const [dcaItems, setDcaItems] = useState<Array<{ fund_code: string; fund_name: string; amount: number; weight_pct?: number; reason?: string }>>([]);
  const [divAdvice, setDivAdvice] = useState<DividendAdviceResponse | null>(null);

  useEffect(() => {
    let alive = true;
    setLoading(true);
    Promise.all([api.getRebalance(ledgerId), api.getCheckin(), api.getDividendAdvice(ledgerId).catch(() => null)])
      .then(([reb, chk, divRes]) => {
        if (!alive) return;
        setData(reb);
        if (divRes) setDivAdvice(divRes);
        const codes = new Set<string>();
        const rawMap = chk?.checked_codes || {};
        for (const [k, v] of Object.entries(rawMap)) {
          if (v === true || (typeof v === 'object' && v !== null && v.checked !== false)) {
            codes.add(k);
          }
        }
        setCheckedSet(codes);
      })
      .catch(() => {})
      .finally(() => {
        if (alive) setLoading(false);
      });
    return () => {
      alive = false;
    };
  }, [ledgerId, refreshTick]);

  useEffect(() => {
    let alive = true;
    const t = setTimeout(() => {
      setDcaLoading(true);
      api
        .planCashflow(Math.max(500, dcaAmount || 3000), ledgerId)
        .then((res) => {
          if (!alive) return;
          const raw = (res.dca_plan || {}) as Record<string, unknown>;
          setDcaSummary(String(raw.summary_text || raw.advice_summary || ''));
          const list = (raw.allocations || raw.monthly_allocations || raw.items || []) as Array<Record<string, unknown>>;
          setDcaItems(
            list.slice(0, 6).map((x) => {
              const code = String(x.fund_code || x['基金代码'] || x.code || '');
              const name = String(x.fund_name || x['基金名称'] || x.name || code);
              const amt = Number(x.monthly_amount ?? x['每月定投金额(元)'] ?? x.amount ?? x.buy_amount ?? 0);
              const pctRaw = x.target_weight_pct ?? x['目标配置占比'] ?? x.weight_pct;
              const pct = pctRaw !== undefined ? Number(String(pctRaw).replace('%', '')) : undefined;
              return {
                fund_code: code,
                fund_name: name,
                amount: amt,
                weight_pct: Number.isFinite(pct) ? pct : undefined,
                reason: String(x.reason || x.note || '优先补齐当前低配核心资产'),
              };
            })
          );
        })
        .catch(() => {})
        .finally(() => {
          if (alive) setDcaLoading(false);
        });
    }, 180);
    return () => {
      alive = false;
      clearTimeout(t);
    };
  }, [dcaAmount, ledgerId, refreshTick]);

  const actionableList = useMemo(() => {
    if (!data) return [];
    const out: Array<{ group: string; item: RebalanceItem; code: string; name: string; amount: number }> = [];
    const pushGroup = (gName: string, items: RebalanceItem[]) => {
      for (const it of items || []) {
        const code = String(it.fund_code || it.code || '');
        const name = String(it.fund_name || it.name || code);
        const amt = Number(it.diff_amount ?? it.amount ?? 0);
        out.push({ group: gName, item: it, code, name, amount: amt });
      }
    };
    pushGroup('C转A省费', data.c_replace?.items || []);
    pushGroup('核心调仓', data.core_trades?.items || []);
    pushGroup('清理尾仓', data.tail_sweep?.items || []);
    return out;
  }, [data]);

  const toggleCheck = async (code: string, amount: number) => {
    const prev = new Set(checkedSet);
    const next = new Set(checkedSet);
    const nextChecked = !next.has(code);
    if (nextChecked) next.add(code);
    else next.delete(code);
    setCheckedSet(next);
    setSaveStatus('saving');
    try {
      const action = amount > 0 ? 'BUY' : 'SELL';
      await api.saveCheckinItem(code, action, Math.abs(amount), nextChecked);
      const nowStr = new Date().toLocaleTimeString('zh-CN', { hour12: false });
      setLastSavedTime(nowStr);
      setSaveStatus('saved');
      onToast(nextChecked ? `已勾选 ${code} 并自动保存至本机（${nowStr}）` : `已取消勾选 ${code} 并同步保存`);
    } catch (e) {
      setCheckedSet(prev);
      setSaveStatus('error');
      onToast(e instanceof Error ? `保存失败：${e.message}` : '保存勾选状态失败，请重试');
    }
  };

  const handleCopy = async () => {
    const text = data?.cheat_sheet_text || '今日无需买卖操作。';
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      onToast('已复制调仓参考清单到剪贴板，请自行对照基金 App 操作');
      setTimeout(() => setCopied(false), 2000);
    } catch {
      onToast('复制失败，请手动选中文本复制');
    }
  };

  if (loading) {
    return <div className="card-elevated rounded-2xl p-10 text-center text-xs text-slate-500">正在测算今日调仓参考方案...</div>;
  }

  const tailCount = data?.tail_sweep?.count || 0;
  const tailCash = data?.tail_sweep?.recovered_cash || 0;
  const cCount = data?.c_replace?.count || 0;
  const coreCount = data?.core_trades?.count || 0;
  const holdCount = data?.buffer_hold?.count || 0;
  const doneCount = actionableList.filter((x) => checkedSet.has(x.code)).length;

  return (
    <div className="space-y-6 fade-in">
      {/* 醒目定位声明 + 一键复制 + 次日同步 */}
      <section className="hero-navy text-white rounded-2xl px-5 py-4 flex flex-wrap items-center justify-between gap-4 shadow-md">
        <div className="text-xs leading-relaxed max-w-2xl">
          <span className="inline-block px-2 py-0.5 rounded bg-amber-400/20 text-amber-300 font-semibold mr-2">
            纯量化分析参考 · 不涉及实盘交易
          </span>
          <span className="text-slate-200">
            以下清单供你核对后自行在支付宝 / 天天基金 App 操作；勾选仅作当天防漏记录，次日份额确认后点击「次日更新持仓」覆盖导入即可完成闭环。
          </span>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <button
            type="button"
            onClick={handleCopy}
            className="px-4 py-2 rounded-xl text-xs font-semibold gold-badge text-[#091529] hover:brightness-110 shadow-sm inline-flex items-center gap-1.5 cursor-pointer"
          >
            {copied ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
            <span>{copied ? '已复制清单' : '一键复制参考清单'}</span>
          </button>
          <button
            type="button"
            onClick={onOpenImport}
            className="px-3.5 py-2 rounded-xl text-xs font-medium bg-white/10 border border-white/15 text-white hover:bg-white/20 inline-flex items-center gap-1.5 cursor-pointer"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            <span>次日更新持仓</span>
          </button>
        </div>
      </section>

      {/* ① 当前组合 3 步重构摘要 */}
      <section className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="card-elevated rounded-2xl p-4 border-t-4 border-t-amber-500">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-amber-700">STEP 01 · 清理碎片尾仓</span>
            <span className="text-[11px] px-2 py-0.5 rounded-full bg-amber-50 text-amber-700 font-semibold">{tailCount} 只</span>
          </div>
          <div className="text-lg font-extrabold text-slate-900 mt-1.5 tabular-nums">
            {tailCount > 0 ? `回收 ¥${tailCash.toLocaleString('zh-CN', { minimumFractionDigits: 2 })}` : '暂无碎片尾仓'}
          </div>
          <p className="text-xs text-slate-500 mt-1">
            {tailCount > 0 ? '单只不足 ¥200 且满免赎期，清仓归拢减少盯盘负担。' : '持仓精简整洁，无需清理尾仓。'}
          </p>
        </div>

        <div className="card-elevated rounded-2xl p-4 border-t-4 border-t-indigo-600">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-indigo-700">STEP 02 · C 转 A 省管理费</span>
            <span className="text-[11px] px-2 py-0.5 rounded-full bg-indigo-50 text-indigo-700 font-semibold">{cCount} 笔</span>
          </div>
          <div className="text-lg font-extrabold text-slate-900 mt-1.5">
            {cCount > 0 ? '年省 0.40% 服务费' : '暂无高费 C 类置换'}
          </div>
          <p className="text-xs text-slate-500 mt-1">
            {cCount > 0 ? '满 30 天免赎回费置换为同款 A 类，长期持有更省钱。' : '当前份额类别结构合理。'}
          </p>
        </div>

        <div className="card-elevated rounded-2xl p-4 border-t-4 border-t-blue-600">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-blue-700">STEP 03 · 核心仓位再平衡</span>
            <span className="text-[11px] px-2 py-0.5 rounded-full bg-blue-50 text-blue-700 font-semibold">{coreCount} 笔</span>
          </div>
          <div className="text-lg font-extrabold text-slate-900 mt-1.5">
            {coreCount > 0 ? '对齐今日量化目标仓位' : '核心仓位已达标'}
          </div>
          <p className="text-xs text-slate-500 mt-1">
            {coreCount > 0 ? '高抛超配、低吸欠配，压低组合波动与回撤。' : `其余 ${holdCount} 只核心仓位在安全缓冲区内，安心持有。`}
          </p>
        </div>
      </section>

      {/* ② 分组调仓参考清单 */}
      <section className="card-elevated rounded-2xl overflow-hidden">
        <div className="p-4 sm:px-5 border-b border-slate-200 flex flex-wrap items-center justify-between gap-2">
          <div>
            <h2 className="text-base font-bold text-slate-900">建议调整明细（附白话理由）</h2>
            <p className="text-xs text-slate-500 mt-0.5">勾选左侧复选框记录你在基金 App 中已手动完成的笔数</p>
          </div>
          <div className="flex items-center gap-2">
            {saveStatus === 'saving' && (
              <span className="text-xs font-medium px-2.5 py-1 rounded-full bg-slate-100 text-slate-600">正在保存...</span>
            )}
            {saveStatus === 'saved' && (
              <span className="text-xs font-semibold px-2.5 py-1 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200 inline-flex items-center gap-1">
                <Check className="w-3.5 h-3.5" />
                已保存至本机 {lastSavedTime}
              </span>
            )}
            {saveStatus === 'error' && (
              <span className="text-xs font-semibold px-2.5 py-1 rounded-full bg-red-50 text-red-700 border border-red-200">
                保存失败，请重试
              </span>
            )}
            <span className="text-xs font-semibold px-3 py-1 rounded-full bg-blue-50 text-blue-700 border border-blue-200 tabular-nums">
              本地已记录 {doneCount} / {actionableList.length} 笔
            </span>
          </div>
        </div>

        {actionableList.length === 0 ? (
          <div className="p-8 text-center text-sm text-slate-500">当前组合处于目标安全缓冲区内，今日无需买卖操作，安心持有即可。</div>
        ) : (
          <div className="divide-y divide-slate-100">
            {/* 先展示 C转A 和 核心调仓 */}
            {actionableList
              .filter((x) => x.group !== '清理尾仓')
              .map(({ group, item, code, name, amount }) => {
                const isBuy = amount > 0;
                const done = checkedSet.has(code);
                return (
                  <label
                    key={`${group}-${code}`}
                    className={`p-4 sm:px-5 flex items-start gap-3.5 cursor-pointer hover:bg-slate-50/80 transition-colors ${
                      done ? 'opacity-55 bg-slate-50/50' : ''
                    }`}
                  >
                    <input
                      type="checkbox"
                      checked={done}
                      onChange={() => toggleCheck(code, amount)}
                      className="mt-1 w-4 h-4 accent-[#0A192F]"
                    />
                    <div className="flex-1 min-w-0 space-y-1">
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <div className="flex flex-wrap items-center gap-2">
                          <span className="px-2 py-0.5 rounded-md text-[11px] font-semibold bg-slate-100 text-slate-700">{group}</span>
                          <span
                            className={`px-2 py-0.5 rounded-md text-[11px] font-bold border ${
                              isBuy ? 'bg-red-50 text-red-700 border-red-200' : 'bg-emerald-50 text-emerald-700 border-emerald-200'
                            }`}
                          >
                            {isBuy ? '买入增配' : '卖出减仓'}
                          </span>
                          <span className={`font-bold text-sm text-slate-900 ${done ? 'line-through' : ''}`}>
                            {name} <span className="font-mono text-xs text-slate-400">({code})</span>
                          </span>
                          {done && (
                            <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
                              ✓ 已记录并保存
                            </span>
                          )}
                        </div>
                        <span className="font-extrabold text-sm text-slate-900 tabular-nums">
                          ¥{Math.abs(amount).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                        </span>
                      </div>
                      <p className="text-xs text-slate-500">
                        {item.reason || (isBuy ? '当前权重低于今日量化目标，建议补齐核心底仓' : '当前权重偏高或风格重叠，建议适度兑现归拢')}
                      </p>
                    </div>
                  </label>
                );
              })}

            {/* 碎片尾仓折叠组，避免 19 条霸屏 */}
            {tailCount > 0 && (
              <div>
                <button
                  type="button"
                  onClick={() => setShowTails(!showTails)}
                  className="w-full px-5 py-3.5 flex items-center justify-between text-xs font-semibold text-amber-800 bg-amber-50/50 hover:bg-amber-50 transition-colors cursor-pointer"
                >
                  <span className="inline-flex items-center gap-1.5">
                    {showTails ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
                    展开查看 {tailCount} 只碎片尾仓清理清单（合计回收 ¥{tailCash.toLocaleString('zh-CN', { minimumFractionDigits: 2 })}）
                  </span>
                  <span className="text-amber-700">全部满 7 天免惩罚费</span>
                </button>
                {showTails && (
                  <div className="divide-y divide-slate-100 bg-slate-50/40">
                    {actionableList
                      .filter((x) => x.group === '清理尾仓')
                      .map(({ code, name, amount }) => {
                        const done = checkedSet.has(code);
                        return (
                          <label
                            key={`tail-${code}`}
                            className={`px-5 py-2.5 flex items-center justify-between gap-3 cursor-pointer text-xs hover:bg-slate-100/70 ${
                              done ? 'opacity-50 line-through' : ''
                            }`}
                          >
                            <span className="flex items-center gap-2.5">
                              <input
                                type="checkbox"
                                checked={done}
                                onChange={() => toggleCheck(code, amount)}
                                className="w-3.5 h-3.5 accent-[#0A192F]"
                              />
                              <span className="font-medium text-slate-800">{name}</span>
                              <span className="font-mono text-slate-400">{code}</span>
                            </span>
                            <span className="font-semibold text-emerald-700 tabular-nums">
                              卖出 ¥{Math.abs(amount).toFixed(2)}
                            </span>
                          </label>
                        );
                      })}
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* 维持持有折叠条 */}
        {holdCount > 0 && (
          <div className="border-t border-slate-200">
            <button
              type="button"
              onClick={() => setShowHold(!showHold)}
              className="w-full px-5 py-3 flex items-center justify-between text-xs text-slate-500 hover:bg-slate-50 cursor-pointer"
            >
              <span className="inline-flex items-center gap-1.5">
                {showHold ? <ChevronDown className="w-3.5 h-3.5" /> : <ChevronRight className="w-3.5 h-3.5" />}
                维持不动的核心持仓（{holdCount} 只，权重偏差在安全缓冲区内）
              </span>
            </button>
            {showHold && (
              <div className="px-5 pb-4 flex flex-wrap gap-2">
                {(data?.buffer_hold?.items || []).map((it, idx) => (
                  <span key={idx} className="px-2.5 py-1 rounded-lg bg-slate-100 text-xs text-slate-700">
                    {it.fund_name || it.name} <span className="font-mono text-slate-400">{it.fund_code || it.code}</span>
                  </span>
                ))}
              </div>
            )}
          </div>
        )}
      </section>

      {/* ③ 增量新钱定投方案（不动老基金） */}
      <section className="card-elevated rounded-2xl p-5 space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <div className="flex items-center gap-2">
              <span className="w-1 h-4 rounded-full bg-emerald-600" />
              <h2 className="text-base font-bold text-slate-900">不想卖老基金？用每月新钱补齐偏离</h2>
            </div>
            <p className="text-xs text-slate-500 mt-1 pl-3">输入计划新增投入金额，系统自动优先分配给当前欠配的优质底仓</p>
          </div>
          <label className="flex items-center gap-2 text-xs font-medium text-slate-600">
            <span>本月新增资金 (¥)</span>
            <input
              type="number"
              min={500}
              step={500}
              value={dcaAmount}
              onChange={(e) => setDcaAmount(Number(e.target.value))}
              className="w-28 h-9 px-3 rounded-lg bg-slate-50 border border-slate-200 text-slate-900 font-bold tabular-nums text-sm focus:border-blue-600 focus:bg-white focus:outline-none"
            />
          </label>
        </div>

        {dcaSummary && (
          <div className="px-3.5 py-2 rounded-xl bg-emerald-50/70 border border-emerald-200 text-xs text-emerald-900">
            {dcaSummary}
          </div>
        )}

        {dcaLoading && dcaItems.length === 0 ? (
          <div className="text-xs text-slate-400 py-2">正在计算增量定投分配方案...</div>
        ) : dcaItems.length === 0 ? (
          <div className="text-xs text-slate-400 py-2">输入金额后自动生成增量定投参考方案...</div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3.5">
            {dcaItems.map((d) => (
              <div key={d.fund_code} className="p-4 rounded-xl bg-slate-50/80 border border-slate-200 space-y-1.5">
                <div className="flex justify-between items-center text-xs">
                  <span className="font-mono text-slate-400">{d.fund_code}</span>
                  {d.weight_pct !== undefined && (
                    <span className="font-bold text-blue-700">目标占比 {d.weight_pct.toFixed(1)}%</span>
                  )}
                </div>
                <div className="font-bold text-sm text-slate-900">{d.fund_name}</div>
                <div className="text-lg font-extrabold text-slate-900 tabular-nums">
                  ¥{d.amount.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                </div>
                <div className="text-xs text-slate-500">{d.reason}</div>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* ④ 大额限购分批买入计划 + 宏观分红方式建议 */}
      <section className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="card-elevated rounded-2xl p-5 space-y-3">
          <div className="flex items-center gap-2">
            <CalendarClock className="w-4 h-4 text-blue-700" />
            <h2 className="text-sm font-bold text-slate-900">大额限购分批买入计划与到账说明</h2>
          </div>
          {(data?.quota_split_plans || []).length === 0 ? (
            <p className="text-xs text-slate-500">当前参考买入清单中暂无限购拆单需求，可按单日完成配置。</p>
          ) : (
            <div className="space-y-2.5 text-xs">
              {(data?.quota_split_plans || []).map((q) => (
                <div key={q.fund_code} className="p-3 rounded-xl bg-slate-50 border border-slate-200 space-y-1">
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-bold text-slate-900">
                      {q.fund_name} <span className="font-mono text-slate-400">({q.fund_code})</span>
                    </span>
                    <span
                      className={`px-2 py-0.5 rounded-full text-[11px] font-semibold ${
                        q.needs_split ? 'bg-amber-50 text-amber-700' : 'bg-emerald-50 text-emerald-700'
                      }`}
                    >
                      {q.needs_split ? `需分 ${q.days_needed} 个交易日买入` : '单日可一次买完'}
                    </span>
                  </div>
                  <div className="text-slate-600 tabular-nums">
                    计划买入 <strong>¥{Number(q.total_amount || 0).toLocaleString()}</strong>
                    {q.daily_limit ? ` · 单日限额 ¥${Number(q.daily_limit).toLocaleString()}` : ''}
                    {q.settlement?.description ? ` · ${q.settlement.description}` : ''}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="card-elevated rounded-2xl p-5 space-y-3">
          <div className="flex items-center justify-between gap-2">
            <div className="flex items-center gap-2">
              <Coins className="w-4 h-4 text-amber-600" />
              <h2 className="text-sm font-bold text-slate-900">基金分红方式建议</h2>
            </div>
            {divAdvice && (
              <span className="px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-amber-50 text-amber-800 border border-amber-200">
                当前首选：{divAdvice.recommended_label}
              </span>
            )}
          </div>
          <p className="text-xs text-slate-600 leading-relaxed">
            {divAdvice?.summary || '根据当前市场估值分位，建议低估区间优先选择“红利再投资”免申购费滚份额，高估区间优先选择“现金分红”落袋为安。'}
          </p>
          <p className="text-[11px] text-slate-400">
            提示：可在支付宝 / 天天基金 App 的单只基金持仓详情页中修改“分红方式”，修改后次个交易日生效且完全免费。
          </p>
        </div>
      </section>
    </div>
  );
}

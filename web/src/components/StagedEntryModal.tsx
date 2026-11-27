import { useEffect, useId, useRef, useState } from 'react';
import { X, Copy, Check, Layers, Flame, ArrowRight, CalendarClock } from 'lucide-react';
import { api, type BlueprintItem, type StagedEntryPlanResponse } from '../api/client';

interface StagedEntryModalProps {
  open: boolean;
  items: BlueprintItem[];
  totalAmount: number;
  horizonMonths: number;
  marketRegime?: string;
  onClose: () => void;
  onGoRebalance: () => void;
  onNotify: (msg: string, tone?: 'default' | 'success' | 'warning' | 'error') => void;
}

const MODES: Array<{ id: 'smart_3_tranche' | 'dca_4_week' | 'lump_sum'; label: string; desc: string }> = [
  { id: 'smart_3_tranche', label: '智能三批 40/30/30（推荐）', desc: '首笔先建底仓防踏空，偏热基自动压降首笔至 25%' },
  { id: 'dca_4_week', label: '4 周均分定投', desc: '每周 25% 匀速平滑震荡成本' },
  { id: 'lump_sum', label: '一步到位 100%', desc: '低估或低波债基一次配齐' },
];

export function StagedEntryModal({
  open,
  items,
  totalAmount,
  horizonMonths,
  marketRegime,
  onClose,
  onGoRebalance,
  onNotify,
}: StagedEntryModalProps) {
  const dlgRef = useRef<HTMLDialogElement | null>(null);
  const titleId = useId();
  const [mode, setMode] = useState<'smart_3_tranche' | 'dca_4_week' | 'lump_sum'>('smart_3_tranche');
  const [plan, setPlan] = useState<StagedEntryPlanResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    const dlg = dlgRef.current;
    if (!dlg) return;
    if (open) {
      if (!dlg.open) dlg.showModal();
    } else if (dlg.open) {
      dlg.close();
    }
  }, [open]);

  useEffect(() => {
    const dlg = dlgRef.current;
    if (!dlg) return;
    const onNativeClose = () => {
      dlg.returnValue = '';
      onClose();
    };
    dlg.addEventListener('close', onNativeClose);

    // modern-web-guidance: closedby="any" pointer-position fallback for browsers lacking HTMLDialogElement.prototype.closedBy
    let cleanupOutside: (() => void) | undefined;
    if (!('closedBy' in HTMLDialogElement.prototype)) {
      const outside = (e: PointerEvent) => {
        const r = dlg.getBoundingClientRect();
        return e.clientX < r.left || e.clientX > r.right || e.clientY < r.top || e.clientY > r.bottom;
      };
      let pressedOutside = false;
      const onDown = (e: PointerEvent) => {
        pressedOutside = outside(e);
      };
      const onUp = (e: PointerEvent) => {
        if (pressedOutside && outside(e) && dlg.open) dlg.close();
      };
      dlg.addEventListener('pointerdown', onDown);
      dlg.addEventListener('pointerup', onUp);
      cleanupOutside = () => {
        dlg.removeEventListener('pointerdown', onDown);
        dlg.removeEventListener('pointerup', onUp);
      };
    }

    return () => {
      dlg.removeEventListener('close', onNativeClose);
      cleanupOutside?.();
    };
  }, [onClose]);

  useEffect(() => {
    if (!open || items.length === 0) return;
    let alive = true;
    setLoading(true);
    api
      .buildStagedEntryPlan({
        items,
        total_amount: totalAmount,
        horizon_months: horizonMonths,
        mode,
        market_regime: marketRegime,
      })
      .then((res) => {
        if (alive) setPlan(res);
      })
      .catch((e) => {
        if (alive) onNotify(e instanceof Error ? e.message : '生成建仓计划失败', 'error');
      })
      .finally(() => {
        if (alive) setLoading(false);
      });
    return () => {
      alive = false;
    };
  }, [open, items, totalAmount, horizonMonths, mode, marketRegime, onNotify]);

  const handleCopy = async () => {
    if (!plan?.copyable_checklist_text) return;
    try {
      await navigator.clipboard.writeText(plan.copyable_checklist_text);
      setCopied(true);
      onNotify('已复制银行/支付宝分批建仓执行清单', 'success');
      setTimeout(() => setCopied(false), 2000);
    } catch {
      onNotify('复制失败，请手动选中复制', 'warning');
    }
  };

  return (
    <dialog
      ref={dlgRef}
      aria-labelledby={titleId}
      {...({ closedby: 'any' } as Record<string, string>)}
      className="dialog-lg rounded-xl shadow-2xl"
    >
      {open && (
        <div className="bg-white border border-slate-200 rounded-xl overflow-hidden flex flex-col max-h-[88vh]">
          <div className="px-5 py-3.5 inst-panel-header flex items-center justify-between gap-3">
            <div className="flex items-center gap-2.5 min-w-0">
              <span className="w-8 h-8 rounded-lg bg-[#0B192C] text-amber-400 flex items-center justify-center shrink-0">
                <Layers className="w-4 h-4" />
              </span>
              <div className="min-w-0">
                <h1 id={titleId} className="text-sm font-bold text-slate-900">
                  智能分批建仓执行向导（100% 场外基金）
                </h1>
                <p className="text-[11px] text-slate-500 tabular-nums">
                  拟投本金 ¥{totalAmount.toLocaleString()} · {items.length} 只基金 · 计划持有 {horizonMonths} 个月（15:00 前下单按当日净值确认）
                </p>
              </div>
            </div>
            <button
              type="button"
              onClick={() => dlgRef.current?.close()}
              aria-label="关闭分批建仓向导"
              className="w-8 h-8 rounded-lg flex items-center justify-center text-slate-400 hover:text-slate-800 hover:bg-slate-200/70 cursor-pointer shrink-0"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          <div className="p-5 overflow-y-auto space-y-4 text-xs">
            {/* 模式切换 */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-2" role="group" aria-label="分批建仓模式">
              {MODES.map((m) => {
                const active = mode === m.id;
                return (
                  <button
                    key={m.id}
                    type="button"
                    onClick={() => setMode(m.id)}
                    className={`p-3 rounded-lg border text-left transition-all cursor-pointer ${
                      active
                        ? 'bg-blue-50/80 border-blue-600 ring-1 ring-blue-600/20'
                        : 'bg-white border-slate-200 hover:border-slate-300'
                    }`}
                  >
                    <div className={`font-bold text-xs ${active ? 'text-blue-900' : 'text-slate-900'}`}>{m.label}</div>
                    <div className="text-[11px] text-slate-500 mt-0.5 leading-snug">{m.desc}</div>
                  </button>
                );
              })}
            </div>

            {plan && (plan.hot_throttled_count > 0 || plan.quota_split_count > 0) && (
              <div className="flex flex-wrap gap-2 text-[11px]">
                {plan.hot_throttled_count > 0 && (
                  <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md bg-amber-50 border border-amber-200 text-amber-900 font-medium">
                    <Flame className="w-3.5 h-3.5 text-amber-600" />
                    已自动保护 {plan.hot_throttled_count} 只短线偏热基金：首笔压降至 25% 防追高
                  </span>
                )}
                {plan.quota_split_count > 0 && (
                  <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md bg-blue-50 border border-blue-200 text-blue-900 font-medium">
                    <CalendarClock className="w-3.5 h-3.5 text-blue-600" />
                    含 {plan.quota_split_count} 只单日限购基金，已自动标注需拆单日定投天数
                  </span>
                )}
              </div>
            )}

            {loading ? (
              <div className="py-10 text-center text-slate-400">正在按市场温度与单日限额测算分批计划...</div>
            ) : (
              <div className="space-y-3">
                {(plan?.tranches || []).map((tr) => (
                  <div key={tr.index} className="rounded-lg border border-slate-200 overflow-hidden">
                    <div className="px-4 py-2.5 bg-slate-50 border-b border-slate-200 flex flex-wrap items-center justify-between gap-2">
                      <div>
                        <span className="font-bold text-slate-900">{tr.title}</span>
                        <span className="ml-2 text-[11px] text-slate-500">{tr.trigger}</span>
                      </div>
                      <span className="font-mono font-extrabold text-slate-900 tabular-nums">
                        本批合计 ¥{tr.subtotal.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                      </span>
                    </div>
                    <div className="divide-y divide-slate-100 tabular-nums">
                      {tr.orders.map((od) => (
                        <div key={`${tr.index}-${od.fund_code}`} className="px-4 py-2 flex flex-wrap items-center justify-between gap-2 hover:bg-slate-50/70">
                          <div className="min-w-0">
                            <div className="flex flex-wrap items-center gap-1.5">
                              <span className="font-semibold text-slate-900">{od.fund_name}</span>
                              <span className="font-mono text-[11px] text-slate-400">{od.fund_code}</span>
                              {od.c_share_code && (
                                <span className="px-1.5 py-0.5 rounded bg-blue-50 border border-blue-200 text-blue-800 text-[10px] font-semibold">
                                  ≤1年可改买 C 类 {od.c_share_code}
                                </span>
                              )}
                              {od.split_days > 1 && (
                                <span className="px-1.5 py-0.5 rounded bg-amber-50 border border-amber-200 text-amber-800 text-[10px] font-semibold">
                                  限购分 {od.split_days} 日
                                </span>
                              )}
                            </div>
                            <div className="text-[11px] text-slate-500 mt-0.5">{od.execution_note}</div>
                          </div>
                          <div className="text-right shrink-0">
                            <div className="font-bold text-slate-900">
                              ¥{od.amount.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                            </div>
                            <div className="text-[10px] text-slate-400">占该基 {od.tranche_ratio_pct.toFixed(0)}%</div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="px-5 py-3 border-t border-slate-200 bg-slate-50 flex flex-wrap items-center justify-between gap-2">
            <span className="text-[11px] text-slate-500">
              提示：银行 / 支付宝 / 天天基金在交易日 15:00 前提交申购按当日净值确认
            </span>
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => void handleCopy()}
                disabled={!plan}
                data-testid="btn-copy-staged-plan"
                className="px-3.5 py-1.5 rounded-lg text-xs font-bold bg-amber-500 text-[#0B192C] hover:bg-amber-400 inline-flex items-center gap-1.5 cursor-pointer disabled:opacity-50"
              >
                {copied ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
                <span>{copied ? '已复制执行清单' : '复制银行/支付宝清单'}</span>
              </button>
              <button
                type="button"
                onClick={() => {
                  dlgRef.current?.close();
                  onGoRebalance();
                }}
                className="px-3.5 py-1.5 rounded-lg text-xs font-semibold bg-[#0B192C] text-white hover:bg-[#132845] inline-flex items-center gap-1 cursor-pointer"
              >
                <span>去调仓台对照</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        </div>
      )}
    </dialog>
  );
}

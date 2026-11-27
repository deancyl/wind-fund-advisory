import { useEffect, useId, useRef, useState } from 'react';
import { X, Plus, Trash2, ReceiptText } from 'lucide-react';
import { api, type CashflowSummaryResponse } from '../api/client';

interface CashflowModalProps {
  open: boolean;
  ledgerId: string;
  ledgerName: string;
  summary: CashflowSummaryResponse | null;
  onUpdated: (next: CashflowSummaryResponse) => void;
  onClose: () => void;
  onNotify: (msg: string, tone?: 'default' | 'success' | 'warning' | 'error') => void;
}

const TX_LABELS: Record<string, { label: string; cls: string }> = {
  BUY: { label: '买入/定投', cls: 'bg-red-50 text-red-700 border-red-200' },
  DEPOSIT: { label: '资金转入', cls: 'bg-red-50 text-red-700 border-red-200' },
  SELL: { label: '赎回卖出', cls: 'bg-emerald-50 text-emerald-700 border-emerald-200' },
  WITHDRAW: { label: '资金转出', cls: 'bg-emerald-50 text-emerald-700 border-emerald-200' },
  DIVIDEND: { label: '现金分红', cls: 'bg-amber-50 text-amber-800 border-amber-200' },
};

export function CashflowModal({
  open,
  ledgerId,
  ledgerName,
  summary,
  onUpdated,
  onClose,
  onNotify,
}: CashflowModalProps) {
  const dlgRef = useRef<HTMLDialogElement | null>(null);
  const titleId = useId();
  const [txDate, setTxDate] = useState(() => new Date().toISOString().slice(0, 10));
  const [txType, setTxType] = useState<'BUY' | 'SELL' | 'DIVIDEND'>('BUY');
  const [amount, setAmount] = useState('5000');
  const [fundCode, setFundCode] = useState('');
  const [note, setNote] = useState('');
  const [saving, setSaving] = useState(false);

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

  const handleAdd = async (e: React.FormEvent) => {
    e.preventDefault();
    const num = Number(amount);
    if (Number.isNaN(num) || num <= 0) {
      onNotify('请输入大于 0 的有效金额', 'warning');
      return;
    }
    setSaving(true);
    try {
      const res = await api.addLedgerCashflow({
        ledger_id: ledgerId,
        date: txDate,
        tx_type: txType,
        amount: num,
        fund_code: fundCode.trim(),
        note: note.trim(),
      });
      onUpdated(res.summary);
      setFundCode('');
      setNote('');
      onNotify('已记入交易流水并重算真实年化 XIRR', 'success');
    } catch (err) {
      onNotify(err instanceof Error ? err.message : '保存交易流水失败', 'error');
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (id: string) => {
    try {
      const res = await api.deleteLedgerCashflow(id, ledgerId);
      onUpdated(res.summary);
      onNotify('已删除该条交易流水', 'default');
    } catch (err) {
      onNotify(err instanceof Error ? err.message : '删除失败', 'error');
    }
  };

  const records = summary?.records || [];

  return (
    <dialog
      ref={dlgRef}
      aria-labelledby={titleId}
      {...({ closedby: 'any' } as Record<string, string>)}
      className="rounded-xl shadow-2xl"
    >
      {open && (
        <div className="bg-white border border-slate-200 rounded-xl overflow-hidden flex flex-col max-h-[86vh]">
          <div className="px-5 py-3.5 inst-panel-header flex items-center justify-between gap-2">
            <div className="flex items-center gap-2.5">
              <span className="w-8 h-8 rounded-lg bg-[#0B192C] text-sky-300 flex items-center justify-center shrink-0">
                <ReceiptText className="w-4 h-4" />
              </span>
              <div>
                <h1 id={titleId} className="text-sm font-bold text-slate-900">
                  真实交易流水与资金加权年化 XIRR（{ledgerName}）
                </h1>
                <p className="text-[11px] text-slate-500">
                  {summary?.source_label || '记录每笔申购/定投/赎回/分红，精准还原真实年化赚钱效率（仅存本机私有文件）'}
                </p>
              </div>
            </div>
            <button
              type="button"
              onClick={() => dlgRef.current?.close()}
              aria-label="关闭交易流水弹窗"
              className="w-8 h-8 rounded-lg flex items-center justify-center text-slate-400 hover:text-slate-800 hover:bg-slate-200/70 cursor-pointer"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          <div className="p-5 overflow-y-auto space-y-4 text-xs">
            {/* XIRR 汇总条 */}
            {summary && (
              <div className="grid grid-cols-2 sm:grid-cols-4 border border-slate-200 rounded-lg divide-y sm:divide-y-0 sm:divide-x divide-slate-200 bg-slate-50/50 tabular-nums">
                <div className="p-3">
                  <div className="text-[11px] text-slate-500">年化资金加权 XIRR</div>
                  <div
                    className={`text-lg font-extrabold mt-0.5 ${
                      (summary.xirr_pct ?? 0) >= 0 ? 'text-red-600' : 'text-emerald-700'
                    }`}
                  >
                    {summary.xirr_pct !== null
                      ? `${summary.xirr_pct >= 0 ? '+' : ''}${summary.xirr_pct.toFixed(2)}%`
                      : '--'}
                  </div>
                </div>
                <div className="p-3">
                  <div className="text-[11px] text-slate-500">累计投入资金</div>
                  <div className="text-sm font-bold text-slate-900 mt-1">
                    ¥{summary.total_invested.toLocaleString('zh-CN', { minimumFractionDigits: 2 })}
                  </div>
                </div>
                <div className="p-3">
                  <div className="text-[11px] text-slate-500">累计赎回 / 分红</div>
                  <div className="text-sm font-bold text-slate-900 mt-1">
                    ¥{summary.total_withdrawn.toLocaleString('zh-CN', { minimumFractionDigits: 2 })}
                  </div>
                </div>
                <div className="p-3">
                  <div className="text-[11px] text-slate-500">累计净收益</div>
                  <div className={`text-sm font-bold mt-1 ${summary.net_profit >= 0 ? 'text-red-600' : 'text-emerald-700'}`}>
                    {summary.net_profit >= 0 ? '+' : '-'}¥
                    {Math.abs(summary.net_profit).toLocaleString('zh-CN', { minimumFractionDigits: 2 })}
                  </div>
                </div>
              </div>
            )}

            {/* 记一笔表单 */}
            <form onSubmit={handleAdd} className="p-3.5 rounded-lg bg-slate-50 border border-slate-200 space-y-3">
              <div className="font-bold text-slate-800">记一笔真实资金流水</div>
              <div className="grid grid-cols-2 sm:grid-cols-5 gap-2">
                <label className="space-y-1">
                  <span className="text-[11px] text-slate-500">交易日期</span>
                  <input
                    type="date"
                    value={txDate}
                    onChange={(e) => setTxDate(e.target.value)}
                    required
                    className="w-full h-8 px-2 rounded-md bg-white border border-slate-300 text-xs tabular-nums"
                  />
                </label>
                <label className="space-y-1">
                  <span className="text-[11px] text-slate-500">操作类型</span>
                  <select
                    value={txType}
                    onChange={(e) => setTxType(e.target.value as 'BUY' | 'SELL' | 'DIVIDEND')}
                    className="w-full h-8 px-2 rounded-md bg-white border border-slate-300 text-xs font-medium"
                  >
                    <option value="BUY">买入 / 定投</option>
                    <option value="SELL">赎回 / 止盈</option>
                    <option value="DIVIDEND">现金分红</option>
                  </select>
                </label>
                <label className="space-y-1">
                  <span className="text-[11px] text-slate-500">金额 (¥)</span>
                  <input
                    type="number"
                    min={1}
                    step={100}
                    value={amount}
                    onChange={(e) => setAmount(e.target.value)}
                    required
                    className="w-full h-8 px-2 rounded-md bg-white border border-slate-300 text-xs font-bold tabular-nums"
                  />
                </label>
                <label className="space-y-1">
                  <span className="text-[11px] text-slate-500">基金代码（可选）</span>
                  <input
                    type="text"
                    value={fundCode}
                    onChange={(e) => setFundCode(e.target.value)}
                    placeholder="如 008163"
                    className="w-full h-8 px-2 rounded-md bg-white border border-slate-300 text-xs font-mono"
                  />
                </label>
                <label className="space-y-1">
                  <span className="text-[11px] text-slate-500">备注（可选）</span>
                  <input
                    type="text"
                    value={note}
                    onChange={(e) => setNote(e.target.value)}
                    placeholder="首笔/定投/止盈"
                    className="w-full h-8 px-2 rounded-md bg-white border border-slate-300 text-xs"
                  />
                </label>
              </div>
              <div className="flex justify-end">
                <button
                  type="submit"
                  disabled={saving}
                  data-testid="btn-submit-cashflow"
                  className="px-3.5 py-1.5 rounded-lg text-xs font-bold bg-[#0B192C] text-white hover:bg-[#132845] inline-flex items-center gap-1.5 cursor-pointer disabled:opacity-50"
                >
                  <Plus className="w-3.5 h-3.5" />
                  <span>{saving ? '记录中...' : '记入流水并重算 XIRR'}</span>
                </button>
              </div>
            </form>

            {/* 历史流水表 */}
            <div className="border border-slate-200 rounded-lg overflow-hidden">
              <div className="px-3.5 py-2 bg-slate-50 border-b border-slate-200 font-bold text-slate-800 flex items-center justify-between">
                <span>已记录交易流水（{records.length} 笔）</span>
                {summary?.is_estimated && (
                  <span className="text-[10px] font-normal text-slate-500">当前尚无手工流水，XIRR 暂由持仓批次推算</span>
                )}
              </div>
              {records.length === 0 ? (
                <div className="py-6 text-center text-slate-400">暂无手工交易流水，添加上方记录后自动切换为实录精准 XIRR</div>
              ) : (
                <div className="max-h-56 overflow-y-auto divide-y divide-slate-100 tabular-nums">
                  {records.map((r) => {
                    const meta = TX_LABELS[r.tx_type] || TX_LABELS.BUY;
                    return (
                      <div key={r.id} className="px-3.5 py-2 flex items-center justify-between gap-2 hover:bg-slate-50">
                        <div className="flex items-center gap-2 min-w-0">
                          <span className="font-mono text-slate-500">{r.date}</span>
                          <span className={`px-1.5 py-0.5 rounded border text-[10px] font-semibold ${meta.cls}`}>
                            {meta.label}
                          </span>
                          {r.fund_code && <span className="font-mono text-slate-700">{r.fund_code}</span>}
                          {r.note && <span className="text-slate-500 truncate">{r.note}</span>}
                        </div>
                        <div className="flex items-center gap-3 shrink-0">
                          <span className="font-bold text-slate-900">
                            ¥{Number(r.amount).toLocaleString('zh-CN', { minimumFractionDigits: 2 })}
                          </span>
                          <button
                            type="button"
                            onClick={() => void handleDelete(r.id)}
                            aria-label="删除流水记录"
                            className="text-slate-400 hover:text-red-600 cursor-pointer"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </dialog>
  );
}

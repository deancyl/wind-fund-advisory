import { useEffect, useId, useRef, useState } from 'react';
import { X, Upload, FileText, PenLine, CheckCircle2, AlertCircle } from 'lucide-react';
import { api } from '../api/client';

interface ImportModalProps {
  open: boolean;
  ledgerId: string;
  onClose: () => void;
  onSuccess: (msg: string) => void;
}

type ImportModeTab = 'text' | 'ocr' | 'manual';

export function ImportModal({ open, ledgerId, onClose, onSuccess }: ImportModalProps) {
  const dialogRef = useRef<HTMLDialogElement | null>(null);
  const titleId = useId();
  const [tab, setTab] = useState<ImportModeTab>('text');
  const [writeMode, setWriteMode] = useState<'merge' | 'overwrite'>('merge');
  const [rawText, setRawText] = useState('');
  const [ocrFile, setOcrFile] = useState<File | null>(null);
  const [manualCode, setManualCode] = useState('');
  const [manualName, setManualName] = useState('');
  const [manualAmount, setManualAmount] = useState('');
  const [manualCost, setManualCost] = useState('1.0');
  const [previewItems, setPreviewItems] = useState<Array<Record<string, unknown>>>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  // 原生 <dialog> showModal() 生命周期与点击背景外侧关闭回退（遵循 modern-web-guidance）
  useEffect(() => {
    const dlg = dialogRef.current;
    if (!dlg) return;
    if (open && !dlg.open) {
      setError('');
      setPreviewItems([]);
      dlg.showModal();
    } else if (!open && dlg.open) {
      dlg.close();
    }
  }, [open]);

  useEffect(() => {
    const dlg = dialogRef.current;
    if (!dlg) return;
    const onNativeClose = () => {
      dlg.returnValue = '';
      onClose();
    };
    let pressedOutside = false;
    const isOutside = (e: PointerEvent) => {
      const r = dlg.getBoundingClientRect();
      return e.clientX < r.left || e.clientX > r.right || e.clientY < r.top || e.clientY > r.bottom;
    };
    const onDown = (e: PointerEvent) => {
      pressedOutside = isOutside(e);
    };
    const onUp = (e: PointerEvent) => {
      if (pressedOutside && isOutside(e)) dlg.close();
    };
    dlg.addEventListener('close', onNativeClose);
    dlg.addEventListener('pointerdown', onDown);
    dlg.addEventListener('pointerup', onUp);
    return () => {
      dlg.removeEventListener('close', onNativeClose);
      dlg.removeEventListener('pointerdown', onDown);
      dlg.removeEventListener('pointerup', onUp);
    };
  }, [onClose]);

  const handlePreviewText = async () => {
    if (!rawText.trim()) {
      setError('请先粘贴基金持仓文本，例如：005561 8000');
      return;
    }
    setBusy(true);
    setError('');
    try {
      const res = await api.importText(rawText, 'preview', ledgerId);
      setPreviewItems(res.items || []);
      if (!res.parsed_count) setError('未识别出有效基金记录，请检查格式（如“6位代码 金额”）。');
    } catch (e) {
      setError(e instanceof Error ? e.message : '解析失败');
    } finally {
      setBusy(false);
    }
  };

  const handleApply = async () => {
    setBusy(true);
    setError('');
    try {
      if (tab === 'text') {
        if (!rawText.trim()) throw new Error('请先输入持仓文本');
        const res = await api.importText(rawText, writeMode, ledgerId);
        if (!res.applied) throw new Error('未能写入有效持仓，请检查输入格式');
        onSuccess(`成功导入 ${res.parsed_count} 只基金（已自动生成冷备快照）`);
        dialogRef.current?.close();
      } else if (tab === 'ocr') {
        if (!ocrFile) throw new Error('请先选择一张持仓截图');
        const res = await api.importOcr(ocrFile, writeMode, ledgerId);
        if (!res.applied) throw new Error('截图未识别出有效基金，请更换清晰截图或改用粘贴文本');
        onSuccess(`截图识别并导入 ${res.parsed_count} 只基金（已自动冷备）`);
        dialogRef.current?.close();
      } else {
        const code = manualCode.trim();
        const amt = Number(manualAmount);
        const nav = Math.max(0.01, Number(manualCost) || 1.0);
        if (!/^\d{6}$/.test(code)) throw new Error('请输入 6 位数字基金代码');
        if (!amt || amt <= 0) throw new Error('请输入大于 0 的持有金额');
        const shares = Number((amt / nav).toFixed(2));
        await api.reconcileManual(
          [{ fund_code: code, fund_name: manualName.trim() || code, shares, cost_price: nav, current_nav: nav }],
          ledgerId
        );
        onSuccess(`已录入基金 ${code}（¥${amt.toLocaleString()}），已自动冷备`);
        dialogRef.current?.close();
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : '导入失败');
    } finally {
      setBusy(false);
    }
  };

  return (
    <dialog
      ref={dialogRef}
      aria-labelledby={titleId}
      {...({ closedby: 'any' } as Record<string, string>)}
      className="rounded-2xl shadow-2xl"
    >
      <div className="bg-white border border-slate-200 rounded-2xl overflow-hidden">
        <div className="px-5 py-4 topbar-navy text-white flex items-center justify-between">
          <div>
            <h1 id={titleId} className="font-semibold text-base">
              导入或更新我的持仓
            </h1>
            <p className="text-xs text-slate-300 mt-0.5">支持粘贴文本、截图离线 OCR 与手动录入，写入前自动备份</p>
          </div>
          <button
            type="button"
            onClick={() => dialogRef.current?.close()}
            aria-label="关闭导入弹窗"
            className="w-8 h-8 rounded-lg flex items-center justify-center text-slate-300 hover:text-white hover:bg-white/10 cursor-pointer"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="p-5 space-y-4">
          {/* 3 种导入方式 */}
          <div className="grid grid-cols-3 gap-1 bg-slate-100 p-1 rounded-xl border border-slate-200">
            {[
              { id: 'text', label: '粘贴文本', icon: FileText },
              { id: 'ocr', label: '截图 OCR', icon: Upload },
              { id: 'manual', label: '手动单笔', icon: PenLine },
            ].map(({ id, label, icon: Icon }) => (
              <button
                key={id}
                type="button"
                onClick={() => {
                  setTab(id as ImportModeTab);
                  setError('');
                }}
                className={`py-2 rounded-lg text-xs font-semibold flex items-center justify-center gap-1.5 transition-all cursor-pointer ${
                  tab === id ? 'bg-white text-slate-900 shadow-xs' : 'text-slate-500 hover:text-slate-800'
                }`}
              >
                <Icon className="w-3.5 h-3.5" aria-hidden="true" />
                <span>{label}</span>
              </button>
            ))}
          </div>

          {tab === 'text' && (
            <div className="space-y-2.5">
              <p className="text-xs text-slate-500">
                每行一只，支持“基金代码 + 持有金额”或从基金 App 复制的文本，例如：
                <code className="ml-1 px-1.5 py-0.5 rounded bg-slate-100 text-slate-800">005561 8000</code>
              </p>
              <textarea
                rows={5}
                value={rawText}
                onChange={(e) => setRawText(e.target.value)}
                placeholder={'005561 8000\n110020 5000\n002351 6000'}
                className="w-full p-3 rounded-xl text-xs bg-slate-50 border border-slate-200 focus:border-blue-600 focus:bg-white focus:outline-none font-mono"
              />
              <div className="flex items-center justify-between">
                <button
                  type="button"
                  onClick={handlePreviewText}
                  disabled={busy}
                  className="text-xs font-semibold text-blue-700 hover:underline cursor-pointer"
                >
                  先解析预览识别结果
                </button>
                {previewItems.length > 0 && (
                  <span className="inline-flex items-center gap-1 text-xs text-emerald-700 font-medium">
                    <CheckCircle2 className="w-3.5 h-3.5" />
                    已识别 {previewItems.length} 只基金
                  </span>
                )}
              </div>
            </div>
          )}

          {tab === 'ocr' && (
            <div className="space-y-2.5">
              <label className="block border-2 border-dashed border-slate-300 hover:border-blue-500 rounded-xl p-6 text-center cursor-pointer bg-slate-50 transition-colors">
                <Upload className="w-6 h-6 text-slate-400 mx-auto mb-2" />
                <div className="text-xs font-medium text-slate-700">
                  {ocrFile ? `已选择：${ocrFile.name}` : '点击选择支付宝 / 天天基金持仓截图（PNG/JPG）'}
                </div>
                <div className="text-[11px] text-slate-400 mt-1">全程在本地离线识别，不上传任何云端服务器</div>
                <input
                  type="file"
                  accept="image/*"
                  className="hidden"
                  onChange={(e) => setOcrFile(e.target.files?.[0] || null)}
                />
              </label>
            </div>
          )}

          {tab === 'manual' && (
            <div className="grid grid-cols-2 gap-3">
              <label className="space-y-1 text-xs">
                <span className="font-medium text-slate-600">6 位基金代码 *</span>
                <input
                  type="text"
                  maxLength={6}
                  value={manualCode}
                  onChange={(e) => setManualCode(e.target.value)}
                  placeholder="如 005561"
                  className="w-full h-9 px-3 rounded-lg bg-slate-50 border border-slate-200 focus:border-blue-600 focus:bg-white focus:outline-none"
                />
              </label>
              <label className="space-y-1 text-xs">
                <span className="font-medium text-slate-600">持有金额 (¥) *</span>
                <input
                  type="number"
                  min={1}
                  value={manualAmount}
                  onChange={(e) => setManualAmount(e.target.value)}
                  placeholder="如 5000"
                  className="w-full h-9 px-3 rounded-lg bg-slate-50 border border-slate-200 focus:border-blue-600 focus:bg-white focus:outline-none"
                />
              </label>
              <label className="space-y-1 text-xs">
                <span className="font-medium text-slate-600">基金名称（选填）</span>
                <input
                  type="text"
                  value={manualName}
                  onChange={(e) => setManualName(e.target.value)}
                  placeholder="留空自动匹配"
                  className="w-full h-9 px-3 rounded-lg bg-slate-50 border border-slate-200 focus:border-blue-600 focus:bg-white focus:outline-none"
                />
              </label>
              <label className="space-y-1 text-xs">
                <span className="font-medium text-slate-600">持仓成本净值</span>
                <input
                  type="number"
                  step="0.0001"
                  value={manualCost}
                  onChange={(e) => setManualCost(e.target.value)}
                  className="w-full h-9 px-3 rounded-lg bg-slate-50 border border-slate-200 focus:border-blue-600 focus:bg-white focus:outline-none"
                />
              </label>
            </div>
          )}

          {tab !== 'manual' && (
            <div className="flex items-center gap-4 text-xs text-slate-600 pt-1">
              <span className="font-medium">写入方式：</span>
              <label className="inline-flex items-center gap-1.5 cursor-pointer">
                <input
                  type="radio"
                  name="writeMode"
                  checked={writeMode === 'merge'}
                  onChange={() => setWriteMode('merge')}
                  className="accent-[#0A192F]"
                />
                合并更新（保留原其他持仓）
              </label>
              <label className="inline-flex items-center gap-1.5 cursor-pointer">
                <input
                  type="radio"
                  name="writeMode"
                  checked={writeMode === 'overwrite'}
                  onChange={() => setWriteMode('overwrite')}
                  className="accent-[#0A192F]"
                />
                全量覆盖（适合次日同步）
              </label>
            </div>
          )}

          {error && (
            <div className="p-3 rounded-xl bg-red-50 border border-red-200 text-xs text-red-700 flex items-start gap-2">
              <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
              <span>{error}</span>
            </div>
          )}

          <div className="flex items-center justify-between pt-3 border-t border-slate-100">
            <span className="text-[11px] text-slate-400">写入前自动生成不可变冷备快照</span>
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => dialogRef.current?.close()}
                className="px-3.5 py-2 rounded-xl text-xs font-medium border border-slate-200 text-slate-600 hover:bg-slate-50 cursor-pointer"
              >
                取消
              </button>
              <button
                type="button"
                disabled={busy}
                onClick={handleApply}
                className="px-4 py-2 rounded-xl text-xs font-semibold bg-[#0A192F] text-white hover:bg-[#132A4A] disabled:opacity-50 cursor-pointer"
              >
                {busy ? '处理中...' : '确认写入账本'}
              </button>
            </div>
          </div>
        </div>
      </div>
    </dialog>
  );
}

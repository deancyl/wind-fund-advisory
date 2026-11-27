import { useEffect, useId, useRef, useState } from 'react';
import {
  X,
  Upload,
  FileText,
  PenLine,
  CheckCircle2,
  AlertCircle,
  RotateCcw,
  FolderPlus,
  Database,
  RefreshCw,
  Trash2,
} from 'lucide-react';
import { api } from '../api/client';
import { useWorkbench, type DataCenterTab } from '../context/WorkbenchContext';

interface EditableImportRow {
  uid: string;
  selected: boolean;
  fund_code: string;
  fund_name: string;
  market_value: number;
  shares: number;
  cost_price: number;
  raw: Record<string, unknown>;
}

function normalizePreviewRows(items: Array<Record<string, unknown>>): EditableImportRow[] {
  return (items || []).map((it, idx) => {
    const code = String(it.fund_code || it.code || '').trim();
    const name = String(it.fund_name || it.name || code).trim();
    const mv = Number(it.market_value ?? it.amount ?? 0);
    const sh = Number(it.shares ?? 0);
    const cp = Number(it.cost_price ?? it.current_nav ?? 1);
    return {
      uid: `${code}_${idx}_${Date.now()}`,
      selected: true,
      fund_code: code,
      fund_name: name,
      market_value: Number.isFinite(mv) ? mv : 0,
      shares: Number.isFinite(sh) ? sh : 0,
      cost_price: Number.isFinite(cp) && cp > 0 ? cp : 1,
      raw: it,
    };
  });
}

export function DataCenterModal() {
  const {
    dataCenterTab,
    openDataCenter,
    closeDataCenter,
    activeLedgerId,
    ledgers,
    switchLedger,
    createLedger,
    notifyDataMutated,
    lakehouse,
    syncingDaily,
    syncLakehouseDaily,
    openConfirm,
    pushToast,
  } = useWorkbench();

  const dialogRef = useRef<HTMLDialogElement | null>(null);
  const titleId = useId();
  const isOpen = dataCenterTab !== null;
  const activeTab: DataCenterTab = dataCenterTab || 'import';

  // 导入子状态（100% 所见即所写：文本 & OCR 均先 preview 核对再 commit）
  const [importMethod, setImportMethod] = useState<'text' | 'ocr' | 'manual'>('text');
  const [writeMode, setWriteMode] = useState<'merge' | 'overwrite'>('merge');
  const [rawText, setRawText] = useState('');
  const [ocrFile, setOcrFile] = useState<File | null>(null);
  const [previewRows, setPreviewRows] = useState<EditableImportRow[]>([]);
  const [manualCode, setManualCode] = useState('');
  const [manualName, setManualName] = useState('');
  const [manualAmount, setManualAmount] = useState('');
  const [manualCost, setManualCost] = useState('1.0');
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState('');

  // 新建账本子表单（零 window.prompt）
  const [newLedgerName, setNewLedgerName] = useState('');
  const [newLedgerCash, setNewLedgerCash] = useState('0');
  const [creatingLedger, setCreatingLedger] = useState(false);

  // 冷备快照
  const [backups, setBackups] = useState<Array<{ snapshot_id: string; timestamp?: string; created_at?: string; reason?: string }>>([]);
  const [loadingBackups, setLoadingBackups] = useState(false);

  useEffect(() => {
    const dlg = dialogRef.current;
    if (!dlg) return;
    if (isOpen && !dlg.open) {
      setErr('');
      dlg.showModal();
    } else if (!isOpen && dlg.open) {
      dlg.close();
    }
  }, [isOpen]);

  useEffect(() => {
    const dlg = dialogRef.current;
    if (!dlg) return;
    const onNativeClose = () => {
      dlg.returnValue = '';
      closeDataCenter();
    };
    dlg.addEventListener('close', onNativeClose);
    return () => dlg.removeEventListener('close', onNativeClose);
  }, [closeDataCenter]);

  useEffect(() => {
    if (!isOpen || activeTab !== 'backups') return;
    let alive = true;
    setLoadingBackups(true);
    api
      .getBackups()
      .then((res) => {
        if (alive) setBackups((res.snapshots || []).slice(0, 12));
      })
      .catch(() => {})
      .finally(() => {
        if (alive) setLoadingBackups(false);
      });
    return () => {
      alive = false;
    };
  }, [isOpen, activeTab]);

  const handleParsePreview = async () => {
    setBusy(true);
    setErr('');
    try {
      if (importMethod === 'text') {
        if (!rawText.trim()) throw new Error('请先粘贴基金持仓文本，例如：005561 8000');
        const res = await api.importText(rawText, 'preview', activeLedgerId);
        const rows = normalizePreviewRows(res.items || []);
        setPreviewRows(rows);
        if (!rows.length) throw new Error('未识别出有效 6 位基金代码与金额，请检查格式');
      } else if (importMethod === 'ocr') {
        if (!ocrFile) throw new Error('请先选择一张支付宝 / 天天基金持仓截图');
        const res = await api.importOcr(ocrFile, 'preview', activeLedgerId);
        const rows = normalizePreviewRows(res.items || []);
        setPreviewRows(rows);
        if (!rows.length) throw new Error('截图未识别出有效基金记录，请更换清晰截图或改用文本粘贴');
      }
    } catch (e) {
      setErr(e instanceof Error ? e.message : '解析预览失败');
    } finally {
      setBusy(false);
    }
  };

  const handleCommitImport = async () => {
    setBusy(true);
    setErr('');
    try {
      if (importMethod === 'manual') {
        const code = manualCode.trim();
        const amt = Number(manualAmount);
        const nav = Math.max(0.01, Number(manualCost) || 1.0);
        if (!/^\d{6}$/.test(code)) throw new Error('请输入 6 位数字基金代码');
        if (!amt || amt <= 0) throw new Error('请输入大于 0 的持有金额');
        const shares = Number((amt / nav).toFixed(2));
        await api.reconcileManual(
          [{ fund_code: code, fund_name: manualName.trim() || code, shares, cost_price: nav, current_nav: nav }],
          activeLedgerId
        );
        await notifyDataMutated(`已录入基金 ${code}（¥${amt.toLocaleString()}，自动冷备）`);
        setManualCode('');
        setManualName('');
        setManualAmount('');
        dialogRef.current?.close();
        return;
      }

      // 若尚未预览，先自动执行预览让用户核对后再落盘（杜绝盲写）
      if (previewRows.length === 0) {
        await handleParsePreview();
        return;
      }

      const selected = previewRows.filter((r) => r.selected && /^\d{6}$/.test(r.fund_code) && (r.market_value > 0 || r.shares > 0));
      if (!selected.length) throw new Error('请至少保留 1 条有效的基金记录');

      const commitItems = selected.map((r) => ({
        ...r.raw,
        fund_code: r.fund_code,
        fund_name: r.fund_name || r.fund_code,
        market_value: r.market_value,
        shares: r.shares,
        cost_price: r.cost_price,
      }));
      const res = await api.commitImport(commitItems, writeMode, activeLedgerId);
      if (!res.applied) throw new Error('写入账本失败');
      await notifyDataMutated(`已按核对表精确写入 ${res.committed_count} 只基金（自动冷备）`);
      setPreviewRows([]);
      setRawText('');
      setOcrFile(null);
      dialogRef.current?.close();
    } catch (e) {
      setErr(e instanceof Error ? e.message : '导入失败');
    } finally {
      setBusy(false);
    }
  };

  const handleCreateLedgerSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newLedgerName.trim()) {
      setErr('请输入新账本名称');
      return;
    }
    setCreatingLedger(true);
    setErr('');
    try {
      await createLedger(newLedgerName.trim(), Math.max(0, Number(newLedgerCash) || 0));
      setNewLedgerName('');
      setNewLedgerCash('0');
      dialogRef.current?.close();
    } catch (ex) {
      setErr(ex instanceof Error ? ex.message : '新建账本失败');
    } finally {
      setCreatingLedger(false);
    }
  };

  const handleRestoreSnapshot = (snapshotId: string) => {
    dialogRef.current?.close();
    openConfirm({
      title: '还原账本冷备快照',
      description: `确认将账本还原至快照 ${snapshotId}？\n当前状态将在还原前自动备份，安全可逆。`,
      confirmLabel: '确认还原',
      tone: 'danger',
      onConfirm: async () => {
        await api.restoreBackup(snapshotId);
        await notifyDataMutated(`账本已成功还原至快照 ${snapshotId}`);
      },
    });
  };

  const selectedCount = previewRows.filter((r) => r.selected).length;

  return (
    <dialog ref={dialogRef} aria-labelledby={titleId} className="rounded-lg shadow-2xl" data-testid="data-center-modal">
      <div className="bg-white border border-slate-200 rounded-lg overflow-hidden">
        {/* 头部 */}
        <div className="px-5 py-3.5 topbar-navy text-white flex items-center justify-between">
          <div>
            <h1 id={titleId} className="font-bold text-sm">
              数据与账本中心
            </h1>
            <p className="text-[11px] text-slate-300 mt-0.5">
              持仓导入核对（所见即所写）、多账本管理、冷备快照还原与本地真净值湖仓
            </p>
          </div>
          <button
            type="button"
            onClick={() => dialogRef.current?.close()}
            aria-label="关闭数据中心弹窗"
            className="w-7 h-7 rounded flex items-center justify-center text-slate-300 hover:text-white hover:bg-white/15 cursor-pointer"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* 统一下划线标签栏 */}
        <div className="px-5 border-b border-slate-200 bg-slate-50/70 flex items-center gap-5 overflow-x-auto no-scrollbar">
          {[
            { id: 'import', label: '导入持仓与核对' },
            { id: 'ledgers', label: `账本管理 (${ledgers.length})` },
            { id: 'backups', label: '冷备快照还原' },
            { id: 'lakehouse', label: '本地真净值湖仓' },
          ].map((t) => (
            <button
              key={t.id}
              type="button"
              data-active={activeTab === t.id}
              onClick={() => {
                setErr('');
                openDataCenter(t.id as DataCenterTab);
              }}
              className="inst-subtab"
            >
              {t.label}
            </button>
          ))}
        </div>

        <div className="p-5 max-h-[72vh] overflow-y-auto space-y-4 text-xs">
          {/* ==================== Tab 1：导入与核对 ==================== */}
          {activeTab === 'import' && (
            <div className="space-y-4">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="inline-flex items-center gap-1 bg-slate-100 p-0.5 rounded-md border border-slate-200">
                  {[
                    { id: 'text', label: '粘贴文本', icon: FileText },
                    { id: 'ocr', label: '截图离线 OCR', icon: Upload },
                    { id: 'manual', label: '手动单笔', icon: PenLine },
                  ].map(({ id, label, icon: Icon }) => (
                    <button
                      key={id}
                      type="button"
                      onClick={() => {
                        setImportMethod(id as 'text' | 'ocr' | 'manual');
                        setPreviewRows([]);
                        setErr('');
                      }}
                      className={`px-3 py-1.5 rounded text-xs font-semibold inline-flex items-center gap-1.5 cursor-pointer ${
                        importMethod === id ? 'bg-white text-slate-900 shadow-2xs' : 'text-slate-500 hover:text-slate-800'
                      }`}
                    >
                      <Icon className="w-3.5 h-3.5" />
                      <span>{label}</span>
                    </button>
                  ))}
                </div>

                {importMethod !== 'manual' && (
                  <div className="inline-flex items-center gap-2 text-[11px] text-slate-600">
                    <label className="inline-flex items-center gap-1 cursor-pointer">
                      <input
                        type="radio"
                        name="dcWriteMode"
                        checked={writeMode === 'merge'}
                        onChange={() => setWriteMode('merge')}
                        className="accent-blue-700"
                      />
                      <span>合并更新</span>
                    </label>
                    <label className="inline-flex items-center gap-1 cursor-pointer">
                      <input
                        type="radio"
                        name="dcWriteMode"
                        checked={writeMode === 'overwrite'}
                        onChange={() => setWriteMode('overwrite')}
                        className="accent-blue-700"
                      />
                      <span>全量覆盖</span>
                    </label>
                  </div>
                )}
              </div>

              {importMethod === 'text' && (
                <div className="space-y-2">
                  <textarea
                    rows={4}
                    value={rawText}
                    onChange={(e) => {
                      setRawText(e.target.value);
                      if (previewRows.length) setPreviewRows([]);
                    }}
                    placeholder={'每行一只，支持“6位代码 金额”或基金 App 复制文本，例如：\n005561 8000\n110020 5000'}
                    className="w-full p-3 rounded-md bg-slate-50 border border-slate-200 focus:border-blue-600 focus:bg-white focus:outline-none font-mono text-xs"
                  />
                  <div className="flex items-center justify-between">
                    <button
                      type="button"
                      disabled={busy}
                      onClick={() => void handleParsePreview()}
                      className="px-3 py-1.5 rounded-md bg-slate-100 hover:bg-slate-200 text-slate-800 font-semibold cursor-pointer"
                    >
                      {busy ? '解析中...' : '解析并生成核对表'}
                    </button>
                    {previewRows.length > 0 && (
                      <span className="inline-flex items-center gap-1 text-emerald-700 font-semibold">
                        <CheckCircle2 className="w-3.5 h-3.5" />
                        已识别 {previewRows.length} 条（可直接在下方改金额或删误识别行）
                      </span>
                    )}
                  </div>
                </div>
              )}

              {importMethod === 'ocr' && (
                <div className="space-y-2.5">
                  <label className="block border border-dashed border-slate-300 hover:border-blue-600 rounded-md p-5 text-center cursor-pointer bg-slate-50 transition-colors">
                    <Upload className="w-5 h-5 text-slate-400 mx-auto mb-1.5" />
                    <div className="font-semibold text-slate-700">
                      {ocrFile ? `已选择：${ocrFile.name}` : '选择支付宝 / 天天基金持仓截图（PNG/JPG）'}
                    </div>
                    <div className="text-[11px] text-slate-400 mt-0.5">纯本机离线 OCR，解析后先出核对表，确认无误再落盘</div>
                    <input
                      type="file"
                      accept="image/*"
                      className="hidden"
                      onChange={(e) => {
                        setOcrFile(e.target.files?.[0] || null);
                        setPreviewRows([]);
                      }}
                    />
                  </label>
                  {ocrFile && previewRows.length === 0 && (
                    <button
                      type="button"
                      disabled={busy}
                      onClick={() => void handleParsePreview()}
                      className="px-3 py-1.5 rounded-md bg-slate-100 hover:bg-slate-200 text-slate-800 font-semibold cursor-pointer"
                    >
                      {busy ? '离线 OCR 识别中...' : '开始离线 OCR 识别预览'}
                    </button>
                  )}
                </div>
              )}

              {importMethod === 'manual' && (
                <div className="grid grid-cols-2 gap-3">
                  <label className="space-y-1">
                    <span className="font-semibold text-slate-600">6 位基金代码 *</span>
                    <input
                      type="text"
                      maxLength={6}
                      value={manualCode}
                      onChange={(e) => setManualCode(e.target.value)}
                      placeholder="如 005561"
                      className="w-full h-8 px-2.5 rounded-md bg-slate-50 border border-slate-200 focus:border-blue-600 focus:bg-white focus:outline-none font-mono"
                    />
                  </label>
                  <label className="space-y-1">
                    <span className="font-semibold text-slate-600">持有金额 (¥) *</span>
                    <input
                      type="number"
                      min={1}
                      value={manualAmount}
                      onChange={(e) => setManualAmount(e.target.value)}
                      placeholder="如 5000"
                      className="w-full h-8 px-2.5 rounded-md bg-slate-50 border border-slate-200 focus:border-blue-600 focus:bg-white focus:outline-none tabular-nums"
                    />
                  </label>
                  <label className="space-y-1">
                    <span className="font-semibold text-slate-600">基金名称（选填）</span>
                    <input
                      type="text"
                      value={manualName}
                      onChange={(e) => setManualName(e.target.value)}
                      placeholder="留空自动补全"
                      className="w-full h-8 px-2.5 rounded-md bg-slate-50 border border-slate-200 focus:border-blue-600 focus:bg-white focus:outline-none"
                    />
                  </label>
                  <label className="space-y-1">
                    <span className="font-semibold text-slate-600">成本净值（选填）</span>
                    <input
                      type="number"
                      step="0.0001"
                      value={manualCost}
                      onChange={(e) => setManualCost(e.target.value)}
                      className="w-full h-8 px-2.5 rounded-md bg-slate-50 border border-slate-200 focus:border-blue-600 focus:bg-white focus:outline-none tabular-nums"
                    />
                  </label>
                </div>
              )}

              {/* 所见即所写：可编辑预览核对表 */}
              {previewRows.length > 0 && importMethod !== 'manual' && (
                <div className="border border-slate-200 rounded-md overflow-hidden" data-testid="import-preview-table">
                  <div className="px-3 py-2 bg-slate-50 border-b border-slate-200 flex items-center justify-between text-[11px]">
                    <span className="font-bold text-slate-800">解析核对表（勾选 {selectedCount} / {previewRows.length} 条写入）</span>
                    <span className="text-slate-400">支持直接修正金额或删除误识别行</span>
                  </div>
                  <div className="max-h-52 overflow-y-auto">
                    <table className="w-full text-xs text-left tabular-nums">
                      <thead>
                        <tr className="border-b border-slate-100 text-slate-500 bg-white">
                          <th className="py-1.5 px-2.5 w-8">选</th>
                          <th className="py-1.5 px-2">代码</th>
                          <th className="py-1.5 px-2">基金名称</th>
                          <th className="py-1.5 px-2 text-right">金额 (¥)</th>
                          <th className="py-1.5 px-2 text-right">删</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-100">
                        {previewRows.map((row) => (
                          <tr key={row.uid} className={row.selected ? '' : 'opacity-45 bg-slate-50'}>
                            <td className="py-1.5 px-2.5">
                              <input
                                type="checkbox"
                                checked={row.selected}
                                onChange={(e) =>
                                  setPreviewRows((prev) =>
                                    prev.map((x) => (x.uid === row.uid ? { ...x, selected: e.target.checked } : x))
                                  )
                                }
                                className="accent-blue-700"
                              />
                            </td>
                            <td className="py-1.5 px-2 font-mono text-slate-700">{row.fund_code}</td>
                            <td className="py-1.5 px-2 text-slate-900 font-medium truncate max-w-[180px]">{row.fund_name}</td>
                            <td className="py-1.5 px-2 text-right">
                              <input
                                type="number"
                                step="10"
                                value={row.market_value}
                                onChange={(e) =>
                                  setPreviewRows((prev) =>
                                    prev.map((x) =>
                                      x.uid === row.uid ? { ...x, market_value: Math.max(0, Number(e.target.value) || 0) } : x
                                    )
                                  )
                                }
                                className="w-24 h-6 px-1.5 rounded border border-slate-300 text-right font-semibold"
                              />
                            </td>
                            <td className="py-1.5 px-2 text-right">
                              <button
                                type="button"
                                onClick={() => setPreviewRows((prev) => prev.filter((x) => x.uid !== row.uid))}
                                className="text-slate-400 hover:text-red-600 cursor-pointer"
                                aria-label={`移除预览行 ${row.fund_code}`}
                              >
                                <Trash2 className="w-3.5 h-3.5" />
                              </button>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {err && (
                <div className="p-2.5 rounded-md bg-red-50 border border-red-200 text-red-700 flex items-center gap-1.5">
                  <AlertCircle className="w-4 h-4 shrink-0" />
                  <span>{err}</span>
                </div>
              )}

              <div className="flex items-center justify-end gap-2 pt-2 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => dialogRef.current?.close()}
                  className="px-3.5 py-1.5 rounded-md border border-slate-300 text-slate-700 hover:bg-slate-50 cursor-pointer"
                >
                  取消
                </button>
                <button
                  type="button"
                  disabled={busy}
                  onClick={() => void handleCommitImport()}
                  className="px-4 py-1.5 rounded-md bg-[#0A1628] text-white font-semibold hover:bg-slate-800 cursor-pointer disabled:opacity-50"
                >
                  {busy
                    ? '处理中...'
                    : importMethod === 'manual'
                    ? '确认录入（自动冷备）'
                    : previewRows.length === 0
                    ? '下一步：解析预览'
                    : `确认写入 ${selectedCount} 只（自动冷备）`}
                </button>
              </div>
            </div>
          )}

          {/* ==================== Tab 2：账本管理 ==================== */}
          {activeTab === 'ledgers' && (
            <div className="space-y-4">
              <div className="divide-y divide-slate-100 border border-slate-200 rounded-md overflow-hidden">
                {ledgers.map((l) => {
                  const active = l.id === activeLedgerId;
                  return (
                    <div
                      key={l.id}
                      className={`px-3.5 py-2.5 flex items-center justify-between gap-2 ${active ? 'bg-blue-50/50' : 'bg-white'}`}
                    >
                      <div className="min-w-0">
                        <div className="font-bold text-slate-900 flex items-center gap-1.5">
                          <span className="truncate">{l.name}</span>
                          {l.is_demo && (
                            <span className="px-1.5 py-0.2 rounded bg-slate-100 text-slate-500 text-[10px]">示例</span>
                          )}
                          {active && (
                            <span className="px-1.5 py-0.2 rounded bg-blue-700 text-white text-[10px]">当前激活</span>
                          )}
                        </div>
                        <div className="text-[11px] text-slate-400 tabular-nums mt-0.5">
                          {l.holding_count} 只基金 · 总资产 ¥{Number(l.total_equity || 0).toLocaleString('zh-CN', { minimumFractionDigits: 2 })}
                        </div>
                      </div>
                      {!active && (
                        <button
                          type="button"
                          onClick={() => {
                            void switchLedger(l.id);
                            dialogRef.current?.close();
                          }}
                          className="px-2.5 py-1 rounded border border-slate-300 text-slate-700 font-semibold hover:bg-slate-50 cursor-pointer shrink-0"
                        >
                          切换
                        </button>
                      )}
                    </div>
                  );
                })}
              </div>

              <form onSubmit={handleCreateLedgerSubmit} className="p-3.5 rounded-md bg-slate-50 border border-slate-200 space-y-3">
                <div className="flex items-center gap-1.5 font-bold text-slate-900">
                  <FolderPlus className="w-4 h-4 text-blue-700" />
                  <span>新建个人空白账本</span>
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
                  <input
                    type="text"
                    value={newLedgerName}
                    onChange={(e) => setNewLedgerName(e.target.value)}
                    placeholder="账本名称（如：2026实盘主仓）"
                    className="sm:col-span-2 h-8 px-2.5 rounded-md bg-white border border-slate-300 focus:border-blue-600 focus:outline-none"
                  />
                  <input
                    type="number"
                    min={0}
                    step={1000}
                    value={newLedgerCash}
                    onChange={(e) => setNewLedgerCash(e.target.value)}
                    placeholder="初始现金 (¥)"
                    className="h-8 px-2.5 rounded-md bg-white border border-slate-300 tabular-nums focus:border-blue-600 focus:outline-none"
                  />
                </div>
                {err && <div className="text-red-600 font-medium">{err}</div>}
                <button
                  type="submit"
                  disabled={creatingLedger}
                  className="px-3.5 py-1.5 rounded-md bg-[#0A1628] text-white font-semibold hover:bg-slate-800 cursor-pointer disabled:opacity-50"
                >
                  {creatingLedger ? '创建中...' : '创建并切换至新账本'}
                </button>
              </form>
            </div>
          )}

          {/* ==================== Tab 3：冷备快照还原 ==================== */}
          {activeTab === 'backups' && (
            <div className="space-y-3">
              <p className="text-slate-500">每次导入、编辑或删除持仓前系统都会自动留存不可变冷备快照，可随时一键可逆还原。</p>
              {loadingBackups ? (
                <div className="py-8 text-center text-slate-400">正在加载本机冷备快照...</div>
              ) : backups.length === 0 ? (
                <div className="py-8 text-center text-slate-400 border border-dashed border-slate-200 rounded-md">暂无历史快照</div>
              ) : (
                <div className="divide-y divide-slate-100 border border-slate-200 rounded-md overflow-hidden">
                  {backups.map((b) => (
                    <div key={b.snapshot_id} className="px-3.5 py-2.5 flex items-center justify-between gap-2 bg-white">
                      <div className="min-w-0">
                        <div className="font-mono font-semibold text-slate-800 truncate">{b.snapshot_id}</div>
                        <div className="text-[11px] text-slate-400">
                          {b.reason || '自动冷备'} · {b.created_at || b.timestamp || ''}
                        </div>
                      </div>
                      <button
                        type="button"
                        onClick={() => handleRestoreSnapshot(b.snapshot_id)}
                        className="px-2.5 py-1 rounded border border-slate-300 text-slate-700 hover:border-red-500 hover:text-red-600 font-semibold inline-flex items-center gap-1 cursor-pointer shrink-0"
                      >
                        <RotateCcw className="w-3 h-3" />
                        <span>还原</span>
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* ==================== Tab 4：本地真净值湖仓 ==================== */}
          {activeTab === 'lakehouse' && (
            <div className="space-y-4">
              <div className="grid grid-cols-2 sm:grid-cols-4 border border-slate-200 rounded-md divide-y sm:divide-y-0 sm:divide-x divide-slate-200 tabular-nums">
                <div className="p-3">
                  <div className="text-[10px] text-slate-400">湖仓总基金数</div>
                  <div className="text-lg font-extrabold text-slate-900 mt-0.5">{lakehouse?.elite_fund_count ?? '--'}</div>
                </div>
                <div className="p-3">
                  <div className="text-[10px] text-slate-400">主动 / 低费指数</div>
                  <div className="text-lg font-extrabold text-slate-900 mt-0.5">
                    {lakehouse?.active_fund_count ?? '--'} / {lakehouse?.index_eligible_count ?? '--'}
                  </div>
                </div>
                <div className="p-3">
                  <div className="text-[10px] text-slate-400">最新净值日期</div>
                  <div className="text-sm font-mono font-bold text-slate-900 mt-1">{lakehouse?.latest_date || '--'}</div>
                </div>
                <div className="p-3">
                  <div className="text-[10px] text-slate-400">覆盖交易日</div>
                  <div className="text-lg font-extrabold text-slate-900 mt-0.5">{lakehouse?.trading_days ?? '--'}</div>
                </div>
              </div>

              <div className="p-3.5 rounded-md bg-slate-50 border border-slate-200 flex flex-wrap items-center justify-between gap-3">
                <div className="space-y-0.5">
                  <div className="font-bold text-slate-900 flex items-center gap-1.5">
                    <Database className="w-4 h-4 text-blue-700" />
                    <span>防封禁盘后增量安全日更</span>
                  </div>
                  <p className="text-[11px] text-slate-500">
                    通过东方财富批量清算接口（50 只/批，总计约 6~8 次 GET，30 分钟冷却锁）追加最新收盘官方复权净值。
                  </p>
                </div>
                <button
                  type="button"
                  disabled={syncingDaily}
                  onClick={() => {
                    void syncLakehouseDaily();
                    pushToast('已发起本地湖仓安全日更检测', 'default');
                  }}
                  className="px-3.5 py-1.5 rounded-md bg-[#0A1628] text-white font-semibold hover:bg-slate-800 inline-flex items-center gap-1.5 cursor-pointer disabled:opacity-50 shrink-0"
                >
                  <RefreshCw className={`w-3.5 h-3.5 ${syncingDaily ? 'animate-spin' : ''}`} />
                  <span>{syncingDaily ? '同步中...' : '立即安全日更'}</span>
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </dialog>
  );
}

import { useEffect, useId, useRef, useState } from 'react';
import { X, AlertTriangle } from 'lucide-react';

export interface ConfirmModalConfig {
  title: string;
  description?: string;
  confirmLabel?: string;
  cancelLabel?: string;
  tone?: 'primary' | 'danger';
  input?: {
    label: string;
    type?: 'text' | 'number';
    placeholder?: string;
    defaultValue?: string;
    min?: number;
    step?: number;
  };
  onConfirm: (value?: string) => void | Promise<void>;
}

interface ConfirmDialogProps {
  config: ConfirmModalConfig | null;
  onClose: () => void;
}

export function ConfirmDialog({ config, onClose }: ConfirmDialogProps) {
  const dlgRef = useRef<HTMLDialogElement | null>(null);
  const titleId = useId();
  const [val, setVal] = useState('');
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState('');

  useEffect(() => {
    const dlg = dlgRef.current;
    if (!dlg) return;
    if (config) {
      setVal(config.input?.defaultValue ?? '');
      setErr('');
      setBusy(false);
      if (!dlg.open) dlg.showModal();
    } else if (dlg.open) {
      dlg.close();
    }
  }, [config]);

  useEffect(() => {
    const dlg = dlgRef.current;
    if (!dlg) return;
    const onNativeClose = () => {
      dlg.returnValue = '';
      onClose();
    };
    dlg.addEventListener('close', onNativeClose);
    return () => dlg.removeEventListener('close', onNativeClose);
  }, [onClose]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!config) return;
    if (config.input) {
      if (config.input.type === 'number') {
        const num = Number(val);
        if (Number.isNaN(num) || (config.input.min !== undefined && num < config.input.min)) {
          setErr('请输入有效数值');
          return;
        }
      } else if (!val.trim()) {
        setErr('请输入有效内容');
        return;
      }
    }
    setBusy(true);
    setErr('');
    try {
      await config.onConfirm(config.input ? val : undefined);
      dlgRef.current?.close();
    } catch (ex) {
      setErr(ex instanceof Error ? ex.message : '操作失败，请重试');
    } finally {
      setBusy(false);
    }
  };

  return (
    <dialog ref={dlgRef} aria-labelledby={titleId} className="dialog-sm rounded-lg shadow-2xl">
      {config && (
        <form onSubmit={handleSubmit} className="bg-white border border-slate-200 rounded-lg overflow-hidden">
          <div className="px-4 py-3 border-b border-slate-200 flex items-center justify-between gap-2 bg-slate-50">
            <div className="flex items-center gap-2">
              {config.tone === 'danger' && <AlertTriangle className="w-4 h-4 text-red-600 shrink-0" />}
              <h2 id={titleId} className="text-sm font-bold text-slate-900">
                {config.title}
              </h2>
            </div>
            <button
              type="button"
              onClick={() => dlgRef.current?.close()}
              aria-label="关闭确认弹窗"
              className="w-7 h-7 rounded flex items-center justify-center text-slate-400 hover:text-slate-700 hover:bg-slate-200/70 cursor-pointer"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          <div className="p-4 space-y-3 text-xs">
            {config.description && <p className="text-slate-600 leading-relaxed whitespace-pre-line">{config.description}</p>}

            {config.input && (
              <label className="block space-y-1.5">
                <span className="font-semibold text-slate-700">{config.input.label}</span>
                <input
                  autoFocus
                  type={config.input.type || 'text'}
                  value={val}
                  min={config.input.min}
                  step={config.input.step}
                  placeholder={config.input.placeholder}
                  onChange={(e) => setVal(e.target.value)}
                  className="w-full h-9 px-3 rounded-md bg-white border border-slate-300 text-slate-900 font-medium tabular-nums focus:border-blue-600 focus:outline-none"
                />
              </label>
            )}

            {err && <div className="px-2.5 py-1.5 rounded bg-red-50 border border-red-200 text-red-700 font-medium">{err}</div>}
          </div>

          <div className="px-4 py-3 border-t border-slate-200 bg-slate-50 flex items-center justify-end gap-2">
            <button
              type="button"
              onClick={() => dlgRef.current?.close()}
              disabled={busy}
              className="px-3 py-1.5 rounded-md text-xs font-medium bg-white border border-slate-300 text-slate-700 hover:bg-slate-100 cursor-pointer"
            >
              {config.cancelLabel || '取消'}
            </button>
            <button
              type="submit"
              disabled={busy}
              className={`px-3.5 py-1.5 rounded-md text-xs font-semibold text-white cursor-pointer disabled:opacity-50 ${
                config.tone === 'danger' ? 'bg-red-600 hover:bg-red-700' : 'bg-[#0A1628] hover:bg-slate-800'
              }`}
            >
              {busy ? '处理中...' : config.confirmLabel || '确认'}
            </button>
          </div>
        </form>
      )}
    </dialog>
  );
}

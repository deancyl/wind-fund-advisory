import { useEffect, useState } from 'react';
import { Search, FlaskConical, Activity, PieChart, ClipboardCheck, Database, RefreshCw, BookmarkPlus, X } from 'lucide-react';
import { api } from '../api/client';
import { useWorkbench } from '../context/WorkbenchContext';

export function CommandPalette() {
  const {
    commandOpen,
    setCommandOpen,
    setActiveTab,
    openInspector,
    openDataCenter,
    syncLakehouseDaily,
    saveCurrentSnapshot,
  } = useWorkbench();

  const [query, setQuery] = useState('');
  const [hits, setHits] = useState<Array<{ code: string; name: string; asset_type: string; sector: string }>>([]);
  const [searching, setSearching] = useState(false);

  useEffect(() => {
    if (!commandOpen) {
      setQuery('');
      setHits([]);
      return;
    }
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setCommandOpen(false);
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [commandOpen, setCommandOpen]);

  useEffect(() => {
    const q = query.trim();
    if (!q || !commandOpen) {
      setHits([]);
      return;
    }
    const t = setTimeout(() => {
      setSearching(true);
      api
        .searchFunds(q, 10)
        .then((res) => setHits(res.items || []))
        .catch(() => {})
        .finally(() => setSearching(false));
    }, 200);
    return () => clearTimeout(t);
  }, [query, commandOpen]);

  if (!commandOpen) return null;

  const quickActions = [
    { label: '前往：量化实验室', icon: FlaskConical, run: () => setActiveTab('quant_lab') },
    { label: '前往：市场与信号（十维投票 / 拥挤度）', icon: Activity, run: () => setActiveTab('market') },
    { label: '前往：实盘与风控（持仓 / 穿透 / 压测）', icon: PieChart, run: () => setActiveTab('holdings') },
    { label: '前往：调仓执行（清单 / 费率 / 定投）', icon: ClipboardCheck, run: () => setActiveTab('rebalance') },
    { label: '打开数据与账本中心（导入核对 / 冷备）', icon: Database, run: () => openDataCenter('import') },
    { label: '将当前实验室方案保存为 A/B 对比快照', icon: BookmarkPlus, run: () => saveCurrentSnapshot() },
    { label: '触发本地真净值湖仓盘后安全日更', icon: RefreshCw, run: () => void syncLakehouseDaily() },
  ];

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center pt-[12vh] px-4" data-testid="command-palette">
      <div
        className="fixed inset-0 bg-slate-900/50 backdrop-blur-[2px]"
        onClick={() => setCommandOpen(false)}
        aria-hidden="true"
      />
      <div className="relative z-10 w-full max-w-lg bg-white border border-slate-200 rounded-lg shadow-2xl overflow-hidden fade-in">
        <div className="px-3.5 py-2.5 border-b border-slate-200 flex items-center gap-2.5">
          <Search className="w-4 h-4 text-slate-400 shrink-0" />
          <input
            autoFocus
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="输入 6 位代码、拼音或关键词检索全市场基金，或执行快捷命令..."
            aria-label="全局检索基金与命令"
            className="flex-1 text-xs text-slate-900 placeholder:text-slate-400 focus:outline-none"
          />
          <button
            type="button"
            onClick={() => setCommandOpen(false)}
            aria-label="关闭命令面板"
            className="p-1 rounded text-slate-400 hover:text-slate-700 cursor-pointer"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="max-h-80 overflow-y-auto divide-y divide-slate-100 text-xs">
          {query.trim() ? (
            searching ? (
              <div className="py-8 text-center text-slate-400">正在检索全市场基金库...</div>
            ) : hits.length === 0 ? (
              <div className="py-8 text-center text-slate-400">未找到匹配「{query}」的基金标的</div>
            ) : (
              hits.map((h) => (
                <button
                  key={h.code}
                  type="button"
                  onClick={() => {
                    setCommandOpen(false);
                    openInspector(h.code);
                  }}
                  className="w-full px-4 py-2.5 text-left hover:bg-blue-50 flex items-center justify-between gap-2 cursor-pointer"
                >
                  <span className="truncate">
                    <strong className="text-slate-900">{h.name}</strong>{' '}
                    <span className="font-mono text-slate-400">{h.code}</span>
                  </span>
                  <span className="text-[10px] px-1.5 py-0.5 rounded bg-slate-100 text-slate-500 shrink-0">
                    {h.sector || h.asset_type || '公募基金'}
                  </span>
                </button>
              ))
            )
          ) : (
            <div className="py-1.5">
              <div className="px-3.5 py-1 text-[10px] font-semibold text-slate-400 uppercase tracking-wider">
                快捷指令
              </div>
              {quickActions.map(({ label, icon: Icon, run }) => (
                <button
                  key={label}
                  type="button"
                  onClick={() => {
                    setCommandOpen(false);
                    run();
                  }}
                  className="w-full px-4 py-2 text-left hover:bg-slate-50 flex items-center gap-2.5 text-slate-700 hover:text-slate-900 cursor-pointer"
                >
                  <Icon className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                  <span className="font-medium">{label}</span>
                </button>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

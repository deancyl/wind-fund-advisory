import { RefreshCw, Plus, SlidersHorizontal, Compass, PieChart, ClipboardCheck, FolderPlus } from 'lucide-react';
import type { LedgerMeta } from '../api/client';

export type MainTab = 'signal' | 'holdings' | 'rebalance';

interface TopBarProps {
  activeTab: MainTab;
  onTabChange: (tab: MainTab) => void;
  ledgers: LedgerMeta[];
  activeLedgerId: string;
  onSwitchLedger: (id: string) => void;
  onCreateLedger: () => void;
  onOpenImport: () => void;
  onRefresh: () => void;
  refreshing: boolean;
  onOpenProDrawer: () => void;
}

const TABS: Array<{ id: MainTab; label: string; icon: typeof Compass }> = [
  { id: 'signal', label: '今日信号与选基', icon: Compass },
  { id: 'holdings', label: '我的持仓与体检', icon: PieChart },
  { id: 'rebalance', label: '调仓参考方案', icon: ClipboardCheck },
];

export function TopBar({
  activeTab,
  onTabChange,
  ledgers,
  activeLedgerId,
  onSwitchLedger,
  onCreateLedger,
  onOpenImport,
  onRefresh,
  refreshing,
  onOpenProDrawer,
}: TopBarProps) {
  return (
    <header className="sticky top-0 z-30 topbar-navy text-white border-b border-white/10 shadow-md">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between gap-3">
        {/* 左：金标品牌 + 定位声明 */}
        <div className="flex items-center gap-3 shrink-0">
          <div className="w-9 h-9 rounded-xl gold-badge text-[#091529] flex items-center justify-center font-extrabold text-sm tracking-tight shadow-sm">
            A2
          </div>
          <div className="flex items-center gap-2.5">
            <span className="font-bold text-base tracking-tight text-white">AGY2 智投</span>
            <span className="hidden xl:inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[11px] bg-white/10 border border-white/15 text-slate-200">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
              纯量化分析参考 · 不涉及实盘交易
            </span>
          </div>
        </div>

        {/* 中：3 个直白主入口 */}
        <nav
          className="hidden lg:flex items-center gap-1 bg-white/[0.07] p-1 rounded-xl border border-white/10"
          aria-label="主导航"
        >
          {TABS.map(({ id, label, icon: Icon }) => {
            const active = activeTab === id;
            return (
              <button
                key={id}
                type="button"
                onClick={() => onTabChange(id)}
                aria-current={active ? 'page' : undefined}
                className={`flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg text-sm whitespace-nowrap shrink-0 transition-all cursor-pointer ${
                  active
                    ? 'bg-white text-[#0A192F] font-semibold shadow-sm'
                    : 'text-slate-300 hover:text-white hover:bg-white/10 font-medium'
                }`}
              >
                <Icon className="w-4 h-4 shrink-0" aria-hidden="true" />
                <span>{label}</span>
              </button>
            );
          })}
        </nav>

        {/* 右：实用工具组 */}
        <div className="flex items-center gap-1.5 sm:gap-2 min-w-0 shrink">
          <div className="flex items-center gap-1 min-w-0">
            <select
              value={activeLedgerId}
              onChange={(e) => onSwitchLedger(e.target.value)}
              aria-label="切换当前账本"
              className="h-9 max-w-[105px] sm:max-w-[190px] px-2 sm:px-2.5 rounded-lg text-xs bg-white/10 border border-white/15 text-slate-100 focus:outline-none focus:border-amber-400 hover:bg-white/15 transition-colors cursor-pointer truncate"
            >
              {ledgers.map((l) => (
                <option key={l.id} value={l.id} className="text-slate-900">
                  {l.is_demo ? '示例 · ' : ''}
                  {l.name} ({l.holding_count}只)
                </option>
              ))}
            </select>
            <button
              type="button"
              onClick={onCreateLedger}
              title="新建空白账本"
              aria-label="新建空白账本"
              className="hidden sm:flex h-9 w-9 rounded-lg items-center justify-center bg-white/10 border border-white/15 text-slate-200 hover:bg-white/20 transition-colors cursor-pointer shrink-0"
            >
              <FolderPlus className="w-4 h-4" aria-hidden="true" />
            </button>
          </div>

          <button
            type="button"
            onClick={onOpenImport}
            className="h-9 px-2.5 sm:px-3.5 rounded-lg text-xs font-semibold gold-badge text-[#091529] hover:brightness-110 transition-all shadow-sm flex items-center gap-1 cursor-pointer shrink-0 whitespace-nowrap"
          >
            <Plus className="w-3.5 h-3.5" aria-hidden="true" />
            <span className="hidden sm:inline">导入持仓</span>
            <span className="sm:hidden">导入</span>
          </button>

          <button
            type="button"
            onClick={onRefresh}
            disabled={refreshing}
            title="同步最新行情与估值"
            aria-label="同步最新行情与估值"
            className="h-9 w-9 rounded-lg flex items-center justify-center bg-white/10 border border-white/15 text-slate-200 hover:bg-white/20 disabled:opacity-50 transition-colors cursor-pointer shrink-0"
          >
            <RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} aria-hidden="true" />
          </button>

          <button
            type="button"
            onClick={onOpenProDrawer}
            aria-label="打开专业分析工具箱"
            className="h-9 px-2.5 sm:px-3 rounded-lg text-xs font-medium bg-white/10 border border-white/15 text-slate-100 hover:bg-white/20 transition-colors flex items-center gap-1.5 cursor-pointer shrink-0 whitespace-nowrap"
          >
            <SlidersHorizontal className="w-3.5 h-3.5" aria-hidden="true" />
            <span className="hidden sm:inline">专业分析</span>
          </button>
        </div>
      </div>

      {/* 窄屏/移动端 3 Tab 栏 */}
      <nav
        className="lg:hidden border-t border-white/10 px-3 py-2 flex items-center gap-1.5 bg-[#0C1C34]"
        aria-label="移动端主导航"
      >
        {TABS.map(({ id, label }) => {
          const active = activeTab === id;
          return (
            <button
              key={id}
              type="button"
              onClick={() => onTabChange(id)}
              aria-current={active ? 'page' : undefined}
              className={`flex-1 py-2 rounded-lg text-xs text-center transition-all cursor-pointer ${
                active ? 'bg-white text-[#0A192F] font-semibold' : 'text-slate-300 font-medium'
              }`}
            >
              {label}
            </button>
          );
        })}
      </nav>
    </header>
  );
}

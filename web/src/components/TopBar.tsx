import { RefreshCw, Database, Search, Activity, FlaskConical, PieChart, ClipboardCheck } from 'lucide-react';
import { useWorkbench, type MainTab } from '../context/WorkbenchContext';

const TABS: Array<{ id: MainTab; label: string; shortLabel: string; icon: typeof FlaskConical }> = [
  { id: 'quant_lab', label: '量化实验室', shortLabel: '实验室', icon: FlaskConical },
  { id: 'market', label: '市场与信号', shortLabel: '市场信号', icon: Activity },
  { id: 'holdings', label: '实盘与风控', shortLabel: '实盘风控', icon: PieChart },
  { id: 'rebalance', label: '调仓执行', shortLabel: '调仓执行', icon: ClipboardCheck },
];

export function TopBar() {
  const {
    activeTab,
    setActiveTab,
    ledgers,
    activeLedgerId,
    switchLedger,
    overview,
    overviewError,
    lakehouse,
    refreshing,
    refreshAll,
    syncingDaily,
    syncLakehouseDaily,
    openDataCenter,
    setCommandOpen,
  } = useWorkbench();

  const verdict = overview?.market_verdict;
  const indices = overview?.indices || {};
  const tickerIndices = [
    { key: 'sh000300', name: '沪深300' },
    { key: 'sh000688', name: '科创50' },
    { key: 'sh000922', name: '中证红利' },
  ];

  return (
    <header className="sticky top-0 z-30 shadow-xs">
      {/* 第 1 层：48px 极简机构顶栏 */}
      <div className="topbar-navy text-white border-b border-white/10">
        <div className="max-w-[1480px] mx-auto px-3 sm:px-5 h-12 flex items-center justify-between gap-2">
          {/* 左：品牌 + 4 个纯净一级工作区 */}
          <div className="flex items-center gap-4 min-w-0">
            <button
              type="button"
              onClick={() => setActiveTab('quant_lab')}
              className="flex items-center gap-2 shrink-0 cursor-pointer"
            >
              <span className="w-7 h-7 rounded-md bg-amber-500 text-[#0A1628] flex items-center justify-center font-extrabold text-xs tracking-tight">
                A2
              </span>
              <span className="font-bold text-sm tracking-tight text-white">AGY2</span>
              <span className="hidden 2xl:inline-block text-[10px] px-1.5 py-0.5 rounded bg-white/10 text-slate-300 font-medium">
                本地纯量化 · 不连券商
              </span>
            </button>

            <nav className="hidden lg:flex items-center gap-1" aria-label="主导航">
              {TABS.map(({ id, label, icon: Icon }) => {
                const active = activeTab === id;
                return (
                  <button
                    key={id}
                    type="button"
                    onClick={() => setActiveTab(id)}
                    aria-current={active ? 'page' : undefined}
                    className={`h-8 px-3 rounded-md text-xs whitespace-nowrap inline-flex items-center gap-1.5 transition-colors cursor-pointer ${
                      active
                        ? 'bg-white text-[#0A1628] font-bold shadow-xs'
                        : 'text-slate-300 hover:text-white hover:bg-white/10 font-medium'
                    }`}
                  >
                    <Icon className="w-3.5 h-3.5 shrink-0" aria-hidden="true" />
                    <span>{label}</span>
                  </button>
                );
              })}
            </nav>
          </div>

          {/* 右：仅保留 3 组高纯度全局工具（账本切换 / 数据与账本中心 / Ctrl+K 命令面板） */}
          <div className="flex items-center gap-1.5 min-w-0 shrink">
            <select
              value={activeLedgerId}
              onChange={(e) => void switchLedger(e.target.value)}
              aria-label="切换当前账本"
              className="h-8 max-w-[110px] sm:max-w-[175px] px-2 rounded-md text-xs bg-white/10 border border-white/15 text-slate-100 focus:outline-none focus:border-amber-400 hover:bg-white/15 cursor-pointer truncate"
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
              onClick={() => openDataCenter('import')}
              data-testid="btn-open-data-center"
              className="h-8 px-2.5 sm:px-3 rounded-md text-xs font-semibold bg-amber-500 text-[#0A1628] hover:bg-amber-400 transition-colors inline-flex items-center gap-1.5 cursor-pointer shrink-0 whitespace-nowrap"
            >
              <Database className="w-3.5 h-3.5" aria-hidden="true" />
              <span className="hidden sm:inline">数据与账本</span>
              <span className="sm:hidden">导入</span>
            </button>

            <button
              type="button"
              onClick={() => setCommandOpen(true)}
              data-testid="btn-open-command-palette"
              title="全局检索基金与快捷命令 (Ctrl+K)"
              aria-label="打开全局命令与基金搜索"
              className="h-8 px-2 sm:px-2.5 rounded-md text-xs bg-white/10 border border-white/15 text-slate-200 hover:bg-white/20 transition-colors inline-flex items-center gap-1.5 cursor-pointer shrink-0"
            >
              <Search className="w-3.5 h-3.5" aria-hidden="true" />
              <span className="hidden md:inline text-[11px] text-slate-300">检索</span>
              <kbd className="hidden xl:inline-block px-1 py-0.5 text-[10px] font-mono rounded bg-white/10 text-slate-300">
                ⌘K
              </kbd>
            </button>

            <button
              type="button"
              onClick={() => void refreshAll()}
              disabled={refreshing}
              title="同步最新行情与持仓估值"
              aria-label="同步最新行情与持仓估值"
              className="h-8 w-8 rounded-md flex items-center justify-center bg-white/10 border border-white/15 text-slate-200 hover:bg-white/20 disabled:opacity-50 transition-colors cursor-pointer shrink-0"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${refreshing ? 'animate-spin' : ''}`} aria-hidden="true" />
            </button>
          </div>
        </div>
      </div>

      {/* 第 2 层：34px 实盘状态 Ticker 带（彻底替代 1/3 屏高广告横幅，移动端横向无溢出滑动） */}
      <div className="ticker-bar">
        <div className="max-w-[1480px] mx-auto px-3 sm:px-5 h-8.5 flex items-center justify-between gap-3 overflow-x-auto no-scrollbar text-[11px] tabular-nums whitespace-nowrap">
          <div className="flex items-center gap-3 shrink-0">
            {overviewError && !overview ? (
              <button
                type="button"
                onClick={() => void refreshAll()}
                className="inline-flex items-center gap-1.5 font-semibold text-amber-800 hover:text-red-700 cursor-pointer"
                title={overviewError}
              >
                <span className="w-1.5 h-1.5 rounded-full bg-amber-500" />
                <span>行情总览异常（点击重试）</span>
              </button>
            ) : (
              <button
                type="button"
                onClick={() => setActiveTab('market')}
                className="inline-flex items-center gap-1.5 font-semibold text-slate-800 hover:text-blue-700 cursor-pointer"
                title={verdict?.detail_explanation || '点击查看宏观十维量化投票与市场全景'}
              >
                <span className={`w-1.5 h-1.5 rounded-full ${verdict?.regime === 'DEGRADED' ? 'bg-amber-500' : 'bg-blue-600'}`} />
                <span>{verdict?.short_label || '大势研判中'}</span>
                {verdict?.action_tag && (
                  <span
                    className={`px-1.5 py-0.2 rounded text-[10px] font-semibold border ${
                      verdict.regime === 'DEGRADED'
                        ? 'bg-amber-50 border-amber-300 text-amber-800'
                        : 'bg-slate-100 border-slate-200 text-slate-700'
                    }`}
                  >
                    {verdict.action_tag}
                  </span>
                )}
              </button>
            )}

            <span className="text-slate-200">|</span>

            {tickerIndices.map(({ key, name }) => {
              const q = indices[key];
              const chg = q?.change_pct ?? null;
              const up = chg !== null && chg >= 0;
              return (
                <span key={key} className="inline-flex items-center gap-1.5 text-slate-600">
                  <span className="font-medium text-slate-700">{q?.name || name}</span>
                  <span className="font-mono text-slate-900 font-semibold">
                    {q?.point ? Number(q.point).toLocaleString('zh-CN', { maximumFractionDigits: 1 }) : '--'}
                  </span>
                  <span className={`font-mono font-bold ${chg === null ? 'text-slate-400' : up ? 'text-red-600' : 'text-emerald-600'}`}>
                    {chg === null ? '--' : `${up ? '+' : ''}${Number(chg).toFixed(2)}%`}
                  </span>
                </span>
              );
            })}
          </div>

          <div className="flex items-center gap-2.5 shrink-0 text-slate-500">
            <span className="hidden sm:inline">
              真净值湖仓 <strong className="text-slate-800">{lakehouse?.elite_fund_count ?? '--'}</strong> 只
              {lakehouse?.latest_date ? ` · 截至 ${lakehouse.latest_date}` : ''}
            </span>
            <button
              type="button"
              onClick={() => void syncLakehouseDaily()}
              disabled={syncingDaily}
              title="仅用 6~8 次批量请求安全追加最新盘后官方复权净值（30 分钟冷却防封禁）"
              className="px-2 py-0.5 rounded bg-slate-100 hover:bg-blue-50 hover:text-blue-700 border border-slate-200 text-[10px] font-semibold text-slate-700 inline-flex items-center gap-1 cursor-pointer disabled:opacity-50"
            >
              <RefreshCw className={`w-2.5 h-2.5 ${syncingDaily ? 'animate-spin text-blue-600' : ''}`} />
              <span>{syncingDaily ? '日更中' : '盘后日更'}</span>
            </button>
          </div>
        </div>
      </div>

      {/* 移动端/平板 4 Tab 导航栏 */}
      <nav
        className="lg:hidden bg-[#0F2038] border-b border-white/10 px-2 py-1.5 grid grid-cols-4 gap-1"
        aria-label="移动端主导航"
      >
        {TABS.map(({ id, shortLabel }) => {
          const active = activeTab === id;
          return (
            <button
              key={id}
              type="button"
              onClick={() => setActiveTab(id)}
              aria-current={active ? 'page' : undefined}
              className={`py-1.5 rounded text-[11px] text-center whitespace-nowrap transition-colors cursor-pointer ${
                active ? 'bg-white text-[#0A1628] font-bold' : 'text-slate-300 font-medium'
              }`}
            >
              {shortLabel}
            </button>
          );
        })}
      </nav>
    </header>
  );
}

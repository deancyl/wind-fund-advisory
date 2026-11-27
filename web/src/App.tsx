import { useEffect, useState } from 'react';
import { WorkbenchProvider, useWorkbench, type MainTab } from './context/WorkbenchContext';
import { TopBar } from './components/TopBar';
import { QuantLabPage } from './pages/QuantLabPage';
import { MarketSignalPage } from './pages/MarketSignalPage';
import { HoldingsPage } from './pages/HoldingsPage';
import { RebalancePage } from './pages/RebalancePage';
import { FundDetailPage } from './pages/FundDetailPage';
import { FundInspectorDrawer } from './components/FundInspectorDrawer';
import { DataCenterModal } from './components/DataCenterModal';
import { CommandPalette } from './components/CommandPalette';
import { ConfirmDialog } from './components/ConfirmDialog';

function WorkbenchShell() {
  const {
    activeTab,
    fullDetailFundCode,
    closeFullDetail,
    confirmModal,
    closeConfirm,
    toasts,
  } = useWorkbench();

  // 懒加载 + 保活：首次进入某个工作区后保持挂载，切 Tab 零重载、后台求解零中断
  const [visited, setVisited] = useState<Record<MainTab, boolean>>({
    quant_lab: true,
    market: false,
    holdings: false,
    rebalance: false,
  });

  useEffect(() => {
    setVisited((prev) => (prev[activeTab] ? prev : { ...prev, [activeTab]: true }));
    // 切换可见面板后通知 ECharts 重算容器尺寸，避免从 hidden 恢复时坍缩
    const t = setTimeout(() => window.dispatchEvent(new Event('resize')), 40);
    return () => clearTimeout(t);
  }, [activeTab]);

  return (
    <div className="min-h-screen flex flex-col bg-[#F8FAFC]">
      <TopBar />

      <main className="flex-1 max-w-[1480px] w-full mx-auto px-3 sm:px-5 py-4 sm:py-5">
        {fullDetailFundCode ? (
          <FundDetailPage fundCode={fullDetailFundCode} onBack={closeFullDetail} />
        ) : (
          <>
            {visited.quant_lab && (
              <div className={activeTab === 'quant_lab' ? '' : 'hidden'}>
                <QuantLabPage />
              </div>
            )}
            {visited.market && (
              <div className={activeTab === 'market' ? '' : 'hidden'}>
                <MarketSignalPage />
              </div>
            )}
            {visited.holdings && (
              <div className={activeTab === 'holdings' ? '' : 'hidden'}>
                <HoldingsPage />
              </div>
            )}
            {visited.rebalance && (
              <div className={activeTab === 'rebalance' ? '' : 'hidden'}>
                <RebalancePage />
              </div>
            )}
          </>
        )}
      </main>

      <footer className="border-t border-slate-200 bg-white py-3 text-center text-[11px] text-slate-400">
        AGY2 智投 · 机构级纯本地量化投研与调仓参考工作台（不连接任何券商交易接口，数据仅存于本机）
      </footer>

      <FundInspectorDrawer />
      <DataCenterModal />
      <CommandPalette />
      <ConfirmDialog config={confirmModal} onClose={closeConfirm} />

      {/* 栈式 Toast（底部居中避开右侧检查器抽屉，多条依次排列不覆盖） */}
      {toasts.length > 0 && (
        <div
          role="status"
          aria-live="polite"
          className="fixed bottom-4 left-1/2 -translate-x-1/2 z-50 flex flex-col items-center gap-2 max-w-md pointer-events-none"
        >
          {toasts.map((t) => (
            <div
              key={t.id}
              className={`px-3.5 py-2.5 rounded-lg text-xs font-medium shadow-xl border fade-in ${
                t.tone === 'error'
                  ? 'bg-red-700 text-white border-red-800'
                  : t.tone === 'warning'
                  ? 'bg-amber-900 text-amber-50 border-amber-700'
                  : 'bg-[#0A1628] text-white border-slate-700'
              }`}
            >
              {t.text}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export function App() {
  return (
    <WorkbenchProvider>
      <WorkbenchShell />
    </WorkbenchProvider>
  );
}

export default App;

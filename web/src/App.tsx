import { useCallback, useEffect, useState } from 'react';
import { api, type LedgerMeta, type OverviewResponse } from './api/client';
import { TopBar, type MainTab } from './components/TopBar';
import { ImportModal } from './components/ImportModal';
import { ProAnalysisDrawer } from './components/ProAnalysisDrawer';
import { SignalPage } from './pages/SignalPage';
import { HoldingsPage } from './pages/HoldingsPage';
import { RebalancePage } from './pages/RebalancePage';

export function App() {
  const [activeTab, setActiveTab] = useState<MainTab>('signal');
  const [ledgers, setLedgers] = useState<LedgerMeta[]>([]);
  const [activeLedgerId, setActiveLedgerId] = useState<string>('combat_29_funds');
  const [overview, setOverview] = useState<OverviewResponse | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  const [refreshTick, setRefreshTick] = useState(0);

  const [importOpen, setImportOpen] = useState(false);
  const [proDrawerOpen, setProDrawerOpen] = useState(false);
  const [toast, setToast] = useState('');

  const showToast = useCallback((msg: string) => {
    setToast(msg);
    setTimeout(() => setToast((cur) => (cur === msg ? '' : cur)), 3000);
  }, []);

  const loadCore = useCallback(async (targetLedger?: string, force = false) => {
    setRefreshing(true);
    try {
      const lRes = await api.getLedgers();
      setLedgers(lRes.items || []);
      const lid = targetLedger || lRes.active_ledger_id || 'combat_29_funds';
      setActiveLedgerId(lid);
      const ov = await api.getOverview(lid, force);
      setOverview(ov);
    } catch (e) {
      showToast(e instanceof Error ? e.message : '后端连接失败，请确认 api_server 已启动');
    } finally {
      setRefreshing(false);
    }
  }, [showToast]);

  useEffect(() => {
    loadCore();
  }, [loadCore]);

  const handleSwitchLedger = async (id: string) => {
    try {
      await api.setActiveLedger(id);
      setActiveLedgerId(id);
      await loadCore(id, false);
      setRefreshTick((t) => t + 1);
      const found = ledgers.find((l) => l.id === id);
      showToast(`已切换账本：${found?.name || id}`);
    } catch (e) {
      showToast(e instanceof Error ? e.message : '切换账本失败');
    }
  };

  const handleCreateLedger = async () => {
    const name = window.prompt('请输入新账本名称（例如：我的实盘组合）：', '我的实盘组合');
    if (!name || !name.trim()) return;
    try {
      const res = await api.createLedger(name.trim(), 0);
      await loadCore(res.ledger_id, true);
      setRefreshTick((t) => t + 1);
      setActiveTab('holdings');
      showToast(`已新建空白账本「${res.name}」，现在可以导入你的持仓`);
    } catch (e) {
      showToast(e instanceof Error ? e.message : '新建账本失败');
    }
  };

  const handleRefresh = async () => {
    await loadCore(activeLedgerId, true);
    setRefreshTick((t) => t + 1);
    showToast('已同步最新行情与持仓估值');
  };

  const handleDataMutated = async (msg: string) => {
    await loadCore(activeLedgerId, true);
    setRefreshTick((t) => t + 1);
    showToast(msg);
  };

  const currentLedger = ledgers.find((l) => l.id === activeLedgerId);

  return (
    <div className="min-h-screen flex flex-col bg-[#F3F6FA]">
      <TopBar
        activeTab={activeTab}
        onTabChange={setActiveTab}
        ledgers={ledgers}
        activeLedgerId={activeLedgerId}
        onSwitchLedger={handleSwitchLedger}
        onCreateLedger={handleCreateLedger}
        onOpenImport={() => setImportOpen(true)}
        onRefresh={handleRefresh}
        refreshing={refreshing}
        onOpenProDrawer={() => setProDrawerOpen(true)}
      />

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 py-6">
        {activeTab === 'signal' && (
          <SignalPage
            overview={overview}
            ledgerId={activeLedgerId}
            onGoHoldings={() => setActiveTab('holdings')}
            onOpenProDrawer={() => setProDrawerOpen(true)}
          />
        )}

        {activeTab === 'holdings' && (
          <HoldingsPage
            overview={overview}
            ledgerId={activeLedgerId}
            isDemoLedger={Boolean(currentLedger?.is_demo)}
            ledgerName={currentLedger?.name || activeLedgerId}
            refreshTick={refreshTick}
            onOpenImport={() => setImportOpen(true)}
            onGoRebalance={() => setActiveTab('rebalance')}
            onDataMutated={handleDataMutated}
          />
        )}

        {activeTab === 'rebalance' && (
          <RebalancePage
            ledgerId={activeLedgerId}
            refreshTick={refreshTick}
            onOpenImport={() => setImportOpen(true)}
            onToast={showToast}
          />
        )}
      </main>

      <footer className="border-t border-slate-200/80 bg-white/60 py-4 text-center text-[11px] text-slate-400">
        AGY2 智投 · 纯本地量化基金分析与调仓参考工作台（不连接任何券商交易接口，数据仅存于本机）
      </footer>

      <ImportModal
        open={importOpen}
        ledgerId={activeLedgerId}
        onClose={() => setImportOpen(false)}
        onSuccess={handleDataMutated}
      />

      <ProAnalysisDrawer
        open={proDrawerOpen}
        ledgerId={activeLedgerId}
        onClose={() => setProDrawerOpen(false)}
        onRestored={() => {
          setProDrawerOpen(false);
          handleDataMutated('账本已还原至所选快照');
        }}
      />

      {toast && (
        <div
          role="status"
          aria-live="polite"
          className="fixed bottom-5 left-1/2 -translate-x-1/2 z-50 px-4 py-2.5 rounded-xl bg-[#0A192F] text-white text-xs font-medium shadow-xl border border-white/10 fade-in"
        >
          {toast}
        </div>
      )}
    </div>
  );
}
export default App;

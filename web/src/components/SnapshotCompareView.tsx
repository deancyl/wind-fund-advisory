import { RefreshCw, Trash2, ArrowUpRight, BookmarkPlus, AlertTriangle } from 'lucide-react';
import { useWorkbench } from '../context/WorkbenchContext';
import { MetricTooltip } from './MetricTooltip';

export function SnapshotCompareView() {
  const {
    snapshots,
    saveCurrentSnapshot,
    removeSnapshot,
    applySnapshotToLab,
    refreshSnapshot,
    lakehouse,
    openInspector,
    blueprint,
  } = useWorkbench();

  const curLakeDate = lakehouse?.latest_date || blueprint?.funnel_audit?.lakehouse_latest_date || '';

  if (snapshots.length === 0) {
    return (
      <div className="inst-panel rounded-lg p-10 text-center space-y-3">
        <div className="text-sm font-bold text-slate-900">尚无保存的方案快照</div>
        <p className="text-xs text-slate-500 max-w-md mx-auto leading-relaxed">
          在「组合方案矩阵」调好任意参数或排除/锁定约束后，点击「存为对比快照」，即可把最多 4 套方案（如全天候 vs 风险平价、全市场 vs 仅指数）放在同一统计口径下并排对比。
        </p>
        <div>
          <button
            type="button"
            onClick={() => saveCurrentSnapshot()}
            disabled={!blueprint}
            className="px-3.5 py-2 rounded-md text-xs font-semibold bg-[#0A1628] text-white hover:bg-slate-800 inline-flex items-center gap-1.5 cursor-pointer disabled:opacity-40"
          >
            <BookmarkPlus className="w-3.5 h-3.5" />
            <span>将当前方案存为方案 A</span>
          </button>
        </div>
      </div>
    );
  }

  // 汇总所有快照中出现过的基金代码，构建横向权重 Diff 矩阵
  const allFundMap = new Map<string, { name: string; bucket: string }>();
  for (const s of snapshots) {
    for (const it of s.items) {
      if (!allFundMap.has(it.fund_code)) {
        allFundMap.set(it.fund_code, { name: it.fund_name, bucket: it.bucket_label });
      }
    }
  }
  const allCodes = Array.from(allFundMap.keys());

  return (
    <div className="space-y-4 fade-in" data-testid="ab-compare-view">
      {/* 顶部工具条 */}
      <div className="inst-panel rounded-lg px-4 py-3 flex flex-wrap items-center justify-between gap-2">
        <div className="text-xs text-slate-600">
          已留存 <strong className="text-slate-900">{snapshots.length} / 4</strong> 套方案快照（强制对齐「近 1 年 + 全周期」固定双口径，杜绝错窗误导）
          <MetricTooltip
            custom={{
              title: 'A/B 方案公平对比口径',
              window: '固定输出近 1 年（252 交易日）与共同存续全周期两套标准口径',
              source: 'localStorage 本地持久化 + 湖仓日期校验',
              note: '当本地湖仓盘后日更后，系统会自动标记早于当前湖仓日期的历史快照，支持一键按原参数重算对齐最新截止日。',
            }}
          />
        </div>
        <button
          type="button"
          onClick={() => saveCurrentSnapshot()}
          disabled={!blueprint}
          className="px-3 py-1.5 rounded-md text-xs font-semibold bg-[#0A1628] text-white hover:bg-slate-800 inline-flex items-center gap-1.5 cursor-pointer disabled:opacity-40"
        >
          <BookmarkPlus className="w-3.5 h-3.5" />
          <span>保存当前方案加入对比</span>
        </button>
      </div>

      {/* 1. 核心指标并排对比表 */}
      <div className="inst-panel rounded-lg overflow-hidden">
        <div className="px-4 py-2.5 border-b border-slate-200 bg-slate-50/70 flex items-center justify-between">
          <h3 className="text-xs font-bold text-slate-900">统一口径核心量化指标对比</h3>
          <span className="text-[11px] text-slate-400">当前湖仓截至：{curLakeDate || '--'}</span>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-xs text-left tabular-nums">
            <thead>
              <tr className="border-b border-slate-200 bg-white text-slate-500">
                <th className="py-2.5 px-4 font-semibold w-44">对比维度</th>
                {snapshots.map((s) => {
                  const isStaleDate = Boolean(curLakeDate && s.lakehouseDate && s.lakehouseDate < curLakeDate);
                  return (
                    <th key={s.id} className="py-2.5 px-4 font-semibold min-w-[180px] align-top">
                      <div className="flex items-start justify-between gap-2">
                        <div className="min-w-0">
                          <div className="text-slate-900 font-bold truncate" title={s.label}>
                            {s.label}
                          </div>
                          <div className="text-[10px] text-slate-400 font-normal mt-0.5">
                            {s.params.riskLevel} · {s.params.horizonMonths}月+{s.params.targetReturnPct}% · {s.params.fundCount}只
                          </div>
                          {isStaleDate && (
                            <div className="mt-1 inline-flex items-center gap-1 px-1.5 py-0.5 rounded bg-amber-50 border border-amber-200 text-[10px] text-amber-800 font-medium">
                              <AlertTriangle className="w-3 h-3" />
                              <span>历史快照 ({s.lakehouseDate})</span>
                            </div>
                          )}
                        </div>
                        <div className="flex items-center gap-1 shrink-0">
                          {isStaleDate && (
                            <button
                              type="button"
                              onClick={() => void refreshSnapshot(s.id)}
                              title="按最新湖仓日期同参数重算刷新"
                              className="p-1 rounded text-amber-700 hover:bg-amber-50 cursor-pointer"
                            >
                              <RefreshCw className="w-3.5 h-3.5" />
                            </button>
                          )}
                          <button
                            type="button"
                            onClick={() => applySnapshotToLab(s, true)}
                            title="载入参数到实验室"
                            className="p-1 rounded text-slate-400 hover:text-blue-700 hover:bg-blue-50 cursor-pointer"
                          >
                            <ArrowUpRight className="w-3.5 h-3.5" />
                          </button>
                          <button
                            type="button"
                            onClick={() => removeSnapshot(s.id)}
                            title="移除此快照"
                            className="p-1 rounded text-slate-400 hover:text-red-600 hover:bg-red-50 cursor-pointer"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      </div>
                    </th>
                  );
                })}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              <tr>
                <td className="py-2 px-4 text-slate-500">选基池 / 约束</td>
                {snapshots.map((s) => (
                  <td key={s.id} className="py-2 px-4 text-slate-700">
                    {s.params.universeMode === 'full_market' ? '全市场海选' : '仅指数低费池'}
                    {(s.params.excludeCodes.length > 0 || s.params.includeCodes.length > 0) && (
                      <span className="ml-1.5 text-[10px] text-slate-500">
                        (排除{s.params.excludeCodes.length}/锁{s.params.includeCodes.length})
                      </span>
                    )}
                  </td>
                ))}
              </tr>
              <tr className="bg-slate-50/40">
                <td className="py-2 px-4 text-slate-600 font-medium">近 1 年实盘校准收益</td>
                {snapshots.map((s) => {
                  const v = s.y1?.return_pct;
                  return (
                    <td key={s.id} className={`py-2 px-4 font-bold ${v !== undefined && v >= 0 ? 'text-red-600' : 'text-emerald-700'}`}>
                      {v !== undefined ? `${v >= 0 ? '+' : ''}${v.toFixed(2)}%` : '--'}
                    </td>
                  );
                })}
              </tr>
              <tr>
                <td className="py-2 px-4 text-slate-500">近 1 年最大回撤 / 夏普</td>
                {snapshots.map((s) => (
                  <td key={s.id} className="py-2 px-4 text-slate-800">
                    {s.y1 ? (
                      <>
                        <span className="text-emerald-700 font-semibold">-{Math.abs(s.y1.max_drawdown_pct).toFixed(2)}%</span>
                        <span className="text-slate-300 mx-1.5">/</span>
                        <span className="font-semibold">{s.y1.sharpe_ratio.toFixed(2)}</span>
                      </>
                    ) : (
                      '--'
                    )}
                  </td>
                ))}
              </tr>
              <tr className="bg-slate-50/40">
                <td className="py-2 px-4 text-slate-600 font-medium">全周期年化 / 最大回撤</td>
                {snapshots.map((s) => (
                  <td key={s.id} className="py-2 px-4 text-slate-800">
                    {s.all ? (
                      <>
                        <span className={`font-bold ${s.all.annualized_return_pct >= 0 ? 'text-red-600' : 'text-emerald-700'}`}>
                          {s.all.annualized_return_pct >= 0 ? '+' : ''}
                          {s.all.annualized_return_pct.toFixed(2)}%
                        </span>
                        <span className="text-slate-300 mx-1.5">/</span>
                        <span className="text-emerald-700 font-semibold">-{Math.abs(s.all.max_drawdown_pct).toFixed(2)}%</span>
                      </>
                    ) : (
                      '--'
                    )}
                  </td>
                ))}
              </tr>
              <tr>
                <td className="py-2 px-4 text-slate-500">滚动触达 / 同温层 / MC</td>
                {snapshots.map((s) => (
                  <td key={s.id} className="py-2 px-4 text-slate-800 font-medium">
                    {s.goalHitRatePct.toFixed(1)}% / {s.condWinRatePct.toFixed(1)}% / {s.mcProbPct.toFixed(1)}%
                  </td>
                ))}
              </tr>
              <tr className="bg-slate-50/40">
                <td className="py-2 px-4 text-slate-500">OOS 胜率 / 波动 / 最大 PCR</td>
                {snapshots.map((s) => (
                  <td key={s.id} className="py-2 px-4 text-slate-800">
                    {s.oosWinRatePct.toFixed(1)}% / {s.portfolioVolPct.toFixed(1)}% / {s.maxPcrPct.toFixed(1)}%
                  </td>
                ))}
              </tr>
              <tr>
                <td className="py-2 px-4 text-slate-500">共同真实存续起点</td>
                {snapshots.map((s) => (
                  <td key={s.id} className="py-2 px-4 font-mono text-slate-500">
                    {s.commonStartDate || '--'}
                  </td>
                ))}
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      {/* 2. 持仓基金权重 Diff 对比矩阵 */}
      <div className="inst-panel rounded-lg overflow-hidden">
        <div className="px-4 py-2.5 border-b border-slate-200 bg-slate-50/70">
          <h3 className="text-xs font-bold text-slate-900">入选基金与配置权重横向 Diff（共涉及 {allCodes.length} 只标的）</h3>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-xs text-left tabular-nums">
            <thead>
              <tr className="border-b border-slate-200 text-slate-500 bg-white">
                <th className="py-2 px-4 font-semibold">基金标的</th>
                <th className="py-2 px-3 font-semibold">风格桶</th>
                {snapshots.map((s) => (
                  <th key={s.id} className="py-2 px-4 font-semibold text-right">
                    {s.label.slice(0, 14)}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {allCodes.map((code) => {
                const info = allFundMap.get(code)!;
                return (
                  <tr key={code} className="hover:bg-slate-50/70">
                    <td className="py-2 px-4">
                      <button
                        type="button"
                        onClick={() => openInspector(code)}
                        className="text-left hover:text-blue-700 cursor-pointer"
                      >
                        <span className="font-semibold text-slate-900 hover:underline">{info.name}</span>
                        <span className="ml-1.5 font-mono text-[11px] text-slate-400">{code}</span>
                      </button>
                    </td>
                    <td className="py-2 px-3 text-[11px] text-slate-500">{info.bucket}</td>
                    {snapshots.map((s) => {
                      const found = s.items.find((x) => x.fund_code === code);
                      return (
                        <td key={s.id} className="py-2 px-4 text-right">
                          {found ? (
                            <span className="font-bold text-slate-900">
                              {found.weight_pct.toFixed(1)}%
                              <span className="ml-1 text-[10px] font-normal text-slate-400">
                                (PCR {found.pcr_pct.toFixed(0)}%)
                              </span>
                            </span>
                          ) : (
                            <span className="text-slate-300">—</span>
                          )}
                        </td>
                      );
                    })}
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

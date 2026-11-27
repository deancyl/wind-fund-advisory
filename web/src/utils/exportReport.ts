import type { BacktestCurvesResponse, BlueprintResponse } from '../api/client';
import type { AppliedSolveParams } from '../context/WorkbenchContext';

export function buildQuantResearchMarkdown(
  blueprint: BlueprintResponse,
  curves: BacktestCurvesResponse | null,
  params: AppliedSolveParams | null,
  capital: number
): string {
  const now = new Date().toISOString().slice(0, 16).replace('T', ' ');
  const uLabel = blueprint.universe_mode === 'index_only' ? '仅指数/宽基低费池' : '全市场量化海选';
  const lines: string[] = [
    `# AGY2 量化投研方案报告`,
    ``,
    `> 生成时间：${now} | 数据源：本地全市场真实复权净值湖仓（截至 ${blueprint.funnel_audit?.lakehouse_latest_date || '--'}）`,
    ``,
    `## 1. 求解参数与约束摘要`,
    `- **风险档位**：${blueprint.risk_level}（${blueprint.risk_meta?.label || ''}）`,
    `- **优化模型**：${blueprint.model_meta?.name || blueprint.model}（${blueprint.solver_audit?.solver_algorithm || ''}）`,
    `- **选基范围**：${uLabel} · 精选 ${blueprint.count} 只 · 拟投本金 ¥${capital.toLocaleString()}`,
    `- **投资目标**：${params?.horizonMonths ?? 12} 个月内期望收益 +${params?.targetReturnPct ?? 10}%（折合年化 +${blueprint.goal_analysis?.required_cagr_pct?.toFixed(1) ?? '--'}%）`,
    `- **排除约束**：${(params?.excludeCodes || []).length ? params?.excludeCodes.join(', ') : '无'} | **锁定约束**：${(params?.includeCodes || []).length ? params?.includeCodes.join(', ') : '无'}`,
    ``,
    `## 2. 组合配置与风险预算矩阵`,
    `| 代码 | 基金名称 | 风格桶 | 目标权重 | 建议金额 (¥) | 风险贡献 PCR | 量化分 | MA20乖离 | 费率/限购 |`,
    `|---|---|---|---:|---:|---:|---:|---:|---|`,
  ];

  for (const it of blueprint.items || []) {
    const amt = Math.round((capital * it.weight_pct) / 100);
    const b20 = it.bias_20 !== null && it.bias_20 !== undefined ? `${it.bias_20 >= 0 ? '+' : ''}${it.bias_20.toFixed(1)}%` : '--';
    lines.push(
      `| \`${it.fund_code}\` | ${it.fund_name} | ${it.bucket_label || it.role} | ${it.weight_pct.toFixed(1)}% | ¥${amt.toLocaleString()} | ${(it.risk_contribution_pcr_pct ?? it.weight_pct).toFixed(1)}% | ${it.quant_score ?? '--'} | ${b20} | ${it.quota_note || '不限购'} |`
    );
  }

  lines.push(``);
  lines.push(`## 3. 真实复权净值回测与达标概率审计`);
  if (curves?.metrics) {
    lines.push(`- **回测窗口**：${curves.period_label || ''}（${curves.date_range || ''}，共同真实存续自 ${curves.real_bt_info?.common_start_date || '--'}）`);
    lines.push(`- **区间收益（实盘校准）**：${curves.metrics.period_return_pct >= 0 ? '+' : ''}${curves.metrics.period_return_pct.toFixed(2)}%（同期沪深300 ${curves.metrics.hs300_return_pct >= 0 ? '+' : ''}${curves.metrics.hs300_return_pct.toFixed(2)}%，超额 ${curves.metrics.excess_return_pct >= 0 ? '+' : ''}${curves.metrics.excess_return_pct.toFixed(2)}%）`);
    lines.push(`- **区间最大回撤**：-${Math.abs(curves.metrics.max_drawdown_pct).toFixed(2)}%（沪深300 -${Math.abs(curves.metrics.hs300_mdd_pct).toFixed(2)}%）`);
    lines.push(`- **风险调整夏普比率**：${curves.metrics.sharpe_ratio.toFixed(2)} | 组合年化波动率：${blueprint.solver_audit?.portfolio_vol_annual_pct?.toFixed(1) ?? '--'}%`);
  }
  if (blueprint.goal_analysis) {
    lines.push(`- **目标滚动触达率**：${blueprint.goal_analysis.historical_hit_rate_pct.toFixed(1)}% | **同温层胜率**：${(blueprint.goal_analysis.conditional_win_rate_pct ?? 0).toFixed(1)}% | **万次 MC 概率**：${(blueprint.goal_analysis.monte_carlo_prob_pct ?? 0).toFixed(1)}% | **样本外 OOS 胜率**：${(blueprint.solver_audit?.oos_conditional_win_rate_pct ?? 0).toFixed(1)}%`);
  }
  if (curves?.extreme_cycle_analysis?.status === 'ready') {
    const ext = curves.extreme_cycle_analysis;
    lines.push(``);
    lines.push(`## 4. 极端周期修复与止盈锚点`);
    lines.push(`- **历史极端平均水下修复**：${ext.historical_recovery.avg_underwater_tdays} 交易日（约 ${ext.historical_recovery.avg_underwater_months} 个月，较沪深300快 ${ext.historical_recovery.days_faster_than_hs300} 交易日）`);
    lines.push(`- **量化建议止盈区间**：+${ext.take_profit_plan.recommended_zone_pct[0].toFixed(1)}% ~ +${ext.take_profit_plan.recommended_zone_pct[1].toFixed(1)}%（移动回撤锁盈线 -${ext.take_profit_plan.trailing_stop_drawdown_pct.toFixed(1)}%）`);
  }

  lines.push(``);
  lines.push(`---`);
  lines.push(`*注：本报告由 AGY2 纯本地量化分析引擎生成，仅供研究与配置参考，过往真实净值业绩不代表未来收益保证。*`);
  return lines.join('\n');
}

export function triggerFileDownload(filename: string, content: string, mime = 'text/markdown;charset=utf-8;') {
  const blob = new Blob([content], { type: mime });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

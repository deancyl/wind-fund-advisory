import { useState, useRef, useEffect } from 'react';
import { HelpCircle } from 'lucide-react';

export interface MetricAuditSpec {
  title: string;
  formula?: string;
  window?: string;
  source?: string;
  note: string;
}

export const METRIC_SPECS: Record<string, MetricAuditSpec> = {
  pcr: {
    title: '风险贡献度 (PCR · Percentage Contribution to Risk)',
    formula: 'PCR_i = w_i · (Σw)_i / (wᵀΣw) × 100%，∑PCR_i = 100%',
    window: '入选基金共同真实复权净值日收益率协方差矩阵 Σ（Ledoit-Wolf 收缩去噪）',
    source: '本地真净值湖仓实算',
    note: '衡量单只基金对组合总方差的实际贡献占比。资金权重低的高波权益可能贡献超 40% 风险，权重高的纯债往往贡献不足 5%。',
  },
  oos_winrate: {
    title: '样本外 OOS 条件胜率',
    formula: '前 70% 历史区间寻优 → 后 30% 样本外区间滚算目标达成概率',
    window: '共同真实复权净值尾部 30% 样本外区间（扣除 95% 实盘仓位与申赎摩擦）',
    source: 'WinRateEngine 实时核验',
    note: '检验优化器在未见过的样本外行情中是否过拟合；若尾部窗口与当下宏观同温层重叠极少，自动回退为样本外无条件滚动胜率。',
  },
  rolling_hit: {
    title: '滚动区间触达目标率',
    formula: 'P( max_{t ∈ [0, H]} R(t) ≥ 目标收益 )',
    window: '共同真实复权净值全部可滚动起点（步长 1 个交易日，持有窗口 H = 目标月数 × 21 交易日）',
    source: 'evaluate_goal_achievement 实算',
    note: '统计历史上任意交易日买入，在设定持有期内至少有一次达到目标止盈线的比例；配合期末达标率与 P05 极端底线交叉验证。',
  },
  cond_winrate: {
    title: '同温层条件胜率',
    formula: '5 维宏观特征（ERP / 股债差 / 动量 / 波动 / 利率）高斯核加权历史胜率',
    window: '全周期宏观同温层相似度加权样本',
    source: 'WinRateEngine 5D Gaussian Kernel',
    note: '给予与当前宏观估值温度最相似的历史起点更高权重，避免把大牛市泡沫起点与低估底部起点的历史胜率简单平均。',
  },
  mc_prob: {
    title: '双万次蒙特卡洛前瞻概率',
    formula: '10,000 条 Block Bootstrap（保留厚尾与自相关）+ Student-t 模拟路径',
    window: '前瞻持有窗口 H 交易日，扣除实盘申赎与现金拖累',
    source: 'Goal Solver & ExtremeCycleAnalyzer',
    note: '在无均值回归保守压力假设下，估计未来持有期内触及目标或极端回撤后的修复分布（常规中位 / 保守中位 / P90 极值）。',
  },
  sharpe: {
    title: '风险调整夏普比率 (Sharpe Ratio)',
    formula: 'Sharpe = (年化组合收益 − Rf) / 年化波动率，Rf = 2.0%',
    window: '当前选定回测区间，基于 95% 实盘校准复权净值日收益率',
    source: '本地真净值湖仓实算',
    note: '衡量每承担 1 单位年化波动所获得的超额回报；一般 > 1.0 为优秀，> 1.5 为顶级低波复利特征。',
  },
  bias20: {
    title: 'MA20 均线乖离率 & 交易拥挤度',
    formula: 'Bias20 = (NAV_t / MA20 − 1) × 100%；拥挤度综合量价动量与短期分位 (0~100)',
    window: '近 20 个交易日真实复权净值（全湖仓 266 只真算，零占位）',
    source: 'lookthrough_analyzer.py',
    note: 'Bias20 > +3.5% 且拥挤度 ≥ 55 提示短线过热，建议分批建仓而非一次性追高；Bias20 < 0 且拥挤度 < 50 处于冷清低吸区。',
  },
  cvar99: {
    title: '99% 极端尾部风险 (CVaR 99% / Expected Shortfall)',
    formula: 'CVaR_99 = E[ Loss | Loss ≥ VaR_99 ]（最坏 1% 情景的平均损失）',
    window: 'Block Bootstrap 历史极端危机重采样（2018 / 2020 / 2022 / 2024）',
    source: 'stress_test & ExtremeCycleAnalyzer',
    note: '比传统 VaR 更严谨的一致性风险度量，刻画真正发生黑天鹅踩踏时组合可能承受的平均最大浮亏深度。',
  },
};

interface MetricTooltipProps {
  specKey?: keyof typeof METRIC_SPECS;
  custom?: MetricAuditSpec;
  align?: 'left' | 'right';
}

export function MetricTooltip({ specKey, custom, align = 'left' }: MetricTooltipProps) {
  const [open, setOpen] = useState(false);
  const wrapRef = useRef<HTMLSpanElement | null>(null);
  const spec = custom || (specKey ? METRIC_SPECS[specKey] : undefined);

  useEffect(() => {
    if (!open) return;
    const onDocDown = (e: MouseEvent) => {
      if (wrapRef.current && !wrapRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setOpen(false);
    };
    document.addEventListener('mousedown', onDocDown);
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('mousedown', onDocDown);
      document.removeEventListener('keydown', onKey);
    };
  }, [open]);

  if (!spec) return null;

  return (
    <span ref={wrapRef} className="relative inline-flex items-center align-middle ml-1">
      <button
        type="button"
        onClick={(e) => {
          e.stopPropagation();
          setOpen((v) => !v);
        }}
        onMouseEnter={() => setOpen(true)}
        onMouseLeave={() => setOpen(false)}
        aria-label={`查看 ${spec.title} 口径说明`}
        className="inline-flex items-center justify-center text-slate-400 hover:text-blue-700 transition-colors cursor-pointer"
      >
        <HelpCircle className="w-3.5 h-3.5" />
      </button>
      {open && (
        <div
          role="tooltip"
          onClick={(e) => e.stopPropagation()}
          className={`absolute z-50 top-full mt-1.5 w-72 sm:w-80 p-3 rounded-lg bg-[#0A1628] text-slate-100 shadow-xl border border-slate-700 text-left space-y-1.5 fade-in ${
            align === 'right' ? 'right-0' : 'left-0'
          }`}
        >
          <div className="text-[11px] font-bold text-white leading-snug">{spec.title}</div>
          {spec.formula && (
            <div className="px-2 py-1 rounded bg-white/10 font-mono text-[10px] text-sky-200 leading-relaxed break-words">
              {spec.formula}
            </div>
          )}
          <p className="text-[11px] text-slate-300 leading-relaxed">{spec.note}</p>
          {(spec.window || spec.source) && (
            <div className="pt-1.5 border-t border-white/10 text-[10px] text-slate-400 space-y-0.5">
              {spec.window && <div>口径窗口：{spec.window}</div>}
              {spec.source && <div>数据来源：{spec.source}</div>}
            </div>
          )}
        </div>
      )}
    </span>
  );
}

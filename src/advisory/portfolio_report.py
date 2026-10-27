"""
投资组合分析报告生成器：
将 PortfolioAnalysisResult 渲染为符合专业投研与财富管理合规标准的 Markdown 报告，
并提供控制台富文本表格生成工具。
"""

from datetime import datetime
from pathlib import Path
from typing import Optional, Union

import pandas as pd
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from ..analysis.portfolio_analyzer import PortfolioAnalysisResult


class PortfolioReportGenerator:
    """投资组合深度分析报告生成引擎"""

    def __init__(self, console: Optional[Console] = None):
        self.console = console or Console()

    def generate_markdown(
        self,
        result: PortfolioAnalysisResult,
        author: str = "Wind 投研量化分析系统"
    ) -> str:
        """生成 Markdown 格式的完整投资组合体检与优化研报"""
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        m = result.metrics
        d = result.diversification

        md = []
        md.append(f"# {result.portfolio_name} 投资组合深度分析与资产配置研报\n")
        md.append(f"> **生成时间**：{now_str}  |  **出具系统**：{author}  |  **调仓再平衡机制**：{result.rebalance_freq}\n")

        # 一、执行摘要
        md.append("## 一、 组合表现执行概要\n")
        rebal_map = {"quarterly": "按季度定期再平衡", "monthly": "按月度定期再平衡", "yearly": "按年度定期再平衡", "none": "买入持有 (无再平衡)"}
        rebal_desc = rebal_map.get(result.rebalance_freq, result.rebalance_freq)

        md.append(
            f"本报告对组合在 **{m.start_date}** 至 **{m.end_date}**（共计 {m.trading_days} 个实际交易日）的历史运行表现进行了深度复盘与量化回测。"
            f"组合采用 **{rebal_desc}** 策略，回测区间内累计录得收益率 **+{m.cum_return_pct}%**（年化复合收益率 **+{m.annualized_return_pct}%**），"
            f"历史最大回撤控制在 **{m.max_drawdown_pct}%**，夏普比率达到 **{m.sharpe_ratio}**，卡玛比率达到 **{m.calmar_ratio}**。"
        )
        if m.alpha_ann_pct > 0:
            md.append(f"相较业绩基准（{m.benchmark_name}），组合实现了年化 **+{m.alpha_ann_pct}%** 的显著超额收益 (Alpha)，信息比率为 **{m.information_ratio}**。\n")
        else:
            md.append(f"相较业绩基准（{m.benchmark_name}），组合相对年化 Alpha 为 **{m.alpha_ann_pct}%**，体现了差异化的贝塔敞口特征。\n")

        # 二、资产配置持仓明细
        md.append("## 二、 组合资产配置与持仓权重结构\n")
        md.append("| 标的代码 | 标的简称 | 资产大类 | 目标配置权重 |")
        md.append("| :---: | :--- | :---: | :---: |")
        for asset in result.assets:
            md.append(f"| `{asset.symbol}` | **{asset.name}** | {asset.asset_class} | **{round(asset.weight * 100, 2)}%** |")
        md.append("")

        # 三、核心风险与收益指标对比
        md.append("## 三、 核心风险与收益量化指标矩阵 (组合 vs 基准)\n")
        md.append("| 量化评估维度 | 投资组合表现 | 对标基准 ({m.benchmark_name}) | 差异 / 超额表现 | 投顾量化解读 |")
        md.append("| :--- | :---: | :---: | :---: | :--- |")
        
        diff_cum = round(m.cum_return_pct - m.benchmark_cum_ret_pct, 2)
        diff_ann = round(m.annualized_return_pct - m.benchmark_ann_ret_pct, 2)
        diff_vol = round(m.annualized_volatility_pct - m.benchmark_vol_pct, 2)
        diff_mdd = round(m.max_drawdown_pct - m.benchmark_max_dd_pct, 2)

        md.append(f"| **累计收益率** | **+{m.cum_return_pct}%** | +{m.benchmark_cum_ret_pct}% | {'+' if diff_cum >= 0 else ''}{diff_cum}% | 投资周期内总资本增值能力 |")
        md.append(f"| **年化复合收益率 (CAGR)** | **+{m.annualized_return_pct}%** | +{m.benchmark_ann_ret_pct}% | {'+' if diff_ann >= 0 else ''}{diff_ann}% | 长期平滑复合回报能力 |")
        md.append(f"| **年化波动率** | **{m.annualized_volatility_pct}%** | {m.benchmark_vol_pct}% | {'+' if diff_vol >= 0 else ''}{diff_vol}% | 收益波动离散度与不确定性 |")
        md.append(f"| **下行标准差** | **{m.downside_deviation_pct}%** | -- | -- | 扣除无风险利率后的纯下行亏损波动 |")
        md.append(f"| **历史最大回撤 (MDD)** | **{m.max_drawdown_pct}%** | {m.benchmark_max_dd_pct}% | {diff_mdd}% | 峰值发生于 {m.max_dd_peak_date}，谷底于 {m.max_dd_trough_date} |")
        md.append(f"| **回撤修复周期** | **{m.max_dd_recovery_days} 个交易日** | -- | -- | 从最大回撤谷底收复前高的时间跨度 |")
        md.append(f"| **夏普比率 (Sharpe, Rf=2%)** | **{m.sharpe_ratio}** | -- | -- | 承担每单位总风险获得的超额收益 (>1.0为优秀) |")
        md.append(f"| **索提诺比率 (Sortino)** | **{m.sortino_ratio}** | -- | -- | 仅对下行亏损风险惩罚的收益性价比 |")
        md.append(f"| **卡玛比率 (Calmar)** | **{m.calmar_ratio}** | -- | -- | 年化复合收益 / 最大回撤比值 (>0.8为优) |")
        md.append(f"| **单日在险价值 (VaR 95%)** | **-{m.var_95_pct}%** | -- | -- | 95% 置信度下正常单日最大潜在亏损 |")
        md.append(f"| **条件在险价值 (CVaR 95%)** | **-{m.cvar_95_pct}%** | -- | -- | 突破 VaR 极值尾部情景下的平均损失期望 |")
        md.append(f"| **最佳月度收益** | **+{m.best_month_pct}%** | -- | -- | 单月最佳进攻爆发力 |")
        md.append(f"| **最差月度收益** | **{m.worst_month_pct}%** | -- | -- | 单月最严峻压力测试冲击 |")
        md.append(f"| **月度盈利胜率** | **{m.positive_months_pct}%** | -- | -- | 正收益月数占比 |")
        md.append(f"| **年化超额收益 (Alpha)** | **+{m.alpha_ann_pct}%** | -- | -- | 经 CAPM 剥离市场系统性风险后的主动管理超额 |")
        md.append(f"| **市场系统性贝塔 (Beta)** | **{m.beta}** | 1.00 | {round(m.beta - 1.0, 2)} | 对基准指数涨跌的敏感弹性 |")
        md.append(f"| **跟踪误差 (Tracking Error)**| **{m.tracking_error_pct}%** | -- | -- | 与业绩基准偏离的年化波动率 |")
        md.append(f"| **信息比率 (Information Ratio)**| **{m.information_ratio}** | -- | -- | 评价单位主动风险所能带来的超额回报 |")
        md.append("")

        # 四、分散化效益与资产相关性分析
        md.append("## 四、 资产间相关性矩阵与分散化效益评估\n")
        md.append(f"- **资产加权独立波动率**：`{d.weighted_asset_vol_pct}%`")
        md.append(f"- **组合实际分散化波动率**：`{d.portfolio_vol_pct}%`")
        md.append(f"- **分散化比率 (Diversification Ratio)**：**{d.diversification_ratio}** (大于 1.0 表明通过多资产配置显著消解了非系统性风险)")
        md.append(f"- **有效分散资产数 (Effective N)**：**{d.effective_n_assets}**\n")

        md.append("### 资产间皮尔逊相关系数矩阵 (Correlation Matrix)")
        symbols = [a.symbol for a in result.assets]
        header = "| 标的代码 | " + " | ".join([f"`{s}`" for s in symbols]) + " |"
        sep = "| :---: | " + " | ".join([":---:" for _ in symbols]) + " |"
        md.append(header)
        md.append(sep)

        for s1 in symbols:
            row_vals = []
            for s2 in symbols:
                val = d.correlation_matrix.get(s1, {}).get(s2, 1.0)
                row_vals.append(f"{val:.3f}")
            md.append(f"| `{s1}` | " + " | ".join(row_vals) + " |")
        md.append("")

        # 五、收益与风险归因拆解
        md.append("## 五、 资产收益贡献与风险暴露拆解 (Attribution)\n")
        md.append("| 标的代码 | 标的简称 | 配置权重 | 标的累计收益% | 组合收益贡献% | 标的年化波动% | 边际风险贡献(MRC) | 风险贡献占比(PCR)% |")
        md.append("| :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: |")
        for item in result.attribution:
            md.append(
                f"| `{item.symbol}` | **{item.name}** | {item.target_weight_pct}% | "
                f"+{item.asset_return_pct}% | **+{item.return_contribution_pct}%** | "
                f"{item.asset_volatility_pct}% | {item.marginal_risk_contribution}% | **{item.risk_contribution_pct}%** |"
            )
        md.append("\n> **量化洞察**：风险贡献占比 (PCR) 反映了各资产在组合实际方差中分担的份额。若某权益资产权重仅为 30%，但 PCR 超过 70%，说明组合风险几乎完全由该资产驱动，建议关注风险平价再平衡。")
        md.append("")

        # 六、现代投资组合优化建议
        if result.optimization_proposals:
            md.append("## 六、 现代投资组合优化建议方案 (Markowitz & Risk Parity)\n")
            md.append("| 优化策略方案 | 策略配置核心逻辑 | 预期年化收益% | 预期年化波动% | 预期夏普比率 | 标的建议权重分配 |")
            md.append("| :--- | :--- | :---: | :---: | :---: | :--- |")
            for prop in result.optimization_proposals:
                w_str = "<br>".join([f"`{k}`: **{round(v*100, 1)}%**" for k, v in prop.weights.items()])
                md.append(
                    f"| **{prop.strategy_name}** | {prop.description} | "
                    f"**+{prop.expected_annual_return_pct}%** | **{prop.expected_annual_vol_pct}%** | "
                    f"**{prop.expected_sharpe_ratio}** | {w_str} |"
                )
            md.append("")

        # 七、投资纪律与合规提示
        md.append("## 七、 投顾动态再平衡纪律与合规免责声明\n")
        md.append(
            "1. **阈值与周期双轨再平衡**：建议在每季度末进行定期再平衡；若单个资产持仓权重偏离目标比例达 ±5% 以上时，触发阈值调仓机制。\n"
            "2. **宏观与流动性监测**：结合市场估值温度计与大类资产股债性价比 (ERP)，在市场过热区适度止盈权益标的并增配稳健固收。\n"
            "3. **合规提示**：本分析报告基于历史量化数据与现代投资组合理论模型回溯测算，过往业绩不代表未来收益，市场有风险，投资需谨慎。\n"
        )

        return "\n".join(md)

    def save_report_to_disk(
        self,
        result: PortfolioAnalysisResult,
        reports_dir: Optional[Union[str, Path]] = None
    ) -> Path:
        """将研报保存至磁盘"""
        target_dir = Path(reports_dir) if reports_dir else Path(__file__).parent.parent.parent / "data" / "reports"
        target_dir.mkdir(parents=True, exist_ok=True)

        safe_name = result.portfolio_name.replace(" ", "_").replace("/", "_")
        filename = f"portfolio_report_{safe_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        out_path = target_dir / filename

        content = self.generate_markdown(result)
        out_path.write_text(content, encoding="utf-8")
        return out_path

    @staticmethod
    def render_ascii_chart(
        history_df: pd.DataFrame,
        height: int = 11,
        width: int = 60
    ) -> str:
        """
        生成极简复古控制台 ASCII 净值曲线走势字符画
        """
        import numpy as np
        if history_df.empty or len(history_df) < 5:
            return "数据点不足，暂无法绘制走势图"

        n = len(history_df)
        indices = np.linspace(0, n - 1, width, dtype=int)
        sampled = history_df.iloc[indices]

        p_vals = sampled["portfolio_nav"].to_numpy()
        b_vals = sampled["benchmark_nav"].to_numpy()

        min_val = min(float(np.min(p_vals)), float(np.min(b_vals)))
        max_val = max(float(np.max(p_vals)), float(np.max(b_vals)))
        val_range = max(max_val - min_val, 1e-4)

        canvas = [[" " for _ in range(width)] for _ in range(height)]

        # 绘制基准线条 (·)
        for x in range(width):
            y_norm = (b_vals[x] - min_val) / val_range
            y_idx = int((1.0 - y_norm) * (height - 1))
            y_idx = max(0, min(height - 1, y_idx))
            canvas[y_idx][x] = "·"

        # 绘制组合净值线条 (■)
        for x in range(width):
            y_norm = (p_vals[x] - min_val) / val_range
            y_idx = int((1.0 - y_norm) * (height - 1))
            y_idx = max(0, min(height - 1, y_idx))
            canvas[y_idx][x] = "■"

        lines = []
        lines.append("  走势图例: [bold green]■ 投资组合净值[/bold green]  vs  [bold white]· 比较基准净值[/bold white]")
        lines.append("  " + "┌" + "─" * width + "┐")
        for r in range(height):
            y_val = max_val - (r / (height - 1)) * val_range
            row_str = "".join(canvas[r])
            lines.append(f"{y_val:5.2f} │{row_str}│")
        lines.append("  " + "└" + "─" * width + "┘")

        start_d = sampled["date"].iloc[0]
        end_d = sampled["date"].iloc[-1]
        pad_len = max(0, width - len(start_d) - len(end_d))
        lines.append(f"       {start_d}" + " " * pad_len + f"{end_d}")
        return "\n".join(lines)

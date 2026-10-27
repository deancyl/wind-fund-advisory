"""
投资建议报告生成器：输出符合专业机构投顾规范的 Markdown 建议书与控制台报告。
"""

from pathlib import Path
from datetime import datetime
from typing import Optional, Union
import pandas as pd
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from ..api.schemas import InvestmentAdviceResult


class InvestmentReportGenerator:
    """投顾方案排版与报告生成器"""

    def __init__(self, console: Optional[Console] = None):
        self.console = console or Console()

    def generate_markdown(
        self,
        advice: InvestmentAdviceResult,
        fund_rank_df: Optional[pd.DataFrame] = None,
        author: str = "Wind 投顾分析团队"
    ) -> str:
        """生成 Markdown 格式的完整投资建议书"""
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        md = []
        md.append(f"# {advice.portfolio_name} 投资建议方案报告\n")
        md.append(f"> **生成时间**：{now_str}  |  **报告出具**：{author}  |  **客户画像**：{advice.client_risk_level}\n")
        md.append("## 一、 方案执行概要\n")
        md.append(f"{advice.advice_summary}\n")

        md.append("### 组合预期核心量化指标")
        md.append("| 指标名称 | 预期数值 | 行业参考中枢 |")
        md.append("| :--- | :--- | :--- |")
        md.append(f"| **预期年化复合收益率** | **+{advice.expected_annual_return}%** | 6.0% ~ 10.0% |")
        md.append(f"| **预期组合最大回撤** | **{advice.expected_max_drawdown}%** | < 15.0% |")
        md.append(f"| **风险收益性价比 (Calmar)** | **{round(advice.expected_annual_return / max(advice.expected_max_drawdown, 0.1), 2)}** | > 0.8 |\n")

        md.append("## 二、 大类资产配置规划矩阵\n")
        md.append("| 资产大类 | 目标权重 | 推荐底层标的工具 | 策略配置逻辑 |")
        md.append("| :--- | :---: | :--- | :--- |")
        for item in advice.allocation_plan:
            instruments = "<br>".join(item.recommended_instruments)
            md.append(f"| **{item.category}** | **{item.target_weight}%** | {instruments} | {item.rationale} |")
        md.append("")

        if fund_rank_df is not None and not fund_rank_df.empty:
            md.append("## 三、 终端真实优选基金量化多维诊断榜单\n")
            md.append("| 基金代码 | 基金简称 | 综合评分 | 等级 | 年化收益% | 最大回撤% | 夏普比率 |")
            md.append("| :---: | :--- | :---: | :---: | :---: | :---: | :---: |")
            for _, r in fund_rank_df.iterrows():
                md.append(
                    f"| {r['基金代码']} | {r['基金简称']} | **{r['综合评分']}** | {r['评级']} | "
                    f"{r['年化收益%']}% | -{r['最大回撤%']}% | {r['夏普比率']} |"
                )
            md.append("")

        md.append("## 四、 投后管理与动态平衡再平衡规则\n")
        md.append("1. **定期再平衡**：建议每季度末对组合进行一次权重检视，若单一大类资产偏离目标权重超过 **±5%**，触发定额再平衡。")
        md.append("2. **市场止盈与防守**：当权益市场估值突破历史 85% 分位或预期目标收益达成后，将浮盈部分平滑结转至固收与货币底仓。")
        md.append("3. **大额定投策略**：增量资金建议采用分批 6~12 个月定投方式建仓，平滑入场波动成本。\n")

        md.append("## 五、 风险揭示与免责声明\n")
        for w in advice.risk_warnings:
            md.append(f"- ⚠️ {w}")
        md.append("\n---\n*本报告由 Wind 投顾终端分析系统本地离线引擎自动生成，不构成直接的投资承诺。*")

        return "\n".join(md)

    def print_terminal_summary(self, advice: InvestmentAdviceResult) -> None:
        """在控制台中渲染高颜值 Rich 表格与面板"""
        table = Table(title=f"📊 {advice.portfolio_name} - 资产配置总览", show_lines=True)
        table.add_column("资产类别", style="cyan", no_wrap=True)
        table.add_column("目标权重", style="magenta", justify="center")
        table.add_column("推荐配置标的", style="green")
        table.add_column("配置依据", style="white")

        for item in advice.allocation_plan:
            instruments_str = "、".join(item.recommended_instruments[:2])
            table.add_row(
                item.category,
                f"{item.target_weight}%",
                instruments_str,
                item.rationale
            )

        summary_text = (
            f"[bold yellow]客户画像等级[/bold yellow]: {advice.client_risk_level}  |  "
            f"[bold green]预期年化复合收益[/bold green]: +{advice.expected_annual_return}%  |  "
            f"[bold red]预期最大回撤[/bold red]: -{advice.expected_max_drawdown}%\n\n"
            f"{advice.advice_summary}"
        )
        self.console.print(Panel(summary_text, title="🎯 投资建议方案摘要", expand=False))
        self.console.print(table)

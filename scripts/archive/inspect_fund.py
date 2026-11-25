"""
基金量化体检与投资建议生成脚本：分析终端缓存与云端基金时序数据，
输出多维评分榜单与定制化投资建议书。
"""

import sys
import argparse
from pathlib import Path
from rich.console import Console
from rich.table import Table

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.parsers.cef_cache_parser import CEFCacheParser
from src.analysis.fund_analyzer import FundAnalyzer
from src.advisory.rules_engine import AdvisoryRulesEngine
from src.advisory.report_generator import InvestmentReportGenerator
from src.api.schemas import RiskProfile


def main():
    parser = argparse.ArgumentParser(description="Wind 基金体检与投资建议生成器")
    parser.add_argument("--risk", default="平衡型", choices=["保守型", "稳健型", "平衡型", "成长型", "进取型"], help="投资者风险偏好等级")
    parser.add_argument("--output", default=None, help="建议书输出 Markdown 文件路径")
    args = parser.parse_args()

    console = Console()
    console.print(f"[bold cyan]正在提取 Wind 投顾终端中的真实基金业绩时序数据...[/bold cyan]")

    cache_parser = CEFCacheParser()
    fund_series = cache_parser.extract_fund_yield_charts()

    if not fund_series:
        console.print("[yellow]! 暂未在本地缓存中解析到基金曲线，正在使用默认监测样本池...[/yellow]")
        return

    console.print(f"[green]✓ 成功提取到 {len(fund_series)} 只基金的时序走势数据[/green]\n")

    # 1. 基金评分排名
    analyzer = FundAnalyzer()
    df_rank = analyzer.compare_and_rank(fund_series)

    table = Table(title="🏆 Wind 投顾终端基金量化综合诊断排名榜", show_lines=True)
    table.add_column("代码", style="cyan", justify="center")
    table.add_column("简称", style="white")
    table.add_column("评分", style="magenta", justify="center")
    table.add_column("评级", style="yellow")
    table.add_column("年化收益%", style="green", justify="right")
    table.add_column("最大回撤%", style="red", justify="right")
    table.add_column("夏普比率", style="white", justify="right")
    table.add_column("卡玛比率", style="white", justify="right")

    for _, row in df_rank.iterrows():
        table.add_row(
            row["基金代码"],
            row["基金简称"],
            str(row["综合评分"]),
            row["评级"],
            f"{row['年化收益%']}%",
            f"{row['最大回撤%']}%",
            str(row["夏普比率"]),
            str(row["卡玛比率"]),
        )
    console.print(table)

    # 2. 生成投资建议方案
    console.print(f"\n[bold green]>>> 正在基于【{args.risk}】客户画像生成定制资产配置方案... <<<[/bold green]\n")
    engine = AdvisoryRulesEngine()
    profile = RiskProfile(level=args.risk)
    advice = engine.generate_advice(profile, fund_series)

    report_gen = InvestmentReportGenerator(console)
    report_gen.print_terminal_summary(advice)

    # 3. 输出 Markdown 报告
    out_path = args.output or str(Path(__file__).parent.parent / "data" / "reports" / f"investment_advice_{args.risk}.md")
    md_content = report_gen.generate_markdown(advice, df_rank)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(md_content)
    console.print(f"\n[bold green]✓ 完整专业投资建议书已保存至: [underline]{out_path}[/underline][/bold green]")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Wind 投顾终端统一命令行工具 (CLI Entrypoint)
用法:
  python wind_cli.py doctor                       # 一键体检终端与环境就绪状态
  python wind_cli.py search 茅台                   # 检索全市场证券/基金代码
  python wind_cli.py analyze 002910.OF            # 对指定基金进行量化深度诊断
  python wind_cli.py advice --risk 平衡型          # 生成专业大类资产配置与投资建议书
  python wind_cli.py export-dict                  # 导出全市场证券标的表至 CSV
  python wind_cli.py sync-cache                   # 同步终端网络缓存数据
"""

import sys
import argparse
from pathlib import Path
from rich.console import Console
from rich.table import Table

from src.parsers.master_dict_parser import MasterDictParser
from src.parsers.cef_cache_parser import CEFCacheParser
from src.analysis.fund_analyzer import FundAnalyzer
from src.advisory.rules_engine import AdvisoryRulesEngine
from src.advisory.report_generator import InvestmentReportGenerator
from src.api.schemas import RiskProfile


def cmd_doctor(args):
    from scripts.doctor import main as doctor_main
    doctor_main()


def cmd_search(args):
    console = Console()
    query = args.query.strip()
    console.print(f"[cyan]正在主字典中模糊检索: [bold]{query}[/bold] ...[/cyan]")
    parser = MasterDictParser()
    results = parser.search(query, limit=args.limit)

    if not results:
        console.print(f"[yellow]未找到与 '{query}' 相关的证券或基金标的[/yellow]")
        return

    table = Table(title=f"🔍 检索结果 (共 {len(results)} 条)", show_lines=True)
    table.add_column("代码", style="cyan")
    table.add_column("标的名称", style="green")
    table.add_column("拼音", style="white")
    table.add_column("英文简称", style="dim")
    table.add_column("类别", style="magenta")
    table.add_column("市场", style="yellow")

    for r in results:
        table.add_row(r.symbol, r.name, r.pinyin, r.english_name, r.asset_class, r.market)

    console.print(table)


def cmd_analyze(args):
    console = Console()
    code = args.code.strip().upper()
    cache_parser = CEFCacheParser()
    funds = cache_parser.extract_fund_yield_charts()

    if code not in funds:
        console.print(f"[red]! 未在终端缓存中找到基金 {code} 的走势数据。[/red]")
        console.print(f"[dim]当前可用缓存基金: {', '.join(list(funds.keys())[:10])}...[/dim]")
        return

    df = funds[code]
    analyzer = FundAnalyzer()
    card = analyzer.analyze_single_fund(code, df)
    if not card:
        console.print(f"[red]数据点不足，无法完成对 {code} 的量化诊断。[/red]")
        return

    table = Table(title=f"📈 基金量化诊断报告: {card.fund_name} ({card.fund_code})", show_lines=True)
    table.add_column("诊断维度", style="cyan")
    table.add_column("量化数值", style="white", justify="right")
    table.add_column("评价参考", style="yellow")

    table.add_row("综合诊断评分", f"{card.total_score} / 100", f"[bold]{card.rating}[/bold]")
    table.add_row("盈利能力得分", f"{card.profitability_score} / 100", "基于年化复合回报加权")
    table.add_row("风险调整性价比", f"{card.risk_adjusted_score} / 100", "基于夏普比率 Sharpe 加权")
    table.add_row("回撤防御韧性", f"{card.defense_score} / 100", "基于最大回撤控制加权")
    table.add_row("区间累计收益率", f"{card.cumulative_return}%", "历史完整区间")
    table.add_row("年化复合收益率", f"{card.annualized_return}%", "年化复合回报率")
    table.add_row("年化收益波动率", f"{card.annualized_volatility}%", "年化标准差")
    table.add_row("历史最大回撤", f"-{card.max_drawdown}%", "高点到低点最大跌幅")
    table.add_row("夏普比率 (Sharpe)", f"{card.sharpe_ratio}", "超额收益与总风险比")
    table.add_row("卡玛比率 (Calmar)", f"{card.calmar_ratio}", "收益对回撤比率")

    console.print(table)


def cmd_advice(args):
    from scripts.inspect_fund import main as inspect_main
    sys.argv = [sys.argv[0], "--risk", args.risk]
    if args.output:
        sys.argv.extend(["--output", args.output])
    inspect_main()


def cmd_export_dict(args):
    from scripts.export_master_dict import main as export_main
    export_main()


def cmd_sync_cache(args):
    from scripts.sync_terminal_cache import main as sync_main
    sync_main()


def main():
    parser = argparse.ArgumentParser(description="Wind 投顾终端机制解析与智能投顾建议系统 CLI")
    subparsers = parser.add_subparsers(dest="subcommand", help="子命令")

    # doctor
    subparsers.add_parser("doctor", help="一键体检终端与离线数据源")

    # search
    p_search = subparsers.add_parser("search", help="模糊检索全市场证券代码")
    p_search.add_argument("query", help="股票代码/名称/拼音 (例如 000001, 平安, PAYH)")
    p_search.add_argument("--limit", type=int, default=15, help="返回条数限制")

    # analyze
    p_ana = subparsers.add_parser("analyze", help="量化深度诊断单只基金")
    p_ana.add_argument("code", help="基金代码 (例如 002910.OF)")

    # advice
    p_adv = subparsers.add_parser("advice", help="生成定制投资建议书")
    p_adv.add_argument("--risk", default="平衡型", choices=["保守型", "稳健型", "平衡型", "成长型", "进取型"], help="投资者风险等级")
    p_adv.add_argument("--output", default=None, help="Markdown 输出路径")

    # export-dict
    subparsers.add_parser("export-dict", help="导出全市场主代码字典至 CSV")

    # sync-cache
    subparsers.add_parser("sync-cache", help="同步终端 Chromium 缓存数据")

    if len(sys.argv) == 1:
        parser.print_help()
        return

    args = parser.parse_args()
    cmds = {
        "doctor": cmd_doctor,
        "search": cmd_search,
        "analyze": cmd_analyze,
        "advice": cmd_advice,
        "export-dict": cmd_export_dict,
        "sync-cache": cmd_sync_cache
    }

    if args.subcommand in cmds:
        cmds[args.subcommand](args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()

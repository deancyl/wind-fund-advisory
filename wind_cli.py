#!/usr/bin/env python3
"""
Wind 投顾终端统一命令行工具 (CLI Entrypoint)
用法:
  python wind_cli.py doctor                       # 一键体检终端与环境就绪状态
  python wind_cli.py search 茅台                   # 检索全市场证券/基金代码
  python wind_cli.py analyze 002910.OF            # 对指定基金进行量化深度诊断
  python wind_cli.py winrate 002910.OF            # 测算基金多维滚动胜率与定投胜率矩阵
  python wind_cli.py advice --risk 平衡型          # 生成专业大类资产配置与投资建议书
  python wind_cli.py ingest                       # 将终端最新数据增量清洗入湖 (Parquet+DuckDB)
  python wind_cli.py query "SELECT * FROM v_winrate" # 执行即席 DuckDB SQL 统一查询
  python wind_cli.py export-dict                  # 导出全市场证券标的表至 CSV
  python wind_cli.py sync-cache                   # 同步终端网络缓存数据
"""

import sys
import argparse
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from src.parsers.master_dict_parser import MasterDictParser
from src.parsers.cef_cache_parser import CEFCacheParser
from src.parsers.speed_log_parser import WindSpeedLogParser
from src.parsers.index_fetcher import IndexDataFetcher
from src.analysis.fund_analyzer import FundAnalyzer
from src.analysis.winrate_analyzer import WinRateAnalyzer
from src.storage.lakehouse import LakehouseManager
from src.analysis.benchmark import BenchmarkManager
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
    lakehouse = LakehouseManager()
    df = lakehouse.get_fund_series(code)

    if df is None:
        cache_parser = CEFCacheParser()
        funds = cache_parser.extract_fund_yield_charts()
        df = funds.get(code)

    if df is None:
        console.print(f"[red]! 未在本地湖仓或终端缓存中找到基金 {code} 的走势数据。[/red]")
        return

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


def cmd_winrate(args):
    console = Console()
    code = args.code.strip().upper()
    console.print(f"[cyan]正在深度推演基金 {code} 的多维投资策略胜率矩阵...[/cyan]")

    lakehouse = LakehouseManager()
    df = lakehouse.get_fund_series(code)
    if df is None:
        cache_parser = CEFCacheParser()
        funds = cache_parser.extract_fund_yield_charts()
        df = funds.get(code)
        if df is not None:
            lakehouse.upsert_fund_series(code, df)

    if df is None:
        console.print(f"[red]! 未找到基金 {code} 的时序数据。[/red]")
        return

    win_analyzer = WinRateAnalyzer(lakehouse)
    res = win_analyzer.analyze(code, df, benchmark_code=args.benchmark)
    if not res:
        console.print(f"[red]时序数据不足（需至少25个交易日），无法计算胜率。[/red]")
        return

    console.print(Panel(
        f"[bold yellow]标的名称[/bold yellow]: {res.fund_name} ({res.symbol})\n"
        f"[bold green]日频上涨胜率[/bold green]: {res.overall_daily_win_rate}%  |  "
        f"[bold magenta]综合盈亏比 (P/L Ratio)[/bold magenta]: {res.profit_loss_ratio} (平均单次盈利/亏损)",
        title="🎯 策略核心胜率特征",
        expand=False
    ))

    # 滚动持有期胜率表
    table = Table(title="📅 任意时点买入并滚动持有各周期胜率矩阵", show_lines=True)
    table.add_column("持有周期", style="cyan", justify="center")
    table.add_column("获利胜率", style="bold green", justify="center")
    table.add_column("平均区间收益", style="white", justify="right")
    table.add_column("收益中位数", style="white", justify="right")
    table.add_column("悲观预期 (Q25)", style="red", justify="right")
    table.add_column("乐观预期 (Q75)", style="green", justify="right")
    table.add_column("跑赢沪深300超额胜率", style="bold yellow", justify="center")
    table.add_column("平均超额收益", style="yellow", justify="right")

    for p in res.holding_win_rates:
        table.add_row(
            p.period_name,
            f"{p.win_rate_pct}%",
            f"{p.avg_return_pct}%",
            f"{p.median_return_pct}%",
            f"{p.q25_return_pct}%",
            f"{p.q75_return_pct}%",
            f"{p.excess_win_rate_pct}%",
            f"{p.avg_excess_return_pct}%"
        )
    console.print(table)

    # 定投胜率表
    if res.dca_win_rates:
        dca_table = Table(title="💰 动态定投周期胜率与年化收益分布", show_lines=True)
        dca_table.add_column("定投周期", style="cyan", justify="center")
        dca_table.add_column("定投最终盈利胜率", style="bold green", justify="center")
        dca_table.add_column("模拟定投平均年化回报", style="bold magenta", justify="right")

        for d in res.dca_win_rates:
            dca_table.add_row(
                d.dca_period_name,
                f"{d.dca_win_rate_pct}%",
                f"{d.avg_dca_annualized_pct}%"
            )
        console.print(dca_table)

    console.print(f"[dim]胜率成果已标准化归档至: data/mart/strategy_winrate.parquet[/dim]")


def cmd_ingest(args):
    console = Console()
    console.print("[cyan]正在执行本地数据湖仓增量同步清洗 (Upsert Ingestion)...[/cyan]")

    lakehouse = LakehouseManager()
    cache_parser = CEFCacheParser()
    funds = cache_parser.extract_fund_yield_charts()

    if not funds:
        console.print("[yellow]! 未在终端缓存中检测到时序数据，请先在 Wind 终端中打开投顾或基金模块[/yellow]")
        return

    bench_mgr = BenchmarkManager(lakehouse)
    bench_mgr.get_or_create_default_benchmark("000300.SH")

    # 1. 逐只标的执行 10 日重叠 Upsert 写入 processed/funds/{symbol}.parquet
    console.print(f"[green]正在将 {len(funds)} 只基金写入 data/processed/funds/ ...[/green]")
    for code, df in funds.items():
        lakehouse.upsert_fund_series(code, df, overlap_window_days=10)

    # 2. 批量计算并沉淀基金综合评分卡至 data/mart/fund_scorecards.parquet
    analyzer = FundAnalyzer()
    df_rank = analyzer.compare_and_rank(funds)
    if not df_rank.empty:
        lakehouse.save_mart_dataframe("fund_scorecards", df_rank)
        console.print("[green]✓ 基金量化诊断宽表已落盘: data/mart/fund_scorecards.parquet[/green]")

    # 3. 批量测算胜率至 data/mart/strategy_winrate.parquet
    win_analyzer = WinRateAnalyzer(lakehouse)
    for code, df in list(funds.items())[:5]:  # 对排名前列标的测算胜率
        win_analyzer.analyze(code, df)
    console.print("[green]✓ 多维策略胜率矩阵已落盘: data/mart/strategy_winrate.parquet[/green]")

    # 4. 刷新 DuckDB 视图
    lakehouse.init_duckdb_views()
    console.print("[bold green]✓ DuckDB 视图注册完成 (v_funds, v_indices, v_scorecards, v_winrate)！[/bold green]")
    console.print(f"[bold cyan]数据湖仓已完全就绪，存储路径: {lakehouse.data_dir}[/bold cyan]")


def cmd_query(args):
    console = Console()
    sql = args.sql.strip()
    console.print(f"[cyan]执行 DuckDB SQL: [bold]{sql}[/bold][/cyan]")
    lakehouse = LakehouseManager()
    try:
        df = lakehouse.query_sql(sql)
        table = Table(title=f"📋 DuckDB SQL 查询结果 (共 {len(df)} 行)", show_lines=True)
        for col in df.columns:
            table.add_column(str(col), style="white")
        for _, row in df.head(30).iterrows():
            table.add_row(*[str(val) for val in row.values])
        console.print(table)
    except Exception as e:
        console.print(f"[red]SQL 查询错误: {e}[/red]")


def cmd_advice(args):
    from scripts.inspect_fund import main as inspect_main
    sys.argv = [sys.argv[0], "--risk", args.risk]
    if args.output:
        sys.argv.extend(["--output", args.output])
    inspect_main()


def cmd_pull_index(args):
    console = Console()
    code = args.code.strip()
    console.print(f"[cyan]🚀 正在拉取指数 [bold]{code}[/bold] 全量历史时序并与 Wind 终端实时流融合...[/cyan]")

    fetcher = IndexDataFetcher()
    try:
        summary = fetcher.pull_and_sync_index(code)
    except Exception as e:
        console.print(f"[red]! 指数拉取失败: {e}[/red]")
        return

    table = Table(title=f"📊 指数数据同步成功: {summary.name} ({summary.symbol})", show_lines=True)
    table.add_column("指标维度", style="cyan")
    table.add_column("详细数值", style="white", justify="right")
    table.add_column("说明", style="yellow")

    table.add_row("指数全称", summary.name, "A股核心大盘基准")
    table.add_row("时序跨度", f"{summary.start_date} ~ {summary.end_date}", f"共 {summary.total_bars:,} 个交易日K线")
    table.add_row("最新收盘点位", f"{summary.latest_close:.2f}", f"涨跌: {summary.latest_change:+.2f} ({summary.latest_change_pct:+.2f}%)")
    table.add_row("历史最高点 (ATH)", f"{summary.all_time_high:.2f}", "历史峰值")
    table.add_row("历史最低点 (ATL)", f"{summary.all_time_low:.2f}", "历史底部")
    table.add_row("Wind 实时流融合", "已对齐 [SpeedData 实时流]" if summary.wind_live_synced else "纯离线日K", "Wind 终端实时行情状态")
    table.add_row("Parquet 存储路径", summary.parquet_path, "processed/indices 列式存储")
    table.add_row("DuckDB 视图", "v_indices (已就绪)", "支持统一 SQL 检索")

    console.print(table)

    # 自动执行多维胜率测算
    console.print(f"[cyan]正在测算 {summary.name} 的全历史滚动持有期胜率矩阵...[/cyan]")
    win_analyzer = WinRateAnalyzer(fetcher.lakehouse)
    res = win_analyzer.analyze(summary.symbol)
    if res:
        console.print(Panel(
            f"[bold yellow]标的名称[/bold yellow]: {res.fund_name} ({res.symbol})\n"
            f"[bold green]历史日频上涨胜率[/bold green]: {res.overall_daily_win_rate}%  |  "
            f"[bold magenta]综合盈亏比 (P/L Ratio)[/bold magenta]: {res.profit_loss_ratio} (单次平均涨跌比)",
            title="🎯 上证指数多维胜率与量化特征",
            expand=False
        ))

        wr_table = Table(title="📅 任意交易日买入并滚动持有期胜率矩阵", show_lines=True)
        wr_table.add_column("持有周期", style="cyan", justify="center")
        wr_table.add_column("获利胜率", style="bold green", justify="center")
        wr_table.add_column("平均区间收益", style="white", justify="right")
        wr_table.add_column("收益中位数", style="white", justify="right")
        wr_table.add_column("悲观预期 (Q25)", style="red", justify="right")
        wr_table.add_column("乐观预期 (Q75)", style="green", justify="right")
        wr_table.add_column("样本区间数", style="dim", justify="right")

        for p in res.holding_win_rates:
            wr_table.add_row(
                p.period_name,
                f"{p.win_rate_pct}%",
                f"{p.avg_return_pct}%",
                f"{p.median_return_pct}%",
                f"{p.q25_return_pct}%",
                f"{p.q75_return_pct}%",
                f"{p.sample_intervals:,}"
            )
        console.print(wr_table)

        # 定投胜率
        if res.dca_win_rates:
            dca_table = Table(title="💰 任意月份开启定期定投胜率分布", show_lines=True)
            dca_table.add_column("定投周期", style="cyan", justify="center")
            dca_table.add_column("定投最终盈利胜率", style="bold green", justify="center")
            dca_table.add_column("模拟定投平均年化回报", style="bold magenta", justify="right")
            for d in res.dca_win_rates:
                dca_table.add_row(
                    d.dca_period_name,
                    f"{d.dca_win_rate_pct}%",
                    f"{d.avg_dca_annualized_pct}%"
                )
            console.print(dca_table)

    console.print(f"[dim]提示: 可使用 [bold]python wind_cli.py query \"SELECT * FROM v_indices WHERE index_code='{summary.symbol}' ORDER BY date DESC LIMIT 5\"[/bold] 进行 SQL 查询[/dim]")


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

    # winrate
    p_win = subparsers.add_parser("winrate", help="测算多维滚动持有期胜率与定投胜率")
    p_win.add_argument("code", help="基金代码 (例如 002910.OF)")
    p_win.add_argument("--benchmark", default="000300.SH", help="基准指数代码 (默认沪深300)")

    # ingest
    subparsers.add_parser("ingest", help="执行本地数据湖仓清洗入库 (Parquet + DuckDB)")

    # query
    p_q = subparsers.add_parser("query", help="使用 DuckDB 执行即席 SQL 查询")
    p_q.add_argument("sql", help="SQL 语句 (例如: SELECT * FROM v_winrate LIMIT 5)")

    # advice
    p_adv = subparsers.add_parser("advice", help="生成定制投资建议书与胜率报告")
    p_adv.add_argument("--risk", default="平衡型", choices=["保守型", "稳健型", "平衡型", "成长型", "进取型"], help="投资者风险等级")
    p_adv.add_argument("--output", default=None, help="Markdown 输出路径")

    # pull-index
    p_idx = subparsers.add_parser("pull-index", help="拉取并同步核心指数全量历史与实时流数据")
    p_idx.add_argument("code", default="000001.SH", nargs="?", help="指数代码 (例如 000001.SH, 000300.SH, 399001.SZ)")

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
        "winrate": cmd_winrate,
        "ingest": cmd_ingest,
        "query": cmd_query,
        "advice": cmd_advice,
        "pull-index": cmd_pull_index,
        "export-dict": cmd_export_dict,
        "sync-cache": cmd_sync_cache
    }

    if args.subcommand in cmds:
        cmds[args.subcommand](args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()

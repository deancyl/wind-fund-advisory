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
from src.parsers.index_catalog import IndexCatalog
from src.core.batch_index_syncer import BatchIndexSyncer
from src.parsers.fund_catalog import FundCatalogManager
from src.parsers.fund_nav_fetcher import FundNAVFetcher
from src.core.batch_fund_syncer import BatchFundSyncer
from src.parsers.market_data_collector import MarketDataCollector
from src.analysis.market_temperature import MarketTemperatureAnalyzer
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


def cmd_sync_all_indices(args):
    console = Console()
    catalog = IndexCatalog()
    syncer = BatchIndexSyncer(
        min_delay=args.delay * 0.8,
        max_delay=args.delay * 1.3,
        max_retries=args.retries
    )

    if args.status:
        cp = syncer.load_checkpoint()
        cat_df = catalog.build_catalog()
        completed = cp.get("completed_count", 0)
        failed = cp.get("failed_count", 0)
        total = len(cat_df)
        pct = (completed / total * 100) if total > 0 else 0
        console.print(Panel(
            f"[bold cyan]全市场指数库收录总量[/bold cyan]: {total:,} 只\n"
            f"[bold green]已成功落盘同步标的[/bold green]: {completed:,} 只 (占比 {pct:.1f}%)\n"
            f"[bold red]当前失败标记标的[/bold red]: {failed} 只\n"
            f"[bold yellow]断点文件路径[/bold yellow]: {syncer.checkpoint_path}",
            title="📊 A 股全市场指数湖仓同步进度看板",
            expand=False
        ))
        return

    tier_str = "全市场所有指数" if args.tier == "all" else f"Tier {args.tier} 指数"
    console.print(Panel(
        f"[bold yellow]同步目标[/bold yellow]: {tier_str} (单线程防风控节流模式)\n"
        f"[bold cyan]冷却抖动策略[/bold cyan]: 随机动态休眠 {args.delay*0.8:.1f}s ~ {args.delay*1.3:.1f}s\n"
        f"[bold magenta]容错保护机制[/bold magenta]: {args.retries} 次指数退避重试 (3s/6s/12s) + 断点记忆无损续传",
        title="🛡️ A 股全市场指数防风控入湖引擎已启动",
        expand=False
    ))

    def on_progress(idx, total, sym, name, status, close):
        if status == "SUCCESS":
            console.print(f"[bold cyan][{idx:03d}/{total:03d}][/bold cyan] {sym} [green]{name}[/green]: [bold green]✓ 成功入湖[/bold green] (最新收盘: {close:.2f})")
        elif status == "SKIPPED":
            console.print(f"[dim][{idx:03d}/{total:03d}] {sym} {name}: ⏭️ 已存在且最新，跳过[/dim]")
        else:
            console.print(f"[bold red][{idx:03d}/{total:03d}] {sym} {name}: ✗ 拉取失败 (已记录断点)[/bold red]")

    summary = syncer.sync_all(
        tier=args.tier if args.tier != "all" else None,
        limit=args.limit,
        force=args.force,
        on_progress=on_progress
    )

    table = Table(title="🏁 批量指数同步任务执行报告", show_lines=True)
    table.add_column("维度", style="cyan")
    table.add_column("数值", style="white", justify="right")
    table.add_column("说明", style="yellow")

    table.add_row("目标标的总数", f"{summary.target_count}", "本次规划任务集")
    table.add_row("本次新增成功", f"{summary.success_count}", "成功拉取入湖")
    table.add_row("断点记忆跳过", f"{summary.skipped_count}", "无需重复拉取 (节省请求)")
    table.add_row("失败重试耗尽", f"{summary.failed_count}", "已记录断点待复核")
    table.add_row("湖仓时序总根数", f"{summary.total_bars:,}", "全历史日 K 样本")
    table.add_row("总耗时", f"{summary.elapsed_seconds:.1f} 秒", f"{summary.start_time} ~ {summary.end_time}")
    table.add_row("断点记录文件", summary.checkpoint_file, "断点恢复保障")

    console.print(table)
    console.print(f"[bold green]✓ DuckDB 统一视图已更新，可执行:[/bold green]")
    console.print(f'[dim]python wind_cli.py query "SELECT count(*) as total_k_bars, count(distinct index_code) as total_indices FROM v_indices"[/dim]')


def cmd_sync_funds_catalog(args):
    console = Console()
    console.print(Panel(
        "[bold yellow]公募基金全景数据库同步规划[/bold yellow]:\n"
        "1. 28,000+ 只基金主代码字典 (代码、名称、类型、拼音、公司)\n"
        "2. 20,000+ 只开放式基金业绩排行快照 (最新NAV、日增长、全周期收益率)\n"
        "3. 18,000+ 只权威多机构综合评级 (晨星、济安金信、招商、上证)\n"
        "4. 36,000+ 条公募基金经理在管档案 (从业年限、在管规模、最佳任期回报)\n"
        "5. 1,700+ 只场内 ETF 基金名录与实时行情",
        title="🚀 全市场公募基金全景大宽表同步中",
        expand=False
    ))

    mgr = FundCatalogManager()
    summary = mgr.sync_all_catalog_tables(force=args.force)

    table = Table(title="🏆 全市场公募基金全景档案湖仓落盘报告", show_lines=True)
    table.add_column("数据维度", style="cyan")
    table.add_column("覆盖规模", style="white", justify="right")
    table.add_column("DuckDB 挂载视图", style="bold green")
    table.add_column("存储路径", style="dim")

    table.add_row("全市场基金主代码档案", f"{summary.total_funds:,} 只", "v_fund_catalog", summary.catalog_path)
    table.add_row("全周期业绩排行快照", f"{summary.ranked_funds:,} 只", "v_fund_snapshot", summary.rank_path)
    table.add_row("晨星/济安等多机构评级", f"{summary.rated_funds:,} 只", "v_fund_ratings", summary.ratings_path)
    table.add_row("基金经理从业与在管档案", f"{summary.total_managers:,} 条", "v_fund_managers", summary.managers_path)
    table.add_row("场内 ETF 基金名录与行情", f"{summary.total_etfs:,} 只", "v_etfs", summary.etf_path)

    console.print(table)
    console.print(f"[bold green]✓ 基金全景大宽表已全部挂载至 DuckDB 视图！可随时执行:[/bold green]")
    console.print(f'[dim]python wind_cli.py query "SELECT fund_type, count(*) as count FROM v_fund_catalog GROUP BY fund_type ORDER BY count DESC LIMIT 10"[/dim]')


def cmd_sync_fund_nav(args):
    console = Console()
    lakehouse = LakehouseManager()

    if args.status:
        syncer = BatchFundSyncer(lakehouse)
        cp = syncer.load_checkpoint()
        completed = cp.get("completed_count", 0)
        failed = cp.get("failed_count", 0)
        console.print(Panel(
            f"[bold green]已成功落盘基金净值时序[/bold green]: {completed:,} 只\n"
            f"[bold red]当前失败标记标的[/bold red]: {failed} 只\n"
            f"[bold yellow]断点文件路径[/bold yellow]: {syncer.checkpoint_path}",
            title="📊 基金历史净值同步看板",
            expand=False
        ))
        return

    fetcher = FundNAVFetcher(lakehouse)

    # 1. 若指定单只代码
    if args.code:
        code = fetcher.normalize_code(args.code)
        console.print(f"[cyan]🚀 正在拉取基金 [bold]{code}.OF[/bold] 全历史净值时序...[/cyan]")
        try:
            summary = fetcher.fetch_fund_nav(code)
            table = Table(title=f"📈 基金净值入湖成功: {summary.fund_name} ({summary.symbol})", show_lines=True)
            table.add_column("维度", style="cyan")
            table.add_column("数值", style="white", justify="right")
            table.add_column("说明", style="yellow")

            table.add_row("时序跨度", f"{summary.start_date} ~ {summary.end_date}", f"共 {summary.total_nav_days:,} 个净值日")
            table.add_row("最新单位净值", f"{summary.latest_unit_nav:.4f}", f"日变动: {summary.latest_daily_return:+.2f}%")
            table.add_row("最新累计净值", f"{summary.latest_cum_nav:.4f}", "累计分红复权")
            table.add_row("历史最高累计净值", f"{summary.all_time_high_nav:.4f}", "全历史峰值")
            table.add_row("Parquet 存储", summary.parquet_path, "processed/funds/ 列式存储")
            table.add_row("DuckDB 视图", "v_funds (已挂载)", "支持统一 SQL 检索")
            console.print(table)
        except Exception as e:
            console.print(f"[red]! 拉取失败: {e}[/red]")
        return

    # 2. 批量拉取头部/指定基金
    top_n = args.top or 10
    console.print(f"[cyan]🚀 正在准备拉取头部旗舰基金历史净值时序 (目标: 前 {top_n} 只)...[/cyan]")
    # 从业绩排行榜中选取代表性标的
    rank_file = lakehouse.mart_dir / "fund_performance_snapshot.parquet"
    target_funds = []
    if rank_file.exists():
        df_rank = pd.read_parquet(rank_file)
        # 挑选主动权益头部与大盘核心
        for _, r in df_rank.head(top_n).iterrows():
            target_funds.append({"symbol": str(r["symbol"]), "name": str(r["fund_name"])})
    else:
        # 保底核心标的列表
        target_funds = [
            {"symbol": "000001", "name": "华夏成长混合"},
            {"symbol": "002910", "name": "易方达供给改革混合"},
            {"symbol": "110011", "name": "易方达中小盘混合"},
            {"symbol": "161725", "name": "招商中证白酒指数"},
            {"symbol": "510300", "name": "华泰柏瑞沪深300ETF"}
        ][:top_n]

    syncer = BatchFundSyncer(lakehouse, min_delay=args.delay * 0.8, max_delay=args.delay * 1.3)

    def on_progress(idx, total, sym, name, status, nav):
        if status == "SUCCESS":
            console.print(f"[bold cyan][{idx:03d}/{total:03d}][/bold cyan] {sym} [green]{name}[/green]: [bold green]✓ 净值入湖成功[/bold green] (最新NAV: {nav:.4f})")
        elif status == "SKIPPED":
            console.print(f"[dim][{idx:03d}/{total:03d}] {sym} {name}: ⏭️ 已存在且最新，跳过[/dim]")
        else:
            console.print(f"[bold red][{idx:03d}/{total:03d}] {sym} {name}: ✗ 净值拉取失败[/bold red]")

    summary = syncer.sync_funds(target_funds, limit=top_n, force=args.force, on_progress=on_progress)
    console.print(f"[bold green]✓ 批量净值拉取完成！成功: {summary.success_count}, 跳过: {summary.skipped_count}, 累计净值样本: {summary.total_nav_days:,} 根[/bold green]")


def cmd_sync_macro(args):
    console = Console()
    console.print(Panel(
        "[bold yellow]宏观经济与市场深度数据全量采集规划[/bold yellow]:\n"
        "1. 中美基准国债收益率与利差曲线 (2Y/5Y/10Y/30Y, 10-2Y倒挂)\n"
        "2. 全市场两融杠杆余额与平均维持担保比例 (3,400+ 交易日)\n"
        "3. 宏观货币供应 M2/M1 剪刀差与官方制造业 PMI\n"
        "4. 核心宽基指数 (沪深300/上证50/中证500/中证1000等) 历史 PE/PB 估值时序",
        title="🌐 宏观与大盘微观深度数据全量同步",
        expand=False
    ))

    collector = MarketDataCollector()
    summary = collector.sync_all_market_data()

    table = Table(title="🏆 宏观经济与市场估值湖仓落盘报告", show_lines=True)
    table.add_column("数据资产维度", style="cyan")
    table.add_column("覆盖规模", style="white", justify="right")
    table.add_column("DuckDB 视图", style="bold green")
    table.add_column("说明", style="yellow")

    table.add_row("中美基准国债与利差", f"{summary.rates_rows:,} 条", "v_macro_rates", "无风险利率中枢与汇率预期")
    table.add_row("全市场两融杠杆资金", f"{summary.margin_rows:,} 条", "v_margin_trading", "杠杆情绪与担保比例安全垫")
    table.add_row("货币供应量 (M2/M1)", f"{summary.m2_rows:,} 个月", "v_macro_money", "M1-M2 货币剪刀差")
    table.add_row("宏观景气度 (PMI)", f"{summary.pmi_rows:,} 个月", "v_macro_pmi", "制造业与非制造业景气度")
    table.add_row("核心指数历史估值 (PE/PB)", f"{summary.valuation_rows:,} 条", "v_index_valuations", "8大宽基历史PE-TTM与PB")

    console.print(table)
    console.print(f"[bold green]✓ 宏观与估值宽表已全部落盘！可随时评估大盘温度计:[/bold green]")
    console.print(f'[dim]python wind_cli.py market-temp[/dim]')


def cmd_market_temp(args):
    console = Console()
    console.print("[cyan]正在调用量化模型推演当前大盘估值温度与股债性价比 (ERP)...[/cyan]")

    analyzer = MarketTemperatureAnalyzer()
    report = analyzer.evaluate()
    if not report:
        console.print("[yellow]! 暂未检测到估值与利率底表，正在自动执行采集同步...[/yellow]")
        collector = MarketDataCollector()
        collector.sync_all_market_data()
        report = analyzer.evaluate()

    if not report:
        console.print("[red]! 无法生成市场温度计报告，请先执行: python wind_cli.py sync-macro[/red]")
        return

    # 温度颜色
    temp = report.market_temperature_score
    if temp < 30:
        temp_color = "bold cyan"
    elif temp < 50:
        temp_color = "bold green"
    elif temp < 70:
        temp_color = "bold yellow"
    else:
        temp_color = "bold red"

    console.print(Panel(
        f"[bold white]评估基准日期[/bold white]: {report.eval_date}\n"
        f"[bold white]沪深300收盘[/bold white]: {report.hs300_close:.2f}  |  "
        f"滚动PE: {report.hs300_pe:.2f}倍 (历史分位: {report.hs300_pe_percentile:.1f}%)  |  "
        f"PB: {report.hs300_pb:.2f}倍 (历史分位: {report.hs300_pb_percentile:.1f}%)\n"
        f"[bold white]中国10年期国债收益率[/bold white]: {report.cn_10y_treasury_yield:.2f}%\n"
        f"[bold green]股债性价比 (ERP)[/bold green]: {report.erp_value:+.2f}%  (全历史分位: {report.erp_percentile:.1f}%)\n"
        f"[bold magenta]两融维持担保比例[/bold magenta]: {report.margin_guarantee_ratio:.1f}% (杠杆安全垫良好)\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🌡️ [bold white]大盘综合估值温度[/bold white]: [{temp_color}]{report.market_temperature_score} 分[/{temp_color}]  "
        f"--> 状态研判: [bold green]{report.valuation_status}[/bold green]",
        title="🌡️ A 股市场全景估值温度计与资产配置罗盘",
        expand=False
    ))

    alloc_table = Table(title="🧭 建议大类资产配置比例与投顾行动指引", show_lines=True)
    alloc_table.add_column("资产大类", style="cyan", justify="center")
    alloc_table.add_column("建议配比", style="bold green", justify="center")
    alloc_table.add_column("角色与功能", style="white")

    alloc_table.add_row("权益类资产 (A股核心基金/宽基ETF)", f"{report.suggested_equity_ratio}%", "博取中长期估值中枢修复与企业盈利超额回报")
    alloc_table.add_row("固收类资产 (纯债基金/中短债)", f"{report.suggested_bond_ratio}%", "压制组合净值波动，提供充裕稳定现金流底仓")
    alloc_table.add_row("避险与商品 (实物黄金/对冲资产)", f"{report.suggested_gold_ratio}%", "抵御外生流动性冲击与地缘宏观不确定性")

    console.print(alloc_table)

    console.print(Panel(
        f"[bold yellow]投顾量化建议[/bold yellow]:\n{report.action_advice}",
        title="💡 投顾决策专家建议",
        expand=False
    ))


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

    # sync-all-indices
    p_all = subparsers.add_parser("sync-all-indices", help="批量防风控拉取 A 股全市场指数数据")
    p_all.add_argument("--tier", choices=["1", "2", "3", "all"], default="all", help="同步梯级 (1:核心宽基 50只, 2:主流行业 167只, all:全量 751只)")
    p_all.add_argument("--delay", type=float, default=1.5, help="请求基准冷却时间 (秒, 附带动态随机抖动)")
    p_all.add_argument("--limit", type=int, default=None, help="最大拉取标的数量限制")
    p_all.add_argument("--force", action="store_true", help="强制覆盖已存在数据，忽略断点跳过")
    p_all.add_argument("--status", action="store_true", help="仅查看当前湖仓与断点同步进度看板")
    p_all.add_argument("--retries", type=int, default=3, help="单标的失败重试次数 (带指数退避)")

    # sync-funds-catalog
    p_fc = subparsers.add_parser("sync-funds-catalog", help="一键同步全市场公募基金五大全景宏观档案表")
    p_fc.add_argument("--force", action="store_true", help="强制重新拉取最新快照")

    # sync-fund-nav
    p_fnav = subparsers.add_parser("sync-fund-nav", help="拉取公募基金全历史日净值时序 (单只或批量)")
    p_fnav.add_argument("code", nargs="?", default=None, help="单只基金代码 (例如 000001 或 002910)")
    p_fnav.add_argument("--top", type=int, default=None, help="批量同步前 N 只头部核心基金时序")
    p_fnav.add_argument("--delay", type=float, default=1.5, help="请求基准冷却时间 (秒)")
    p_fnav.add_argument("--force", action="store_true", help="强制覆盖已存在时序")
    p_fnav.add_argument("--status", action="store_true", help="查看基金净值时序同步进度看板")

    # sync-macro
    subparsers.add_parser("sync-macro", help="全量同步宏观经济、利率中枢、两融杠杆与指数估值")

    # market-temp
    subparsers.add_parser("market-temp", help="计算大盘估值温度计分数、股债性价比 (ERP) 与大类资产配置建议")

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
        "sync-all-indices": cmd_sync_all_indices,
        "sync-funds-catalog": cmd_sync_funds_catalog,
        "sync-fund-nav": cmd_sync_fund_nav,
        "sync-macro": cmd_sync_macro,
        "market-temp": cmd_market_temp,
        "export-dict": cmd_export_dict,
        "sync-cache": cmd_sync_cache
    }

    if args.subcommand in cmds:
        cmds[args.subcommand](args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()

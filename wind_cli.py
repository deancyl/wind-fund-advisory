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
from src.parsers.fund_rules_collector import FundTradingRulesCollector
from src.parsers.research_report_collector import ResearchReportCollector
from src.parsers.market_data_collector import MarketDataCollector
from src.parsers.global_market_collector import GlobalMarketCollector
from src.analysis.market_temperature import MarketTemperatureAnalyzer
from src.analysis.global_linkage_analyzer import GlobalLinkageAnalyzer
from src.analysis.between_the_lines_analyzer import BetweenTheLinesAnalyzer
from src.analysis.fund_analyzer import FundAnalyzer
from src.analysis.winrate_analyzer import WinRateAnalyzer
from src.storage.lakehouse import LakehouseManager
from src.analysis.benchmark import BenchmarkManager
from src.advisory.rules_engine import AdvisoryRulesEngine
from src.advisory.report_generator import InvestmentReportGenerator
from src.analysis.portfolio_analyzer import PortfolioAnalyzer
from src.advisory.portfolio_report import PortfolioReportGenerator
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

    # 附带交易规则与费率摘要
    rule_info = lakehouse.get_fund_trading_rule(code)
    if rule_info:
        pur_status = rule_info.get("purchase_status", "未知")
        red_status = rule_info.get("redemption_status", "未知")
        min_pur = rule_info.get("min_purchase_amount", 10.0)
        daily_lim = rule_info.get("daily_limit_amount", 1e11)
        lim_str = "无限额" if daily_lim >= 1e8 else f"{daily_lim:,.0f}元"
        op_fee = rule_info.get("est_total_operating_fee", 1.40)
        pur_fee = rule_info.get("discount_purchase_fee_pct", 0.15)

        table.add_row("申购/赎回准入状态", f"{pur_status} / {red_status}", f"单日限额: {lim_str}")
        table.add_row("起购金额 / 代销费率", f"起点 {min_pur:.2f}元", f"申购手续费: {pur_fee:.2f}% (优惠)")
        table.add_row("综合年化运作费率", f"{op_fee:.2f}% / 年", f"管理+托管+销售服务费 (每日计提)")

    console.print(table)


def cmd_sync_fund_rules(args):
    console = Console()
    console.print(Panel(
        "[bold cyan]启动全市场公募基金交易规则与全景费率全量同步管道[/bold cyan]\n"
        "[dim]覆盖范围: 全市场 27,000+ 只开放式基金 (申购状态/赎回状态/购买起点/日累计限额/手续费/下一开放日/运作费率)[/dim]",
        title="📋 基金交易规则与全景费率入湖",
        expand=False
    ))

    collector = FundTradingRulesCollector()
    summary = collector.sync_all_trading_rules(delay=args.delay)

    table = Table(title="📋 公募基金交易规则与费率入湖看板", show_lines=True)
    table.add_column("统计维度", style="cyan")
    table.add_column("样本数量", style="bold green", justify="right")
    table.add_column("占比 / 状态", style="yellow")
    table.add_column("说明与投顾影响", style="white")

    table.add_row("全市场公募基金总数", f"{summary.total_funds:,} 只", "100.0%", "涵盖全部开放式及定期开放公募基金")
    p_pct = f"{summary.purchase_allowed_count / summary.total_funds * 100:.1f}%"
    table.add_row("正常开放申购标的", f"{summary.purchase_allowed_count:,} 只", p_pct, "可直接买入/定投配置的核心底仓池")
    r_pct = f"{summary.redemption_allowed_count / summary.total_funds * 100:.1f}%"
    table.add_row("正常开放赎回标的", f"{summary.redemption_allowed_count:,} 只", r_pct, "流动性充沛，支持实时申请赎回")
    l_pct = f"{summary.large_amount_limited_count / summary.total_funds * 100:.1f}%"
    table.add_row("暂停大额申购标的 (限额)", f"{summary.large_amount_limited_count:,} 只", l_pct, "高人气绩优基金保护策略规模与持有人利益")

    console.print(table)
    console.print(f"[bold green]✓ 全市场基金交易规则表已成功落盘至 data/master/fund_trading_rules.parquet！[/bold green]")
    console.print(f"[dim]DuckDB 统一视图: v_fund_trading_rules[/dim]")


def cmd_fund_rule(args):
    console = Console()
    code = args.code.strip().upper()
    console.print(f"[cyan]正在深度调阅基金 [bold]{code}[/bold] 的交易规则与全景阶梯费率...[/cyan]")

    collector = FundTradingRulesCollector()
    fee_struct = collector.get_fund_detailed_fee_structure(code)

    if not fee_struct:
        lakehouse = LakehouseManager()
        rule = lakehouse.get_fund_trading_rule(code)
        if not rule:
            console.print(f"[red]! 未在本地规则库中检索到基金 {code} 的交易信息，请先运行: python wind_cli.py sync-fund-rules[/red]")
            return
        # 降级展示基准规则
        console.print(Panel(
            f"[bold white]基金代码[/bold white]: {rule.get('wind_code')} ({rule.get('symbol')})\n"
            f"[bold white]基金简称[/bold white]: {rule.get('fund_name')}  |  类型: {rule.get('fund_type')}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"申购状态: [bold green]{rule.get('purchase_status')}[/bold green]  |  赎回状态: [bold green]{rule.get('redemption_status')}[/bold green]\n"
            f"购买起点: {rule.get('min_purchase_amount', 10.0):.2f}元  |  单日限额: {'无限额' if rule.get('daily_limit_amount', 1e11) >= 1e8 else str(rule.get('daily_limit_amount')) + '元'}\n"
            f"预估年化运作费率: {rule.get('est_total_operating_fee', 1.40):.2f}% (管理费 {rule.get('est_management_fee'):.2f}% + 托管费 {rule.get('est_custodian_fee'):.2f}%)\n"
            f"优惠申购费率: {rule.get('discount_purchase_fee_pct', 0.15):.2f}%",
            title=f"📋 基金交易规则档案: {rule.get('fund_name')}",
            expand=False
        ))
        return

    # 深度渲染全景卡片
    console.print(Panel(
        f"[bold white]基金全称[/bold white]: {fee_struct.fund_name} ({fee_struct.fund_code})\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🏷️  [bold cyan]申赎准入状态[/bold cyan]: 申购: [bold green]{fee_struct.purchase_status}[/bold green]  |  赎回: [bold green]{fee_struct.redemption_status}[/bold green]  |  定投: [bold green]{fee_struct.regular_investment_status}[/bold green]\n"
        f"💵  [bold cyan]交易门槛与限额[/bold cyan]: 首次买入 {fee_struct.min_purchase_amount:.2f}元起  |  追加购买 {fee_struct.min_additional_amount:.2f}元起  |  单日累计限额: {'无限额' if fee_struct.daily_limit_amount < 0 else f'{fee_struct.daily_limit_amount:,.0f}元'}\n"
        f"⏱️  [bold cyan]申赎确认周期[/bold cyan]: 买入确认日: [bold white]{fee_struct.purchase_confirm_cycle}[/bold white]  |  卖出确认日: [bold white]{fee_struct.redemption_arrive_cycle}[/bold white]\n"
        f"─────────────────────────────────────────────────────\n"
        f"🏛️  [bold yellow]固定运作年化费率 (每日从净值计提)[/bold yellow]:\n"
        f"   管理费率: [bold white]{fee_struct.management_fee_pct:.2f}%/年[/bold white]  |  "
        f"托管费率: [bold white]{fee_struct.custodian_fee_pct:.2f}%/年[/bold white]  |  "
        f"销售服务费率: [bold white]{fee_struct.sales_service_fee_pct:.2f}%/年[/bold white]\n"
        f"   --> 综合年化持有成本: [bold green]{fee_struct.total_operating_fee_pct:.2f}%/年[/bold green]",
        title=f"📋 基金交易规则与全景费率深度卡: {fee_struct.fund_name}",
        expand=False
    ))

    # 申购费率阶梯
    if fee_struct.subscription_tiers:
        sub_table = Table(title="🛒 前端申购费率金额阶梯 (Subscription Fee Schedule)", show_lines=True)
        sub_table.add_column("申购金额区间", style="cyan")
        sub_table.add_column("收费标准 (原费率 / 代销渠道优惠)", style="bold green", justify="right")
        for tier in fee_struct.subscription_tiers:
            sub_table.add_row(tier.get("tier", ""), tier.get("fee", ""))
        console.print(sub_table)

    # 赎回费率阶梯
    if fee_struct.redemption_tiers:
        red_table = Table(title="🚪 赎回费率持有期阶梯 (Redemption Fee Schedule - 严守证监会流动性规约)", show_lines=True)
        red_table.add_column("实际持有时间区间", style="cyan")
        red_table.add_column("适用赎回费率", style="bold red", justify="right")
        red_table.add_column("监管归属与资金去向", style="yellow")
        for tier in fee_struct.redemption_tiers:
            t_name = tier.get("tier", "")
            t_fee = tier.get("fee", "")
            if "<7" in t_name or "小于7天" in t_name:
                note = "【监管强制惩罚性费率】100% 计入基金资产，严打短期套利"
            elif "730" in t_name or "2年" in t_name or "0.00%" in t_fee or "免" in t_fee:
                note = "【长期持有免收】费率为 0.00%，鼓励中长期价值投资"
            elif "365" in t_name or "1年" in t_name:
                note = "中长期费率优惠区间，25% 计入基金资产"
            elif "30天" in t_name or "1个月" in t_name:
                note = "常规短期赎回费率，至少 75% 计入基金资产"
            else:
                note = "常规赎回费率，25%~50% 计入基金资产补充净值"
            red_table.add_row(t_name, t_fee, note)
        console.print(red_table)


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


def cmd_sync_global(args):
    console = Console()
    console.print(Panel(
        "[bold cyan]启动全球宏观资产与外部联动数据全量采集管道[/bold cyan]\n"
        "[dim]数据范围: 海外核心股指 (美股/港股/亚太) + 全球基准汇率 (在岸/离岸/利差/美元指数) + 核心大宗商品 (黄金/原油/铜/白银)[/dim]",
        title="🌐 全球宏观资产采集同步",
        expand=False
    ))

    collector = GlobalMarketCollector()
    cat = getattr(args, "category", "all")
    delay = getattr(args, "delay", 1.2)

    if cat == "indices":
        rows = collector.sync_global_indices(delay=delay)
        console.print(f"[bold green]✓ 全球海外核心股指同步完毕，共沉淀 {rows:,} 条日 K 线。[/bold green]")
    elif cat == "fx":
        rows = collector.sync_fx_rates(delay=delay)
        console.print(f"[bold green]✓ 全球基准汇率与在离岸价差同步完毕，共沉淀 {rows:,} 交易日样本。[/bold green]")
    elif cat == "commodities":
        rows = collector.sync_commodities(delay=delay)
        console.print(f"[bold green]✓ 核心大宗商品期货同步完毕，共沉淀 {rows:,} 条日 K 线。[/bold green]")
    else:
        summary = collector.sync_all_global_data(delay=delay)
        table = Table(title="🌐 全球宏观外部资产入湖汇总看板", show_lines=True)
        table.add_column("外部资产维度", style="cyan")
        table.add_column("采集样本量", style="bold green", justify="right")
        table.add_column("DuckDB 视图", style="magenta")
        table.add_column("涵盖核心标的", style="white")

        table.add_row("全球核心股指", f"{summary.indices_rows:,} 条", "v_global_indices", "标普500, 纳指, 道指, 恒生, 恒生科技, 日经225, 台湾加权")
        table.add_row("全球基准汇率", f"{summary.fx_rows:,} 条", "v_global_fx", "USD/CNY, USD/CNH, 在离岸汇差, 美元指数(DXY)")
        table.add_row("核心大宗商品", f"{summary.commodities_rows:,} 条", "v_global_commodities", "COMEX黄金(GC), WTI原油(CL), 布伦特(OIL), 铜(HG), 白银(SI)")

        console.print(table)
        console.print(f"[bold green]✓ 全球外部资产已全部入湖并挂载 DuckDB 视图！[/bold green]")
        console.print(f"[dim]执行联动温度计测算: python wind_cli.py market-temp[/dim]")


def cmd_market_temp(args):
    console = Console()
    console.print("[cyan]正在调用量化模型推演当前大盘估值温度与全球宏观联动传导...[/cyan]")

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

    # 1. 主看板：本土估值温度与全球宏观综合温度
    ext_adj_str = f"{report.total_external_adjustment:+.1f} 分"
    console.print(Panel(
        f"[bold white]评估基准日期[/bold white]: {report.eval_date}\n"
        f"[bold white]沪深300收盘[/bold white]: {report.hs300_close:.2f}  |  "
        f"滚动PE: {report.hs300_pe:.2f}倍 (历史分位: {report.hs300_pe_percentile:.1f}%)  |  "
        f"PB: {report.hs300_pb:.2f}倍 (历史分位: {report.hs300_pb_percentile:.1f}%)\n"
        f"[bold white]中国10年期国债收益率[/bold white]: {report.cn_10y_treasury_yield:.2f}%\n"
        f"[bold green]股债性价比 (ERP)[/bold green]: {report.erp_value:+.2f}%  (全历史分位: {report.erp_percentile:.1f}%)\n"
        f"[bold magenta]两融维持担保比例[/bold magenta]: {report.margin_guarantee_ratio:.1f}% (杠杆安全垫充足)\n"
        f"─────────────────────────────────────────────────────\n"
        f"🏛️ [bold white]本土估值基础温度[/bold white]: {report.base_valuation_score:.1f} 分\n"
        f"🌐 [bold cyan]外生宏观修正调节[/bold cyan]: [{ 'bold red' if report.total_external_adjustment > 3 else 'bold green' }]{ext_adj_str}[/]  "
        f"(汇率: {report.fx_pressure_factor:+.1f} | 利差: {report.us_yield_spread_factor:+.1f} | 避险: {report.risk_sentiment_factor:+.1f})\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🌡️ [bold white]全球宏观综合温度[/bold white]: [{temp_color}]{report.market_temperature_score} 分[/{temp_color}]  "
        f"--> 状态研判: [bold green]{report.valuation_status}[/bold green]",
        title="🌡️ A 股市场全景估值温度计与资产配置罗盘 (融合全球宏观传导)",
        expand=False
    ))

    # 2. 全球宏观联动与外生风险雷达
    linkage_analyzer = GlobalLinkageAnalyzer()
    metrics = linkage_analyzer.analyze()
    if metrics:
        radar_table = Table(title="🌍 全球宏观联动与外生风险雷达", show_lines=True)
        radar_table.add_column("外部监控维度", style="cyan")
        radar_table.add_column("最新市场数值", style="white", justify="right")
        radar_table.add_column("滚动联动/状态", style="yellow")
        radar_table.add_column("宏观传导机制与外生影响", style="green")

        # 汇率
        spread_desc = f"价差: {metrics.cnh_cny_spread:+.4f}"
        radar_table.add_row(
            "人民币汇率 (USD/CNY & CNH)",
            f"在岸 {metrics.usd_cny_latest:.4f} / 离岸 {metrics.usd_cnh_latest:.4f}",
            spread_desc,
            f"近20日变动 {metrics.usd_cny_20d_pct:+.2f}% (调节分: {metrics.fx_pressure_factor:+.1f})"
        )

        # 中美利差
        spread_color = "red" if metrics.cn_us_spread_10y < -1.5 else "green"
        radar_table.add_row(
            "中美基准利差 (10Y 国债)",
            f"利差 {metrics.cn_us_spread_10y:+.2f}%",
            f"[{spread_color}]{'深度倒挂' if metrics.cn_us_spread_10y < -1.5 else '利差温和'}[/{spread_color}]",
            f"美债收益率中枢高位约束货币空间 (调节分: {metrics.us_yield_spread_factor:+.1f})"
        )

        # 海外股市联动
        radar_table.add_row(
            "跨市场相关性 (A股 vs 海外)",
            f"HS300-SPX 30D: {metrics.corr_hs300_spx_30d:+.2f}",
            f"HS300-HSI 30D: {metrics.corr_hs300_hsi_30d:+.2f}",
            f"创业板-纳指 30D: {metrics.corr_chinext_nasdaq_30d:+.2f} (科技产业链映射)"
        )

        # 大宗避险
        radar_table.add_row(
            "全球大宗与避险资产",
            f"黄金 ${metrics.gold_close:.1f} / 原油 ${metrics.crude_oil_close:.1f}",
            f"DXY {metrics.dxy_close:.2f} (黄金20D: {metrics.gold_20d_pct:+.1f}%)",
            f"避险情绪调节项: {metrics.risk_sentiment_factor:+.1f} 分"
        )

        console.print(radar_table)

    # 3. 资产配置比例与投顾行动指引
    alloc_table = Table(title="🧭 建议大类资产配置比例与投顾行动指引", show_lines=True)
    alloc_table.add_column("资产大类", style="cyan", justify="center")
    alloc_table.add_column("建议配比", style="bold green", justify="center")
    alloc_table.add_column("角色与功能", style="white")

    alloc_table.add_row("权益类资产 (A股核心基金/宽基ETF)", f"{report.suggested_equity_ratio}%", "博取中长期估值中枢修复与企业盈利超额回报")
    alloc_table.add_row("固收类资产 (纯债基金/中短债)", f"{report.suggested_bond_ratio}%", "压制组合净值波动，提供充裕稳定现金流底仓")
    alloc_table.add_row("避险与商品 (实物黄金/对冲资产)", f"{report.suggested_gold_ratio}%", "抵御外生流动性冲击与地缘宏观不确定性")

    console.print(alloc_table)

    console.print(Panel(
        f"[bold yellow]投顾量化建议[/bold yellow]:\n{report.action_advice}\n\n"
        f"[bold cyan]全球宏观研判[/bold cyan]: {report.global_linkage_summary}",
        title="💡 投顾决策专家建议",
        expand=False
    ))


def cmd_export_dict(args):
    from scripts.export_master_dict import main as export_main
    export_main()


def cmd_sync_cache(args):
    from scripts.sync_terminal_cache import main as sync_main
    sync_main()


def cmd_portfolio(args):
    console = Console()
    portfolio_name = args.name
    weights_map = {}

    TEMPLATE_CONFIGS = {
        "保守型": ("保守防守型配置", {"CBA00101.CS": 0.60, "SHIBOR3M": 0.30, "000300.SH": 0.05, "AU9999.SGE": 0.05}),
        "稳健型": ("稳健固收增强配置", {"CBA00101.CS": 0.60, "000300.SH": 0.15, "SHIBOR3M": 0.15, "AU9999.SGE": 0.10}),
        "平衡型": ("全天候平衡配置", {"000300.SH": 0.25, "000905.SH": 0.15, "CBA00101.CS": 0.40, "AU9999.SGE": 0.10, "SHIBOR3M": 0.10}),
        "成长型": ("积极成长配置", {"000300.SH": 0.30, "000905.SH": 0.20, "399006.SZ": 0.10, "CBA00101.CS": 0.25, "AU9999.SGE": 0.10, "SHIBOR3M": 0.05}),
        "进取型": ("高弹性进攻配置", {"000300.SH": 0.35, "000905.SH": 0.25, "399006.SZ": 0.20, "CBA00101.CS": 0.10, "AU9999.SGE": 0.05, "SHIBOR3M": 0.05})
    }

    if args.weights:
        try:
            parts = [p.strip() for p in args.weights.split(",") if p.strip()]
            for p in parts:
                sym, w_str = p.split(":")
                weights_map[sym.strip().upper()] = float(w_str.strip())
            if not portfolio_name:
                portfolio_name = "定制多元投资组合"
        except Exception as e:
            console.print(f"[red]! 权重参数解析失败，格式应为 '代码1:权重1,代码2:权重2'，如 '000300.SH:0.4,CBA00101.CS:0.6'。错误: {e}[/red]")
            return
    elif args.template:
        t_name = args.template.strip()
        if t_name in TEMPLATE_CONFIGS:
            default_title, w_dict = TEMPLATE_CONFIGS[t_name]
            weights_map = w_dict
            if not portfolio_name:
                portfolio_name = f"{t_name}投顾标准投资组合 ({default_title})"
        else:
            console.print(f"[red]! 未知模板类型 '{t_name}'，可选: 保守型, 稳健型, 平衡型, 成长型, 进取型[/red]")
            return
    else:
        default_title, w_dict = TEMPLATE_CONFIGS["平衡型"]
        weights_map = w_dict
        if not portfolio_name:
            portfolio_name = f"平衡型投顾标准投资组合 ({default_title})"

    console.print(f"[cyan]正在执行投资组合量化回测与深度分析: [bold]{portfolio_name}[/bold] ...[/cyan]")

    analyzer = PortfolioAnalyzer()
    try:
        result = analyzer.analyze_portfolio(
            weights_map=weights_map,
            benchmark_code=args.benchmark,
            rebalance_freq=args.rebalance,
            start_date=args.start_date,
            end_date=args.end_date,
            portfolio_name=portfolio_name
        )
    except Exception as e:
        console.print(f"[red]! 组合回测执行异常: {e}[/red]")
        return

    m = result.metrics
    d = result.diversification

    # 1. 核心看板
    ret_color = "bold green" if m.cum_return_pct >= 0 else "bold red"
    alpha_color = "bold green" if m.alpha_ann_pct >= 0 else "bold yellow"

    console.print(Panel(
        f"[bold white]组合名称[/bold white]: {result.portfolio_name}  |  [bold white]再平衡机制[/bold white]: {result.rebalance_freq}\n"
        f"[bold white]回测区间[/bold white]: {m.start_date} ~ {m.end_date} (共 {m.trading_days} 交易日)  |  "
        f"[bold white]对标基准[/bold white]: {m.benchmark_name} ({m.benchmark_code})\n"
        f"─────────────────────────────────────────────────────────────────────────────\n"
        f"📈 [bold white]累计收益率[/bold white]: [{ret_color}]+{m.cum_return_pct}%[/{ret_color}]  |  "
        f"[bold white]年化复合收益率 (CAGR)[/bold white]: [{ret_color}]+{m.annualized_return_pct}%[/{ret_color}]\n"
        f"📉 [bold white]历史最大回撤 (MDD)[/bold white]: [bold yellow]{m.max_drawdown_pct}%[/bold yellow] (谷底: {m.max_dd_trough_date})  |  "
        f"[bold white]年化波动率[/bold white]: {m.annualized_volatility_pct}%\n"
        f"⚖️ [bold white]夏普比率 (Sharpe)[/bold white]: [bold cyan]{m.sharpe_ratio}[/bold cyan]  |  "
        f"[bold white]索提诺比率[/bold white]: [bold cyan]{m.sortino_ratio}[/bold cyan]  |  "
        f"[bold white]卡玛比率[/bold white]: [bold cyan]{m.calmar_ratio}[/bold cyan]\n"
        f"🛡️ [bold white]单日在险价值 (VaR 95%)[/bold white]: [bold magenta]-{m.var_95_pct}%[/bold magenta]  |  "
        f"[bold white]条件在险价值 (CVaR)[/bold white]: [bold magenta]-{m.cvar_95_pct}%[/bold magenta]\n"
        f"🚀 [bold white]年化超额 Alpha[/bold white]: [{alpha_color}]+{m.alpha_ann_pct}%[/{alpha_color}]  |  "
        f"[bold white]系统贝塔 (Beta)[/bold white]: {m.beta}  |  "
        f"[bold white]信息比率[/bold white]: {m.information_ratio}\n"
        f"🌐 [bold white]分散化比率[/bold white]: [bold green]{d.diversification_ratio}[/bold green] "
        f"(加权独立波动 {d.weighted_asset_vol_pct}% -> 组合实际波动 {d.portfolio_vol_pct}%)  |  "
        f"[bold white]有效资产数[/bold white]: {d.effective_n_assets}",
        title="💼 投资组合全景量化诊断体检看板",
        expand=False
    ))

    # 2. 资产持仓与归因表
    t_hold = Table(title="📊 资产配置权重与收益/风险归因明细表", show_lines=True)
    t_hold.add_column("标的代码", style="cyan", justify="center")
    t_hold.add_column("标的简称", style="bold white")
    t_hold.add_column("目标权重", style="bold yellow", justify="center")
    t_hold.add_column("标的累计收益", style="green", justify="right")
    t_hold.add_column("组合收益贡献", style="bold green", justify="right")
    t_hold.add_column("年化波动率", style="white", justify="right")
    t_hold.add_column("边际风险(MRC)", style="magenta", justify="right")
    t_hold.add_column("风险贡献占比(PCR)", style="bold magenta", justify="right")

    for it in result.attribution:
        t_hold.add_row(
            it.symbol,
            it.name,
            f"{it.target_weight_pct}%",
            f"+{it.asset_return_pct}%" if it.asset_return_pct >= 0 else f"{it.asset_return_pct}%",
            f"+{it.return_contribution_pct}%" if it.return_contribution_pct >= 0 else f"{it.return_contribution_pct}%",
            f"{it.asset_volatility_pct}%",
            f"{it.marginal_risk_contribution}%",
            f"{it.risk_contribution_pct}%"
        )
    console.print(t_hold)

    # 3. 资产间相关系数矩阵表格
    symbols = [a.symbol for a in result.assets]
    t_corr = Table(title="🔗 资产间皮尔逊相关系数矩阵 (Correlation Heatmap)", show_lines=True)
    t_corr.add_column("标的代码", style="cyan", justify="center")
    for s in symbols:
        t_corr.add_column(s, justify="center")

    for s1 in symbols:
        row = [s1]
        for s2 in symbols:
            val = d.correlation_matrix.get(s1, {}).get(s2, 1.0)
            if s1 == s2:
                val_str = "[bold white]1.000[/bold white]"
            elif val > 0.7:
                val_str = f"[bold red]{val:.3f}[/bold red]"
            elif val > 0.3:
                val_str = f"[yellow]{val:.3f}[/yellow]"
            elif val > -0.1:
                val_str = f"[green]{val:.3f}[/green]"
            else:
                val_str = f"[bold cyan]{val:.3f}[/bold cyan]"
            row.append(val_str)
        t_corr.add_row(*row)
    console.print(t_corr)

    # 4. ASCII 走势图
    chart_text = PortfolioReportGenerator.render_ascii_chart(result.history_df, height=11, width=62)
    console.print(Panel(chart_text, title="📈 组合累计净值走势 vs 基准走势拟合", expand=False))

    # 5. 组合优化配置建议 (如果指定 --optimize)
    if args.optimize and result.optimization_proposals:
        t_opt = Table(title="✨ 现代资产配置优化前沿方案推荐 (Markowitz & Risk Parity)", show_lines=True)
        t_opt.add_column("策略方案", style="bold cyan")
        t_opt.add_column("策略核心导向", style="white")
        t_opt.add_column("预期年化收益", style="bold green", justify="center")
        t_opt.add_column("预期年化波动", style="bold yellow", justify="center")
        t_opt.add_column("预期夏普比率", style="bold cyan", justify="center")
        t_opt.add_column("推荐权重配置", style="white")

        for prop in result.optimization_proposals:
            w_summary = ", ".join([f"{k}: {round(v*100, 1)}%" for k, v in prop.weights.items()])
            t_opt.add_row(
                prop.strategy_name,
                prop.description,
                f"+{prop.expected_annual_return_pct}%",
                f"{prop.expected_annual_vol_pct}%",
                f"{prop.expected_sharpe_ratio}",
                w_summary
            )
        console.print(t_opt)

    # 6. 报告导出 (如果指定 --export)
    if args.export:
        reporter = PortfolioReportGenerator(console)
        report_file = reporter.save_report_to_disk(result)
        console.print(f"\n[bold green]✓ 专业投资组合分析研报已成功导出至磁盘: [underline]{report_file}[/underline][/bold green]")


def cmd_sync_reports(args):
    console = Console()
    collector = ResearchReportCollector()
    symbols = [args.code] if args.code else None
    console.print(f"[cyan]🚀 开始同步权威卖方研报数据入湖仓 (宏观策略 / 核心行业 / 重点龙头)...[/cyan]")
    total = collector.sync_reports_to_lakehouse(symbols=symbols)
    console.print(f"[bold green]✓ 研报数据同步完成，湖仓累计沉淀 {total} 篇卖方研报，已挂载至 DuckDB 视图 v_research_reports[/bold green]")


def cmd_reports(args):
    console = Console()
    lakehouse = LakehouseManager()
    collector = ResearchReportCollector(lakehouse=lakehouse)
    
    code = args.code.strip() if args.code else None
    if code:
        df = lakehouse.get_stock_reports(code, limit=args.limit)
        if df.empty or len(df) < 3:
            console.print(f"[cyan]ℹ 本地湖仓暂无或研报较少，正在全市场高规格通道拉取 {code} 最新研报...[/cyan]")
            collector.fetch_stock_reports(code, limit=args.limit)
            collector.sync_reports_to_lakehouse([code])
            df = lakehouse.get_stock_reports(code, limit=args.limit)
    else:
        df = lakehouse.get_stock_reports(None, limit=args.limit)
        if df.empty:
            console.print("[cyan]ℹ 本地研报湖仓为空，正在全市场高规格通道拉取全市场最新研报...[/cyan]")
            collector.sync_reports_to_lakehouse()
            df = lakehouse.get_stock_reports(None, limit=args.limit)

    if df.empty:
        console.print("[yellow]! 未检索到相关研报数据[/yellow]")
        return

    table = Table(title=f"📑 权威卖方研报检索流 (共 {len(df)} 篇, 支持原文 PDF 直链)", show_lines=True)
    table.add_column("日期", style="cyan", width=11)
    table.add_column("标的", style="green", width=14)
    table.add_column("券商机构", style="magenta", width=10)
    table.add_column("分析师", style="white", width=10)
    table.add_column("评级", style="yellow", width=8)
    table.add_column("研报标题", style="bold white", width=36)
    table.add_column("PDF 直读链接", style="blue underline", width=40)

    for _, r in df.iterrows():
        stk = f"{r.get('stock_name', '')} ({r.get('symbol', '')})"
        table.add_row(
            str(r.get("publish_date", ""))[:10],
            stk,
            str(r.get("org_name", "")),
            str(r.get("analyst_name", ""))[:10],
            str(r.get("rating", "")),
            str(r.get("title", ""))[:34],
            str(r.get("pdf_url", ""))
        )

    console.print(table)


def cmd_report_subtext(args):
    console = Console()
    analyzer = BetweenTheLinesAnalyzer()
    code = args.code.strip()
    console.print(f"[cyan]🔍 正在对 {code} 卖方研报进行‘听话听音’潜台词挖掘与一致预期分析...[/cyan]")
    res = analyzer.analyze(code, limit=args.limit)
    analyzer.print_terminal_card(res)


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

    # sync-fund-rules
    p_sfr = subparsers.add_parser("sync-fund-rules", help="全量同步中国公募基金交易规则、运作费率与申赎限额主表")
    p_sfr.add_argument("--delay", type=float, default=1.0, help="网络请求基准延迟")

    # fund-rule
    p_fr = subparsers.add_parser("fund-rule", help="深度调阅单只基金全景阶梯费率与申赎交易规则")
    p_fr.add_argument("code", help="基金代码 (例如 000001 或 000001.OF)")

    # sync-fund-nav
    p_fnav = subparsers.add_parser("sync-fund-nav", help="拉取公募基金全历史日净值时序 (单只或批量)")
    p_fnav.add_argument("code", nargs="?", default=None, help="单只基金代码 (例如 000001 或 002910)")
    p_fnav.add_argument("--top", type=int, default=None, help="批量同步前 N 只头部核心基金时序")
    p_fnav.add_argument("--delay", type=float, default=1.5, help="请求基准冷却时间 (秒)")
    p_fnav.add_argument("--force", action="store_true", help="强制覆盖已存在时序")
    p_fnav.add_argument("--status", action="store_true", help="查看基金净值时序同步进度看板")

    # sync-macro
    subparsers.add_parser("sync-macro", help="全量同步宏观经济、利率中枢、两融杠杆与指数估值")

    # sync-global
    p_sg = subparsers.add_parser("sync-global", help="全量同步全球宏观市场、基准汇率、利差与核心大宗商品")
    p_sg.add_argument("--category", choices=["all", "indices", "fx", "commodities"], default="all", help="同步类别 (all, indices, fx, commodities)")
    p_sg.add_argument("--delay", type=float, default=1.2, help="单标的请求冷却时间 (秒)")

    # market-temp
    subparsers.add_parser("market-temp", help="计算大盘估值温度计分数、股债性价比 (ERP) 与大类资产配置建议")

    # export-dict
    subparsers.add_parser("export-dict", help="导出全市场主代码字典至 CSV")

    # sync-cache
    subparsers.add_parser("sync-cache", help="同步终端 Chromium 缓存数据")

    # portfolio
    p_port = subparsers.add_parser("portfolio", help="投资组合深度分析、历史加权回测、风险收益全景矩阵与资产配置优化")
    p_port.add_argument("--weights", "-w", default=None, help="标的与权重映射 (例如: '000300.SH:0.4,000905.SH:0.3,CBA00101.CS:0.3')")
    p_port.add_argument("--template", "-t", default=None, choices=["保守型", "稳健型", "平衡型", "成长型", "进取型"], help="投顾标准配置模板")
    p_port.add_argument("--benchmark", "-b", default="000300.SH", help="业绩对标基准代码 (默认 000300.SH 沪深300)")
    p_port.add_argument("--rebalance", "-r", default="quarterly", choices=["quarterly", "monthly", "yearly", "none"], help="定期再平衡调仓机制 (默认 quarterly 按季度)")
    p_port.add_argument("--start-date", default=None, help="回测起始日期 (YYYY-MM-DD)")
    p_port.add_argument("--end-date", default=None, help="回测截止日期 (YYYY-MM-DD)")
    p_port.add_argument("--name", default=None, help="投资组合定制名称")
    p_port.add_argument("--optimize", action="store_true", help="求解现代资产组合优化前沿配置建议 (最大夏普、最小方差、风险平价)")
    p_port.add_argument("--export", action="store_true", help="自动导出专业 Markdown 研报至 data/reports/")

    # sync-reports
    p_srep = subparsers.add_parser("sync-reports", help="全量同步权威卖方研报库 (宏观大势、核心行业与重点龙头)")
    p_srep.add_argument("--code", default=None, help="单只股票/指数代码 (例如 600519 或 300750)")

    # reports
    p_rep = subparsers.add_parser("reports", help="检索全市场最新卖方研报流 (支持查看机构、分析师与原文 PDF 直链)")
    p_rep.add_argument("code", nargs="?", default=None, help="股票代码 (可选，默认查看全市场最新宏观与行业研报)")
    p_rep.add_argument("--limit", type=int, default=20, help="返回研报条数限制 (默认 20)")

    # report-subtext
    p_rst = subparsers.add_parser("report-subtext", help="卖方研报‘听话听音’量化透视 (挖掘主旋律下的潜台词踩刹车与真看多信号)")
    p_rst.add_argument("code", help="股票代码 (例如 600519, 300750, 000001)")
    p_rst.add_argument("--limit", type=int, default=30, help="分析样本研报条数 (默认 30)")

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
        "sync-fund-rules": cmd_sync_fund_rules,
        "fund-rule": cmd_fund_rule,
        "sync-fund-nav": cmd_sync_fund_nav,
        "sync-macro": cmd_sync_macro,
        "sync-global": cmd_sync_global,
        "market-temp": cmd_market_temp,
        "export-dict": cmd_export_dict,
        "sync-cache": cmd_sync_cache,
        "portfolio": cmd_portfolio,
        "sync-reports": cmd_sync_reports,
        "reports": cmd_reports,
        "report-subtext": cmd_report_subtext
    }

    if args.subcommand in cmds:
        cmds[args.subcommand](args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()

"""
Wind 投顾工作区环境体检诊断工具 (Doctor)：一键体检终端进程、离线数据源、
网络连通性与投顾会话凭证状态。
"""

import sys
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

# 将项目根目录添加进 sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import WIND_CONFIG
from src.core.terminal_probe import TerminalProbe
from src.core.session_manager import SessionManager
from src.parsers.calendar_parser import CalendarParser
from src.parsers.master_dict_parser import MasterDictParser


def main():
    console = Console()
    console.print(Panel.fit(
        "[bold cyan]Wind 投顾终端环境与数据源体检 (Doctor)[/bold cyan]\n"
        "[dim]自动诊断客户端运行状态、本地离线核心字典、交易日历与云端会话凭证[/dim]",
        border_style="cyan"
    ))

    table = Table(show_header=True, header_style="bold magenta", show_lines=True)
    table.add_column("检查项目", style="cyan", width=22)
    table.add_column("检测结果", style="white", width=42)
    table.add_column("状态", justify="center", width=12)

    # 1. 终端根目录检测
    root_exists = WIND_CONFIG.root_dir.exists()
    table.add_row(
        "Wind 客户端安装目录",
        str(WIND_CONFIG.root_dir),
        "[green]✓ 就绪[/green]" if root_exists else "[red]✗ 未找到[/red]"
    )

    # 2. 进程活跃性探测
    probe = TerminalProbe(WIND_CONFIG)
    status = probe.detect_status()
    proc_desc = (
        f"主进程 WMain PID: {status.wmain_proc.pid if status.wmain_proc else '未运行'} | "
        f"CEF 渲染引擎: {len(status.wbrowser_procs)} 个 | 占用内存: {status.total_memory_mb} MB"
    )
    table.add_row(
        "终端运行进程树",
        proc_desc,
        "[green]✓ 运行中[/green]" if status.is_running else "[yellow]! 未启动[/yellow]"
    )

    # 3. 本地交易日历检测
    cal = CalendarParser()
    cal_desc = (
        f"交易日记录数: {cal.total_count} 条 | "
        f"区间: {cal.earliest_date} ~ {cal.latest_date}"
    )
    table.add_row(
        "A股完整交易日历",
        cal_desc,
        "[green]✓ 完整[/green]" if cal.total_count > 0 else "[red]✗ 缺失[/red]"
    )

    # 4. 全市场代码表检测
    code_cache = WIND_CONFIG.code_cache_path
    if code_cache.exists():
        size_mb = round(code_cache.stat().st_size / (1024 * 1024), 2)
        dict_desc = f"FreqUsedCodeFile.codecache ({size_mb} MB 离线主字典)"
        dict_status = "[green]✓ 就绪[/green]"
    else:
        dict_desc = "未找到 FreqUsedCodeFile.codecache"
        dict_status = "[red]✗ 缺失[/red]"
    table.add_row("全市场证券代码字典", dict_desc, dict_status)

    # 5. 板块与行业树检测
    sysgrp = WIND_CONFIG.sysgrp_dat_path
    if sysgrp.exists():
        size_mb = round(sysgrp.stat().st_size / (1024 * 1024), 2)
        sysgrp_desc = f"sysgrp.dat ({size_mb} MB 行业板块分类树)"
        sysgrp_status = "[green]✓ 就绪[/green]"
    else:
        sysgrp_desc = "未找到 sysgrp.dat"
        sysgrp_status = "[red]✗ 缺失[/red]"
    table.add_row("行业与板块分类体系", sysgrp_desc, sysgrp_status)

    # 6. CEF 磁盘与内存缓存
    cef_cache = WIND_CONFIG.cef_cache_dir
    cache_count = len(list(cef_cache.glob("f_*"))) if cef_cache.exists() else 0
    table.add_row(
        "Chromium 网络数据缓存",
        f"缓存对象: {cache_count} 个响应数据文件 (含基金收益率走势图)",
        "[green]✓ 丰富[/green]" if cache_count > 10 else "[yellow]! 较少[/yellow]"
    )

    # 7. 投顾云端 SessionID 凭证
    sess_mgr = SessionManager(WIND_CONFIG)
    sid = sess_mgr.get_session_id()
    if sid:
        sid_masked = f"{sid[:12]}...{sid[-8:]} (长度 {len(sid)})"
        is_val = sess_mgr.validate_session(sid)
        sid_status = "[green]✓ 授权在线[/green]" if is_val else "[yellow]! 待续期/离线可用[/yellow]"
    else:
        sid_masked = "未检测到活跃 SessionID"
        sid_status = "[red]✗ 未授权[/red]"
    table.add_row("投顾云端认证凭证", sid_masked, sid_status)

    console.print(table)


if __name__ == "__main__":
    main()

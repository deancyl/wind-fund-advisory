"""
终端缓存数据同步与持久化脚本：扫描 Chromium 缓存池，
提取基金净值、投顾要闻、企业图谱等离线资产，归档至 data/cache/ 目录。
"""

import sys
import json
from pathlib import Path
from rich.console import Console

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.parsers.cef_cache_parser import CEFCacheParser


def main():
    console = Console()
    console.print("[cyan]正在扫描并同步 Wind 投顾终端 Chromium 网络数据缓存...[/cyan]")

    parser = CEFCacheParser()
    out_dir = Path(__file__).parent.parent / "data" / "cache"
    out_dir.mkdir(parents=True, exist_ok=True)

    # 1. 同步基金曲线
    fund_charts = parser.extract_fund_yield_charts()
    console.print(f"[green]✓ 提取到 {len(fund_charts)} 只基金的时序收益率数据[/green]")
    for code, df in fund_charts.items():
        csv_path = out_dir / f"fund_{code}.csv"
        df.to_csv(csv_path, index=False, encoding="utf-8-sig")

    # 2. 同步快讯要闻
    news = parser.extract_cached_news()
    if news:
        news_path = out_dir / "latest_news.json"
        with open(news_path, "w", encoding="utf-8") as f:
            json.dump(news, f, ensure_ascii=False, indent=2)
        console.print(f"[green]✓ 提取到 {len(news)} 条要闻简报已保存至: {news_path}[/green]")

    console.print(f"[bold green]✓ 缓存数据同步完成，已归档至: {out_dir}[/bold green]")


if __name__ == "__main__":
    main()

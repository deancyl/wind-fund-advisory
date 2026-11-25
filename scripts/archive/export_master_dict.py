"""
全市场标的字典导出脚本：从 Wind FreqUsedCodeFile.codecache 提取全市场
A股股票、公募基金与指数代码表，并保存至 data/master/securities.csv。
"""

import sys
from pathlib import Path
from rich.console import Console

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.parsers.master_dict_parser import MasterDictParser


def main():
    console = Console()
    console.print("[cyan]正在从 Wind 本地 40MB 主字典提取全市场证券标的...[/cyan]")
    parser = MasterDictParser()
    total = parser.load()
    console.print(f"[green]✓ 成功解析 {total} 只标的代码数据[/green]")

    out_file = Path(__file__).parent.parent / "data" / "master" / "securities.csv"
    saved_path = parser.export_csv(out_file)
    console.print(f"[bold green]✓ 已导出至: {saved_path}[/bold green]")

    # 打印前 10 只样本
    df = parser.to_dataframe()
    console.print("\n[yellow]前 10 只标的预览:[/yellow]")
    console.print(df.head(10).to_string())


if __name__ == "__main__":
    main()

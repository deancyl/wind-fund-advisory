from pathlib import Path

tests_dir = Path("AGY2_FundAdvisory/tests")
test_files = list(tests_dir.glob("*.py"))

checked_strings = [
    "设定目标风险", "现场推演评估", "生成实盘建仓", "当前持仓账本", "调仓时机裁决", "调仓方案执行",
    "三句话看懂本方案", "全周期跨牛熊滚动持有胜率", "六维量化打分加权公式", "四大机构级量化模型特性",
    "前十大重仓股重叠交叉检测", "聪明钱跟踪与机构抱团", "大类资产配置缺口量化分析表", "场内 ETF 溢价率监控"
]

print("Scanning tests for title strings...")
found_any = False
for tf in test_files:
    content = tf.read_text(encoding="utf-8")
    for s in checked_strings:
        if s in content:
            print(f"[{tf.name}] contains '{s}'")
            found_any = True

if not found_any:
    print("None of the title strings found in tests!")

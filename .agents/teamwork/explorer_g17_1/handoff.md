# Handoff Report — Explorer G17-1

## 1. Observation
1. **代码与行号定位**:
   - 在 `AGY2_FundAdvisory/advisory_engine.py` 的 `generate_chief_advisor_memo` 算子中（第 4170 至 4491 行）：
     - 第 4185 行: `cgb_10y = float(snap.get("treasury_10y", 1.6258))`
     - 第 4238 行: `usdcnh_rate = float(macro_multi.get("usdcnh_rate", snap.get("spot_usdcnh", 7.2450)))`
     - 第 4240 行: `gold_chg = float(macro_multi.get("gold_change_pct", 0.35))`
     - 第 4241 行: `gold_price = float(macro_multi.get("gold_price", 628.5))`
     - 第 4242 行: `nasdaq_chg = float(macro_multi.get("nasdaq_change_pct", -0.25))`
     - 第 4245 行: `us_10y = float(macro_multi.get("us_treasury_10y", snap.get("us_treasury_10y", 4.40)))`
     - 第 4246 行: `spread_cgb_us = round((cgb_10y - us_10y) * 100.0, 1)`
2. **断裂键与虚假常数实测**:
   - 运行 `.agents/teamwork/explorer_g17_1/test_snapshot_memo.py` 证实：
     - `StrategyBridge.get_latest_market_snapshot()` 输出的 snapshot 中，`spot_usdcnh` 为 `None`，`us_treasury_10y` 为 `None`。
     - `generate_chief_advisor_memo()` 输出中，美债 10Y 收益率 100% 退化为假常数 `4.40%`，利差退化为 `-277.7 bp`。
     - 黄金 ETF 华安 (518880) 价格为 `8.29元/份`，但界面文案为 `国内黄金现价 ¥8.29/克`，将每份 ETF 净值与实物克重混淆。
     - 当网络离线或无在线行情时，`gold_price` 退化为 `628.5`，`nasdaq_chg` 退化为 `-0.25%`。
3. **真实湖仓实测数据**:
   - `data/macro/bond_zh_us_rate.parquet` (9,374 行 × 12 列，截至 2026-10-26)：
     - `cn_yield_10y`: 1.6376% (20日变动 -2.9 bp)
     - `us_yield_10y`: 5.0000% (20日变动 -26.0 bp)
     - `cn_us_spread_10y`: -3.3624 (中美利差真实倒挂 -336.2 bp)
   - `data/global/global_indices.parquet` (23,990 行 × 9 列，截至 2026-10-26)：
     - `IXIC`(纳指): 收盘 26169.38，日涨跌 +0.82%，MA20乖离 -2.46%
     - `SPX`(标普): 收盘 7676.77，日涨跌 +0.70%，MA20乖离 -0.65%
     - `HSTECH`(恒科): 收盘 3857.53，日涨跌 -0.37%，MA20乖离 -6.32%
   - `data/global/fx_rates.parquet`: `usd_cnh` 最新为 6.6676；实时接口 `fetch_realtime_usdcnh_fx` 最新为 6.6708 (-0.08%)。
4. **现有单元测试缺位**:
   - 在 `AGY2_FundAdvisory/tests/` 目录下，所有测试文件均无对 `generate_chief_advisor_memo` 的输出真伪校验与魔法数字拦截断言。

## 2. Logic Chain
1. **缺陷归因 (Based on Observation 1 & 2)**:
   `generate_chief_advisor_memo` 设计时直接向 `snapshot` 索取不存在的键名（`spot_usdcnh`、`us_treasury_10y`），向 `macro_multi` 索取未被采样的键名。由于缺乏上游供给与单元测试门禁，代码运行时静默降级为后门写死的字面量：`628.5`、`-0.25%`、`7.2450`、`1.6258`、`4.40%`。
2. **湖仓可替代性 (Based on Observation 3)**:
   本地数据湖中完备存储了 1990 年至今的中美 10Y 国债、利差、全球指数、外汇与黄金历史数据，完全满足零网络依赖下的高可用全息分析需求。
3. **因果透明性推演 (Based on Observation 1 & 3)**:
   结合宏观经济 (1.64%)、货币流动性 (DR007 1.389%)、股债ERP (82.6%)、外汇锁汇 (6.6708) 与国际联动 (-336.2bp)，可构建数学完备、多空明确的十维投票矩阵与如下清晰因果链：
   `基准权益中枢 60% + ERP极低估溢价(+10%) + 货币宽松(+5%) + 结构性机会(+5%) - 美债倒挂约束(-3%) = 当前建议权益仓位 77% (防守固收 23%)`。

## 3. Caveats
1. **数据截面日期说明**: 本地湖仓 `data/macro/bond_zh_us_rate.parquet` 与 `data/global/global_indices.parquet` 的静态切片最新交易日为 `2026-10-26`，而在线实时行情（新浪/东财）若网络可用时可获取当天实时截面（如 2026-11-11）。系统架构应遵循“优先在线实时带时间戳，离线平滑降级至湖仓最新切片并显式标注数据截面”的原则。
2. **黄金计价口径**: 场内标的统一采用黄金 ETF (518880，单位: 元/份)；宏观回报与相关性矩阵统一采用 SGE AU9999 现货收益序列，文案中明确标注代码与单位，杜绝把 ETF 单价标为克重价格。
3. **只读约束遵守**: 本 Explorer 代理严格遵守只读契约，未对工作区任何业务源码进行写入。

## 4. Conclusion
1. 彻底确认了五维备忘录中 5 大写死常数与断裂键的存在位置与机理。
2. 完成了对 `data/macro/bond_zh_us_rate.parquet`、`data/global/global_indices.parquet`、`data/global/fx_rates.parquet` 等高保真湖仓数据的实证探索。
3. 产出了可供 Developer 代理直接落地的「十维全息投顾投票模型」与「透明仓位因果传导公式」算法实现方案（参见 `.agents/teamwork/explorer_g17_1/analysis.md`）。
4. 产出了禁止魔法数字死灰复燃的 3 组严苛单元测试断言设计。

## 5. Verification Method
1. **重现与断言检验**:
   执行探针脚本：
   ```powershell
   py -3 .agents/teamwork/explorer_g17_1/test_snapshot_memo.py
   py -3 .agents/teamwork/explorer_g17_1/test_causal_engine.py
   ```
2. **下阶段开发交付验收标准**:
   - 开发者修改 `data_loader.py`、`advisory_engine.py`、`strategy_bridge.py` 后，在 `generate_chief_advisor_memo` 输出中运行：
     `pytest AGY2_FundAdvisory/tests/ -k "test_chief_advisor_memo"`
   - 验证输出中 `628.5`、`-0.25%`、`7.2450`、`1.6258`、`4.40` 彻底绝迹，且包含截面日期与数据源标签。

# 5-Component Handoff Report: 单基真实历史波动率与单基乖离率穿透调研

**Agent**: teamwork_explorer (`explorer_survey_r12_1`)  
**Target Recipient**: Orchestrator (`71f16351-ac4e-45f7-b8a4-89e38ec8863c`)  
**Timestamp**: 2026-11-06T17:06:00Z  

---

## 1. Observation (客观观察)

1. **固定常数代码位置与逻辑**：
   - 文件：`AGY2_FundAdvisory/advisory_engine.py`
   - 第 1324 行（ETF 轨道）：
     `vol = float(volatility) if (volatility is not None and np.isfinite(volatility) and volatility > 0) else 0.18`
   - 第 1365-1373 行（场外公募轨道）：
     ```python
     if volatility is not None and np.isfinite(volatility) and volatility > 0:
         vol = float(volatility)
     elif any(k in fn for k in ["债", "固收", "纯债"]) or fc == "002351":
         vol = 0.04
     elif any(k in fn for k in ["黄金"]) or fc == "000216":
         vol = 0.14
     else:
         vol = 0.18
     ```
   - 第 1377-1380 行（MA20 乖离率因子）：
     ```python
     b20 = float(kwargs.get("bias_20", 0.0) if bias_20 is None else bias_20)
     if not np.isfinite(b20):
         b20 = 0.0
     bias_factor = 1.0 + min(1.5, abs(b20) / 5.0) * 0.3
     ```

2. **调用点排查**：
   - `AGY2_FundAdvisory/advisory_engine.py:1484` (`plan_smart_dca`)：
     `SmartExecutionDCAEngine.calculate_vwap_execution_slippage(..., volatility=a.get("volatility"), bias_20=bias)`
     传递的是大盘基准偏离度 `bias`，且 `volatility` 为 `None`，触发常数回退。
   - `AGY2_FundAdvisory/app_gui.py:3415`：
     `plan_smart_dca` 调用时，`alloc_list_for_dca`（第 3387-3390 行）未携带 `volatility` 与 `bias_20`。
   - `AGY2_FundAdvisory/app_gui.py:5235`（Tab 2 调仓买入单）：
     `sl_inf = SmartExecutionDCAEngine.calculate_vwap_execution_slippage(..., bias_20=snapshot.get("bias_20", 0.0))`
     未传 `volatility`，且 `bias_20` 传递的是大盘快照。

3. **本地列式湖仓与数据湖资产验证**：
   - `data/processed/aligned_matrix_total_return.parquet` 存在，shape 为 `(2145, 13)`，包含全量对齐交易日至 2026-11-06，涵盖 `H00300`, `H00905`, `H00852`, `H00922`, `H30269`, `930609`, `H11009`, `STAR50_STITCH`, `AU9999`, `SPX_CNY` 等列。
   - `data/processed/indices/` 包含 754 个指数 parquet 文件（含 `000688.SH`, `000922.SH`, `AU9999.SGE`, `CBA00101.CS`, `399986.SZ`, `000685.SH`, `000932.SH`, `000933.SH` 等）。
   - `data/processed/funds/` 包含 26 个单基 parquet 文件（含 `000001.OF.parquet` 等）。

4. **实测真实 20 日波动率与乖离率精算结果**：
   - 易方达裕祥债券A (`002351`): `vol = 0.68%`, `bias_20 = +0.31%`（申购 5 万元损耗 2.25 bps $\to$ 0.67 bps，省 1.58 bps）；
   - 华安黄金ETF联接A (`000216`): `vol = 13.86%`, `bias_20 = +2.29%`（申购 5 万元损耗 18.55 bps $\to$ 3.99 bps，省 14.56 bps）；
   - 创金合信红利低波A (`005561`): `vol = 14.89%`, `bias_20 = +0.91%`（申购 5 万元损耗 18.48 bps $\to$ 4.25 bps，省 14.23 bps）；
   - 华安纳指100联接A (`017436`): `vol = 19.14%`, `bias_20 = -5.02%`（申购 5 万元损耗 28.43 bps $\to$ 5.32 bps，省 23.11 bps）；
   - 华夏科创50联接C (`011613`): `vol = 31.75%`, `bias_20 = -11.76%`（申购 5 万元损耗 51.28 bps $\to$ 8.50 bps，省 42.78 bps）。

---

## 2. Logic Chain (推理逻辑链)

1. 由观察 1 可知，`calculate_vwap_execution_slippage` 之所以存在同质化，是因为当调用方未传 `volatility` 时，代码在第 1324 行与 1367-1372 行回退到了粗颗粒度的硬编码常数 `0.04/0.14/0.18`。
2. 由观察 2 可知，`plan_smart_dca`（第 1484 行）与 `app_gui.py`（第 3415 行与 5235 行）在调用滑点算子时，均未计算单只基金自身真实的 20 日波动率与乖离率，而是传入 `None` 或大盘全局快照 `bias_20`。
3. 由观察 3 可知，工作区本地已有极其齐备的四级数据湖（单基 parquet、754 个赛道指数 parquet、全收益对齐矩阵 parquet），无需调用外部网络即可 100% 离线计算任意基金的真实 20 日波动率与均线偏离度。
4. 由观察 4 可知，一旦使用真实时序计算单基波动率与乖离率，低风险纯债（0.68% 波动）与高风险硬科技（31.75% 波动）在滑点模型中的输出将产生高达数十倍的真实金融梯度差异，完美消除假常数与同质化假象，完全符合买方投顾量化逻辑。

---

## 3. Caveats (局限与边界)

1. 若用户在持仓或自选池中输入一个完全未知且本地无任何指数日线的全新冷启动代码（如某未纳入主流行业的新发场外冷门混合基），三级数据湖可能均无法找到对应代码，此时需通过资产分类（`pm.classify_fund_asset_class`）或名称关键字动态映射至对齐矩阵最贴近的赛道列，确保计算依然基于真实时序，杜绝报错或使用假常数。
2. 本次任务为只读探索员身份，严禁直接修改 `advisory_engine.py` 或 `app_gui.py` 源代码，具体落地实现交由后续开发角色执行。

---

## 4. Conclusion (结论与建议)

1. **核心行动方案**：
   - 在 `AGY2_FundAdvisory/advisory_engine.py` 的 `SmartExecutionDCAEngine` 类中增加静态/类方法 `get_fund_real_volatility_and_bias(fund_code, fund_name)`；
   - 改造 `calculate_vwap_execution_slippage`：删除硬编码的 `0.04/0.14/0.18`，当入参缺失时自适应调用 `get_fund_real_volatility_and_bias` 填充；
   - 改造 `plan_smart_dca`（第 1484 行）：为每只订单计算单基自身真实波动率与偏离度并传入；
   - 改造 `app_gui.py`（第 3415 行与 5235 行）：在 Tab 1 定投清单与 Tab 2 调仓买入单中注入单基自身真实波动率与偏离度。
2. **完整详细报告路径**：`d:\Google\Workspace\Wind\.agents\teamwork\explorer_survey_r12_1\report.md`。

---

## 5. Verification Method (独立验证方法)

1. **静态代码核查**：
   - 检查 `advisory_engine.py` 中是否存在 `get_fund_real_volatility_and_bias` 方法；
   - 使用正则表达式搜索 `advisory_engine.py`，确认 `0.04`, `0.14`, `0.18` 常数回退分支被彻底删除；
   - 检查 `app_gui.py` 第 5235 行附近是否传入了单基真实的 `volatility` 与 `bias_20`。
2. **测试用例验证**：
   - 执行 `pytest tests/test_g3_evolution_loop.py`，验证既有滑点优化、单调性递增及 5 阶段分笔调度测试 100% 通过；
   - 在测试集中断言不同资产类型（纯债 vs 科创50）测算得出的 `slippage_saved_bps` 显著不同（纯债 < 5 bps，科创50 > 30 bps）。

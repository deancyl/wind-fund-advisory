# Handoff Report — Explorer M3-2 (Tab 2 调仓处方与 estimate_rebalance_impact 联动)

## 1. Observation (观测事实与代码取证)

1. **`strategy_bridge.py` 现状与位置**：
   - 文件路径：`D:\Google\Workspace\Wind\AGY2_FundAdvisory\strategy_bridge.py`；
   - 函数位置：第 6140 至 6235 行 `estimate_rebalance_impact(cls, current_holdings, target_weights_funds, total_equity, rebalance_items)`；
   - 算法逻辑：
     - 利用 `code_to_col` 映射矩阵列名，取近 250 天历史数据计算调仓前后年化波动率（`vol_before`, `vol_after`, `vol_diff`）；
     - 利用 `dividend_yield_map`（红利低波 5.5%、中证红利 5.2%、纯债 2.6% 等）加权计算组合股息率变化（`div_before`, `div_after`, `div_diff`）；
     - 累加 `rebalance_items` 的 `est_fee` 计算总手续费与回本天数（`total_fee`, `payback_days`, `payback_desc`）；
   - 现存脱节：全局检索发现 `estimate_rebalance_impact` 仅在单测中被调用，在 `app_gui.py` 生产 UI 中**完全未被调用**（调用次数为 0）；且返回值未直接暴露用户关心的“29->6只”、“盘活资金 ¥442.70~¥962.57”等实战核心指标。

2. **`app_gui.py` Tab 2 现状与位置**：
   - 文件路径：`D:\Google\Workspace\Wind\AGY2_FundAdvisory\app_gui.py`；
   - 结构分工：第 5360~5370 行实装了主模式与工具坞模式的双视图解耦（规则 28）：
     - `is_t2_main_mode = True` 时为主流程（持仓指标卡、`st.data_editor` 表格、诊断裁决与执行单合流）；
   - 29 基处方面板位于第 6116 至 6180 行（`if active_lid == "combat_29_funds":`）：
     - 包含 ① 19只碎片清扫、② 三大出血点手术、③ 2018-2026全周期对照；
     - **现存缺陷一**：该处方面板目前为纯静态 HTML 文本，**缺少一键触发执行按钮**（对比第 6107 行通用碎片卡拥有 `btn_sweep_tail_cleaner`）；
     - **现存缺陷二**：第 ③ 项使用的是硬编码文字（29只->7只全天候），未与 `estimate_rebalance_impact` 联动，未列出 29->6只、¥442.70~¥962.57、票息垫提升与回本天数缩短四大维度量化对比。

3. **29 基真实存量账本数据核验**：
   - Python 实测 `MultiLedgerManager.get_instance().get_pm('combat_29_funds')`：
     - 总资产市值：¥26,615.10，投入本金 ¥27,371.65，可用现金 ¥1,000.00；
     - 全部 29 只标的持有天数均为 400 天（>365天），A类满期免赎，C类满30天免赎，赎回费严格为 **¥0.00**；
     - 19 只免赎碎片尾仓（单只 < ¥200 且非 005827）：合计市值 **¥442.70**；
     - 冗余/微型腰部仓：`000217 华安黄金C`（¥395.73）+ `005827 易方达蓝筹`（¥124.14）合计 **¥519.87**；
     - 两者合计：$$442.70 + 519.87 = 962.57 \text{ 元}$$，分厘不差精确验证了 **¥442.70 ~ ¥962.57** 的来源！
     - 三大核心亏损源：#5 `100032` (浮亏 -¥332.54), #6 `011613` (浮亏 -¥428.48), #8 `161725` (浮亏 -¥175.76)，合计浮亏 -¥936.78。

---

## 2. Logic Chain (推理链条)

1. **由需求契约与 29 基数据特征**：
   用户持有 29 只基金，其中 19 只是历史红包/体验金零头（共 ¥442.70），严重分散看盘精力；且 011613 虽已满 400 天但仍被每年计提 0.40% C 类销售服务费，161725 单一行业深套 -25.1%。
2. **由三步手术处方设计**：
   - 步骤一：全额赎回 19 只碎片尾仓（回收 ¥442.70 零赎回费，增持 002351 纯债或核心底仓）；
   - 步骤二：实施三大出血点精准手术（011613 华夏同公司零在途免赎转 011612 A 类彻底省去 0.40% 抽血；161725 均线反抽减亏平移至宽基/底仓；100032 与 005561 形成高股息攻守协同）；
   - 步骤三：重构为 6 只纯 A 类低费率全天候核心压舱石（005561, 100032, 110020, 002351, 011612, 000216）。
3. **由 `estimate_rebalance_impact` 的算法扩展性**：
   在现有测算基础上，补充持仓只数（29->6）、盘活资金区间（¥442.70~¥962.57）、预计缩短回本天数（~210天）等输出字段，完全保持既有键值兼容；并封装 `get_combat_29_rebalance_prescription` 便捷入口。
4. **由 Tab 2 交互闭环与规则约束**：
   在 Tab 2 主流程中为 29 基处方面板新增主操作按钮 `[🧹 执行三步瘦身重构模拟（清扫 19 只免赎尾仓 + 置换深套出血点）]`，点击后通过 `st.session_state` 自动联动 `sweep_tail_and_c_class` 与 `tab2_c_replace = "011613"`，触发调仓引擎直接生成对应的执行单；界面展示 4 维量化指标对比网格，全量经由 `safe_markdown_html` 渲染，满足规则 27 与 28。

---

## 3. Caveats (潜在风险与边界条件)

1. **测试隔离约束**：
   由于 `tests/test_multi_ledger_manager.py` 中的 `test_get_all_ledgers_summary` 会断言 `len(res["ledgers"]) == 1`，`MultiLedgerManager` 幂等挂载 `combat_29_funds` 时必须受 `self.root == WORKSPACE_ROOT` 隔离保护（此部分由 M3 Item 1 负责）。
2. **Tab 1 / Tab 3 权重字典兼容**：
   `estimate_rebalance_impact` 必须保持对任意自定义权重字典（不仅限于 6 基，包括 4 基、7 基或单基）的普适兼容性，不能因为针对 29 基优化而写死假常数。
3. **只读文件红线**：
   四个只读裁判文件（`judge_engine.py`、`holdout_vault.py`、`AGENT_SPEC.md`、`tests/test_infra.py`）及 `DataLoader.simulate_execution` 默认签名必须坚守 0 修改。

---

## 4. Conclusion (勘查结论与实施指导)

1. **技术可行性 100% 确认**：
   `strategy_bridge.py` 内部模型与 `portfolio_manager.py` 的场景引擎（`sweep_tail_and_c_class`、同公司免赎转换）已具备底层能力，仅需打通 `estimate_rebalance_impact` 的输出扩充与 `app_gui.py` Tab 2 的一键按钮与指标网格。
2. **实施落地收口于两个文件**：
   - 文件 1：`AGY2_FundAdvisory/strategy_bridge.py`（扩充 `estimate_rebalance_impact` 字段并新增 `get_combat_29_rebalance_prescription`）；
   - 文件 2：`AGY2_FundAdvisory/app_gui.py`（升级 Tab 2 29 基处方面板为 4 维指标网格，新增一键重构模拟按钮并绑定 `st.session_state` 状态机）。

---

## 5. Verification Method (独立验证方法与复核指令)

在后续 Worker 实施完成后，可通过以下步骤执行确定性验收：

1. **算法与指标单测**：
   ```powershell
   $env:PYTHONPATH='AGY2_FundAdvisory'
   pytest AGY2_FundAdvisory/tests/test_realtime_and_upgrades.py -k test_estimate_rebalance_impact -v
   ```
   断言既有单测 100% 绿灯。
2. **新增 29 基处方专项单测**：
   运行新编写的 `tests/test_m3_item2_rebalance_impact.py`，断言：
   - `impact["fund_count_before"] == 29`
   - `impact["fund_count_after"] == 6`
   - `impact["revitalized_cash_min"] == 442.70`
   - `impact["revitalized_cash_max"] == 962.57`
   - `impact["total_fee"] == 0.0`
   - `impact["payback_days"] == 0`
3. **端到端 AppTest 渲染核验**：
   ```powershell
   $env:PYTHONPATH='AGY2_FundAdvisory'
   pytest AGY2_FundAdvisory/tests/test_e2e_gui_render.py -v
   ```
   断言 `app_gui.py` 在 Tab 2 渲染无异常，且 29 基处方按钮在激活 `combat_29_funds` 时正确渲染。
4. **四裁判文件哈希防篡改校验**：
   ```powershell
   Get-FileHash AGY2_FundAdvisory/judge_engine.py, AGY2_FundAdvisory/holdout_vault.py, AGY2_FundAdvisory/AGENT_SPEC.md, AGY2_FundAdvisory/tests/test_infra.py
   ```
   确认哈希一致，无任何污染。

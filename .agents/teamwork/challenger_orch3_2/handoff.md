# Handoff Report — Challenger-2 (De-Mining & Classification)

## 1. Observation
1. **裁判基建文件完整性**:
   - `git status -s judge_engine.py holdout_vault.py AGENT_SPEC.md tests/test_infra.py` 输出完全为空。4 个裁判基建文件 100% 保持只读未改且非空。
2. **边缘金融机构豁免与万科A暴雷识别**:
   - 包含 19 只边缘金融机构（渝农商行、华林证券、中邮人寿保险、陕国投信托、南华期货等）的测试用例均通过 `screen_fund_look_through_risk` 自动标记为 `double_high_risk = False`，状态 `金融业豁免（正常）`，无股票代码白名单。
   - 万科A（000002.SZ）坚决判定为 `double_high_risk = True`，`double_high_status = "存贷双高预警"`，扣除存贷双高 40 分 + 负现金流 10 分，得分 50 分，评级 `Danger 🔴 预警`。
3. **真实生产组合中芯国际误扣 40 分 (Bug 1)**:
   - 执行 `pm.screen_fund_look_through_risk("011612")`（华夏科创50 ETF联接A），其第一大重仓股 `中芯国际` (688981.SH) 判定结果如下：
     ```python
     中芯国际 double_high_risk: True status: 存贷双高预警 score: 40.0
     ```
   - 在 `portfolio_manager.py` 第 3967 行，代码为：
     ```python
     cfo_healthy = (cfo_val is not None and cfo_val > 0)
     ```
   - 湖仓 `v_stock_financials` 视图中仅有 7 条记录，不含 `688981.SH`，故 `cfo_val` 为 `None`；而 `v_financial_risk_screen` 中 `fcf_billion = 65.47 > 0`（健康正向现金流），却未被联动。
4. **统一资产分类器 501029 分类撞车 (Bug 2)**:
   - 执行 `pm.classify_fund_asset_class("501029", "华宝标普中国A股红利机会")`，实际返回值：
     ```python
     '美股海外对冲'  # 期望为 'A股红利高股息'
     ```
   - 在 `portfolio_manager.py` 第 3531-3536 行，先验规则命中关键词 `"标普"`，先于第 3543 行的 `"红利"` 匹配，且未排除 `"A股"` 或 `"中国A股"`，导致纯正的 A 股红利基金被误判为海外美股对冲。
5. **未缓存的高频 DuckDB 连接引发性能衰减 (Bug 3)**:
   - 执行 1,000 次分类解析耗时 `19,472.3ms` (~19.5 秒)。在 `portfolio_manager.py` 第 3496 行，对非核心池代码每次都新建 `duckdb.connect(str(db_p), read_only=True)`，造成沉重的文件 open/lock 损耗。

---

## 2. Logic Chain
1. 基于 Observation 1：4 个裁判基建文件保持绝对未修改，符合工程物理安全红线。
2. 基于 Observation 2：金融机构业态识别与真实造假企业（万科A）高危红灯判定机制在理论与通用规则上已脱离硬编码，具备健壮性。
3. 基于 Observation 3：Agent-2 在其交接文档中承诺 `(ocf_per_share > 0 or fcf_billion > 0)` 证明重资产企业造血活力，但实现代码 `portfolio_manager.py:3967` 遗漏了 `or (fcf_val > 0)`。由于生产数据库中 `v_stock_financials` 未预录中芯国际，导致核心硬科技晶圆标的（中芯国际，FCF = 65.47 亿）在实盘组合穿透中被错误认定为存贷双高造假，直接拖累华夏科创50基金（011612、011613）及银华集成电路（013841）的评级与表现。
4. 基于 Observation 4：统一分类器在规则顺序与关键词设计上存在盲区，将跟踪标普指数编制公司但底层 100% 投资于 A 股的红利高股息基金（501029）错误分类为美股海外资产，违背全组合资产配置底层穿透原则。
5. 基于 Observation 5：由于分类解析缺乏进程内缓存，批量归类产生显著 I/O 停顿，影响推演反馈与组合计算体验。
6. 综合上述步骤，尽管金融业态识别与裁判文件合规，但两项关键业务逻辑缺陷直接影响生产环境表现，因此裁决必须为 **REQUEST_CHANGES**。

---

## 3. Caveats
- 模拟测试已覆盖各类边缘金融机构、电力能源重资产及造假企业；
- 若湖仓补充录入 `688981.SH` 至 `v_stock_financials`，现有代码中芯国际亦可判定正常，但通用排雷引擎必须具备自身健壮性（即联动 `fcf_val > 0`），绝不能因单一底层子视图缺失某股即导致硬科技被当场误杀。

---

## 4. Conclusion
- **实证裁决**: **REQUEST_CHANGES** ❌
- **整改指引 (给 Agent-2)**:
  1. `portfolio_manager.py` 第 3967 行：修改为 `cfo_healthy = (cfo_val is not None and cfo_val > 0) or (fcf_val > 0)`。
  2. `portfolio_manager.py` 第 3531 行：在 `is_overseas_name` 判定前加入排除逻辑，若同时包含 `"A股"`/`"中国A股"` 与 `"红利"`/`"高股息"`，则不认定为海外美股。
  3. `portfolio_manager.py` 第 3460 行：增加针对 `(fund_code, fund_name)` 的简单字典内存缓存，消除重复 DuckDB 文件连接。

---

## 5. Verification Method
- **运行 Challenger-2 实证对抗套件**:
  ```powershell
  python -m pytest AGY2_FundAdvisory/tests/test_adversarial_orch3_challenger2.py -o pythonpath=AGY2_FundAdvisory -v
  ```
- **验证判定条件**:
  - `test_real_world_smic_de_mining_empirical_audit` 必须 PASSED；
  - `test_sp_china_a_dividend_edge_case` 必须 PASSED；
  - `test_batch_classification_throughput_cached` 必须 PASSED (耗时 < 100ms)；
  - 全套件 13 项对抗用例 100% 全部 PASSED。

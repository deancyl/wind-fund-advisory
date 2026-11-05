# Handoff Report — Requirement R2 Survey
## 数据同源单源同真与双翼看板升级（全景机会雷达 + 六维主动风险预警哨）

- **Agent Name**: Explorer Survey R8-2
- **Agent Directory**: `d:\Google\Workspace\Wind\.agents\teamwork\explorer_survey_r8_2`
- **Parent Conversation ID**: `3ef18151-e1aa-4330-83a1-353aa7bcc35e`
- **Handoff Type**: Hard Handoff (Investigation & Survey Complete)
- **Primary Artifact**: `d:\Google\Workspace\Wind\.agents\teamwork\explorer_survey_r8_2\analysis.md`

---

### 1. Observation (直接观察事实与证据)

1. **`RADAR_SECTOR_CATALOG` 静态硬编码现状**:
   - 见 `AGY2_FundAdvisory/advisory_engine.py:21-176`，14 个赛道均硬编码了 `base_val_pct`、`er_20`、`bias_20`、`slope_20` 与 `crowding_score`。
   - 例：`csi_dividend`（中证红利 000922）硬编码 `base_val_pct: 25.0`，而 `data/cache/index_valuation.json:82-90` 中真实分位数为 `93.2`。
2. **行情矩阵探测路径失效**:
   - 见 `AGY2_FundAdvisory/advisory_engine.py:209-214`，探测路径为 `data/aligned_matrix_total_return.parquet`。
   - 终端命令执行 `py -3 -c "import os; print(os.path.exists('data/aligned_matrix_total_return.parquet'))"` 输出 `False`。真实文件位于 `data/processed/aligned_matrix_total_return.parquet`（大小 218 KB，2142 行，13 列）。导致动态计算异常被吞，全部降级使用静态常量。
3. **侧边栏走廊与双翼看板估值分位冲突 (图1 vs 图2)**:
   - 侧边栏走廊 (`app_gui.py:1351-1375`) 调用 `fetch_or_calc_index_valuations()`，图 1 显示中证红利为 `PE 9.0 (93%过热)`；
   - 双翼看板雷达 (`app_gui.py:1569`) 读取 `OpportunityRadarEngine`，图 2 显示红利低波 28%、医药医疗 16%，若读取中证红利则为静态 25%（低估），两端数据完全脱节矛盾。
4. **`ActiveRiskSentry` 现有缺陷与特定持仓比对**:
   - 见 `AGY2_FundAdvisory/advisory_engine.py:360-528`，仅实现了 `<=3天`、`7~9天`、`30~35天`、迷你基和攻防线；
   - 持仓账本 `portfolio_ledger.json`:
     - `011612` (华夏科创50联接A): 持有 3 天（命中 <=3天 锁仓）；
     - `011613` (华夏科创50C): 持有 28 天（现行代码不触发任何黄牌保护，漏检 2 天后免赎关键窗口）；
     - `013841` (银华集成电路C): 浮亏 -16.19%（现行代码完全无深套诊断逻辑）；
     - 预警卡片 (`app_gui.py:1636-1651`) 仅为静态 HTML 纯文本，无交互式动作按钮，无法一键跳转 Tab 2 锁定或生成阶梯止盈单。
5. **裁判文件与现有测试运行**:
   - 执行 `py -3 scripts/verify_referee_hashes.py` 输出：`ALL 4 READONLY REFEREE FILES ARE INTACT AND UNMODIFIED`；
   - 执行 `py -3 -m pytest AGY2_FundAdvisory/tests/test_m3_advisory_modules.py` 输出：`11 passed in 1.45s`；
   - 执行 `py -3 -m pytest AGY2_FundAdvisory/tests/test_sidebar_remodel_and_bugfixes.py` 输出：`6 passed in 8.64s`。

---

### 2. Logic Chain (推导逻辑链条)

- **推导 1 (数据同源)**: 由观察 1 与观察 2 可知，静态常量的存在以及矩阵路径失效是造成双翼看板与侧边栏走廊数据矛盾的根本原因。因此，必须将矩阵路径纠正为 `data/processed/aligned_matrix_total_return.parquet`，对缺失赛道引入 `data/processed/indices/*.parquet` 兜底，并彻底废弃 `RADAR_SECTOR_CATALOG` 中的静态常量，使雷达估值 100% 统一调取 `IndexValuationEngine.fetch_or_calc_index_valuations`，从根源消除两套分位数。
- **推导 2 (全景雷达与脉搏晨报)**: 观察 3 表明用户目前仅能看到 Top 3 卡片，无法全局对比 14 赛道量化温度；通过在 Top 3 下方增加 `st.expander` 承载 14 赛道量化温度计总表（赛道名称、估值分位、趋势信噪比、20日乖离率、拥挤度评分、综合得分、状态标签、优选基金），并在双翼看板顶部增加自动串联“两市成交额 + ERP分位 + 领涨主线 + 低估击球区”的 <=80 字晨报，可完整满足左翼升级需求。
- **推导 3 (六维风险哨与交互闭环)**: 由观察 4 可知，实盘核心标的 `011613`（28天临免赎期）与 `013841`（-16.19% 深套）在现行四维巡检下存在严重防御盲区。必须将巡检拓展为完整的 6 大维度（未满7天红牌、临免赎期倒计时黄牌、C类满30天置换、阶梯止盈与深套诊断、赛道集中度与重仓重叠、迷你基清盘与大盘攻防线），并在卡片下方注入交互按钮，通过 Session State 联动 Tab 2 调仓（自动下界锁仓与生成阶梯止盈减仓单）。

---

### 3. Caveats (局限性与假设)

1. **赛道行情矩阵补全方式**: `aligned_matrix_total_return.parquet` 中未包含医药（000933）、白酒（000932）、银行（399986）的收盘序列；调查确认这些指数存在于 `data/processed/indices/` 目录中，实施时需通过 `pd.read_parquet` 读取收盘价补全 20 日 ER、Bias 与 Slope。
2. **测试文本向后兼容**: 现有测试 `test_m3_full_integration_apptest.py` 与 `test_m3_advisory_modules.py` 中包含 `assert "主动风险预警哨"`、`assert "≤3天"`、`assert "已满 7 天"`、`assert "C类份额已满 30 天"`、`assert "超买"`、`assert "清盘警戒线"` 的严格断言。六维风险哨的文案设计必须完全包容上述子字符串。
3. **只读约束遵循**: 本次调查严格遵守 Explorer 只读铁律，未对系统任何业务代码与裁判文件做就地修改。

---

### 4. Conclusion (结论与实施建议)

1. **调查结论**: Requirement R2 的技术瓶颈与断裂点已 100% 定位清楚，技术改造方案完整自洽，完全可行。
2. **交付工件**: 详细调查与架构设计已固化于 `d:\Google\Workspace\Wind\.agents\teamwork\explorer_survey_r8_2\analysis.md`。
3. **实施行动建议**: 协调调度实施代理人（Implementer）依次执行：
   - 步骤 1：重构 `advisory_engine.py` 的 `RADAR_SECTOR_CATALOG` 与动态精算引擎；
   - 步骤 2：实装 `ActiveRiskSentry` 六维风控检测逻辑；
   - 步骤 3：升级 `app_gui.py` 双翼看板（脉搏晨报 + 14 赛道温度计总表 + 快捷交互按钮）；
   - 步骤 4：通过针对性回归测试（包含 011612、011613、013841 三类风险用例与 AppTest）。

---

### 5. Verification Method (独立验证方法)

后续实施完成后，可通过以下命令进行独立核验：
1. **裁判文件哈希防篡改核验**:
   ```powershell
   py -3 scripts/verify_referee_hashes.py
   ```
2. **投顾模块与侧边栏单元测试回归**:
   ```powershell
   py -3 -m pytest AGY2_FundAdvisory/tests/test_m3_advisory_modules.py
   py -3 -m pytest AGY2_FundAdvisory/tests/test_sidebar_remodel_and_bugfixes.py
   ```
3. **双翼看板与 AppTest 端到端验证**:
   ```powershell
   py -3 -m pytest AGY2_FundAdvisory/tests/test_m3_full_integration_apptest.py
   ```
4. **单源同真数据一致性脚本断言**:
   编写针对性用例，断言 `OpportunityRadarEngine().scan_all_sectors()` 中各赛道 `val_percentile` 与 `data_loader.fetch_or_calc_index_valuations()` 对应指数的 `percentile` 浮点数差值绝对值 `< 1e-4`。

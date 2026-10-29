# 实证对抗性压测分析报告 — Challenger-2 (De-Mining & Classification)

## 0. 压测概述与执行环境
- **测试执行者**: Challenger-2 (Empirical Challenger)
- **被测目标**: `AGY2_FundAdvisory/portfolio_manager.py` (负责人: Agent-2)
- **执行时间**: 2026-10-30T02:30:00Z
- **实证原则**: 独立编写测试生成器与对抗套件（`tests/test_adversarial_orch3_challenger2.py`），严禁轻信 Worker 自述或日志，一切以真实执行输出为唯一依据。
- **裁决结论**: **REQUEST_CHANGES** (发现 2 项重大业务逻辑漏洞 + 1 项性能隐患，详见下文实证分析)。

---

## 1. 四个裁判基建文件完整性审计
按照系统只读红线要求，对以下 4 个核心裁判基建文件进行了物理存在性与 Git 修改状态审计：
1. `judge_engine.py`
2. `holdout_vault.py`
3. `AGENT_SPEC.md`
4. `tests/test_infra.py`

### 实证命令与结果
```powershell
cd AGY2_FundAdvisory; git status -s judge_engine.py holdout_vault.py AGENT_SPEC.md tests/test_infra.py
```
- **输出**: 空（返回码 0），确认 4 个文件完全未被修改、内容完整非空，100% 保持只读与系统基线。

---

## 2. 三层通用基本面财务排雷引擎对抗性实证

### 2.1 边缘金融机构业态识别与豁免（通过 ✅）
- **测试方法**: 构造包含 19 只边缘金融机构的穿透测试组合，涵盖：
  - 农商行：渝农商行 (601077.SH)、常熟农商银行、张家港农商银行、江南农商行、虚构民营商业银行
  - 民营券商/互联网金融：华林证券 (002945.SZ)、东方财富证券 (300059.SZ)、国金证券、虚构民营联合证券
  - 险资/人寿险：中邮人寿保险、安联人寿保险、中意人寿保险、虚构合资人寿保险
  - 信托/期货/小贷：陕国投信托 (000563.SZ)、平安信托、华润信托、南华期货 (603093.SH)、永安期货、东海期货
- **实证结果**:
  - 全部 19 只标的均被正确标记为 `double_high_risk = False`，状态为 `金融业豁免（正常）`，`double_high_exempt = True`。
  - 扣分项中存贷双高扣分为 0 分，无任何 6 位股票代码白名单，完全基于名称关键词与申万行业属性匹配，达成通用豁免目标。

### 2.2 真实造假与暴雷特征企业（万科A）高危红灯（通过 ✅）
- **测试方法**: 输入万科A（000002.SZ，货币资金 900 亿，有息负债 2400 亿，FCF = -120 亿 < 0，CFO < 0）。
- **实证结果**:
  - `double_high_risk = True`，`double_high_status = "存贷双高预警"`，`double_high_exempt = False`。
  - 扣除存贷双高 40.0 分 + 自由现金流为负 10.0 分，个股得分 50.0 分，定级为 `Danger 🔴 预警`。组合整体穿透触发预警。

### 2.3 重资产硬科技晶圆/能源标的现金流校验（发现重大实证缺陷 ❌）
- **测试场景 A（Mock 注入健康 CFO > 0）**:
  - 验证了当 `cfo_healthy = True` 时，硬科技标的（半导体设备、电力能源、光伏）能正确进入 `double_high_status = "重资产正常经营/现金流健康"` 并免除风险扣分。
- **测试场景 B（反向恶化 CFO <= 0）**:
  - 验证了当重资产硬科技企业现金流恶化为负数时，系统不会盲目豁免，坚决亮起存贷双高红灯并扣 40 分。
- **测试场景 C（真实生产组合未 Mock 实证审计 — 核心缺陷暴露 🚨）**:
  - **实证命令**: 运行 `pm.screen_fund_look_through_risk("011612")`（华夏科创50 ETF联接A）、`011613`（联接C）以及 `013841`（银华集成电路混合C）。
  - **直接观察**:
    ```python
    中芯国际 double_high_risk: True status: 存贷双高预警 score: 40.0
    天合光能 double_high_risk: True status: 存贷双高预警 score: 60.0
    中国石化 double_high_risk: True status: 存贷双高预警 score: 60.0
    ```
    国家战略级重资产晶圆龙头【中芯国际】(688981.SH) 被扣除 40 分，评级暴跌为 40 分 (Danger 🔴 预警)！直接导致华夏科创50全系列基金被拖累至 `Watch 🟡 关注`！
  - **根因代码溯源**:
    在 `portfolio_manager.py` 第 3943-3967 行：
    ```python
    # 经营造血现金流 (CFO) 提取
    cfo_val = None
    try:
        # 查询 v_stock_financials
        cfo_df = c_sql.execute("SELECT ocf_per_share FROM v_stock_financials WHERE ...").df()
        if not cfo_df.empty:
            cfo_val = _safe_float(cfo_df.iloc[0]["ocf_per_share"], None)
    except Exception:
        pass
    ...
    cfo_healthy = (cfo_val is not None and cfo_val > 0)
    ```
    1. 湖仓视图 `v_stock_financials` 在实际部署中仅包含 7 只特定个股，根本没有 `688981.SH`（中芯国际）、`688599.SH`（天合光能）、`600028.SH`（中国石化）！因此 `cfo_val` 永远为 `None`。
    2. 与此同时，`fin_data` 中（来自 `v_financial_risk_screen` 与 `toolkit.earnings_forecast`）明明拥有真实健康的自由现金流：
       - 中芯国际 `fcf_billion = 65.47` (> 0)
       - 天合光能 `fcf_billion = 33.82` (> 0)
       - 中国石化 `fcf_billion = 228.48` (> 0)
    3. Agent-2 在其 `handoff.md` 第 21 行明确声称已实现：
       `their cash flow from operations (ocf_per_share > 0 or fcf_billion > 0) proves operational viability.`
       然而实际代码第 3967 行**只写了 `cfo_healthy = (cfo_val is not None and cfo_val > 0)`，漏掉了 `or (fcf_val > 0)`**！
    4. 这一遗漏导致所有不在 `v_stock_financials` 极简视图中的硬科技重资产龙头，在自由现金流充沛健康（几十上百亿）的情况下全部因 `cfo_val is None` 被误判为暴雷造假，扣除 40 分并亮红灯！

---

## 3. 全局统一资产分类解析器对抗性实证

### 3.1 9 大核心标准大类覆盖与同源份额映射（通过 ✅）
- **核心池与扩展池**: `100032` (红利高股息)、`005561` (红利低波)、`002351` (纯债固收)、`000216` (黄金对冲)、`050025` (美股海外对冲)、`011613` (科技成长进攻)、`016634` (中小盘成长)、`001053` (中盘均衡)、`110003` (核心蓝筹) 等预设基金 100% 精准归类。
- **A/C 同源拆单份额**: 验证 `050025` & `001071` (美股海外对冲)、`100032` & `008682` (A股红利高股息)、`005561` & `005562` (A股红利低波)、`011612` & `011613` (科技成长进攻)、`000216` & `000217` (黄金对冲) 归类完全一致。
- **多态调用幂等**: 实例调用 `pm.classify_fund_asset_class`、类调用 `PortfolioManager.classify_fund_asset_class`、模块调用 `classify_fund_asset_class` 输出字节级一致。
- **兜底与废弃资产标签**: 未入围/未知基金（如医药、消费、新能源、999999）全部兜底为 `其他权益资产`，全局代码中不存在已废弃的 `其他存量资产`。

### 3.2 标普中国A股红利机会基金分类撞车（发现实证缺陷 ❌）
- **实证案例**: `501029 华宝标普中国A股红利机会指数A/LOF`（跟踪标普中国A股红利机会指数，实盘为纯正的 A 股银行/煤炭/公用高股息红利基金）。
- **实证输出**:
  ```python
  pm.classify_fund_asset_class("501029", "华宝标普中国A股红利机会")
  # 实际返回: "美股海外对冲"
  # 期望返回: "A股红利高股息"
  ```
- **根因代码溯源**:
  在 `portfolio_manager.py` 第 3531-3544 行：
  ```python
  # 3. 美股海外对冲
  is_qdii_type = (fund_type == "QDII")
  is_overseas_name = any(k in text for k in [
      "标普", "纳斯达克", "美股", "纳指", "海外", "全球", "QDII", ...
  ])
  if is_qdii_type or is_overseas_name:
      return "美股海外对冲"

  # 4. A股红利低波 ...
  # 5. A股红利高股息 ...
  ```
  “标普”作为海外指数先验词排在红利之前，且未做“A股 / 中国A股”排除逻辑。只要基金名带有“标普”，哪怕明确写着“标普中国A股红利”，也会被一票否决提前拦截并错误定性为美股海外对冲。

### 3.3 批量归类高频 DuckDB 连接性能瓶颈（发现实证性能隐患 ⚠️）
- **实证表现**: 批量执行 1,000 次分类解析耗时高达 `19,472ms`（约 19.5 秒，平均每次耗时近 20ms）。
- **根因代码溯源**:
  在 `portfolio_manager.py` 第 3493-3507 行：
  ```python
  if code:
      try:
          import duckdb
          db_p = WORKSPACE_ROOT / "data" / "storage.duckdb"
          if db_p.exists():
              conn = duckdb.connect(str(db_p), read_only=True)
              df_c = conn.execute("SELECT fund_name, fund_type FROM v_fund_catalog WHERE ...").df()
  ```
  对未在核心静态池命中的基金代码，每次调用都会重新触发 `duckdb.connect(read_only=True)` 进行文件系统 open 与只读锁握手，无任何进程内字典缓存（in-memory LRU cache），导致批量穿透组合时出现严重 I/O 延迟。

---

## 4. 实证测试执行汇总 (Summary of Test Execution)

执行命令：
```powershell
python -m pytest AGY2_FundAdvisory/tests/test_adversarial_orch3_challenger2.py -o pythonpath=AGY2_FundAdvisory -v
```

| 测试用例 | 结果 | 发现与判定 |
|---------|------|-----------|
| `test_referee_infrastructure_files_integrity` | **PASSED** | 4 个裁判基建文件 100% 保持只读且完整 |
| `test_layer1_edge_financial_institutions_exemption` | **PASSED** | 农商行、民营券商、合资险资、信托无需白名单自动豁免存贷双高 |
| `test_layer1_shenwan_financial_industry_by_code` | **PASSED** | 申万金融行业（银行/证券/保险Ⅱ）通过行业字段自动豁免 |
| `test_layer2_heavy_asset_strategic_tech_healthy_cfo` | **PASSED** | 在 CFO > 0 时正确判定为重资产正常经营并豁免 |
| `test_layer2_heavy_asset_tech_deteriorated_cfo_gets_penalized` | **PASSED** | 在 CFO <= 0 恶化时坚决判定存贷双高预警并扣 40 分 |
| `test_layer3_true_financial_fraud_vanke_a_trigger_danger` | **PASSED** | 万科A 坚决识别存贷双高+负现金流，扣 50 分定级 Danger 🔴 |
| `test_real_world_smic_de_mining_empirical_audit` | **FAILED** ❌ | **真实生产环境缺陷**: 中芯国际因缺少 ocf_per_share 且未联动 fcf_billion>0，被误扣 40 分 |
| `test_canonical_9_categories_exhaustive` | **PASSED** | 9 大核心标准大类预置标的映射准确 |
| `test_sp_china_a_dividend_edge_case` | **FAILED** ❌ | **分类词库碰撞缺陷**: 501029 华宝标普中国A股红利机会被误判为“美股海外对冲” |
| `test_unclassified_fallback_and_no_deprecated_asset_class` | **PASSED** | 未知基金兜底为“其他权益资产”，无已废弃的“其他存量资产” |
| `test_polymorphic_invocations_consistency` | **PASSED** | 类方法、实例方法、模块级三态调用完全幂等 |
| `test_companion_split_shares_identical_classification` | **PASSED** | A/C 份额同源拆单伴生标的大类归属绝对一致 |
| `test_batch_classification_throughput_cached` | **FAILED** ⚠️ | **I/O 性能隐患**: 批量 1000 次分类因重复 duckdb.connect 耗时 19.5s |

---

## 5. 建议修复方案 (Actionable Recommendations for Agent-2)

1. **修复硬科技自由现金流兜底联动 (`portfolio_manager.py:3967`)**:
   将：
   ```python
   cfo_healthy = (cfo_val is not None and cfo_val > 0)
   ```
   修改为：
   ```python
   cfo_healthy = (cfo_val is not None and cfo_val > 0) or (fcf_val > 0)
   ```
   *作用*: 彻底对齐 Agent-2 在 handoff 中的承诺，当湖仓明细缺少每股经营现金流时，利用自由现金流正数证明造血能力，还中芯国际、天合光能等龙头硬科技以清白。

2. **精细化标普海外匹配规则，防止 A 股红利误杀 (`portfolio_manager.py:3531`)**:
   在 `is_overseas_name` 判定中，增加对 A 股标普指数的排除：
   ```python
   is_china_ashare = any(k in text for k in ["A股", "中国A股"]) and any(k in text for k in ["红利", "高股息"])
   is_overseas_name = (not is_china_ashare) and any(k in text for k in [
       "标普", "纳斯达克", "美股", "纳指", "海外", "全球", "QDII",
       "德国", "日经", "法兰克福", "道琼斯", "恒生", "港股", "互联", "中概", "S&P", "NASDAQ"
   ])
   ```

3. **增加分类解析进程内内存缓存 (`portfolio_manager.py:3460`)**:
   在 `PortfolioManager` 类初始化或函数入口加入 `self._asset_class_cache: Dict[str, str]`，命中直接返回，避免无谓的高频 DuckDB 文件连接开销。

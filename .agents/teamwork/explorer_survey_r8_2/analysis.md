# Requirement R2 深度调查与技术方案分析报告
## 数据同源单源同真与双翼看板升级（全景机会雷达 + 六维主动风险预警哨与一键处置联动）

- **调查负责人**: Explorer Survey R8-2
- **工作区目录**: `d:\Google\Workspace\Wind\.agents\teamwork\explorer_survey_r8_2`
- **调研时间**: 2026-11-05
- **调研范围**: `AGY2_FundAdvisory/advisory_engine.py`, `AGY2_FundAdvisory/data_loader.py`, `AGY2_FundAdvisory/app_gui.py`, `AGY2_FundAdvisory/portfolio_manager.py`, `data/` 本地行情湖仓与持久化缓存

---

## 1. 执行摘要 (Executive Summary)

本报告针对 **Requirement R2**（数据同源单源同真与双翼看板升级）开展深入只读调查。调查确认了当前系统存在的数项关键断裂点并给出了完整的技术解决方案：

1. **估值与动量数据严重割裂**：`advisory_engine.py` 中的 `RADAR_SECTOR_CATALOG` 静态硬编码了 14 大赛道的 `base_val_pct`、`er_20`、`bias_20`、`slope_20` 与 `crowding_score`。例如中证红利（000922）在 `RADAR_SECTOR_CATALOG` 中静态写死估值分位为 `25.0%`（低估），而在 `IndexValuationEngine` 与侧边栏走廊展示中其真实 PE 分位为 `93.2%`（过热）（图1 与图2 真实对比存在 68.2% 的巨大鸿沟）。同时，`advisory_engine.py` 加载本地行情矩阵时尝试读取不存在的路径 `data/aligned_matrix_total_return.parquet`（真实路径为 `data/processed/aligned_matrix_total_return.parquet`），导致动态指标计算静默失败并退化为静态常数。
2. **左翼机会雷达缺少全景视图与脉搏晨报**：现有左翼仅提供 Top 3 机会卡片，用户无法纵览其余 11 个赛道的量化温度；双翼看板顶部缺少自动整合“两市成交额 + ERP 分位 + 领涨主线 + 低估击球区”的精炼晨报（<=80字）。
3. **右翼风险哨仅为四维且缺失交互处置闭环**：现行 `ActiveRiskSentry` 仅实现了 FIFO 批次 <=3天、C类 30~35天、迷你基和攻防线，缺失了未满 7 天（4~6天）红色红牌、C类 23~29天免赎倒计时黄牌（如 011613 持有 28 天未被识别）、个基阶梯止盈与深套诊断（如 013841 浮亏 -16.19% 无法诊断）、以及细分赛道集中度（>35%）和重仓股重叠预警。此外，预警卡片仅纯文本展示，缺失一键跳转 Tab 2 自动锁仓与生成止盈单的快捷操作按钮。

---

## 2. 现状排查与根因深度剖析 (Root Cause Analysis)

### 2.1 `advisory_engine.py` 中 `RADAR_SECTOR_CATALOG` 的静态硬编码现状
在 `AGY2_FundAdvisory/advisory_engine.py` 第 21~176 行，`RADAR_SECTOR_CATALOG` 定义了 14 大赛道映射字典。每个赛道均显式硬编码了 5 个静态假常量字段：
- `base_val_pct`: 基础估值分位数
- `er_20`: 20日考夫曼信噪比
- `bias_20`: 20日均线乖离率
- `slope_20`: 20日动量斜率
- `crowding_score`: 拥挤度安全分

**代码原貌证据 (`advisory_engine.py:21-65`)**:
```python
RADAR_SECTOR_CATALOG: Dict[str, Dict[str, Any]] = {
    "dividend_low_vol": {
        "name": "红利低波", "index_code": "000978", "category": "本土权益防御",
        "default_fund": {"code": "005561", "name": "创金合信红利低波A", "share_class": "A"},
        "base_val_pct": 28.0, "er_20": 0.62, "bias_20": 1.2, "slope_20": 8.5, "crowding_score": 92.0,
    },
    "csi_dividend": {
        "name": "中证红利", "index_code": "000922", "category": "本土权益高股息",
        "default_fund": {"code": "100032", "name": "富国中证红利增强A", "share_class": "A"},
        "base_val_pct": 25.0, "er_20": 0.58, "bias_20": 0.8, "slope_20": 6.2, "crowding_score": 90.0,
    },
    ...
```

### 2.2 本地行情矩阵与 `IndexValuationEngine` 现状与断裂点
在 `OpportunityRadarEngine._calc_dynamic_sector_metrics` (`advisory_engine.py:204-248`) 中：
```python
# 行 209-214:
mat_path = None
for p in ["data/aligned_matrix_total_return.parquet", "AGY2_FundAdvisory/data/aligned_matrix_total_return.parquet"]:
    if os.path.exists(p):
        mat_path = p
        break
```
**断裂点 1：文件路径失效**：
通过本地文件系统检索：
- `data/aligned_matrix_total_return.parquet` 路径返回 `False`；
- 真实对齐矩阵位于 `data/processed/aligned_matrix_total_return.parquet`（大小 218 KB，2142 行，13 列）。
由于探测路径全错，`mat_path` 为 `None`，`_calc_dynamic_sector_metrics` 直接静默返回空字典 `{}`，导致下游 `evaluate_sector` 强制降级使用 `meta.get("er_20")`、`meta.get("bias_20")` 等静态硬编码！

**断裂点 2：矩阵列覆盖度不足 14 赛道**：
`aligned_matrix_total_return.parquet` 仅包含 13 列：
`['date', 'H00300', 'H00905', 'H00852', 'H00922', 'H30269', '930609', 'H11009', 'STAR50_STITCH', 'AU9999', 'SPX_CNY', 'BENCHMARK_30_70', 'BENCHMARK_50_50']`
未直接包含：
- 医药医疗（000933 / 399933）
- 消费白酒（000932 / 399997）
- 银行高股息（399986）
- 恒生科技（HSTECH）
经排查，这些赛道在 `data/processed/indices/`（包含 754 只指数日线）和 `data/global/global_indices.parquet` 中均有完整日线数据，但未在 `advisory_engine.py` 中建立多层级联动解析机制。

**断裂点 3：估值分位引擎 `IndexValuationEngine` 赛道未对齐**：
在 `data_loader.py:218-228` 中，`IndexValuationEngine.fetch_or_calc_index_valuations` 的 `index_defs` 仅定义了 9 只指数（000300, 000905, 000852, 000016, 000922, H30269, 000688, 518880, 513500），未包含其余行业指数，导致其产出的 `index_valuation.json` 覆盖不全。当机会雷达查询医药（000933）或白酒（000932）时，缓存未命中，被迫回退到静态硬编码。

### 2.3 侧边栏与双翼看板估值分位不一致实证比对
通过比对用户上传的实际界面截图：
- **图 1 (侧边栏行情走廊)**：
  中证红利（000922）显示为 `PE 9.0 (93%过热)`，来源于 `corridor_val_map = fetch_or_calc_index_valuations()`，其历史分位为 `93.2%`。
- **图 2 (双翼看板)**：
  红利低波显示估值分位为 `28%`，医药医疗显示为 `16%`；若中证红利进入雷达，雷达读取 `base_val_pct: 25.0%`。
- **结论**：同一个中证红利指数，侧边栏显示 93%（极度高估过热），而雷达静态显示 25%（低估黄金击球区），存在重大系统级逻辑冲突！必须彻底拆除双轨数据源，实现 100% 同源同真。

---

## 3. 数据同源单源同真架构设计 (Single Source of Truth)

### 3.1 废弃静态假字段与重构 `RADAR_SECTOR_CATALOG`
彻底废弃 `RADAR_SECTOR_CATALOG` 中的 `base_val_pct`、`er_20`、`bias_20`、`slope_20`，将其重构为纯元数据结构，定义赛道名称、标准指数代码、资产大类、优选公募基金以及本地数据湖仓的映射标识：

```python
RADAR_SECTOR_CATALOG: Dict[str, Dict[str, Any]] = {
    "dividend_low_vol": {
        "name": "红利低波", "index_code": "000978", "cs_code": "H30269", "matrix_col": "H30269",
        "category": "本土权益防御", "default_fund": {"code": "005561", "name": "创金合信红利低波A", "share_class": "A"}
    },
    "csi_dividend": {
        "name": "中证红利", "index_code": "000922", "cs_code": "H00922", "matrix_col": "H00922",
        "category": "本土权益高股息", "default_fund": {"code": "100032", "name": "富国中证红利增强A", "share_class": "A"}
    },
    "csi_300": {
        "name": "沪深300", "index_code": "000300", "cs_code": "H00300", "matrix_col": "H00300",
        "category": "大盘蓝筹基石", "default_fund": {"code": "110020", "name": "易方达沪深300ETF联接A", "share_class": "A"}
    },
    "csi_500": {
        "name": "中证500", "index_code": "000905", "cs_code": "H00905", "matrix_col": "H00905",
        "category": "中盘成长基石", "default_fund": {"code": "000478", "name": "建信中证500增强A", "share_class": "A"}
    },
    "csi_1000": {
        "name": "中证1000", "index_code": "000852", "cs_code": "H00852", "matrix_col": "H00852",
        "category": "小盘弹性成长", "default_fund": {"code": "004194", "name": "招商中证1000增强A", "share_class": "A"}
    },
    "star_50": {
        "name": "科创50", "index_code": "000688", "cs_code": "000688", "matrix_col": "STAR50_STITCH",
        "category": "硬科技核心宽基", "default_fund": {"code": "011612", "name": "华夏科创50联接A", "share_class": "A"}
    },
    "semiconductor": {
        "name": "半导体芯片", "index_code": "980017", "cs_code": "000685", "matrix_col": "930609",
        "fallback_parquet": "data/processed/indices/000685.SH.parquet",
        "category": "高弹性科技赛道", "default_fund": {"code": "008888", "name": "华夏半导体芯片ETF联接A", "share_class": "A"}
    },
    "pharma_health": {
        "name": "医药医疗", "index_code": "000933", "cs_code": "000933",
        "fallback_parquet": "data/processed/indices/000933.SH.parquet",
        "category": "消费医药超跌赛道", "default_fund": {"code": "161726", "name": "招商国证生物医药A", "share_class": "A"}
    },
    "consumer_liquor": {
        "name": "消费白酒", "index_code": "000932", "cs_code": "000932",
        "fallback_parquet": "data/processed/indices/000932.SH.parquet",
        "category": "传统消费核心", "default_fund": {"code": "161725", "name": "招商中证白酒指数A", "share_class": "A"}
    },
    "banking_dividend": {
        "name": "银行高股息", "index_code": "399986", "cs_code": "399986",
        "fallback_parquet": "data/processed/indices/399986.SZ.parquet",
        "category": "深度低估金融", "default_fund": {"code": "160418", "name": "华安中证银行指数A", "share_class": "A"}
    },
    "domestic_gold": {
        "name": "国内黄金", "index_code": "518880", "matrix_col": "AU9999",
        "category": "大宗对冲压舱", "default_fund": {"code": "000216", "name": "华安易富黄金ETF联接A", "share_class": "A"}
    },
    "us_sp500_nasdaq": {
        "name": "美股标普纳指", "index_code": "SPX", "matrix_col": "SPX_CNY",
        "category": "全球配置QDII", "default_fund": {"code": "050025", "name": "博时标普500ETF联接A", "share_class": "A"}
    },
    "hstech": {
        "name": "恒生科技", "index_code": "HSTECH",
        "fallback_parquet": "data/global/global_indices.parquet",
        "category": "港股离岸互联", "default_fund": {"code": "013402", "name": "华夏恒生科技ETF联接A", "share_class": "A"}
    },
    "pure_bond": {
        "name": "纯债固收", "index_code": "H11009", "matrix_col": "H11009",
        "category": "纯债流动性防守", "default_fund": {"code": "002351", "name": "易方达裕祥回报债券A", "share_class": "A"}
    },
}
```

### 3.2 统一估值分位数生成链路
1. **统一由 `data_loader.py` 的 `IndexValuationEngine` 输出唯一真相**:
   - `IndexValuationEngine.fetch_or_calc_index_valuations` 扩充其索引目录，包含全部 14 大赛道代码与用户自选代码；
   - 优先通过本地 `csindex_*.parquet`、`indices/*.parquet` 或 DuckDB 计算滚动历史 PE-TTM/PB 分位数；若为黄金或纯债，明确给出“大宗避险/纯债流动性”中性分位（如 50% 或根据实际利率环境测算）；
   - 输出统一持久化缓存 `data/cache/index_valuation.json`，侧边栏走廊与机会雷达全部从此入口提取。
2. **`OpportunityRadarEngine` 严禁私设独立估值来源**:
   - `get_sector_valuation_percentile(sec_id, meta)` 改为：
     ```python
     def get_sector_valuation_percentile(self, sec_id: str, meta: Dict[str, Any]) -> float:
         code = meta.get("index_code", "")
         if code in self.valuation_cache:
             p = self.valuation_cache[code].get("percentile")
             if p is not None:
                 return float(p)
         # 尝试从 fetch_or_calc_index_valuations 获取最新
         from data_loader import fetch_or_calc_index_valuations
         val_map = fetch_or_calc_index_valuations()
         if code in val_map and val_map[code].get("percentile") is not None:
             return float(val_map[code]["percentile"])
         return 50.0  # 中性基准兜底，绝不使用死常量 25.0
     ```

### 3.3 真实行情矩阵动态指标计算引擎
修复 `_calc_dynamic_sector_metrics`：
1. 正确指向 `data/processed/aligned_matrix_total_return.parquet`；
2. 若某赛道在矩阵中不存在对应列（如医药 000933、白酒 000932、银行 399986），自动通过 `meta.get("fallback_parquet")` 读取本地 parquet 文件中的收盘价序列；
3. **数学精算公式**:
   - **考夫曼信噪比 (ER20)**:
     $$\text{ER}_{20} = \frac{|P_t - P_{t-20}|}{\sum_{k=1}^{20} |P_{t-k+1} - P_{t-k}|} \in [0.1, 0.95]$$
   - **20日均线乖离率 (Bias20)**:
     $$\text{Bias}_{20} = \frac{P_t - \text{MA}_{20}}{\text{MA}_{20}} \times 100\%$$
   - **20日动量斜率 (Slope20)**:
     $$\text{Slope}_{20} = \frac{\text{MA}_{20}(t) - \text{MA}_{20}(t-20)}{\text{MA}_{20}(t-20)} \times 100\%$$
   - **拥挤度评分 (Crowding Score)**:
     结合成交金额放大倍数与短期乖离率计算，超买或放量过热时拥挤度分值压低，安全区间保持在 80~95 分。

---

## 4. 升级左翼全市场机会雷达设计

### 4.1 现有 Top 3 机会卡片展示机制与数据穿透
- 保持现有的 3 列并排布局 (`st.columns(3)`)，每张卡片展示：
  - 赛道名称与状态徽章（如 `🎯 黄金击球区`、`🔥 右侧共振`）
  - 综合得分与**真实估值分位**（与侧边栏 100% 对齐）
  - 优选公募基金名称与代码
  - `➕ 入备选池` 交互按钮，支持一键加入 Session State 候选池并触发重新定权。

### 4.2 可展开全市场 14 大赛道量化温度计总表
在 Top 3 机会卡片下方，增加可折叠组件：
```python
with st.expander("📊 全市场 14 大赛道量化温度计总表 (动态排序)", expanded=False):
```
- **展示列定义**:
  1. 赛道名称 (`name`)
  2. 估值分位 (`f"{val_percentile:.1f}%"`)
  3. 趋势信噪比 (`f"{er_20:.2f}"`)
  4. 20日乖离率 (`f"{bias_20:+.1f}%"`)
  5. 拥挤度安全分 (`f"{s_crowd:.1f}"`)
  6. 综合得分 (`f"{total_score:.1f}"`)
  7. 状态标签 (`tag`)
  8. 优选基金 (`f"{fund_name} ({fund_code})"`)
- **交互形式**: 使用 `st.dataframe(df_thermometer, use_container_width=True, hide_index=True)`，用户可点击任意列头自由升降序排序。

### 4.3 今日市场脉搏晨报生成引擎 (<=80字)
在双翼看板顶部，增加一段自适应市场脉搏晨报卡片：
- **生成逻辑**:
  1. 获取两市成交额与量能标签（来自 `fetch_market_turnover_and_sentiment`，如 `turnover_str="18,250 亿"`, `vol_text="放量活跃"`）；
  2. 获取大盘综合估值温度与股债性价比 ERP 分位数（来自 `market_snapshot` 或 `v_market_temperature`，如 `erp_pct=82.2%`，判定为“历史高性价比击球区”）；
  3. 获取机会雷达排名第 1~2 位的低估/共振领涨主线（如“红利低波与医药医疗”）；
  4. 自动模板串联，字数严格控制在 80 字以内：
     > **📢 今日市场脉搏**：两市成交 18,250 亿放量活跃，ERP 分位 82.2% 处历史高性价比击球区；红利低波与医药医疗领衔低估主线，右侧共振渐次强化。(73字)

---

## 5. 右翼六维主动风险预警哨全面实装方案

### 5.1 现有 `ActiveRiskSentry` 缺陷诊断
现行 `inspect_portfolio`（`advisory_engine.py:366-528`）主要存在以下缺陷：
1. **未满 7 天仅拦截了 `<= 3天`**：若持有天数为 4、5、6 天，在旧代码中直接漏检，用户若执行赎回依然会触发证监会 1.50% 巨额扣款！
2. **临近免赎期倒计时缺失**：A 类持有 4~6 天（还差 1~3 天满 7 天）或 C 类持有 23~29 天（还差 1~7 天满 30 天免赎，如实盘组合中的 `011613` 华夏科创50C 持有 28 天），旧代码完全无黄牌提醒，导致用户轻易在最后 2 天误操作扣费；
3. **C 类满 30 天窗口限制过窄**：旧代码仅在 `30 <= min_days <= 35` 触发，若持有 36 天或 60 天则不再提醒；新规则要求 `>= 30天` 均提示赎回费已归零、建议逢高置换为低费率 A 类；
4. **缺失个基阶梯止盈与深套诊断**：进攻型基金浮盈 >= 15% 且赛道偏热时无止盈提醒；浮亏 <= -12%（如 `013841` 银华集成电路C 浮亏 -16.19%）无专业诊断；
5. **缺失赛道集中度（>35%）与重仓股交叉重合度预警**；
6. **预警卡片缺失交互式动作按钮**：无法一键跳转 Tab 2 锁定标的或生成阶梯止盈单。

### 5.2 六维全景检测逻辑与触发阈值细则

| 维度编号 | 维度名称 | 触发条件与判定阈值 | 警报级别 | 针对标的与案例 | 建议处置与交互按钮 |
|---|---|---|---|---|---|
| **维度 1** | 未满 7 天惩罚锁仓红牌 | `min_days < 7`（悲观批次最小天数） | 🔴 `red` | `011612`（持有仅 3 天） | 严禁赎回！锁定持仓下界，防 1.50% 惩罚费。<br>按钮：`🔒 锁定调仓下界` |
| **维度 2** | 临近免赎期倒计时保护 | A/C 类 `4 <= min_days <= 6`（差 1~3 天满 7 天）；<br>或 C 类 `23 <= min_days <= 29`（差 1~7 天满 30 天） | 🟡 `yellow` | `011613`（C类持有 28 天，差 2 天免赎） | 倒计时保护，再等几天赎回费归零。<br>按钮：`⏳ 暂缓调仓倒计时` |
| **维度 3** | C 类满 30 天零费率置换 | `share_class == 'C'` 且 `min_days >= 30` | 🟡 `yellow` | 任意已满 30 天的 C 类长持标的 | 赎回费已归零，建议逢高置换为 A 类防销售服务费磨损。<br>按钮：`🔄 择机置换A类` |
| **维度 4** | 个基阶梯止盈与深套诊断 | **分支 A (止盈)**: `pnl_pct >= 15.0%` 且 (`bias_20 > 5.0%` 或 `val_pct > 75%`)；<br>**分支 B (深套)**: `pnl_pct <= -12.0%` | 🟡 `yellow`<br><br>🔴 `red` | 浮盈达标进攻基；<br>`013841`（银华集成电路C，浮亏 -16.19%） | 分批止盈 30%~50% 沉淀至纯债/红利；<br>深套结合赛道估值实施阶梯减亏或定投摊薄，拒绝割肉踏空。<br>按钮：`📉 生成阶梯止盈单` / `📊 查看深套诊断` |
| **维度 5** | 组合赛道集中度与重仓重叠 | **分支 A (赛道集中)**: 单一细分赛道市值占比 `> 35%`；<br>**分支 B (重仓交叉)**: 非豁免基金间重仓股重叠度 `> 40%` | 🟡 `yellow` | 科技成长等高暴露细分赛道；<br>持仓多只权益基重仓股高度重叠 | 适度均衡配置，平衡至弱相关红利/纯债/海外资产。<br>按钮：`⚖️ 平衡赛道敞口` / `🔍 查看重仓穿透` |
| **维度 6** | 基金本体清盘线与大盘攻防 | **分支 A (迷你基)**: `aum < 0.50` 亿元；<br>**分支 B (大盘攻防)**: 沪深300跌破防守线 / 放量突破进攻线 | 🔴 `red`<br><br>🔴/🟢 `notice` | 规模 < 5000 万迷你基；<br>沪深300突破或破位关键点位 | 迷你基择机置换为 10~50 亿标杆基；<br>大盘破位转入纯债防守，放量突破增配高弹性成长。<br>按钮：`🚨 置换标杆基金` / `🛡️ 启动防守预案` |

### 5.3 演示组合中特定测试持仓实测表现预判
在当前 `portfolio_ledger.json` 中：
- `011612` (华夏科创50ETF联接A): 持有天数 3 天 -> **精确命中维度 1 惩罚锁仓红牌**（提示持有仅 3 天，严禁赎回）；
- `011613` (华夏上证科创板50成份ETF联接C): 持有天数 28 天 -> **精确命中维度 2 临近免赎期倒计时黄牌**（提示已持 28 天，距 30 天免赎仅差 2 天）；
- `013841` (银华集成电路混合C): 浮亏 -16.19% -> **精确命中维度 4 深套诊断红牌**（提示深度浮亏 -16.2%，结合芯片赛道估值与 MA20 给出阶梯减亏指引）。
三只特定标的 100% 靶向命中，完美满足验收要求。

### 5.4 交互式快捷动作按钮与 Tab 2 状态机联动设计
在 `render_dual_wing_advisory_dashboard` 中，针对每条预警卡片，动态渲染一个操作按钮：
```python
act_type = alert.get("action_type")
act_lbl = alert.get("action_label", "⚡ 立即处置")
if st.button(act_lbl, key=f"btn_sentry_act_{i}_{alert.get('fund_code', '')}"):
    if act_type == "lock_shares":
        # 记录受保护标的，调仓算法将其加入 locked_shares 下界
        if "tab2_locked_funds" not in st.session_state:
            st.session_state.tab2_locked_funds = []
        st.session_state.tab2_locked_funds.append(alert["fund_code"])
        st.session_state.tab2_trigger_diagnose = True
        st.toast(f"🔒 已锁定标的【{alert['fund_code']}】持仓下界，严禁调仓卖出！")
        st.rerun()
    elif act_type == "take_profit":
        # 生成阶梯止盈单（例如减持 40%）
        st.session_state.tab2_pending_take_profit = {
            "fund_code": alert["fund_code"],
            "ratio": 0.40
        }
        st.session_state.tab2_trigger_rebalance = True
        st.toast(f"📉 已生成【{alert['fund_code']}】阶梯止盈单，正在转入调仓执行！")
        st.rerun()
    elif act_type == "deep_loss_rebalance":
        st.session_state.tab2_trigger_diagnose = True
        st.toast(f"💼 正在转入持仓调仓研判【{alert['fund_code']}】反弹阶梯减亏方案...")
        st.rerun()
```

---

## 6. 兼容性与防御保障 (Defensive Guardrails)

### 6.1 现有单元测试断言兼容矩阵
为防止修改导致现有测试套件回归失败，六维预警哨的文案输出必须向下兼容以下现有测试断言：
1. `test_m3_advisory_modules.py`:
   - `assert "≤3天" in alert_titles`: 维度 1 当 `min_days <= 3` 时标题保留“（≤3天）”字样；
   - `assert "已满 7 天" in alert_titles`: 保留已满 7 天脱离惩罚窗口的绿灯通知；
   - `assert "C类份额已满 30 天" in alert_titles`: 维度 3 保留“C类份额已满 30 天”字样；
   - `assert "超买" in alert_titles`: 维度 4 暴涨超买保留“超买”字样；
   - `assert "清盘警戒线" in alert_titles`: 维度 6 迷你基保留“清盘警戒线”字样。
2. `test_sidebar_remodel_and_bugfixes.py`:
   - `assert "red" in levels`: 持有 2 天输出 `red`；
   - `assert "yellow" in levels`: C类满 30 天输出 `yellow`。
3. `test_m3_full_integration_apptest.py`:
   - `assert "主动风险预警哨" in gui_text`: 保留关键标识，确保 AppTest 文本断言 100% 成立。

### 6.2 物理安全红线保障
- 4 大裁判只读文件（`judge_engine.py`, `holdout_vault.py`, `AGENT_SPEC.md`, `tests/test_infra.py`）严格保持只读，禁止任何代理进行接触或修改。已通过 `scripts/verify_referee_hashes.py` 核验全部通过。

### 6.3 GEMINI.md 核心红线对照表
- **规则 1 & 规则 16（防张冠李戴）**: 中证红利必须且仅允许映射为 `000922`，点位必须处于 5000~6500 点合理区间；
- **规则 2 & 规则 7（先进先出与锁仓）**: 必须使用 `min((b.holding_days for b in batches), default=30)` 进行悲观天数判定，守死 1.50% 惩罚费红线；
- **规则 8（反超买均值回归）**: Bias20 > +6.0% 标的必须在雷达打分中执行超买折价惩罚；
- **规则 14 & 规则 15（空间几何与防挤压）**: 新增的全市场温度计总表必须在窄视口下保持横向滚动自适应，严禁 `overflow: hidden` 切断文字。

---

## 7. 实施行动建议蓝图 (Implementer Blueprint)

后续实施代理人在推进代码改造时，建议遵循以下标准执行顺序：

```
Step 1: 重构 advisory_engine.py 中的 RADAR_SECTOR_CATALOG 与 dynamic_metrics
  - 彻底剥离 base_val_pct、er_20、bias_20、slope_20 等静态假字段
  - 修正 aligned_matrix 路径为 data/processed/aligned_matrix_total_return.parquet
  - 增加 fallback_parquet 补全医药、白酒、银行等赛道日线数据
  - 估值分位统一下潜至 IndexValuationEngine 动态获取

Step 2: 在 advisory_engine.py 中全面升级 ActiveRiskSentry 为六维风险哨
  - 维度 1: min_days < 7 红色红牌锁仓
  - 维度 2: A/C 4~6天 或 C 23~29天 免赎倒计时黄牌
  - 维度 3: C 类 >= 30天 零费率置换提醒
  - 维度 4: 浮盈 >= 15% 阶梯止盈 + 浮亏 <= -12% 深套诊断
  - 维度 5: 赛道集中度 > 35% + 重仓股重叠 > 40% 预警
  - 维度 6: < 0.5亿 迷你基清盘 + 沪深300 攻防线

Step 3: 升级 app_gui.py 中 render_dual_wing_advisory_dashboard
  - 顶部增加 <=80 字今日市场脉搏晨报卡片
  - 左翼 Top 3 下方增加全市场 14 大赛道量化温度计总表 (可折叠)
  - 右翼卡片下方渲染可交互快捷动作按钮并绑定 Session State

Step 4: 回归核验与无感平滑交付
  - 运行 pytest AGY2_FundAdvisory/tests/test_m3_advisory_modules.py
  - 运行 pytest AGY2_FundAdvisory/tests/test_sidebar_remodel_and_bugfixes.py
  - 运行 python scripts/verify_referee_hashes.py
  - 运行 AppTest 核验 Streamlit 前端 0 异常
```

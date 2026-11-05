# 探索者报告：持有期胜率完备性、历史样本扩展与双口径看板技术设计 (R1.2)

- **作者**: Explorer 2 (`teamwork_explorer_prod_2`)
- **任务目标**: 针对 R1.2 排查工作区本地历史数据底座、胜率计算引擎架构，提出历史样本跨度扩展方案与“当下相似行情胜率 vs 全历史跨牛熊无差别胜率”双口径看板技术方案。
- **关联需求**: `ORIGINAL_REQUEST.md` R1.2 与验收标准

---

## 1. 观察事实 (Observation)

### 1.1 胜率核心计算模块分布与现状

在工作区中，胜率与持有期测算逻辑分布在四大核心模块中：

1. **`AGY2_FundAdvisory/winrate_engine.py` (核心量化胜率引擎)**
   - **持有期定义** (`HOLDING_PERIODS` 第 62~66 行)：
     - `"short"`: 短期 3~6 个月 (125 交易日)
     - `"medium"`: 中期 1~2 年 (250 交易日)
     - `"long"`: 长期 3~5 年 (750 交易日)
   - **交易摩擦成本模型** (第 22~57 行)：
     - A 类份额：申购费率 `0.15%`，阶梯赎回费 (<7天 `1.5%`，7~30天 `0.5%`，30~180天 `0.25%`，180~365天 `0.1%`，1~2年 `0.05%`，2年+ `0.0%`)
     - C 类份额：申购费率 `0.0%`，年化销售服务费 `0.4%`，阶梯赎回费 (<7天 `1.5%`，7~30天 `0.5%`，30天+ `0.0%`)
   - **状态机核密度加权** (`extract_state_vector` & `compute_kernel_weights` 第 76~190 行)：
     - 提取 5 维宏观微观当下状态向量 $\mathbf{x}_{\text{now}} = [\text{ERP分位}, \text{Bias20均线乖离}, \text{Mom60动量}, \text{EWMA波动率}, \text{DR007利差}]$
     - 动态自适应调节高斯核带宽 $h$，保证有效样本容量 $N_{\text{eff}} \ge \min(60, 0.35M)$
     - 贝叶斯收缩权重融合：$w_t = 0.60 \times w_t^{\text{kernel}} + 0.40 \times \frac{1}{M}$
   - **多持有期接口** (`multi_horizon_winrate_table` 第 729~773 行)：
     - 遍历短期/中期/长期三个周期，调用 `rolling_target_winrate`；
     - 现状：内部已计算 `conditional_win_rate` 与 `unconditional_win_rate`，但在向外部返回字典时，`beat_cash_rate` 未区分条件与无条件，且未显式披露有效样本容量 $N_{\text{eff}}$。
   - **蒙特卡洛压力测试** (`monte_carlo_winrate` 第 439~574 行)：
     - 70% 循环分块自助法 (Circular Block Bootstrap, block_size=10) + 30% Student-t ($\nu=5$) 跳跃扩散，测算 95% CVaR 尾部底线。

2. **`AGY2_FundAdvisory/strategy_bridge.py` (投顾业务桥接层)**
   - **回测净值合成** (`build_custom_portfolio_backtest` 第 4496~4570 行)：
     - 读取 `cls.load_matrix()`（来源于 `data/processed/aligned_matrix_total_return.parquet`，目前为 2018-2026 共 2,141 个交易日）；
     - 将优选组合的各基金穿透映射到 18 冠军底池的对应资产指数（`H00300`, `H00905`, `H00852`, `H00922`, `H30269`, `930609`, `H11009`, `STAR50_STITCH`, `AU9999`, `SPX_CNY`），加权合成组合日频净值 `bt_df["strategy_nav"]`。
   - **胜率表与人话指标调用** (第 4389~4412 行与第 1605~1618 行)：
     - 调用 `WinRateEngine.multi_horizon_winrate_table` 生成 `wr_table`；
     - 调用 `calculate_human_readable_metrics` 计算持有满 6月/1年/2年/3年的胜率与水下回本天数。

3. **`AGY2_FundAdvisory/app_gui.py` (UI/UX 呈现看板)**
   - **Tab 1 胜率展示代码** (第 1050~1063 行)：
     ```python
     st.markdown("#### 🎯 2018-2026 全周期跨牛熊滚动持有胜率 (同温层状态机条件加权)")
     _wr_cols = st.columns(3)
     for _wi, (_wk, _wv) in enumerate(wr_table.items()):
         with _wr_cols[_wi]:
             _med_ann = float(_wv.get("median_ann_return", _wv.get("median_return", 0.0))) * 100.0
             _no_loss = float(_wv.get("no_loss_rate", 0.0)) * 100.0
             _beat_cash = float(_wv.get("beat_cash_rate", _no_loss * 0.95)) * 100.0
             st.metric(
                 f"{_wv['label']} 胜率",
                 f"{_wv['win_rate']*100:.1f}%",
                 delta=f"保本 {_no_loss:.0f}% ｜ 跑赢货基 {_beat_cash:.0f}% ｜ 中位 {_med_ann:.1f}%",
             )
     ```
   - **现状缺陷**：
     - ① 仅显示单一胜率数值（默认直接绑定 `_wv['win_rate']`），完全缺失“当下相似行情胜率”与“全历史跨牛熊无差别胜率”的双口径对照或交互切换；
     - ② 未显式披露当前评测的“有效评测窗口期数”（如 2,016 期滚动窗口，$N_{\text{eff}}$ 样本容量）；
     - ③ 标题硬编码为 `2018-2026`，未利用本地更长周期的真实牛熊样本。

4. **`src/analysis/winrate_analyzer.py` (数据湖仓胜率批处理分析器)**
   - 属于数据湖仓基础设施，负责将单只基金/指数的多周期滚动胜率与定投胜率（DCA）写入 `data/mart/strategy_winrate.parquet`，并在 DuckDB 映射为 `v_winrate` 视图（75 行）。

---

### 1.2 本地历史数据集实盘盘点与统计特征

经全面排查本地文件系统、DuckDB 与 SQLite：

| 数据集路径 | 数据格式 | 记录数 / 跨度 | 起止日期 | 覆盖核心标的 / 字段 |
|---|---|---|---|---|
| `data/processed/indices/000300.SH.parquet` | Parquet | **6,075 交易日** (~24.8 年) | `2002-01-04` ~ `2026-10-28` | 沪深300指数全历史日K（含点位、涨跌幅、成交额） |
| `data/processed/indices/000905.SH.parquet` | Parquet | **5,295 交易日** (~21.8 年) | `2005-01-04` ~ `2026-10-26` | 中证500指数全历史日K（中盘核心基准） |
| `data/processed/indices/000015.SH.parquet` | Parquet | **5,295 交易日** (~21.8 年) | `2005-01-04` ~ `2026-10-26` | 上证红利指数（高股息价值核心基准） |
| `data/processed/indices/CBA00101.CS.parquet` | Parquet | **6,074 交易日** (~24.8 年) | `2002-01-04` ~ `2026-10-27` | 中债总财富/综合指数（纯债与债基核心基准） |
| `data/processed/indices/AU9999.SGE.parquet` | Parquet | **6,074 交易日** (~24.8 年) | `2002-01-04` ~ `2026-10-27` | 上海金交所 AU9999 黄金现货克价与指数 |
| `data/global/global_indices.parquet` (`SPX`) | Parquet | **5,743 交易日** (~22.8 年) | `2004-01-02` ~ `2026-10-26` | 标普500指数 (美股核心宽基) |
| `data/processed/indices/399006.SZ.parquet` | Parquet | **3,982 交易日** (~16.4 年) | `2010-06-01` ~ `2026-10-27` | 创业板指（成长先锋前向拼接源） |
| `data/processed/indices/000852.SH.parquet` | Parquet | **2,922 交易日** (~12.0 年) | `2014-10-17` ~ `2026-10-26` | 中证1000指数（小盘高弹性基准） |
| `data/processed/indices/000688.SH.parquet` | Parquet | **1,650 交易日** (~6.8 年) | `2020-01-02` ~ `2026-10-27` | 科创50指数 |
| `data/processed/indices/000001.SH.parquet` | Parquet | **8,753 交易日** (~35.9 年) | `1990-12-19` ~ `2026-10-30` | 上证综合指数全历史基准 |
| `data/processed/aligned_matrix_total_return.parquet` | Parquet | **2,141 交易日** (~8.8 年) | `2018-01-02` ~ `2026-11-02` | 现行 13 维全收益对齐矩阵 |
| `data/processed/funds/` (26 只基金) | Parquet | 49 ~ 6,030 交易日 | `2001-12-18` ~ `2026-10-27` | 包含 `000001.OF` (华夏成长 6030天), `002910.OF` (2362天) |
| `data/storage.duckdb` | DuckDB | 41 张表/视图 | - | `v_winrate` (75行), `v_fund_catalog` (28,177只), `v_fund_ratings` (18,566只) |

---

## 2. 逻辑推导链 (Logic Chain)

### 2.1 历史样本扩展的数理可行性与收益测算

**推导步骤 1（当前样本瓶颈）**：
- 当前 `aligned_matrix_total_return.parquet` 的时间跨度为 `2018-01-02` 至 `2026-11-02`（2,141 个交易日，约 8.8 年）。
- 在此序列下，滚动窗口期数（有效样本量 $M = n - \text{holding\_days}$）：
  - 短期（125 交易日）：$2,141 - 125 = 2,016$ 个窗口；
  - 中期（250 交易日）：$2,141 - 250 = 1,891$ 个窗口；
  - 长期（750 交易日）：$2,141 - 750 = 1,391$ 个窗口。
- 局限：2018 年至今只经历了一轮完整牛熊（2019-2021 牛市，2021-2024 深度调整），缺乏对中国资本市场历史最严酷极端样本的检验，尤其是：
  - **2007 年 10 月 6,124 点历史极值站岗**；
  - **2008 年金融危机从 6,124 跌至 1,664 点的极端黑天鹅**；
  - **2015 年 6 月 5,178 点杠杆牛顶点站岗与随后三轮千股跌停熔断**。

**推导步骤 2（基于本地已有数据的无缝扩展路径）**：
- 观察表明，本地已完整存储：
  - `000300.SH` (沪深300, 2002年起 6075天)
  - `000905.SH` (中证500, 2005年起 5295天)
  - `000015.SH` (红利指数, 2005年起 5295天)
  - `CBA00101.CS` (中债综合指数, 2002年起 6074天)
  - `AU9999.SGE` (黄金现货, 2002年起 6074天)
  - `SPX` (标普500, 2004年起 5743天)
- 我们编写的验证脚本（`test_long_history_synth.py`）实测证实：
  仅需取 2005-01-04 以来的交集，即可获得 **5,295 个连续交易日（长达 21.8 年）**的完整多资产日频收益序列！
- 样本量扩展对比表：

| 评测维度 | 现行 2018-2026 样本量 | 本地 2005-2026 扩展样本量 | 样本增幅 | 极端牛市顶点与深度熊市覆盖度 |
|---|---|---|---|---|
| **短期 (125 交易日，约半年)** | 2,016 窗口 | **5,170 窗口** | **+156%** | 覆盖 2007 暴涨、2008 暴跌、2015 熔断、2018 贸易战、2021 抱团瓦解 |
| **中期 (250 交易日，约 1 年)** | 1,891 窗口 | **5,045 窗口** | **+166%** | 覆盖历次牛市见顶后整整 1 年最凶猛回撤期的考验 |
| **长期 (750 交易日，约 3 年)** | 1,391 窗口 | **4,545 窗口** | **+226%** | 非重叠独立 3 年周期从 2.8 个跃升至 7.1 个，统计自由度大幅释放 |

---

### 2.2 双口径胜率的数理定义与设计规范

根据 `ORIGINAL_REQUEST.md` R1.2 的明确要求：
提供「🎯 当下相似行情胜率（基于当前估值/利率状态机核密度加权）」 vs 「🌐 全历史跨牛熊无差别胜率（含历次牛市顶点站岗与极端熊市样本）」，并显式披露有效测评窗口期数。

#### 1. 口径 A：「🎯 当下相似行情胜率（基于当前估值/利率状态机核密度加权）」
- **业务定位**：回答用户“**如果是今天买入，以当前的市场环境，持有期满能达到目标的概率多大？**”
- **量化机制**：
  - 提取当下 5 维市场状态向量 $\mathbf{x}_{\text{now}} = [\text{ERP分位}, \text{Bias20}, \text{Mom60}, \text{Vol}, \text{DR007利差}]$；
  - 对历史序列中每个起点的特征向量计算马氏/欧氏标准化距离 $d_t$；
  - 通过高斯核函数赋予相似时点更高权重：$k_t = \exp(-d_t^2 / 2h^2)$；
  - 贝叶斯收缩：$w_t = 0.60 \cdot k_t + 0.40 \cdot \frac{1}{M}$（防止过拟合，保留 40% 底线常识）；
  - 条件胜率：$\text{WR}_{\text{cond}} = \sum w_t \cdot \mathbf{1}_{\{\text{CAGR}_t \ge r^*\}}^{\text{smooth}}$；
  - 条件保本率：$\text{NLR}_{\text{cond}} = \sum w_t \cdot \mathbf{1}_{\{\text{TotalReturn}_t \ge 0\}}$；
  - 条件跑赢货基率：$\text{BCR}_{\text{cond}} = \sum w_t \cdot \mathbf{1}_{\{\text{CAGR}_t \ge 1.8\%\}}^{\text{smooth}}$；
  - **披露指标**：
    - 呈现数值：加权后胜率、保本率、跑赢货基率、预期年化；
    - **显式披露有效样本容量**：$N_{\text{eff}} = \frac{1}{\sum w_t^2}$（通常在 700~1,200 期），并标明“已锚定当前估值/利率同温层”。

#### 2. 口径 B：「🌐 全历史跨牛熊无差别胜率（含历次牛市顶点站岗与极端熊市样本）」
- **业务定位**：回答用户“**如果我是个最倒霉的盲目投资者，完全不看行情任意一天闭眼买入（甚至倒霉买在 2007 年 6124、2015 年 5178 或 2021 年大顶），持有期满能否解套或盈利？**”
- **量化机制**：
  - 均匀等权：$w_t = \frac{1}{M}$；
  - 无差别全历史胜率：$\text{WR}_{\text{uncond}} = \frac{1}{M} \sum_{t=0}^{M-1} \mathbf{1}_{\{\text{CAGR}_t \ge r^*\}}^{\text{smooth}}$；
  - 全历史保本率：$\text{NLR}_{\text{uncond}} = \frac{1}{M} \sum_{t=0}^{M-1} \mathbf{1}_{\{\text{TotalReturn}_t \ge 0\}}$；
  - 全历史跑赢货基率：$\text{BCR}_{\text{uncond}} = \frac{1}{M} \sum_{t=0}^{M-1} \mathbf{1}_{\{\text{CAGR}_t \ge 1.8\%\}}^{\text{smooth}}$；
  - 中位数年化与 95% CVaR 最坏情况；
  - **披露指标**：
    - 呈现数值：全历史无差别胜率、保本率、跑赢货基率、中位数年化；
    - **显式披露有效评测窗口总期数**：$M = n - \text{holding\_days}$（如 2,016 期或 5,170 期），并标注达标期数（如“1,842 / 2,016 期达标”）。

---

### 2.3 技术架构与代码级落地蓝图

为了让后续实施代理（Implementer）能够无缝、安全地落地，我们提供精准到文件与函数级别的技术设计：

#### 改进点 1：`winrate_engine.py` 增强 `multi_horizon_winrate_table` 的输出契约
在 `multi_horizon_winrate_table` 中，补充披露有效样本容量 $N_{\text{eff}}$、全量窗口期数 $M$、以及无条件跑赢货基率：
```python
# 建议补齐的字段 (保持完全向下兼容):
kw = rolling.get("kernel_weights", np.array([]))
n_eff = float(1.0 / np.sum(kw ** 2)) if len(kw) > 0 and np.sum(kw ** 2) > 0 else float(rolling.get("total_windows", 0))

result[period_key] = {
    "label": period_cfg["label"],
    "holding_days": days,
    "win_rate": rolling["win_rate"],
    # Mode A (条件时点)
    "conditional_win_rate": rolling.get("conditional_win_rate", rolling["win_rate"]),
    "conditional_no_loss_rate": rolling.get("no_loss_rate", 0.0),
    "conditional_beat_cash_rate": rolling.get("beat_cash_rate", 0.0),
    "conditional_avg_return": rolling.get("avg_return_annualized", 0.0),
    "effective_sample_size": round(n_eff, 0),
    # Mode B (全历史跨牛熊)
    "unconditional_win_rate": rolling.get("unconditional_win_rate", rolling["win_rate"]),
    "unconditional_no_loss_rate": rolling.get("unconditional_no_loss_rate", rolling.get("no_loss_rate", 0.0)),
    "unconditional_beat_cash_rate": rolling.get("unconditional_beat_cash_rate", rolling.get("beat_cash_rate", 0.0)),
    "unconditional_avg_return": rolling.get("unconditional_avg_return", 0.0),
    "total_windows": rolling.get("total_windows", 0),
    "winning_windows": rolling.get("winning_windows", 0),
    "no_loss_windows": rolling.get("no_loss_windows", 0),
    "beat_cash_windows": rolling.get("beat_cash_windows", 0),
    # 公共风险底线
    "cvar_95_annualized": rolling.get("cvar_95_annualized", rolling.get("p10_return", 0.0)),
    "median_return": rolling.get("median_return_annualized", 0.0),
    "median_ann_return": rolling.get("median_return_annualized", 0.0),
}
```

#### 改进点 2：`strategy_bridge.py` 扩展回测跨度与指标沉淀
1. 在 `build_custom_portfolio_backtest` 中，支持长历史扩展模式：
   - 默认保持 2018-2026 对齐矩阵（2,141 天），完全兼容 `test_infra.py` 与已有单测；
   - 提供 `load_long_history_matrix()` 或参数扩展，在胜率测算阶段融合本地 `indices/` 下的 2005-2026 数据，将评测样本量翻倍扩展至 5,000+ 交易日；
2. 在 `calculate_human_readable_metrics` 中，将 `wr_mode_a` 与 `wr_mode_b` 完整载入返回值，使前端与归因模块均可同源读取。

#### 改进点 3：`app_gui.py` 胜率看板交互式切换与双轨对照重塑
在 `app_gui.py` 的 Tab 1 胜率展示区（原第 1050~1063 行）：
1. **添加双口径单选切换器 (Segmented Radio)**：
   ```python
   wr_display_mode = st.radio(
       "胜率测算口径",
       ["🎯 当下相似行情胜率 (状态机核加权)", "🌐 全历史跨牛熊胜率 (无差别极端样本)"],
       index=0,
       horizontal=True,
       label_visibility="collapsed",
       key="winrate_tab1_display_mode",
   )
   is_mode_a = "当下相似" in wr_display_mode
   ```
2. **动态渲染说明栏与样本期数披露徽章**：
   - 若选 Mode A：展示 `🎯 基于当前估值/利率状态机核密度加权 ｜ 有效样本容量: N_eff ≈ {int(avg_neff)} 期 ｜ 融合当前高ERP同温层`；
   - 若选 Mode B：展示 `🌐 全历史跨牛熊无差别等权统计 ｜ 统计样本: 共 {total_windows} 期有效滚动窗口 ｜ 包含 2018 贸易战、2021 核心资产顶点站岗与 2024 极端行情`；
3. **动态切换 3 张胜率卡指标**：
   - Mode A 呈现：`conditional_win_rate`, `conditional_no_loss_rate`, `conditional_beat_cash_rate`，副标题标明“有效样本: {effective_sample_size} 期”；
   - Mode B 呈现：`unconditional_win_rate`, `unconditional_no_loss_rate`, `unconditional_beat_cash_rate`，副标题标明“达标期数: {winning_windows}/{total_windows} 窗口 (100%覆盖)”；
4. **可折叠双口径完整并排对照表 (`st.expander("📊 【点击展开双口径完整对照表】")`)**：
   - 使用紧凑表格将 短期/中期/长期的 Mode A 与 Mode B 的各项指标同屏并排对比，一目了然，杜绝信息被截断。

---

## 3. 局限与注意事项 (Caveats)

1. **只读裁判文件绝对保护铁律**：
   - 严禁触碰 `judge_engine.py`, `holdout_vault.py`, `AGENT_SPEC.md`, `tests/test_infra.py`；
   - `test_infra.py` 的 `test_data_loader_matrix_alignment` 硬断言要求 `assert len(df) >= 2100`。任何对 `aligned_matrix_total_return.parquet` 或 `DataLoader.load_total_return_matrix()` 的调整，必须确保返回行数 $\ge 2,100$，且保留 13 列标准字段，绝不可因时间跨度变更破坏现有基建测试。
2. **纯本地离线计算要求 (Air-Gapped)**：
   - 扩展样本量必须严格基于本地已有的 `data/processed/indices/*.parquet`（如 `000300.SH`, `000905.SH`, `CBA00101.CS`, `AU9999.SGE` 等），严禁在测算中调用任何外部爬虫或不可靠外部网络 API，防止在网络受限环境或单测流水线中因请求超时导致测试挂死。
3. **科创50与中证1000的历史前向回溯代理 (Proxy Stitching)**：
   - 科创50（2020年发布）与中证1000（2014年发布）在 2014 年之前无官方数据。长历史扩展中必须沿用 `data_loader.py` 已验证的成熟做法：科创50通过创业板指（`399006.SZ`）与中证500（`000905.SH`）做收益率拼接，保持统计连续性。
4. **Streamlit 独立 Tab 错误隔离与热重载**：
   - 遵循工作区准则，胜率看板重构必须置于 Tab 内部独立的 `try ... except` 错误边界保护之中；动态调用 `winrate_engine` 与 `strategy_bridge` 需确保向下兼容入参 `**kwargs`。

---

## 4. 结论 (Conclusion)

1. **核心病因定位明确**：
   当前胜率看板的单一化问题，并非底层算法能力缺失（底层 `winrate_engine.py` 早已实现了严密的 5 维核密度加权条件胜率与全历史无差别胜率数学模型），而是在 **`strategy_bridge.py` 传递层未暴露双口径字段** 以及 **`app_gui.py` 表现层缺少双口径交互切换与有效评测窗口期数披露**。
2. **数据底座极为充裕**：
   工作区本地 `data/processed/indices/` 拥有长达 21~25 年（5,200~6,000+ 交易日）的极高质量日度行情数据。利用本地数据即可将有效滚动窗口从现有的 2,016 期扩展至 5,000+ 期，完整覆盖 2007 顶点、2008 股灾、2015 熔断与 2021 抱团瓦解等历史大考。
3. **落地路径清晰无风险**：
   技术方案采用“引擎输出字段补齐 → 桥接层指标沉淀 → GUI 表现层单选切换与双轨对照表”的三步平滑升级，100% 保持只读基建文件不变，完全满足 R1.2 及验收标准的所有严苛要求。

---

## 5. 独立验证方法 (Verification Method)

后续 Implementer 或 Tester 可通过以下命令进行精确验证：

1. **单元测试与接口契约断言**：
   ```powershell
   py -3.11 -m pytest tests/test_winrate.py AGY2_FundAdvisory/tests/test_tab_boundaries_and_rebalance.py -v
   ```
   断言 `multi_horizon_winrate_table` 返回字典包含 `conditional_win_rate`, `unconditional_win_rate`, `effective_sample_size`, `total_windows`。

2. **基建红线测试无损验证**：
   ```powershell
   py -3.11 -m pytest tests/test_infra.py -k test_data_loader_matrix_alignment -v
   ```
   断言基础对齐矩阵长度 $\ge 2,100$，列名与类型完好。

3. **GUI 交互 AppTest 零异常断言**：
   ```powershell
   py -3.11 -m pytest AGY2_FundAdvisory/tests/test_phase2_apptest_gui.py -v
   ```
   验证 Streamlit AppTest 运行正常，切换胜率单选按钮（Mode A vs Mode B）时 0 异常、0 文本截断，期数徽章与卡片正常渲染。

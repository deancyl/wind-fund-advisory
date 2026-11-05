# Requirement R3 & R4 深度调研与实现方案全景报告
**文件路径**: `d:\Google\Workspace\Wind\.agents\teamwork\explorer_survey_r8_3\analysis.md`  
**调研人**: Explorer Survey R8-3  
**完成时间**: 2026-11-05  
**状态**: 调研完成·已由只读探针全面验证（4 大裁判文件哈希 100% 完好）

---

## 1. 调研执行摘要与红线基线

本调研针对用户原始需求中的 **R3（扩充 7 大机构级量化定权模型、历史黑天鹅压力测试器与 UI 细节修复）** 与 **R4（物理安全红线、测试规划与工作区行为准则）**，进行了细致的代码级、数学公式级及 UI 样式级探查。

### 1.1 物理安全红线验证结果
通过运行 `py -3 scripts/verify_referee_hashes.py`，已对 4 大只读裁判文件进行 SHA256 完整性核验，全部完美通过基线：

| 文件路径 | 预期 SHA256 | 实际核验状态 |
| :--- | :--- | :--- |
| `AGY2_FundAdvisory/judge_engine.py` | `76F930371176DE7EE6A413174B030101E3210AC6E037F5D10FE229AF31CC07BE` | ✅ MATCH |
| `AGY2_FundAdvisory/holdout_vault.py` | `88122EAF647040A410E2FD95DA81077DB10149A498A47340FF40B670BD031D2A` | ✅ MATCH |
| `AGY2_FundAdvisory/AGENT_SPEC.md` | `A346586F9BD2DC0EE83E665BD18E7A6471464C9F7B658E392B989B800CD63957` | ✅ MATCH |
| `tests/test_infra.py` | `48BEE0DA300D7C0A0848EC1376E4B9B2E55224D2736081713B4340F0362CD100` | ✅ MATCH |

**运行 `test_infra.py` 结果**：14/14 tests passed in 5.34s。

---

## 2. 7 大机构级量化定权求解算子深入分析与数学架构

### 2.1 现有代码现状分析
目前在 `AGY2_FundAdvisory/portfolio_optimizer.py` 的 `QUANT_MODELS_CATALOG`（第 43~76 行）中仅注册了 4 个模型：
1. `hrp_cvar`（鲁棒双核HRP）
2. `cond_winrate`（条件胜率最优）
3. `min_cvar`（尾部风控CVaR）
4. `kelly_momentum`（凯利动量增强）

在 `AGY2_FundAdvisory/app_gui.py`（第 1953~1958 行 与 第 1994~2012 行）中：
- 下拉框字典 `model_options_map` 仅包含上述 4 种模型；
- 模型对比展示仅为「四大模型对比」4 列卡片。

在 `recommend_model_for_regime`（`portfolio_optimizer.py` 第 79~135 行）中：
- 宏观阶段自适应推荐仅路由至上述 4 种模型。

### 2.2 7 大机构级量化定权模型数学与逻辑全景

| 序号 | 模型标识 (Key) | 模型名称 (Name $\le$ 6字) | 徽章定位 (Badge) | 核心数学公式 / 目标泛函 | 适用宏观/资产情景 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| 1 | `hrp_cvar` | **鲁棒双核HRP** | 🛡️ 机构首选·高确定性 | 层次聚类树二分逆方差分配：$\alpha = 1 - \frac{V_1}{V_1 + V_2}$，融合 95% CVaR 与条件胜率先验 | 宽幅震荡磨底、赛道轮动剧烈、全天候底仓 |
| 2 | `core_satellite` | **核心卫星杠铃** | ⚖️ 攻守两极·底仓压舱 | 核心底仓 $W_{\text{core}} \in [70\%, 80\%]$（纯债+红利）按逆波动/等方差配置，卫星仓 $W_{\text{sat}} \in [20\%, 30\%]$（成长/科技/雷达）按考夫曼信噪比加权 | 既要纯债红利稳稳收息，又要保留成长弹性 |
| 3 | `all_weather` | **全天候平价** | 🌍 跨周期风险等权 | 风险平价 ERC (Equal Risk Contribution)：$\min_w \sum_{i,j} \left( w_i (\Sigma w)_i - w_j (\Sigma w)_j \right)^2$，跨宽基、红利、纯债、黄金、QDII 等权风险贡献 | 宏观牛熊不确定、跨周期资产配置、防范单一黑天鹅 |
| 4 | `black_litterman` | **BL观点融合** | 🧬 主客观贝叶斯后验 | 先验均衡收益率 $\Pi = \lambda \Sigma w_{\text{eq}}$，融入机会雷达赛道主观观点矩阵 $P, Q, \Omega$：$E[R] = \left[ (\tau \Sigma)^{-1} + P^T \Omega^{-1} P \right]^{-1} \left[ (\tau \Sigma)^{-1} \Pi + P^T \Omega^{-1} Q \right]$ | 机会雷达出现明确主升浪或自选赛道高胜率时 |
| 5 | `cond_winrate` | **条件胜率最优** | 🎯 同温层状态匹配 | 五维状态向量高斯核加权：$K(x, x_t) = \exp\left(-\frac{1}{2} (x - x_t)^T \Sigma_h^{-1} (x - x_t)\right)$，平滑 Sigmoid 最大化目标年化达标率 | 宏观估值明确，对特定目标年化胜率有强诉求时 |
| 6 | `min_cvar` | **尾部风控CVaR** | ⚓ 极小化极端回撤 | Rockafellar-Uryasev 95% CVaR：$\min_w \text{CVaR}_{0.95}(w) + 2.0 \times \text{DownsideVol}(w)$，严控 5% 极端亏损 | 期权 iVIX 飙升、大盘破位、厌恶任何深度回撤 |
| 7 | `kelly_momentum` | **凯利动量增强** | ⚡ 右侧复利进攻 | 考夫曼信噪比自适应半凯利：$\max_w \mathbb{E}[\ln(1 + 0.5 R_p(w))] + 0.25 \text{SNR}_{20} \cdot \mu_p$，内置超买均值回归折价 | ERP 处于底部击球区且指数放量站上 MA20 的主升浪 |

### 2.3 核心实现细节与算法伪代码

#### 1) 核心-卫星杠铃模型 (`core_satellite`)
- **资产分类逻辑**：
  - 核心池 $\mathcal{C}$：资产分类为「纯债固收」、「红利价值」、「固收增强」或黄金，对应代码如 `002351`, `000086`, `018757`, `005561`, `100032`, `090010`, `001015`, `000216`。
  - 卫星池 $\mathcal{S}$：资产分类为「科技先锋」、「成长小盘」、「海外QDII」或「宽基核心」，对应代码如 `011612`, `011613`, `013841`, `004194`, `011860`, `050025`, `110020`，以及机会雷达推荐基金。
- **权重划分**：
  - 若组合全部为核心或全部为卫星，退化为逆波动分配；
  - 正常情况下：根据档位设定 $W_{\text{core}} = 0.75$（C1/C2 为 $0.80$，C3 为 $0.75$，C4/C5 为 $0.70$），$W_{\text{sat}} = 1.0 - W_{\text{core}}$；
  - 核心池内部：按 $1 / \sigma_i$ 逆波动分配；
  - 卫星池内部：按 $\max(0.1, \text{SNR}_k \cdot \text{Sharpe}_k)$ 动量加权分配；
  - 约束裁剪与归一化：将权重裁剪在 $[w_{\min}, w_{\max}]$，最终执行 $\sum w_i = 1.0000$ 绝对闭合。

#### 2) 全天候风险平价模型 (`all_weather`)
- **数学求解器**：
  - 协方差矩阵：$\Sigma = \text{cov}(R) \times 250$；
  - 目标函数：
    $$\mathcal{L}(w) = \sum_{i=1}^n \sum_{j=1}^n \left( w_i (\Sigma w)_i - w_j (\Sigma w)_j \right)^2$$
  - 先验初值：$x_0 = \frac{1/\sigma_i}{\sum 1/\sigma_j}$；
  - 约束：$\sum w_i = 1.0, w_i \in [w_{\min}, w_{\max}]$；
  - 使用 `scipy.optimize.minimize(..., method="SLSQP")` 快速求解（通常 15~30 次迭代即收敛）。

#### 3) BL主客观观点融合模型 (`black_litterman`)
- **数学求解器**：
  - 市场均衡配置：$w_{\text{eq}} = \text{softmax}(\text{Sharpe}) \approx \frac{1}{N}$；
  - 风险厌恶系数：$\lambda = 2.5$；
  - 先验期望收益率：$\Pi = \lambda \Sigma w_{\text{eq}}$；
  - 构造观点 $P, Q, \Omega$：
    - 针对机会雷达 Top 赛道基金或个体条件胜率 $> 60\%$ 标的，赋予相对观点：$Q_k = \Pi_k + 0.035$；
    - 针对超买均值回归或条件胜率 $< 45\%$ 标的，赋予保护观点：$Q_j = \Pi_j - 0.025$；
    - 观点置信度协方差：$\Omega = \text{diag}(P (\tau \Sigma) P^T)$，其中 $\tau = 0.05$；
  - 贝叶斯后验期望：
    $$E[R] = \left[ (\tau \Sigma)^{-1} + P^T \Omega^{-1} P \right]^{-1} \left[ (\tau \Sigma)^{-1} \Pi + P^T \Omega^{-1} Q \right]$$
  - 均值-方差反推权重：$w_{\text{raw}} = \frac{1}{\lambda} \Sigma^{-1} E[R]$，裁剪并在 $[w_{\min}, w_{\max}]$ 上归一化。

### 2.4 宏观推荐环境逻辑更新 (`recommend_model_for_regime`)
将现有 4 分支扩充为全天候 7 维状态机：
1. **高波防御避险期**（iVIX > 26.0 或 Bias20 < -2.5% 或 ERP < 35%）$\rightarrow$ 推荐 `min_cvar`（尾部风控CVaR）；
2. **底部右侧突破期**（ERP $\ge$ 65% 且 0.3% $\le$ Bias20 $\le$ 5.5% 且站上 MA20）$\rightarrow$ 推荐 `kelly_momentum`（凯利动量增强）；
3. **稳健防守固收期**（C1/C2 档位 或 波动厌恶 或 目标年化 $\le 8\%$）$\rightarrow$ 推荐 `core_satellite`（核心卫星杠铃）；
4. **宏观变盘平衡期**（跨资产分化显著、DR007 平稳）$\rightarrow$ 推荐 `all_weather`（全天候平价）；
5. **结构分化主线期**（机会雷达 Top 赛道信噪比突显）$\rightarrow$ 推荐 `black_litterman`（BL观点融合）；
6. **高性价比磨底期**（ERP $\ge$ 60% 且均线窄幅震荡）$\rightarrow$ 推荐 `hrp_cvar`（鲁棒双核HRP）；
7. **同温层状态匹配期**（常规震荡轮动市）$\rightarrow$ 推荐 `cond_winrate`（条件胜率最优）。

---

## 3. 历史黑天鹅压力测试器深入分析与实测

### 3.1 真实历史切片定义
基于已对齐的数据湖仓（2018-01-02 至 2026-11-04 全收益矩阵，共 2,143 交易日），选定 3 个最具代表性的极端承压切片：

1. **2018 贸易摩擦熊市 (`2018-01-29 ~ 2018-12-28`)**
   - 宏观背景：中美贸易摩擦剧烈升级，去杠杆叠加盈利估值双杀；
   - 沪深300同期最大回撤：`-31.8%`。
2. **2022 杀估值熊市 (`2022-01-04 ~ 2022-10-31`)**
   - 宏观背景：美联储连续超预期暴力加息百基点，俄乌地缘局势突变，全球风险资产剧烈杀估值；
   - 沪深300同期最大回撤：`-28.9%`。
3. **2024 年初微盘流动性危机 (`2024-01-02 ~ 2024-02-08`)**
   - 宏观背景：雪球期权集中敲入、量化微盘踩踏，小微盘遭遇史诗级流动性抽水（中证1000 回撤 `-27.1%`）；
   - 沪深300同期最大回撤：`-7.3%`。

### 3.2 组合承压精算实测验证
以典型平衡进取组合（创金红利低波 35%、富国中证红利 20%、华安黄金 20%、海外标普 15%、科创50C 10%）在 ¥100,000 本金下的真实计算结果：

| 黑天鹅历史切片 | 组合最大回撤 | 最大账面浮亏 | 全周期回本天数 | 同期沪深300回撤 | 相对沪深300超额防御 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **2018 贸易摩擦熊市** | **-14.74%** | **¥14,737.86** | **264 交易日**（约 13.3 个月） | -31.8% | **少亏 +17.06%** |
| **2022 杀估值熊市** | **-9.71%** | **¥9,707.83** | **214 交易日**（约 10.7 个月） | -28.9% | **少亏 +19.19%** |
| **2024 年初微盘流动性危机** | **-3.38%** | **¥3,378.77** | **15 交易日**（约 0.7 个月） | -7.3% | **少亏 +3.92%** |

*实测脚本已在 `.agents/teamwork/explorer_survey_r8_3/test_stress.py` 成功运行，无任何运行时警告或假数据。*

### 3.3 UI 渲染接入点设计

#### 1) Tab 1 步骤二（现场推演评估）渲染位置
位于 5 张大字号人话指标卡（`app_gui.py` 第 2197 行）之后、选基漏斗之前，或者在「方案核心归因」（第 2371 行）之后作为专属卡片区块呈现：
- 使用 3 列并排卡片展示 3 大黑天鹅情景；
- 每张卡片包含：
  - 顶部黑天鹅名称与时间切片标签；
  - 核心大字：组合极限浮亏率与金额（如 `-9.71%` / `-¥9,708`）；
  - 关键行：水下回本时长（如 `214 交易日 / 10.7 个月`）；
  - 对照行：沪深300 同期回撤（如 `-28.9%`），并高亮展示「超额防御安全垫」。

#### 2) Tab 3（穿透回测）渲染位置
位于 4 张表现卡片与净值曲线之间（`app_gui.py` 第 3880 行），或位于「历史切片战报」（第 4041 行）上方：
- 以独立高级分析卡片形式呈现，配合 Plotly 回测曲线上的垂直着色区域（`vrect`），让用户直观检视至暗时刻的净值回撤与修复形态。

---

## 4. UI 细节修复与精炼

### 4.1 修复 Primary 主按钮文字颜色 (强制 `#ffffff !important`)
#### 问题定位
在 `AGY2_FundAdvisory/app_gui.py` 中，全局样式（第 936~940 行）对所有文字做了强穿透：
```css
label, [data-testid="stWidgetLabel"] p, [data-testid="stWidgetLabel"] span,
.stRadio div[role="radiogroup"] label p, .stCheckbox label p,
[data-testid="stMarkdownContainer"] p, [data-testid="stCaptionContainer"] {
    color: var(--text-primary) !important;
}
```
Streamlit 的 Primary 主按钮（`button[kind="primary"]` 或 `[data-testid="stBaseButton-primary"]`）内部通常渲染 `<p>` 标签。在浅色主题（如 `light_slate`，`--text-primary: #0f172a`）下，按钮内部 `<p>` 受到上述规则的 `!important` 污染，导致深蓝底色上渲染深黑文字，发生严重不可读。

#### 修复方案
在 `app_gui.py` 的全局 `<style>` 样式块中补充如下专属选择器覆盖规则：
```css
/* 🛡️ Primary 主按钮文字绝对防护：任何主题下强制纯白文字 */
button[kind="primary"],
button[kind="primary"] *,
button[kind="primary"] p,
button[kind="primary"] span,
button[kind="primary"] div,
[data-testid="stBaseButton-primary"],
[data-testid="stBaseButton-primary"] *,
[data-testid="stBaseButton-primary"] p,
[data-testid="stBaseButton-primary"] span {
    color: #ffffff !important;
}
```

### 4.2 消除 Tab 1 步骤一重复摘要文字
#### 问题定位
在 `app_gui.py` 第 1839~1851 行：
```python
cur_tier_meta = RISK_TIERS_CONFIG.get(active_tier, RISK_TIERS_CONFIG["C3"])
_num_f = int(st.session_state.get("tab1_num_funds", 6))
_m_type = st.session_state.get("tab1_model_type", "hrp_cvar")
_m_name = QUANT_MODELS_CATALOG.get(_m_type, {}).get("name", "鲁棒双核HRP")

safe_markdown_html(f"""
<div style="background: var(--bg-elevated); border: 1px solid var(--border-subtle); border-radius: 6px; padding: 8px 12px; margin-top: 8px; margin-bottom: 8px; font-size: 11px; line-height: 1.5; color: var(--text-secondary);">
    <div><b>定权模型：</b>{_m_name}（{_num_f}只优选配置）</div>
    <div><b>资产锚点：</b>{cur_tier_meta['core_assets']}</div>
    <div><b>权益中枢：</b>{cur_tier_meta['equity_range_str']} ｜ <b>回撤上限：</b>{cur_tier_meta['max_drawdown_limit']}</div>
</div>
""")

if target_ret_input > 25.0:
    st.caption(f"⚡ 高收益提示：目标年化 {target_ret_input:.0f}% 对应【{active_tier} {cur_tier_meta['name']}】，历史最大回撤约 {abs(cur_tier_meta['historical_mdd']):.1f}%，解套需 {cur_tier_meta['max_tolerated_months']} 个月，建议长钱长投。")
else:
    st.caption(f"💡 目标收益 {target_ret_input:.0f}% ➔ 当前档位：【{active_tier} {cur_tier_meta['name']}】（权益上限 {cur_tier_meta['equity_range'][1]}% ｜ 预期年化 {cur_tier_meta['target_cagr']} ｜ 核心：{cur_tier_meta['core_assets']}）")
```
灰框与下方 `st.caption` 完全重复输出了：
1. `cur_tier_meta['core_assets']`（资产锚点 / 核心）；
2. `cur_tier_meta['equity_range']`（权益中枢 / 权益上限）；
3. 档位名称与预期收益。

#### 修复方案
精炼合并为单一优雅的「策略配置锚点卡片」：
```python
cur_tier_meta = RISK_TIERS_CONFIG.get(active_tier, RISK_TIERS_CONFIG["C3"])
_num_f = int(st.session_state.get("tab1_num_funds", 6))
_m_type = st.session_state.get("tab1_model_type", "hrp_cvar")
_m_name = QUANT_MODELS_CATALOG.get(_m_type, {}).get("name", "鲁棒双核HRP")

high_ret_alert = ""
if target_ret_input > 25.0:
    high_ret_alert = f'<div style="color: var(--color-up); font-size: 11px; margin-top: 4px;">⚡ 高收益提示：目标年化 {target_ret_input:.0f}% 历史最大回撤约 {abs(cur_tier_meta["historical_mdd"]):.1f}%，建议长钱长投。</div>'

safe_markdown_html(f"""
<div style="background: var(--bg-elevated); border: 1px solid var(--border-subtle); border-radius: 8px; padding: 10px 14px; margin-top: 8px; margin-bottom: 8px; font-size: 12px; line-height: 1.6; color: var(--text-secondary); box-shadow: var(--shadow-card);">
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
        <span style="font-weight: 700; color: var(--accent-primary); font-size: 13px;">🎯 策略锚点：【{active_tier} {cur_tier_meta['name']}】（预期年化 {cur_tier_meta['target_cagr']} ｜ 目标总投入 ¥{plan_capital:,.0f}）</span>
        <span style="font-size: 11px; background: var(--bg-surface); padding: 2px 8px; border-radius: 4px; border: 1px solid var(--border-subtle);">模型：{_m_name}（{_num_f}只优选配置）</span>
    </div>
    <div><b>核心底仓：</b>{cur_tier_meta['core_assets']}</div>
    <div><b>权益中枢：</b>{cur_tier_meta['equity_range_str']}（上限 {cur_tier_meta['equity_range'][1]}%） ｜ <b>容忍回撤：</b>{cur_tier_meta['max_drawdown_limit']}</div>
    {high_ret_alert}
</div>
""")
# 彻底删除下方重复冗余的 st.caption(...)
```

---

## 5. 六维风险预警哨与图1/图2估值同源调研

### 5.1 演示持仓 3 大标的与 6 维风险准确映射
在实盘测试账本 `portfolio_ledger.json` 中：
1. **011612 (华夏科创50ETF联接A)**:
   - `batches[0].holding_days = 3` (天数 $\le 3$ 且 $< 7$)；
   - 必须触发：**维度 1（未满 7 天惩罚锁仓红牌）**，严禁赎回防 1.50% 巨额惩罚扣款。
2. **011613 (华夏上证科创板50成份ETF联接C)**:
   - `share_class = "C"`, `batches[0].holding_days = 28` (处于 23~29 天区间，差 2 天满 30 天)；
   - 必须触发：**维度 2（临近免赎期倒计时黄牌保护）**，提醒再等 2 天赎回费归零。
3. **013841 (银华集成电路混合C)**:
   - `floating_pnl_pct = -16.19%` ($\le -12\%$)；
   - 且与 011612/011613 同属半导体/芯片赛道，在持仓中合并赛道占比超标；
   - 必须触发：**维度 4（深套诊断）** 与 **维度 5（赛道集中度/重仓股重叠预警）**。

### 5.2 图1 与 图2 估值分位一致性 Single Source of Truth
- **图 1**：侧边栏垂直行情走廊（`app_gui.py` 中的 `sidebar-index-card`）
- **图 2**：双翼看板机会雷达（`app_gui.py` 中的 `OpportunityRadarEngine`）
- **同源架构机制**：
  统一由 `data_loader.py` 的 `IndexValuationEngine`（结合本地行情对齐矩阵与真实 PE/PB 滚动历史分位数）作为单源同真入口。彻底废弃 `advisory_engine.py` 中 `RADAR_SECTOR_CATALOG` 内硬编码的静态 `base_val_pct`，确保中证红利（000922）、科创50（000688）、沪深300（000300）等关键赛道在图 1 和图 2 展示的分位数 100% 同步。

---

## 6. 自动化增量测试规划 (Test Plan)

为遵循敏捷交付与分层剪枝铁律（规避无意义重跑全量 92 个历史测试），针对 R3 与 R4 规划增量测试套件 `AGY2_FundAdvisory/tests/test_r8_quant_models_and_sentry.py`：

```python
# 测试用例规划清单：
# 1. test_all_seven_quant_models_normalization_and_differentiation()
#    - 遍历 7 大模型 (hrp_cvar, core_satellite, all_weather, black_litterman, cond_winrate, min_cvar, kelly_momentum)
#    - 遍历基金数量 N in [3, 6, 12, 15]
#    - 断言: abs(sum(w.values()) - 1.0) < 1e-4
#    - 断言: len(set(round(v, 4) for v in w.values())) > 1 (杜绝等权塌陷)
#    - 断言: np.std(list(w.values())) > 0.005

# 2. test_active_risk_sentry_six_dimensions_targets()
#    - 传入含有 011612 (3天), 011613 (28天C), 013841 (-16.19%深套) 的持仓
#    - 断言: 011612 触发维度 1 锁仓红牌
#    - 断言: 011613 触发维度 2 临近免赎黄牌
#    - 断言: 013841 触发维度 4 浮亏深套诊断 或 维度 5 赛道重叠

# 3. test_corridor_and_radar_valuation_percentile_ssot()
#    - 校验 IndexValuationEngine 动态计算结果与侧边栏走廊、机会雷达取值 100% 一致

# 4. test_black_swan_stress_tester_calculation()
#    - 验证 2018, 2022, 2024 三大历史切片回撤与回本计算输出完整无 None、无 NaN

# 5. test_ui_css_primary_button_and_step1_dedup()
#    - AST / Regex 核验 app_gui.py 中 button[kind="primary"] color: #ffffff !important
#    - AST 核验 Tab 1 步骤一已消除重复的 core_assets 与 equity_range caption

# 6. test_referee_hashes_integrity()
#    - 物理红线校验 4 大裁判文件 SHA256
```

---

## 7. 实施风险提示与防御建议

1. **`test_deep_remodel_final.py` 断言注意**：
   此前该文件中第 264 行包含了侧边栏老版 4 分区的断言（`##### 🎯 全局目标联动` 等），而最新 UI 已在 commit `804b869` 将侧边栏重塑为「外观色彩 + 市场状态底座 + 垂直行情走廊」。实现团队在跑该旧测试时需注意这一历史变更，或在增量测试中以最新侧边栏标准进行校验。
2. **性能与缓存**：
   全天候风险平价与 BL 观点融合求解包含局部优化，计算耗时通常在 0.1~0.3 秒以内。务必沿用已有的 `st.session_state.tab1_sim_cache` 防抖与参数比对逻辑（`cur_tab1_params != _last_p` 才重新计算），保障 GUI 极致顺滑。
3. **裁判文件绝对只读**：
   严禁触碰 `judge_engine.py`, `holdout_vault.py`, `AGENT_SPEC.md`, `tests/test_infra.py`。

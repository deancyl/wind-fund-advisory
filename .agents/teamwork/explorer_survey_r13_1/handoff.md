# Handoff Report — G6 实时数据、资讯感知与在线基因编程进化引擎调研

**Agent**: Explorer 1  
**Working Directory**: `d:\Google\Workspace\Wind\.agents\teamwork\explorer_survey_r13_1`  
**Recipient**: Parent Agent (`970e6279-6781-4b89-b765-9b8036125fe8`)  
**Date**: 2026-11-07T14:05:00Z  

---

## 1. Observation (客观观察证据)

### 观察点 1.1：`OpportunityRadarEngine` 与 14 大赛道评级结构
- **文件**: `AGY2_FundAdvisory/advisory_engine.py`
  - 第 25-224 行定义了全局赛道元数据字典 `RADAR_SECTOR_CATALOG`，包含全部 14 个赛道元数据：
    `dividend_low_vol`、`csi_dividend`、`csi_300`、`csi_500`、`csi_1000`、`star_50`、`semiconductor`、`pharma_health`、`consumer_liquor`、`banking_dividend`、`domestic_gold`、`us_sp500_nasdaq`、`hstech`、`pure_bond`。
  - 第 227 行声明 `class OpportunityRadarEngine`。
  - 第 252-402 行实现 `_calc_dynamic_sector_metrics(self) -> Dict[str, Dict[str, float]]`，从本地 parquet、DuckDB 及大盘矩阵（`aligned_matrix_total_return.parquet`）加载历史价格序列 $s$ 并精算指标。
  - 第 354-381 行直接使用 $s[-1]$ 作为 $p_t$。在未接入实时盘中行情时，$s[-1]$ 为历史交易日收盘价，导致今日盘中指标与历史完全重合。
  - 运行 `python` 验证：`ore.scan_all_sectors()` 当前第一名始终为纯债 `pure_bond` 82.1 分，第二名为消费白酒 `consumer_liquor` 78.5 分，印证了用户需求所述“纯债 82.1 分、白酒 78.5 分万年不变的静态假象”。

### 观察点 1.2：静态因子权重硬编码位置
- **文件**: `AGY2_FundAdvisory/advisory_engine.py`
  - 第 575-578 行：
    ```python
    575:         # 综合加权得分
    576:         total_score = round(
    577:             0.30 * s_val + 0.30 * s_mom + 0.25 * s_er + 0.15 * s_crowd,
    578:             1
    579:         )
    ```
  - 静态写死了 0.30 估值、0.30 动量、0.25 信噪比、0.15 拥挤度。
  - 该方法为 `evaluate_sector(self, sec_id: str, meta: Dict[str, Any]) -> Dict[str, Any]` (第 542 行)。

### 观察点 1.3：实时资讯与快讯获取能力现状
- **文件**: `AGY2_FundAdvisory/data_loader.py`
  - 目前仅包含 `fetch_market_turnover_and_sentiment` (第 59 行，拉取东财两市成交额与涨跌家数情绪) 与 `fetch_custom_realtime_indices` (第 1725 行，拉取指数/ETF 实时点位)；
  - **完全不存在实时财经快讯或宏观资讯获取函数**。
  - 实测验证外网接口：
    1. 东方财富 7x24 快讯: `https://newsapi.eastmoney.com/kuaixun/v1/getlist_102_ajaxResult_50_1_.html` (HTTP 200, 28KB, 包含 `LivesList`, 字段 `title`, `digest`, `showtime`, `url_w`)；
    2. 新浪财经 7x24 直播: `https://zhibo.sina.com.cn/api/zhibo/feed?page=1&page_size=30&zhibo_id=152` (HTTP 200, 63KB, 包含 `result.data.feed.list`, 字段 `create_time`, `rich_text`, `tag`, `id`)。

### 观察点 1.4：在线基因编程向量化回测性能
- 实测编写纯 NumPy 向量化回测算子：
  - 32 个个体、60 个交易日、14 大赛道收益率矩阵；
  - 采用张量点乘 `np.tensordot(F, W, axes=([2], [1]))` 计算打分，`np.argpartition` 提取 Top-3 赛道计算滚动收益率；
  - 运行 8 代锦标赛选择、算术交叉与自适应突变，实测总耗时 **15.58 毫秒**，完全满足 $<50\text{ms}$ 限制。

### 观察点 1.5：只读裁判文件状态
- 运行 `git status --porcelain AGY2_FundAdvisory/judge_engine.py AGY2_FundAdvisory/holdout_vault.py AGY2_FundAdvisory/AGENT_SPEC.md tests/test_infra.py`：输出为空 (0 差异)。
- 运行 `py -3 -m pytest tests/test_infra.py`：14 passed in 10.36s。

### 观察点 1.6：前端双翼看板视觉瑕疵
- **文件**: `AGY2_FundAdvisory/app_gui.py`
  - 第 2521 行：`st.markdown("<div style='font-size: 14px; font-weight: 700; color: var(--text-primary); margin-bottom: 8px;'>🚨 主动风险预警哨 · 六维主动巡检 <span style='font-size: 11px; font-weight: 400; color: var(--text-secondary);'>[主动风险预警哨 · 四维巡检升级版]</span></div>", unsafe_allow_html=True)` 明确残留灰色尾缀；
  - 第 2531 行：`with st.container(height=300):` 缺少顶部安全内边距，在部分视口下容易截断第一张卡片上半部分。

---

## 2. Logic Chain (推理逻辑链)

1. **实时盘中 K 线缝合可行性**:
   - 依据观察点 1.1，指标计算的源头是各赛道的价格序列 $s$。
   - 依据观察点 1.3，`fetch_custom_realtime_indices` 已具备实时拉取 14 大赛道对应指数/ETF 当日涨跌幅 `change_pct` 的成熟能力。
   - 推理：在 `_calc_dynamic_sector_metrics` 中，通过收益率缝合公式 $p_{\text{today}} = s[-1] \times (1.0 + \text{change\_pct} / 100.0)$，将 $p_{\text{today}}$ 作为第 $T+1$ 根 Bar 追加至 $s$ 末尾，后续所有均线、乖离率、斜率和打分均基于该有效序列动态计算，即可自然实现盘中打分实时联动，纯债与白酒的静态分数被物理消除。

2. **在线基因编程替代静态权重可行性**:
   - 依据观察点 1.2，第 575-578 行写死了 4 维权重。
   - 依据观察点 1.4，纯 NumPy 向量化张量运算只需 15.58ms 即可演化出更优权重，且通过将个体 0 锚定为静态基线并实行精英保留，数学上保证进化后的适应度永远不低于静态基准。
   - 推理：将第 575-578 行替换为 `OnlineHeuristicFactorEvolver` 演化出的动态最优权重，同时通过 `OpportunityRadarEngine.get_evolution_badge_data()` 传递给前端展示白盒徽章，完全闭环且具备自我进化能力。

3. **实时资讯感知落地可行性**:
   - 依据观察点 1.3，东财与新浪两个 7x24 快讯端点均可在 200ms 内响应完整结构化资讯。
   - 配合 2 秒超时、内存与 `data/cache/realtime_news.json` 双层缓存，以及关键词打标分类器，可实现极度健壮的宏观与赛道资讯感知，供晨报与赛道推荐依据呈现。

---

## 3. Caveats (注意事项与边界条件)

1. **接口防封与频控**:
   东财与新浪接口虽然免 Token，但调用时必须设置合理的内存缓存（如 TTL 60~120 秒），防止 Streamlit 每次 rerun 都重复发起网络请求触发风控。
2. **场外基金交易日 15:00 规则**:
   实盘交易规则中，场外基金在 15:00 之后申请属于次日交易日，因此在 15:00 之后，今日盘中估算净值应平滑沉淀或提示“已收盘确认中”。
3. **只读文件绝对防护**:
   `tests/test_infra.py` 等 4 个文件严禁任何修改；新增的针对性测试必须写入 `tests/test_g3_evolution_loop.py`。

---

## 4. Conclusion (调研结论与实施方案)

1. **实施路径高度明确且风险极低**：
   - 在 `AGY2_FundAdvisory/data_loader.py` 中新增 `fetch_realtime_market_news_and_catalysts`；
   - 在 `AGY2_FundAdvisory/advisory_engine.py` 中新增 `OnlineHeuristicFactorEvolver` 并打通 `OpportunityRadarEngine` 的实时 K 线拼接与动态权重；
   - 在 `AGY2_FundAdvisory/app_gui.py` 中升级晨报证据链、Top 3 赛道实时涨跌幅与四维得分拆解、进化白盒徽章，并清除预警哨标题灰色尾缀；
   - 在 `tests/test_g3_evolution_loop.py` 中新增对应的验证测试。

---

## 5. Verification Method (独立验证方法)

1. **只读文件完整性核验**:
   ```powershell
   git status --porcelain AGY2_FundAdvisory/judge_engine.py AGY2_FundAdvisory/holdout_vault.py AGY2_FundAdvisory/AGENT_SPEC.md tests/test_infra.py
   # 预期输出：空 (0 改动)
   ```
2. **基础设施回归测试**:
   ```powershell
   py -3 -m pytest tests/test_infra.py
   # 预期输出：14 passed
   ```
3. **量化与进化闭环测试**:
   ```powershell
   py -3 -m pytest tests/test_g3_evolution_loop.py
   # 预期输出：12 passed (新增专项测试后应为 15+ passed)
   ```
4. **实时打分与进化引擎单体校验**:
   ```powershell
   py -3 -c "from advisory_engine import OpportunityRadarEngine; r = OpportunityRadarEngine(); s = r.scan_all_sectors(); print('Top1:', s[0]['name'], s[0]['total_score'], s[0].get('is_realtime_spliced', False))"
   ```

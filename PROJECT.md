# Project: Wind Advisory System Production Deep Refactoring

## Architecture
- **Host System**: `AGY2_FundAdvisory`
- **Scope**: Production-grade refactoring covering quantitative optimization algorithms, win rate statistical expansion, and global UI/UX redesign.
- **Key Modules**:
  1. `portfolio_optimizer.py`: SLSQP smooth sigmoid gradient ($\tau=0.025$), model-specific prior tilt $x_0$, HRP hierarchical isolation in local search, 4 models differentiation (`hrp_cvar`, `cond_winrate`, `min_cvar`, `kelly_momentum`).
  2. `strategy_bridge.py`: Dynamic weight allocation, purchasing limit (单日限购) deduction & companion fund deduplication, dual-mode win rate bridge (State-Conditional vs All-History), 2-stage penny and percentage residual reconciliation.
  3. `portfolio_manager.py`: Zero-start blueprint generation (`generate_zero_start_blueprint`), companion allocation deduction, absolute capital and weight conservation.
  4. `winrate_engine.py`: Long-history 2005-2026 index dataset integration (5,295 trading days), multi-horizon sample expansion, effective sample count calculation.
  5. `app_gui.py`: Sidebar restoration as 「🧭 全局领航台」 (decoupled 4 modules), top 6 index tickers full-width single line, responsive 4-model cards, 6-dim scoring `st.popover`, 3-card dynamic deep attribution, dual-mode win rate selector & side-by-side comparison, and all titles $\le 7$ Chinese characters.
  6. Read-Only Invariants (Strictly untouched):
     - `AGY2_FundAdvisory/judge_engine.py`
     - `AGY2_FundAdvisory/holdout_vault.py`
     - `AGY2_FundAdvisory/AGENT_SPEC.md`
     - `AGY2_FundAdvisory/tests/test_infra.py`

## Code Layout
- `AGY2_FundAdvisory/portfolio_optimizer.py`: M1 (Optimizer Invariants)
- `AGY2_FundAdvisory/strategy_bridge.py`: M1 (Purchasing Limits & Invariants) & M2 (Win Rate Dual Modes)
- `AGY2_FundAdvisory/portfolio_manager.py`: M1 (Blueprint Generation)
- `AGY2_FundAdvisory/winrate_engine.py`: M2 (Long History Integration)
- `AGY2_FundAdvisory/app_gui.py`: M3 (Global UI/UX Redesign)
- `AGY2_FundAdvisory/tests/`: E2E Testing Track & M4 (Regression & Verification)

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | Optimizer Smooth Gradient | Replace hard indicator step function with smooth Sigmoid proxy ($\tau=0.025$) in SLSQP objective | M1 | ORIGINAL_REQUEST §R1.1 |
| 2 | Model-Specific Prior Tilts | Provide intelligent $x_0$ based on model theory rather than mechanical 1/N | M1 | ORIGINAL_REQUEST §R1.1 |
| 3 | HRP Protection in Local Search | Prevent `_local_search` from overwriting HRP hierarchy with default SLSQP weights | M1 | ORIGINAL_REQUEST §R1.1 |
| 4 | Weight & Penny Conservation | 2-stage residual alignment: sum of `allocated_amount` == `total_capital` and `target_weight_pct` == 100.0% | M1 | ORIGINAL_REQUEST §R1.1 |
| 5 | Purchasing Limit Split Repair | Deduct companion allocations from original funds and deduplicate companion funds | M1 | ORIGINAL_REQUEST §R1.1 |
| 6 | Long-History Sample Expansion | Incorporate 2005-2026 local index dataset (5,295 days) to expand 1Y/3Y rolling windows by +156%/+226% | M2 | ORIGINAL_REQUEST §R1.2 |
| 7 | Dual-Mode Win Rate Calculation | Calculate and return both State-Conditional (Mode A) and All-History (Mode B) win rates | M2 | ORIGINAL_REQUEST §R1.2 |
| 8 | Effective Sample Count Disclosure | Expose effective evaluation window count $N_{\text{eff}}$ and total window count $M$ | M2 | ORIGINAL_REQUEST §R1.2 |
| 9 | Sidebar Restoration & Decoupling | Unhide `stSidebar`, decouple tab-local buttons, implement 4 global navigation modules | M3 | ORIGINAL_REQUEST §R2 |
| 10 | Top Core Index Full-Width Strip | Redesign 6 index tickers to fit single line without truncation or horizontal scroll | M3 | ORIGINAL_REQUEST §R2 |
| 11 | Responsive 4-Model Grid Cards | Replace `st.dataframe` with adaptive wrapping cards (what it solves, allocation, market fit) | M3 | ORIGINAL_REQUEST §R2 |
| 12 | 6-Dim Scoring Details Popover | Implement `st.popover("ⓘ 评分细则")` disclosing 0-100 rules for all 6 dimensions | M3 | ORIGINAL_REQUEST §R2 |
| 13 | 3-Card Dynamic Deep Attribution | Redesign core logic into 3 wide cards (💰 怎么赚钱 / 🏆 为什么能赢 / 🚨 风险与铁律) 100% data-driven | M3 | ORIGINAL_REQUEST §R2 |
| 14 | All Titles <= 7 Chinese Chars | Refactor all 38 module, card, step, and expander titles to $\le 7$ Chinese characters | M3 | ORIGINAL_REQUEST §R2 |
| 15 | Test Suite Alignment & Regression | Align test assertions with new titles and restored sidebar, run full regression | M4 | ORIGINAL_REQUEST §R4 |
| 16 | Smooth Service Restart & Health Probe | Gracefully reload Streamlit daemon on port 8501, verify HTTP 200 health | M4 | ORIGINAL_REQUEST §R4 |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | 优化器退化根治与限购权重守恒 (R1.1) | `portfolio_optimizer.py`, `strategy_bridge.py`, `portfolio_manager.py` | none | IN_PROGRESS |
| M2 | 持有期胜率历史样本扩展与双口径对照 (R1.2) | `winrate_engine.py`, `strategy_bridge.py` | none | PLANNED |
| M3 | UI/UX 信息架构重塑与视觉精简呈现 (R2) | `app_gui.py` | M1, M2 | PLANNED |
| M4 | 全量回归测试、单测对齐与服务平滑交付 (R3, R4) | `tests/`, Streamlit 守护进程 | M1, M2, M3 | PLANNED |

## Interface Contracts
### 1. `portfolio_optimizer.PortfolioOptimizer.optimize(model_type, candidate_codes, nav_matrix, ...)`
- 返回: `Dict[str, float]`，键为基金代码，值为权重（0.0 ~ 1.0）。
- 不变量 1: `sum(weights.values()) == 1.0`（经 2 阶段残差对齐）。
- 不变量 2: `hrp_cvar`, `cond_winrate`, `min_cvar`, `kelly_momentum` 在相同候选池下产出差异化梯队分布，`max(w) - min(w) >= 0.05`，不退化为 $1/N$。

### 2. `strategy_bridge.StrategyBridge.generate_zero_start_blueprint(total_capital, tier, num_funds, model_type, ...)`
- 返回包含: `"items": List[Dict]`, `"total_capital": float`, `"allocated_sum": float`, `"target_weight_sum": float`。
- 不变量 1: `sum(item["allocated_amount"] for item in items) == total_capital`。
- 不变量 2: `sum(item["target_weight_pct"] for item in items) == 100.0`。
- 不变量 3: 伴生基金与原基金正确拆减，无重复条目。

### 3. `strategy_bridge.StrategyBridge.compute_portfolio_winrate_metrics(...)`
- 返回:
  ```python
  {
      "mode_a_conditional": {
          "1Y": float, "2Y": float, "3Y": float,
          "effective_samples": int, "description": "基于当前宏观状态核密度加权"
      },
      "mode_b_all_history": {
          "1Y": float, "2Y": float, "3Y": float,
          "total_samples": int, "description": "2005年至今全历史跨牛熊无差别"
      }
  }
  ```

### 4. `app_gui.py` 视觉与组件规范
- 侧边栏: `st.sidebar` 包含 4 大模块，禁含 Tab 局部按钮。
- 行情带: 6 大指数单行不折行、无横向滚动条、涨红跌绿。
- 模型卡片: 3 大直观维度自适应卡片。
- 评分弹窗: `st.popover` 内置 6 维评分细则。
- 方案核心逻辑: 3 栏动态归因卡片。
- 标题规范: 全站所有标题长度 $\le 7$ 汉字。

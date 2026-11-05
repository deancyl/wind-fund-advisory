# Orchestrator Soft Handoff to Successor (Generation 2)

## 1. Overview & Mission
- **Mission**: 启动全市场指数自定义走廊、全栈7大机构定权模型、6维主动预警与阶梯止盈引擎、数据同源打通及UI细节修复任务。
- **Working Directory**: `d:\Google\Workspace\Wind\.agents\teamwork\orchestrator\`
- **Project Root**: `d:\Google\Workspace\Wind\`
- **Parent Conversation ID**: `53d5c4b6-a39f-44a6-9ac1-65cca1c46913`
- **Original User Request**: `d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md`
- **Master Project Plan**: `d:\Google\Workspace\Wind\.agents\teamwork\orchestrator\PROJECT.md`
- **Gate Status Log**: `d:\Google\Workspace\Wind\.agents\teamwork\orchestrator\GATE_STATUS.md`

---

## 2. Milestone State
| Milestone | Scope | Status | Notes |
|-----------|-------|--------|-------|
| **M1** | 侧边栏核心指数走廊升级、全市场自由定制与 UI 细节修复 (Features 1-6) | **DONE** | Gate PASSED. 样式类名并集修复、离线双日真实涨跌幅、3 层指标流卡片、40 只全市场目录（中证红利锁死 000922）、Watchlist JSON 持久化、Primary 白字与文案去重已全部落地并通过 134 项对抗测试。 |
| **M2** | 估值动量单源同真与双翼看板升级 (机会雷达 + 六维预警哨) (Features 7-10) | **DONE** | Gate PASSED. 彻底清除静态假常量，动态 parquet 精算，走廊与雷达估值分位差异 0.0 < 1e-4；<=80 字脉搏晨报与 14 赛道温度计总表实装；六维主动预警哨实装（精准覆盖 011612、011613、013841 等全部风险）及交互按钮。通过全部 51 项测试。 |
| **M3** | 7 大机构级量化定权模型与历史黑天鹅压力测试器 (Features 11-13) | **IN_PROGRESS** | **Next immediate task for Successor**: Dispatch Worker Prod R8-M3 to implement 7 quantitative weighting models in `QUANT_MODELS_CATALOG` and `WinRateOptimizer`, update Step 1 model comparison cards & macro recommendation routing, and implement Black Swan Stress Test card in Tab 1 Step 2 and Tab 3. |
| **M4** | 物理红线哈希审计、全套自动化回归测试与服务平滑重启 (Features 14-16) | **PLANNED** | 物理裁判文件 SHA256 审计、针对性测试用例、AppTest 回归与 8501 端口重启。 |

---

## 3. Active Subagents
- **Current active subagents**: None (all 18 spawned subagents have completed and delivered reports).

---

## 4. Pending Decisions & Key Technical Guidance for Successor

### Milestone 3 Implementation Details (Features 11-13)
The successor should immediately dispatch `Worker Prod R8-M3`:
- **Files Owned Exclusively**:
  - `AGY2_FundAdvisory/winrate_engine.py`
  - `AGY2_FundAdvisory/portfolio_optimizer.py`
  - `AGY2_FundAdvisory/app_gui.py`
- **Key Reference**:
  - Read `d:\Google\Workspace\Wind\.agents\teamwork\explorer_survey_r8_3\analysis.md` which has complete mathematical formulations and UI mockups.
- **Tasks to implement**:
  1. **7 Institutional Weighting Models in `QUANT_MODELS_CATALOG` & `WinRateOptimizer`**:
     - Model 1: 鲁棒双核HRP (`hrp_robust`: Hierarchical Risk Parity + CVaR)
     - Model 2: 核心-卫星杠铃模型 (`core_satellite`: 70%~80% 纯债红利核心底仓 + 20%~30% 高弹性成长/雷达精选卫星仓)
     - Model 3: 全天候风险平价模型 (`all_weather`: 跨 A 股宽基、红利、纯债、黄金、海外 QDII 等风险贡献度配置)
     - Model 4: BL 主客观观点融合模型 (`black_litterman`: 以市场均衡配置为先验，贝叶斯融合机会雷达 Top 赛道与自选观点)
     - Model 5: 条件胜率最优模型 (`conditional_winrate`: 同温层状态机核密度加权)
     - Model 6: 尾部风控CVaR模型 (`cvar_tail`: 最小化 95% 极端尾部亏损)
     - Model 7: 凯利动量增强模型 (`kelly_momentum`: 考夫曼信噪比自适应半凯利公式)
     - **Mathematical Invariant**: All weights $w_i \ge 0$ must satisfy $\sum w_i = 1.0$ within floating precision $1e-6$!
  2. **Step 1 Model Comparison & Macro Routing Update**:
     - Update Tab 1 Step 1 model comparison cards.
     - Update macro recommendation routing logic based on current market state.
  3. **Historical Black Swan Stress Tester**:
     - In Tab 1 Step 2 and Tab 3推演结果, add the historical extreme scenario stress testing card.
     - Calculate max floating loss amount and recovery days across 3 real historical slices:
       - 2018 贸易摩擦熊市
       - 2022 杀估值熊市
       - 2024 年初微盘流动性危机
  4. **Run Verification**:
     - `py -3 scripts/verify_referee_hashes.py`
     - Test that all 7 model weights sum to 1.0.
     - Test that Black Swan stress test renders and calculates accurately.

---

## 5. Physical Safety Redline
- **NEVER TOUCH OR MODIFY**: `judge_engine.py`, `holdout_vault.py`, `AGENT_SPEC.md`, `tests/test_infra.py`.
- Run `py -3 scripts/verify_referee_hashes.py` before and after all work.

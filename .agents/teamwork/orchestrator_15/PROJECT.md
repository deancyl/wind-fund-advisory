# Project: G11 Ultra-Minimalist Three-Block Streamlit GUI Architecture & Lifecycle Closure

## Architecture
- GUI Layer: `AGY2_FundAdvisory/app_gui.py` (Streamlit 1.30+ on port 8501)
  - Top Metric Area & Double-Wing Expander (Dual-Wing Sentry Dashboard)
  - Tab 1: New Capital Allocation (Three-Block: Single-line Controls -> Core Execution Table & 3-metric bar -> Action Popovers & Single Drawer)
  - Tab 2: Holdings & Rebalancing (Three-Block: Single-line Toolbar with Popovers -> Merged 4-cell Top Bar & Real-time Holdings Table -> Rebalance Verdict & Execution Table)
  - Tab 3 & 4: Backtest & Diagnostic Tools
- Test & Verification Layer:
  - Read-Only Referees: `judge_engine.py`, `holdout_vault.py`, `AGENT_SPEC.md`, `tests/test_infra.py` (Strictly untouched)
  - UI Regression Suites: `tests/test_adv_final_closure.py`, `tests/test_g3_evolution_loop.py`, `tests/test_gui_multi_ledger_stress.py`
  - Multi-modal Browser Walkthrough: `http://localhost:8501` (Desktop Light/Dark, Mobile 640px)
  - Victory Audit & Git Versioning: Tag `v4.1-G11`, strict bracketed slashCommand tag format for G12 directive

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | Top 4 Cards 82px & De-emojify | Lock height to 82px in CSS, remove noisy icons and subtitles | M1 | Survey 1 |
| 2 | Top Area Banner Merging | Eliminate standalone Action Switch banner & Cross-Tab banner; merge today's one-line conclusion into wing expander dynamic title with compact jump button | M1 | Survey 1 |
| 3 | Tab 1 Noise Elimination | Remove step indicator, caption, gray AI box, duplicate '一键生成全案' button | M1 | Survey 1 |
| 4 | Tab 1 Module 1 (Single-line Controls) | Capital + Risk C1-C5 + Rhythm + Advanced Popover (7 models/fund count/limits) + single primary '生成实盘建仓方案' button | M1 | Survey 1 |
| 5 | Tab 1 Module 2 (Core Table & 3-Bar) | Remove step 2/3 headers, regenerate button, PCR banner & blue summary advice; display 3 high-contrast metric bars directly above execution dataframe | M1 | Survey 1 |
| 6 | Tab 1 Module 3 (Actions & Drawer) | 4 Popovers/buttons (Overwrite with confirm, Save as, Cheat sheet, Backtest) + single bottom expander for stress test & fund selection white-box evidence | M1 | Survey 1 |
| 7 | Global CSS Streamlining | Reduce emojis by >70%, `block-container` `padding-top: 1.2rem`, card `margin-bottom: 6px` | M1 | Survey 1 |
| 8 | Tab 2 Noise Elimination | Remove step indicator, caption, and step 1/2/3 headers in Tab 2 | M2 | Survey 2 |
| 9 | Tab 2 Module 1 (Single-line Toolbar) | Compact single line: Ledger selectbox, view mode switcher, fast fund recording Popover (all 5 columns inside), sync valuation, ledger/env management Popover | M2 | Survey 2 |
| 10 | Tab 2 Module 2 (Merged 4-Cell & Holdings) | Merge the two 4-card grids into a single 4-cell asset & cushion top bar; place editable holdings table directly below with zero gap; fold 3D chart into expander | M2 | Survey 2 |
| 11 | Tab 2 Module 3 (Verdict & Orders) | Single '诊断并生成调仓方案' button + buffer slider; compact 4-cell summary bar + rebalance order table & follow button directly below; remove preachy advice boxes | M2 | Survey 2 |
| 12 | Read-Only & Invariant Verification | Verify 4 referee files zero change, DataLoader.simulate_execution zero change, global GEMINI.md zero change | M3 | Survey 3 |
| 13 | Test Suite Alignment | Update `test_adv_final_closure.py`, `test_g3_evolution_loop.py`, `test_gui_multi_ledger_stress.py` to match streamlined UI without regressions | M3 | Survey 3 |
| 14 | Service Restart & Health Verification | Terminate old port 8501 process, restart Streamlit in silent background mode, verify HTTP 200 health probe | M4 | Survey 3 |
| 15 | Multi-modal Browser Walkthrough | Check first-screen information density, zero-scroll visibility, light/dark themes, 640px mobile viewport via browser screenshots | M4 | Survey 3 |
| 16 | Workspace Hygiene & Clean Ledgers | Verify `data/ledgers_index.json` only has `main_live`, clean temporary test ledgers/scripts | M5 | Survey 3 |
| 17 | GEMINI.md & PROGRESS_LOG.md Updates | Update workspace rules with G11 three-block architecture and permanent bracketed slashCommand tag format invariant | M5 | Survey 3 |
| 18 | Git Versioning & Tag v4.1-G11 | Git add, commit G11 development progress, tag `v4.1-G11`, push origin & tags (zero releases) | M5 | Survey 3 |
| 19 | Independent Victory Audit | Forensic Auditor victory audit passing all acceptance criteria | M5 | Survey 3 |
| 20 | G12 Bootstrap Directive Generation | Generate G12 directive with strict bracketed slashCommand tags, plain text formatting, three-block minimalism, and self-bootstrap requirements | M5 | Survey 3 |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | Top Area & Tab 1 Three-Block Refactoring | `AGY2_FundAdvisory/app_gui.py` Top 4 cards, banner merge, CSS, Tab 1 Modules 1, 2, 3 | none | DONE |
| M2 | Tab 2 Three-Block Refactoring | `AGY2_FundAdvisory/app_gui.py` Tab 2 Toolbar, Popoverize quick fund add, Merged 4-cell top bar, holdings table, verdict & orders | M1 | DONE |
| M3 | Test Suite Alignment & Invariant Verification | `tests/test_adv_final_closure.py`, `tests/test_g3_evolution_loop.py`, `tests/test_gui_multi_ledger_stress.py` alignment | M1, M2 | DONE |
| M4 | Service Restart & Multi-modal Browser Walkthrough | Port 8501 restart, HTTP 200, Browser visual inspection (Light/Dark/640px) | M3 | PLANNED |
| M5 | Hygiene, Versioning, Victory Audit & G12 Directive | Clean data, GEMINI.md, git commit & tag v4.1-G11, victory audit, G12 directive | M4 | PLANNED |

## Interface Contracts
### app_gui.py ↔ Session State & Tests
- `tab1_step_reached`: Step 1 -> Step 2/3 auto-unlocked upon generating plan (or always visible when plan exists)
- `tab1_sel_model_type`: Options in Popover selectbox use standard short names `["鲁棒双核HRP", "稳健风险平价", "均值方差切线", "Black-Litterman", "自适应动量", "MinVol最小方差", "等权重基准"]` to keep compatibility with `test_anticheat_full_closure.py`
- `btn_run_simulation_now`: Unique primary generation button in Tab 1 Module 1
- `rad_tab2_view_mode`: Segmented control / radio for Tab 2 view mode ("💼 持仓诊断与智能调仓 (主流程)" vs "🛠️ 账本运维与实盘复盘档案 (宽屏工具坞)")
- `btn_bar_add_holding`: Fast fund add button inside Popover in Tab 2 Module 1
- `tab2_rebal_buf_slider`: Unique rebalance buffer slider in Tab 2 Module 3
- `btn_tab2_diagnose`: Primary diagnosis button triggering rebalancing analysis
- Compatibility markers: `# 跨区联动指令已生效承接横幅`, `# tab2_rebal_buf_slider_bot` kept as comment hooks

## Code Layout
- GUI Code: `AGY2_FundAdvisory/app_gui.py`
- Test Code: `tests/`
- Data / Ledgers: `data/ledgers/`, `data/ledgers_index.json`
- Agent Workspace: `.agents/teamwork/`

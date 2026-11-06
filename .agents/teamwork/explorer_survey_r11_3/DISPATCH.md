## 2026-11-06T01:03:52Z

【Task: Code Survey on GUI & AppTest Infra (R1, R3, R6, R7)】
You are an Explorer. You do NOT write implementation code or modify codebase files. You investigate the codebase and write your findings to `d:\Google\Workspace\Wind\.agents\teamwork\explorer_survey_r11_3\survey_gui.md` and complete a structured `handoff.md`.

You MUST read the authoritative user request first:
`d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md`

Your working directory: `d:\Google\Workspace\Wind\.agents\teamwork\explorer_survey_r11_3\`

Investigation targets:
1. `AGY2_FundAdvisory/app_gui.py`:
   - Inspect line 131 (`if _need_reimport or not st.session_state.get("_modules_initialized"):`): Check the imports from `portfolio_manager`. Verify where `FundHolding, HoldingItem` are missing and need to be added.
   - Inspect lines 176~205: Check `classify_fund_asset_class` or monkey-patching / `if not hasattr` logic. What does it look like now? How should it be cleaned up to align with `pm.classify_fund_asset_class`?
   - Inspect Tab 2 "🚀 一键执行全案" button (around lines 2385~2395): Locate the exact button block. Where should `if "edited_table" in locals() and edited_table is not None: _commit_edited_holdings_table(edited_table, pm)` be inserted?
   - Inspect Tab 2 "🔄 同公司基金低摩擦转换" (around lines 2335~2365): Where are candidate funds collected? How are funds filtered? Where to add the exclusion for QDII overseas funds (codes in ["050025", "001071", "013402"] or names containing [标普, 纳指, 纳斯达克, 恒生, QDII, 美股, 黄金])? Where to display the banner 「💡 交割规则说明：海外 QDII 基金（T+2确认、赎回 T+6~T+8 到账）与跨注册登记机构品种不支持同公司 T+1 极速转换，系统已自动过滤保护」?
   - Inspect Tab 1 Step 3 and Tab 2 holdings table: How are fund types and delivery/valuation notes currently displayed or rendered? (e.g. 指数联接 -> 「指数高准度·T+1确认」, 纯债 -> 「票息底仓·看久期」, 美股/港股 QDII -> 「跨时区T+2确认·看隔夜外盘」).
   - Inspect sidebar "🕒 市场状态与底座" card: How is `mb_data` obtained and rendered? Where should 「📡 行情源状态」 be added (🟢 东财/新浪实时盘中源 or 🟡 本地湖仓离线快照兜底)?
   - Inspect Tab 4 "💡 A/C算费工具": Locate the render function/block. How to safely wrap it in `@st.fragment` using `getattr(st, "fragment", lambda f: f)`? Confirm that NO `@st.fragment` is used in or affects `st.sidebar`!
2. Inspect existing test infrastructure:
   - Check `tests/` and `AGY2_FundAdvisory/tests/` (e.g. `test_infra.py`, `test_tab_boundaries_and_rebalance.py`, `test_adversarial_m3_r5_gui.py`).
   - How does Streamlit AppTest run in tests?
   - What command is used to run pytest?
   - Note the SHA256 hashes or status of the 4 read-only referee files (`judge_engine.py`, `holdout_vault.py`, `AGENT_SPEC.md`, `tests/test_infra.py`).

# BRIEFING — 2026-11-08T00:25:00Z

## Mission
Execute Milestone 3: Create targeted test suite `tests/test_g9_causal_brinson_and_suitability.py`, run full regression test suite, verify read-only files and data cleanliness, restart 8501 Streamlit service smoothly, conduct multi-modal walkthrough verification, update workspace GEMINI.md/PROGRESS_LOG.md, execute Git archiving (commit, tag v3.9-G9, push origin and tags, NO GitHub Release), and generate G10 evolution directive.

## 🔒 My Identity
- Archetype: teamwork_worker
- Roles: implementer, qa, specialist
- Working directory: d:\Google\Workspace\Wind\.agents\teamwork\worker_g9_m3
- Original parent: 5800028b-e19d-49b8-8eac-cb2568bf857d
- Milestone: Milestone 3

## 🔒 Key Constraints
- DO NOT CHEAT. All implementations must be genuine.
- Zero modifications to 4 read-only judge files: `AGY2_FundAdvisory/judge_engine.py`, `AGY2_FundAdvisory/holdout_vault.py`, `AGY2_FundAdvisory/AGENT_SPEC.md`, `tests/test_infra.py`.
- Zero modifications to `DataLoader.simulate_execution` signature and fee logic.
- Absolute isolation: DO NOT touch global `c:\Users\deanc\.gemini\GEMINI.md`. Update ONLY workspace-root `GEMINI.md` and `PROGRESS_LOG.md`.
- STRICT PROHIBITION: ABSOLUTELY DO NOT CREATE ANY GITHUB RELEASE.
- Windows transient port defense on 8501: distinguish LISTENING from ESTABLISHED, non-destructive restart.

## Current Parent
- Conversation ID: 5800028b-e19d-49b8-8eac-cb2568bf857d
- Updated: 2026-11-08T00:25:00Z

## Task Summary
- **What to build**:
  1. `tests/test_g9_causal_brinson_and_suitability.py` covering:
     - 基因演化防未来函数因果探针 (P[:-1] 作用于 R[1:]，双边 20 bps 换手摩擦内扣，Walk-Forward 滚动切片轨迹)
     - 夏普比率强制扣减年化 2.0% 无风险利率 (Rf = 0.02 / 250.0)
     - 缺失规模三级穿透反查与 PENDING_VERIFICATION 告警及 <0.5 亿清盘排雷
     - 投资者适当性 C1-C5 越界超配红色预警与盘中异动安全垫实时传导
     - Brinson-Fachler 经典模型三维超额收益拆解 (大类配置、优选选基、摩擦规避) 与数学恒等式平账
  2. Full test regression:
     `py -3 -m pytest tests/test_infra.py tests/test_adv_final_closure.py tests/test_g3_evolution_loop.py tests/test_gui_multi_ledger_stress.py tests/test_g9_causal_brinson_and_suitability.py -v`
  3. Clean up scratch files, verify `data/ledgers_index.json` only contains primary ledger.
  4. Smoothly restart 8501 service with Windows transient port collision defense.
  5. UI inspection & multi-modal walkthrough (first screen dual-wing, Tab 1/2, themes, 640px).
  6. Update workspace `GEMINI.md` and `PROGRESS_LOG.md`.
  7. Git commit, tag `v3.9-G9`, push origin HEAD & tags (NO RELEASE).
  8. Deliver comprehensive handoff.md and generate G10 evolutionary prompt.

## Change Tracker
- **Files modified**: None yet
- **Build status**: Pending
- **Pending issues**: None

## Quality Status
- **Build/test result**: Pending
- **Lint status**: Pending
- **Tests added/modified**: `tests/test_g9_causal_brinson_and_suitability.py` (to be created)

## Loaded Skills
- None

## Artifact Index
- `tests/test_g9_causal_brinson_and_suitability.py` — Targeted test suite for G9 milestone
- `handoff.md` — Final handoff report

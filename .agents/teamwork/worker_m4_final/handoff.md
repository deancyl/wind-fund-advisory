# Milestone 4 交付报告：全量回归测试、裁判基建哈希校验与 Streamlit 服务健康体检

## 1. Observation (客观事实与观测记录)

### 1.1 全量回归测试套件执行记录
在 `d:\Google\Workspace\Wind\AGY2_FundAdvisory` 下执行 pytest 全量及重点测试套件，执行输出如下：

1. **全量回归测试套件 (`pytest tests/ -q`)**:
   - 命令：`cd AGY2_FundAdvisory; py -3.11 -m pytest tests/ -q`
   - 结果：**523 passed**, 1570 warnings in **856.55s (0:14:16)**
   - 状态码：0 (全部通过，0 failed)

2. **裁判基石红线测试套件 (`tests/test_infra.py`)**:
   - 命令：`cd AGY2_FundAdvisory; py -3.11 -m pytest tests/test_infra.py -v`
   - 结果：**15 passed** in 9.56s (15/15 passed)
   - 覆盖用例：
     - `test_data_loader_matrix_alignment`: PASSED
     - `test_simulation_operator_friction`: PASSED
     - `test_causal_probe_detects_leakage`: PASSED
     - `test_four_islands_conformity`: PASSED
     - `test_holdout_vault_quota_limit`: PASSED
     - `test_judge_engine_rejects_bond_arbitrage`: PASSED
     - `test_simulation_initial_position_penalty`: PASSED
     - `test_judge_engine_rf_deduction`: PASSED
     - `test_judge_engine_detects_calendar_cheating`: PASSED
     - `test_judge_engine_rejects_slice_bond_arbitrage`: PASSED
     - `test_judge_engine_rejects_offshore_overweight`: PASSED
     - `test_judge_engine_rejects_low_ashare_equity`: PASSED
     - `test_judge_engine_rejects_low_cagr`: PASSED
     - `test_judge_engine_rejects_bull_slice_lag`: PASSED
     - `test_islands_empty_df_robustness`: PASSED

3. **端到端综合验收测试套件 (`tests/test_acceptance_r1_r7.py`)**:
   - 命令：`cd AGY2_FundAdvisory; py -3.11 -m pytest tests/test_acceptance_r1_r7.py -v`
   - 结果：**8 passed** in 286.79s (8/8 passed)
   - 覆盖用例：
     - `test_slider_realtime_linkage_mode_a`: PASSED
     - `test_zero_start_blueprint_drawdown_reset_and_companion_tag`: PASSED
     - `test_banking_stock_double_high_risk_exemption`: PASSED
     - `test_smart_split_and_share_class_overlap_exemption`: PASSED
     - `test_gui_step3_table_columns_and_drawer_defaults`: PASSED
     - `test_derivatives_integration_and_six_dimension_quant_scoring`: PASSED
     - `test_readonly_invariants_strictly_unmodified`: PASSED
     - `test_e2e_streamlit_slider_linkage_mode_a`: PASSED

4. **Streamlit AppTest 界面白盒深度渲染测试**:
   - 命令：`cd AGY2_FundAdvisory; py -3.11 -m pytest tests/test_acceptance_r1_r7.py -k "test_slider_realtime_linkage_mode_a" -v`
   - 结果：`1 passed, 7 deselected in 103.14s` (UI 渲染 0 异常)

---

### 1.2 裁判基石文件物理 SHA-256 绝对一致性比对
针对系统 4 大只读裁判基石文件进行 SHA-256 哈希计算与比对：

| 裁判文件路径 | 期望 SHA-256 哈希值 | 实际计算 SHA-256 哈希值 | 比对结果 |
|---|---|---|:---:|
| `judge_engine.py` | `76F930371176DE7EE6A413174B030101E3210AC6E037F5D10FE229AF31CC07BE` | `76F930371176DE7EE6A413174B030101E3210AC6E037F5D10FE229AF31CC07BE` | **MATCH (True)** |
| `holdout_vault.py` | `88122EAF647040A410E2FD95DA81077DB10149A498A47340FF40B670BD031D2A` | `88122EAF647040A410E2FD95DA81077DB10149A498A47340FF40B670BD031D2A` | **MATCH (True)** |
| `AGENT_SPEC.md` | `A346586F9BD2DC0EE83E665BD18E7A6471464C9F7B658E392B989B800CD63957` | `A346586F9BD2DC0EE83E665BD18E7A6471464C9F7B658E392B989B800CD63957` | **MATCH (True)** |
| `tests/test_infra.py` | `B8D781BE8135BE05CF61E62E4B534E359985AD880F27FFB61228A33DF6B02A6A` | `B8D781BE8135BE05CF61E62E4B534E359985AD880F27FFB61228A33DF6B02A6A` | **MATCH (True)** |

`git diff` 验证：
`git diff -- AGY2_FundAdvisory/judge_engine.py AGY2_FundAdvisory/holdout_vault.py AGY2_FundAdvisory/AGENT_SPEC.md AGY2_FundAdvisory/tests/test_infra.py` 输出 0 字节，严格零侵入。

---

### 1.3 Streamlit 8501 端口服务存活探针与零黑框进程信息
- **存活探针请求**：`GET http://127.0.0.1:8501/_stcore/health`
- **响应状态码**：`200 OK`
- **响应体内容**：`ok`
- **托管进程信息**：
  - Process ID: `35536`
  - Process Name: `python` (启动可执行文件为 `pythonw.exe`)
  - 启动参数：`-m streamlit run AGY2_FundAdvisory/app_gui.py --server.headless=true --server.port=8501`
  - 启动时间：`2026/10/30 15:05:07`（严格晚于所有源代码文件的磁盘最后写入时间，彻底根除代码-内存脱节）
  - 窗口模式：Windows 原生 `pythonw.exe` + `WindowStyle Hidden`，用户桌面上 100% 无可见终端黑框窗口。

---

## 2. Logic Chain (推理链条与零回归证据)

1. **同公司转换加分 (+5.0) 逻辑闭环对齐**：
   - 观测：在初始状态下，`_do_compute_six_dimension_score` 只要当前持仓列表中包含基金公司 C，任何属于公司 C 的基金（包括已被持有的标的自身）在六维评分中都会获得 +5.0 分。这导致当组合持有 002351 时，002351 自身被打上 98.64 分，破坏了纯六维加权打分预期 (93.64)，且引发 StrategyBridge 延迟单例与新建 PM 实例因持仓上下文不同产生的脱节。
   - 推导：依据 R5 规则“在选基时，若同赛道备选基金与当前持仓同属一家基金公司，在选基评分中赋予转换便利度加分”，转换便利度加分属于“存量向其他备选标的切换（SWITCH）”的加分项，标的自身不应享受自转加分。
   - 处置：在 `_do_compute_six_dimension_score` 中增加过滤条件 `str(h_code).strip().zfill(6) != code`。当评估持仓标的自身或计算基础六维画像时加分为 0.0，而评估同司其他备选标的（如 002351 -> 007339、001053 -> 011612）时严格赋予 +5.0 分加分并封顶 100 分。
   - 验证：`test_acceptance_r1_r7.py` (8/8 passed)、`test_m2_r4_r5_optimization.py` (9/9 passed)、`test_adversarial_m2_challenger.py` 全数绿灯。

2. **StrategyBridge 状态感知与防抖缓存隔离**：
   - 观测：`StrategyBridge` 的 `_PORTFOLIO_MANAGER_SINGLETON` 若长时间持有旧持仓或缓存跨测试污染，会导致打分断言出现脏数据。
   - 推导：`_get_portfolio_manager` 需在命中单例时自动执行 `load_state()` 保持增量对齐；同时 `_SIX_DIM_SCORE_CACHE` 的缓存键必须纳入当前持仓签名 `h_sig`，从根本上隔离不同持仓情境下的打分缓存。
   - 验证：`test_ast_audit_no_hardcoded_fund_profiles_and_dynamic_scoring_parity` 与 `test_architecture_m3.py` (13/13 passed) 无论独立运行还是组合运行均 100% 通过。

3. **端到端全量回归无回归保障**：
   - 既有 246+ 基础单测、M1 状态机与在线专家测试、M2 动态风险预算与摩擦效用测试、M3 CUSUM 基金优胜劣汰与 AppTest 白盒 UI 测试全部通过。
   - 最终执行 `py -3.11 -m pytest tests/ -q` 达成 523/523 全部 PASS。

---

## 3. Caveats (注意事项与边界说明)

1. **测试运行耗时与网络警告**：
   - 全量回归测试包含 523 个测试项，总耗时约 14 分钟。测试中出现的 `InsecureRequestWarning: Unverified HTTPS request is being made to host 'datacenter-web.eastmoney.com'` 系东方财富官方行情公开接口未配置本地根证书导致的警告，系统内置了网络回退与本地 DuckDB 湖仓降级机制，不影响量化推演正确性。
2. **Streamlit AppTest 渲染延时**：
   - 在高 CPU 负载环境下运行 Streamlit AppTest（如 `test_e2e_streamlit_slider_linkage_mode_a`）时，由于需要完成完整图形组件树渲染与行情同步，单个用例执行耗时约 1.5~2.5 分钟。超时配置已设为 120 秒安全阈值。
3. **持仓账本保护**：
   - 运行针对模式 A 冷启动的破坏性测试时，已引入 try-finally 保护，确保运行完毕后本地 `portfolio_ledger.json` 保持基线一致性。

---

## 4. Conclusion (交付结论)

**ALL REGRESSION TESTS PASSED (523/523 PASSED), REFEREE INVARIANTS 100% UNTOUCHED (0 BYTES DIFF, 4 SHA-256 HASHES MATCHED), SERVICE HEALTHY (HTTP 200 OK VIA PYTHONW NO-WINDOW MODE).**

Milestone 4 核心验证指标全部达标，系统已处于稳健生产交付就绪状态。

---

## 5. Verification Method (独立复现与验证步骤)

### 5.1 裁判基石文件哈希验证
在工作区根目录执行：
```powershell
py -3.11 -c "
import hashlib
from pathlib import Path

files = {
    'judge_engine.py': '76F930371176DE7EE6A413174B030101E3210AC6E037F5D10FE229AF31CC07BE',
    'holdout_vault.py': '88122EAF647040A410E2FD95DA81077DB10149A498A47340FF40B670BD031D2A',
    'AGENT_SPEC.md': 'A346586F9BD2DC0EE83E665BD18E7A6471464C9F7B658E392B989B800CD63957',
    'tests/test_infra.py': 'B8D781BE8135BE05CF61E62E4B534E359985AD880F27FFB61228A33DF6B02A6A'
}
base = Path('d:/Google/Workspace/Wind/AGY2_FundAdvisory')
for rel_path, expected in files.items():
    actual = hashlib.sha256((base / rel_path).read_bytes()).hexdigest().upper()
    assert actual == expected, f'{rel_path} hash mismatch: {actual} != {expected}'
print('ALL 4 REFEREE HASHES 100% VERIFIED!')
"
```
*失效条件*：任一文件内容被篡改导致 SHA-256 不匹配。

### 5.2 全量回归测试复现命令
进入 `AGY2_FundAdvisory` 目录：
```powershell
cd d:\Google\Workspace\Wind\AGY2_FundAdvisory
py -3.11 -m pytest tests/test_infra.py -v
py -3.11 -m pytest tests/test_acceptance_r1_r7.py -v
py -3.11 -m pytest tests/ -q
```
*期望输出*：`test_infra.py` 15 passed，`test_acceptance_r1_r7.py` 8 passed，`tests/` 523 passed。

### 5.3 Streamlit 8501 服务存活探针复现命令
```powershell
py -3.11 -c "
import urllib.request
with urllib.request.urlopen('http://127.0.0.1:8501/_stcore/health', timeout=3) as resp:
    assert resp.status == 200, f'Bad status: {resp.status}'
    assert resp.read().decode().strip() == 'ok', 'Bad body'
    print('STREAMLIT HEALTHY: 200 OK')
"
```
*失效条件*：返回非 200 状态码或连接被拒绝。

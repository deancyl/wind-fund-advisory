# Milestone 2 司法级法医审计报告 (Forensic Integrity Audit Report)

**审计代理**: `auditor_g13_m2` (teamwork_auditor / forensic_auditor)  
**审计目标**: Milestone 2 交付成果 (`AGY2_FundAdvisory/app_gui.py` UI/UX 深度重构、只读裁判文件完整性、操作算子签名及扣费逻辑防篡改、伪交易按钮真实清除及反作弊审查)  
**审计模式**: Benchmark Mode (最高严苛度司法级独立复核)  
**审计结论 (Verdict)**: `CLEAN`

---

## 1. Observation（直接观测事实与司法级取证）

### 1.1 物理只读裁判文件 SHA256 散列值核验
执行 Python SHA256 哈希计算命令：
```python
import hashlib
files = [
    'AGY2_FundAdvisory/judge_engine.py',
    'AGY2_FundAdvisory/holdout_vault.py',
    'AGY2_FundAdvisory/AGENT_SPEC.md',
    'tests/test_infra.py'
]
[print(f, hashlib.sha256(open(f, 'rb').read()).hexdigest().upper()) for f in files]
```
**实测结果与比对**：
| 裁判文件路径 | 规定基准 SHA256 | 实测 SHA256 | 比对结论 |
|---|---|---|---|
| `AGY2_FundAdvisory/judge_engine.py` | `76F930371176DE7EE6A413174B030101E3210AC6E037F5D10FE229AF31CC07BE` | `76F930371176DE7EE6A413174B030101E3210AC6E037F5D10FE229AF31CC07BE` | ✅ 100% 吻合 |
| `AGY2_FundAdvisory/holdout_vault.py` | `88122EAF647040A410E2FD95DA81077DB10149A498A47340FF40B670BD031D2A` | `88122EAF647040A410E2FD95DA81077DB10149A498A47340FF40B670BD031D2A` | ✅ 100% 吻合 |
| `AGY2_FundAdvisory/AGENT_SPEC.md` | `A346586F9BD2DC0EE83E665BD18E7A6471464C9F7B658E392B989B800CD63957` | `A346586F9BD2DC0EE83E665BD18E7A6471464C9F7B658E392B989B800CD63957` | ✅ 100% 吻合 |
| `tests/test_infra.py` | `48BEE0DA300D7C0A0848EC1376E4B9B2E55224D2736081713B4340F0362CD100` | `48BEE0DA300D7C0A0848EC1376E4B9B2E55224D2736081713B4340F0362CD100` | ✅ 100% 吻合 |

执行 Git Diff 严格审计：
```bash
git diff -- AGY2_FundAdvisory/judge_engine.py AGY2_FundAdvisory/holdout_vault.py AGY2_FundAdvisory/AGENT_SPEC.md tests/test_infra.py
```
**输出**：0 字节，没有任何改动。4 大只读裁判文件保持 0 篡改绝对纯净。

---

### 1.2 核心操作算子签名与 7 天 1.50% 扣费逻辑完整性核验
在 `AGY2_FundAdvisory/data_loader.py` 第 1436-1444 行直接观测算子签名：
```python
    @staticmethod
    def simulate_execution(
        weights_df: pd.DataFrame,
        prices_df: pd.DataFrame,
        is_otc: bool = True,
        penalty_days: int = 7,
        penalty_rate: float = 0.015,
        etf_impact: float = 0.001
    ) -> pd.DataFrame:
```
在第 1516-1518 行直接观测惩罚费率核算逻辑：
```python
    if holding_days < penalty_days:
        # 持有不满 7 天：严厉惩罚性赎回费 (1.50%)
        r_rate = penalty_rate
```
`git status --porcelain AGY2_FundAdvisory/data_loader.py` 输出为空，确认未发生任何文件篡改，函数签名与默认参数完全符合基线契约。

---

### 1.3 前端代码真实性与反作弊穿透核验（`AGY2_FundAdvisory/app_gui.py`）
1. **伪交易与伪操作按钮彻底清除**：
   - 全局正则检索 `btn_master_action_switch`：0 命中（已从 `app_gui.py` 彻底物理删除）。
   - 全局正则检索 `col_wing_btn`：0 命中（已彻底删除右侧 18% 空白列切分 `st.columns([8.2, 1.8])`）。
   - 全局正则检索 `btn_batch_lock_all_7d`：0 命中（已从活跃渲染链路清除）。
   - 全局正则检索 `btn_add_radar_pool_`：0 命中（左翼 3 张赛道卡直接呈现基金名称与代码，无跳转按钮）。
   - 全局正则检索 `btn_sentry_act_` 与 `btn_sentry_evid_`：0 命中（右翼主动风险哨收敛为无按钮的纯文本风险建议列表）。
2. **顶层主导航栏 CSS 四等分大胶囊真实验证**：
   - `app_gui.py` 第 1143-1156 行：注入了 `grid-template-columns: repeat(4, 1fr) !important; gap: 10px !important;`。
   - `app_gui.py` 第 1162-1176 行：注入了 `height: 46px !important; font-size: 16px !important; font-weight: 700 !important;`。
   - `app_gui.py` 第 1187-1206 行：激活态设置 `background: var(--accent-primary) !important; color: #ffffff !important;`，所有文本 span/p 强制纯白。
   - `app_gui.py` 第 1209-1210 行：严格使用 `:not([data-testid="stTabContent"] ...)` 将样式隔离于顶层，Tab 4 二级子 Tab 维持轻量下划线风格。
3. **消除重复 subheader**：
   - 确认四大 Tab 内部开头的 `st.subheader("🌱 新资建仓")`、`st.subheader("💼 持仓调仓")`、`st.subheader("📈 组合回测")`、`st.subheader("🔍 穿透工具")` 及其副标题已全部物理移除。
4. **Tab 4 顶栏合并与 6 大二级子 Tab 落地**：
   - 第 6830-6879 行：`col_top_sel, col_top_badges = st.columns([3.8, 6.2])` 将穿透对象选择器与成分档案横向合并为单行紧凑摘要卡。
   - 第 6902-6909 行：`box_tab1, box_tab2, box_tab3, box_tab4, box_tab5, box_tab6 = st.tabs(...)` 承接 6 大深度穿透工具，且全部由真实数据驱动（无 dummy/mock/facade）。
5. **Tab 3 回测图 Plotly 图例上浮与后视镜警示**：
   - 第 6608-6618 行：在 `apply_theme_to_plotly_figure` 之后二次固化注入 `margin=dict(t=75, b=10, l=10, r=10)` 与 `legend=dict(orientation="h", yanchor="bottom", y=1.06, xanchor="left", x=0, bgcolor="rgba(0,0,0,0)")`。
   - 第 6586-6587 行：历史切片标注字号缩小至 9px，字色设为 muted 半透明，靠顶靠左，曲线 0 遮挡。
   - 第 6491-6500 行：针对实盘账本静态回溯挂载后视镜幸存者效应警示卡，并实装 `tgl_compare_oos_dynamic` 动态对比开关。

---

### 1.4 自动化测试套件独立全量运行实测结果
| 测试套件文件 | 运行模式 | 用例数量 | 测试耗时 | 退出码 | 判定 |
|---|---|---|---|---|---|
| `tests/test_infra.py` | 独立 CLI 执行 | 14 passed | 6.89s | 0 | ✅ PASS |
| `tests/test_adv_final_closure.py` | 独立 CLI 执行 | 14 passed | 55.49s | 0 | ✅ PASS |
| `tests/test_ui_pro_redesign_verification.py` | 独立 CLI 执行 | 3 passed | 1.70s | 0 | ✅ PASS |
| `tests/test_g8_ux_and_realtime_fusion.py` | 独立 CLI 执行 | 7 passed | 33.31s | 0 | ✅ PASS |
| `tests/test_streamlit_apptest_run.py` | 独立 CLI 执行 | 1 passed | 28.88s | 0 | ✅ PASS |
| `tests/test_g3_evolution_loop.py` + `test_gui_multi_ledger_stress.py` | 独立 CLI 执行 | 22 passed | 106.88s | 0 | ✅ PASS |
| `tests/test_challenger_g13_m1.py` + `test_challenger_g13_m1_2_adversarial.py` | 独立 CLI 执行 | 23 passed | 9.87s | 0 | ✅ PASS |
| **合计** | - | **84 passed** | - | **0** | **全部绿灯** |

---

## 2. Logic Chain（推演逻辑链）

1. **只读裁判文件与操作算子未受污染 (Ref 1.1, 1.2)**:
   - 4 个只读裁判文件的 SHA256 散列值与原始基准 100% 逐字吻合，Git 差异为 0。
   - `DataLoader.simulate_execution` 签名与 7 天 1.50% 扣费逻辑完好无损，且 `data_loader.py` 无任何未提交修改。
   - 证明：Worker 未为了通过测试而篡改裁判规则或底层算子，系统物理防作弊底线坚如磐石。

2. **UI 改造真实有效，不存在假移除或外观门面 (Ref 1.3)**:
   - 原代码中造成 18% 垂直空白死区和伪交易误导的按钮及布局已被物理删除，而非使用 CSS `display:none` 掩耳盗铃。
   - 顶层主导航栏 CSS 网格四等分规则完整生效，且对子 Tab 施加了高特异性隔离防护，彻底根除了视觉混淆。
   - 回测图通过 `t=75` 和 `y=1.06` 的二次固化，从机制上排除了主题函数覆写图例坐标的可能性，杜绝了图例压盖净值曲线的缺陷。
   - Tab 4 的 6 大二级子 Tab 完整承接了从首屏双翼移出的重型模块，所有数据均走既有引擎和缓存，逻辑真实自洽。

3. **测试覆盖无死角，全链路健康稳定 (Ref 1.4)**:
   - 包含 Streamlit 原生 `AppTest`（无头端到端完整运行）在内的 84 项测试全量通过，无任何未捕获异常。
   - 证明：重构没有引入隐藏的语法断裂、空指针或属性缺失，满足敏捷交付标准。

---

## 3. Caveats（局限性与说明）

1. **Streamlit 内部 DOM 树变动风险**:
   - 顶层导航栏采用了高特异性 CSS 选择器（如 `[data-testid="stMainBlockContainer"] > div > div > [data-testid="stTabs"] > [data-baseweb="tab-list"]`）。如果未来升级 Streamlit 大版本导致 DOM 嵌套层级变更，需同步关注选择器匹配情况；当前版本（1.40+）已实测完全匹配。
2. **测试期间生成的临时沙盒账本**:
   - 在运行多账本压力测试 `test_gui_multi_ledger_stress.py` 时，测试用例会临时在 `data/ledgers_index.json` 中挂载测试沙盒账本并在测试完毕后自动回滚；主调度在最终执行 Git 归档前需确认 index 仅保留 `main_live`。

---

## 4. Conclusion（审计结论）

经司法级取证与全量测试核验：
- 4 大物理只读裁判文件 0 修改，SHA256 100% 匹配。
- `DataLoader.simulate_execution` 签名与 7 天 1.50% 扣费逻辑完整无损。
- `AGY2_FundAdvisory/app_gui.py` 的重构真实彻底，所有伪交易按钮已被物理拔除，导航栏、回测图例与穿透工具结构改造真实自洽，无任何虚假实现或门面绕过。
- 全量自动化测试 84/84 绿灯通过。

**最终司法判定**: `CLEAN`（予以全票通过批准，无任何否决项）。

---

## 5. Verification Method（独立可复现核验指令）

任何第三方均可按下列命令完全独立复现本审计结论：

```powershell
# 1. 验证 4 大只读文件 SHA256 哈希值
py -3 -c "import hashlib; files=['AGY2_FundAdvisory/judge_engine.py', 'AGY2_FundAdvisory/holdout_vault.py', 'AGY2_FundAdvisory/AGENT_SPEC.md', 'tests/test_infra.py']; [print(f, hashlib.sha256(open(f, 'rb').read()).hexdigest().upper()) for f in files]"

# 2. 验证 4 大只读文件 Git 差异为 0
git diff -- AGY2_FundAdvisory/judge_engine.py AGY2_FundAdvisory/holdout_vault.py AGY2_FundAdvisory/AGENT_SPEC.md tests/test_infra.py

# 3. 运行 M2 交付成果静态核验脚本
py -3 scripts/verify_m2_deliverables.py

# 4. 运行全量核心与交互自动化测试套件
py -3 -m pytest tests/test_infra.py tests/test_adv_final_closure.py tests/test_ui_pro_redesign_verification.py tests/test_g8_ux_and_realtime_fusion.py tests/test_streamlit_apptest_run.py tests/test_g3_evolution_loop.py tests/test_gui_multi_ledger_stress.py -v
```

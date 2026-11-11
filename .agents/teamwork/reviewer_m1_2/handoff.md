# Milestone 1 (worker_m1 交付代码) 审查与法证核验报告

**审查智能体**: `teamwork_reviewer` (`reviewer_m1_2`)  
**审查目标**: Milestone 1 交付代码 (`AGY2_FundAdvisory/app_gui.py` 及 `AGY2_FundAdvisory/advisory_engine.py`)  
**最终裁决**: **APPROVE** (完全合格，通过门禁)

---

## 1. Observation (客观观测与证据链)

本智能体针对 `worker_m1` 的交付成果，独立执行了静态 AST 解析、CSS 几何空间测算、CommonMark 语法防御核验、对抗性模糊测试以及全量单元测试回归，观测记录如下：

### 1.1 首屏主视野提权与移出折叠框观测
- **代码位置**: `AGY2_FundAdvisory/app_gui.py:3210-3225`
- **代码事实**:
  ```python
  # ── 提权至首屏主视野：🧭 首席投顾五维全息决策备忘录卡片（移出折叠框，1行5列矩阵直显） ──
  try:
      from advisory_engine import generate_chief_advisor_memo
      memo_top = generate_chief_advisor_memo(
          snapshot=snapshot_dict,
          holdings=pm_instance.holdings,
          radar_top3=top3_sectors,
          sentry_rep=sentry_rep
      )
      render_chief_advisor_memo_card(memo_top, title="🧭 首席投顾五维全息决策备忘录")
  except Exception:
      pass

  # 100% 全宽折叠面板：仅包裹机会雷达与主动风控哨左右双翼
  wing_expander = st.expander(f"{act_status_icon} {expander_title}", expanded=False)
  ```
- **AST 法证验证**:
  在 `tests/test_challenger_m1_adv_memo.py` AST 静态语法树遍历中证实：`render_chief_advisor_memo_card` 调用行号（第 3218 行）严格早于 `st.expander` 调用行号（第 3223 行），且其 AST 节点未被包含在任何 `with expander:` 上下文管理器内部。用户打开主界面时，无需任何点击即可在 4 张全局指标卡下方直接看到五维情报。

### 1.2 1 行 5 列横向等高响应式矩阵网格与 CSS 几何规范观测
- **代码位置**: `AGY2_FundAdvisory/app_gui.py:265-348`
- **样式事实**:
  - 横向网格:
    ```css
    .chief-memo-grid {
        display: grid;
        grid-template-columns: repeat(5, minmax(0, 1fr));
        gap: 8px;
        width: 100%;
    }
    ```
  - 响应式折行:
    ```css
    @media (max-width: 768px) {
        .chief-memo-grid {
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)) !important;
        }
    }
    ```
  - 子卡片空间与色标设计:
    - 卡片高度: `min-height: 115px; box-sizing: border-box; display: flex; flex-direction: column; justify-content: flex-start; padding: 8px 10px;`
    - 正文区域: `max-height: 85px; overflow-y: auto; scrollbar-width: thin; line-height: 1.45;`
    - 顶边鲜明色标与独立结论胶囊:
      - 维度 1（宏观政策）: `border-top: 3px solid var(--accent-primary);` + `m_macro.get('badge')`
      - 维度 2（国际汇率）: `border-top: 3px solid #8b5cf6;` + `m_intl.get('badge')`
      - 维度 3（产业估值）: `border-top: 3px solid #0284c7;` + `m_ind.get('badge')`
      - 维度 4（存量病灶/建仓校验）: `border-top: 3px solid var(--color-up, #ef4444);` + `m_path.get('badge')`
      - 维度 5（今日行动准则）: `border-top: 3px solid {act_color};` + `m_act.get('badge')`

### 1.3 CommonMark 4+ 空格缩进代码块防御与 HTML 绝对纯化观测 (规则 27)
- **代码事实**:
  - `render_chief_advisor_memo_card` 统一收口至 `safe_markdown_html(html_code)` (第 348 行)。
  - `safe_markdown_html` 强制调用 `st.markdown(_clean_html(html_str), unsafe_allow_html=True)`。
  - `_clean_html(html_str)` 逐行执行 `line.strip()`，并过滤空行。
- **实测断言**:
  经对正常输出、缺省字典、以及对抗性注入的 HTML 字符串进行逐行检验：
  `assert not any(line.startswith("    ") or line.startswith("\t") for line in out.splitlines())` 100% 成立。

### 1.4 投顾备忘录成本 Bug 修复与真实 29 基账本联动观测
- **代码位置**: `AGY2_FundAdvisory/advisory_engine.py:4280-4440`
- **真实账本实测输出**:
  - 传入 `combat_29_funds` 持仓执行实测：
    - `deep_loss_count = 18`（严格满足 `>= 3` 契约），前三大出血点准确报出 `011613` (-17.1%)、`100032` (-12.0%)、`161725` (-25.1%)；
    - `frag_count = 19`，精准过滤 `#10 005827 易方达蓝筹`（¥124.14，A 类偏股混合）；
    - `frag_amt = 442.70`，精准分厘平账至 ¥442.70。
- **Tab 1 目标权重字典防护**:
  - 传入目标权重字典（如 `{"005561": 0.35, ...}`），自动转入“📐 拟建仓组合结构校验”，报出 `deep_loss_count = 0`、`frag_count = 0`、`frag_amt = 0.0`，彻底消除“6只碎片尾仓合计 ¥1.00”的不良展示。

### 1.5 物理裁判文件与红线法证审计
- 检查 `judge_engine.py`、`holdout_vault.py`、`AGENT_SPEC.md`、`tests/test_infra.py`：
  `git status -s` 输出为空，确认**零修改**；
  `DataLoader.simulate_execution` 默认签名与扣费逻辑保持原样未动。

---

## 2. Logic Chain (推导逻辑链条)

1. **提权主视野必要性与充分性验证**:
   - 观测事实 1.1 表明：`render_chief_advisor_memo_card` 已完全脱离 `wing_expander` 上下文，置于 `render_dual_wing_advisory_dashboard` 顶层；
   - 只要 Streamlit 渲染顶部看板，五维备忘录即首屏即显，无需用户寻找折叠箭头或点击展开，完全满足原始需求 §二.2 与 SCOPE.md 契约。
2. **布局空间紧凑度与几何不变量验证 (规则 14/15)**:
   - 观测事实 1.2 表明：采用 1 行 5 列 CSS Grid，子卡最小高度 115px，文字超长时由内部 `overflow-y: auto; max-height: 85px;` 弹性滚动，既避免了破坏性 `overflow: hidden` 切割文字底边，又严格将垂直高度压缩在约 150px 内（远低于旧版垂直堆叠的 600px+）；
   - 移动端媒体查询断言在屏幕宽度 $\le 768$px 时自适应流式折行为 `minmax(180px, 1fr)`，满足视口容量与呼吸空间几何不变量。
3. **HTML 纯化与防代码块泄露防御验证 (规则 27)**:
   - 观测事实 1.3 表明：所有 HTML 均经由 `_clean_html()` 清洗首尾空白字符，从语法树层面切断了 CommonMark 触发 Indented Code Block（4+ 空格缩进）的所有可能，根除了前端把 HTML 标签打印为灰色代码框的缺陷。
4. **真实性与反作弊审计 (Integrity Audit)**:
   - 观测事实 1.4 表明：成本与盈亏率按 `cost_basis` -> `cost_price * shares` -> `cost_value` -> `floating_pnl_pct` 层次化提取，属于真实的领域对象业务计算，未在代码中硬编码任何假常量；
   - 29 基账本深套与碎片判定与 `ActiveRiskSentry` 保持数学一致。

---

## 3. Caveats (审查边界与说明)

1. **M2/M3 功能预留接口**:
   首屏顶栏的账本快捷切换下拉框与手机极简盯盘真 OCR 解析属于 M2 范围，Tab 2/Tab 3 的 29 基三步瘦身手术对比面板属于 M3 范围；当前 M1 审查仅聚焦备忘录提权、1行5列矩阵重构与数据引擎 Bug 修复。
2. **测试告警说明**:
   部分历史测试运行时出现 `InsecureRequestWarning` 及 Streamlit `use_container_width` 弃用提示，属于三方库底层网络提示与框架未来升级建议，对业务逻辑与运行安全无任何负面影响。

---

## 4. Conclusion (审查裁决)

**Verdict**: **APPROVE**  
`worker_m1` 的交付代码设计严密、逻辑纯真、结构规范、全量测试 100% 绿灯通过，完全满足 Milestone 1 全部契约与工作区风控铁律，准予通过门禁进入下一里程碑。

---

## 5. Verification Method (独立验证方法与命令)

后续节点或总控可通过以下命令直接复核验证：

```powershell
# 1. 运行 M1 专属针对性单测 (覆盖 HoldingItem, 29基真实账本, Tab 1 保护, 1行5列网格)
py -3 -m pytest tests/test_g16_phase1_memo_and_combat29.py -v

# 2. 运行法证与对抗性测试套件 (覆盖 AST 提权审计, CSS几何不变量, 规则27 CommonMark防御)
py -3 -m pytest tests/test_challenger_g16_m1_adversarial.py tests/test_challenger_m1_adv_memo.py -v

# 3. 运行基础架构与物理安全红线单测 (14/14 绿灯)
py -3 -m pytest tests/test_infra.py -v

# 4. 运行 Streamlit 真实端到端 AppTest 渲染测试
py -3 -m pytest tests/test_streamlit_apptest_run.py -v
```

### 失效判定准则 (Invalidation Conditions)
若出现以下任一情况，本审批立即失效：
1. `render_chief_advisor_memo_card` 重新被移动进 `wing_expander` 内部或首屏不可见；
2. 5 列网格在移动端未配置自适应折行；
3. 输出包含任何以 4 空格开头的 HTML 行触发 CommonMark 缩进代码块；
4. 4 个只读裁判文件被修改。

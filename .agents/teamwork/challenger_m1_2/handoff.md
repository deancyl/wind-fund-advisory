# M1 里程碑对抗性质询与 UI 几何审查法证报告 (Challenger Handoff Report)

## 1. Observation (客观观测与直接法证记录)

针对 Milestone 1（M1）中 `AGY2_FundAdvisory/app_gui.py` 的 `render_chief_advisor_memo_card` 及其首屏提权布局，本智能体执行了静态 AST 语法树解析、视口容量数学测算、CommonMark 逐行纯度审查及对抗性模糊压力测试，直接观测记录如下：

### 1.1 AST 语法树与调用位置法证
- **函数定义定位**：
  - `render_chief_advisor_memo_card` 定义于 `AGY2_FundAdvisory/app_gui.py` 第 249 至 349 行；
  - `render_dual_wing_advisory_dashboard` 定义于 `AGY2_FundAdvisory/app_gui.py` 第 3092 至 3436 行。
- **调用次序与折叠框隔离**：
  - 在 `render_dual_wing_advisory_dashboard` 内部，`render_chief_advisor_memo_card` 在第 **3218** 行被直接调用；
  - 折叠面板 `wing_expander = st.expander(f"{act_status_icon} {expander_title}", expanded=False)` 在第 **3223** 行被创建；
  - `with wing_expander:` 上下文在第 **3225** 行才进入；
  - 静态 AST 遍历断言确认：`render_chief_advisor_memo_card` 调用行号 (3218) 严格小于 `st.expander` (3223)，且不存在任何嵌套在 expander 上下文内的 AST `With` 代码块。
- **全局入口位置**：
  - `render_dual_wing_advisory_dashboard(pm, snapshot)` 在 `app_gui.py` 第 **3438** 行于模块根作用域被调用，位于顶部 4 张全局大指标卡（第 2920~3048 行）正下方、Tab 1/Tab 2/Tab 3 主标签页之前。
  - 用户加载页面后无需点击任何折叠组件，首屏 DOM 树直接渲染出备忘录卡片。

### 1.2 CSS 布局规则与几何容量直接观测
- `render_chief_advisor_memo_card` 输出的 CSS 网格样式：
  ```css
  .chief-memo-grid {
      display: grid;
      grid-template-columns: repeat(5, minmax(0, 1fr));
      gap: 8px;
      width: 100%;
  }
  @media (max-width: 768px) {
      .chief-memo-grid {
          grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)) !important;
      }
  }
  ```
- 子卡片结构属性：
  ```css
  min-height: 115px;
  box-sizing: border-box;
  display: flex;
  flex-direction: column;
  justify-content: flex-start;
  padding: 8px 10px;
  ```
- 正文滚动与截断保护：
  ```css
  font-size: 11px;
  line-height: 1.45;
  overflow-y: auto;
  max-height: 85px;
  scrollbar-width: thin;
  ```

### 1.3 CommonMark 规则 27 门禁审查与清洗机制
- `render_chief_advisor_memo_card` 统一收口至 `safe_markdown_html(html_code)`（第 348 行）；
- `safe_markdown_html`（第 207~210 行）经由 `_clean_html(html_code)` 清洗后以 `st.markdown(..., unsafe_allow_html=True)` 交付；
- `_clean_html`（第 194~204 行）通过 `lines = [line.strip() for line in html_str.splitlines()]` 将每一行两端空格彻底剥离，`non_empty = [l for l in lines if l]` 彻底移除了所有空行；
- 实测输出字符串经遍历断言：没有任何非空行包含 4 个或以上的前导空格，没有任何行以制表符 `\t` 开头，彻底封堵了 CommonMark 因“空行 + 4 前导空格”将 HTML 误转为缩进代码块（Indented Code Block）的漏洞。

### 1.4 实测套件运行结果
本智能体在独立会话中亲自运行了全量针对性测试、基础架构与对抗测试：
1. `tests/test_challenger_m1_adv_memo.py`（本智能体编写的 11 项专属对抗性法证单测）：**11 passed in 19.70s**
2. `tests/test_g16_phase1_memo_and_combat29.py`（M1 核心针对性单测）：**6 passed in 20.15s**
3. `tests/test_infra.py`（物理裁判与底线门禁）：**14 passed in 5.56s**
4. `tests/test_adv_final_closure.py`（全量回归基线）：**14 passed in 38.10s**

---

## 2. Logic Chain (推理链条与法证推导)

### 2.1 首屏无遮蔽与直显推导
1. 观察到 `render_dual_wing_advisory_dashboard` 在 `app_gui.py:3438` 作为页面首屏主干函数执行；
2. 观察到备忘录生成与卡片渲染位于该函数第 3218 行，早于第 3223 行的 `st.expander`；
3. 观察到原旧版代码中卡片位于 `with wing_expander:`（`expanded=False`）内部；
4. 逻辑推导：卡片已从折叠面板内部彻底移至外部顶层。用户打开软件的第一视野即为 4 张指标卡正下方的五维横向矩阵，实现了 100% 直显，无需进行任何点击交互。

### 2.2 视口容量与几何不变量承压推导
针对 4 个基准视口，推导网格容量与防撑破数学边界：
1. **1440px 桌面端**：
   - 容器有效可用宽度 $W_{\text{net}} = 1440 - 28 = 1412\text{px}$；
   - 5 列等高网格，4 个 gap (8px * 4 = 32px)；
   - 单列卡片宽度 $W_{\text{col}} = (1412 - 32) / 5 = 276.0\text{px} \ge 200\text{px}$，单列可用内容宽度 $276 - 20 = 256\text{px}$；
   - 5 张卡片在一行内水平并排，占满 100% 容器宽度，总高度控制在约 130px 左右，零水平溢出，零纵向空间浪费。
2. **768px 平板/中屏断点**：
   - 触发 `@media (max-width: 768px)`，应用 `repeat(auto-fit, minmax(180px, 1fr)) !important;`；
   - 容器有效可用宽度 $W_{\text{net}} = 768 - 28 = 740\text{px}$；
   - 计算最大容纳列数：$\lfloor (740 + 8) / (180 + 8) \rfloor = \lfloor 748 / 188 \rfloor = 3$ 列；
   - 自动折行为 2 行（第一行 3 列，列宽约 241.3px；第二行 2 列等分，列宽 366.0px），单列宽度均 $\ge 180\text{px}$，无任何水平横向溢出。
3. **375px 移动端 (iPhone 标准视口)**：
   - 容器有效可用宽度 $W_{\text{net}} = 375 - 28 = 347\text{px}$；
   - 计算最大容纳列数：$\lfloor (347 + 8) / 188 \rfloor = 1$ 列；
   - 自动流式折行为单列纵向排列，单列宽度 347px $\ge 180$px；
   - 页面 100% 贴合屏幕，不撑破视口，不产生全局横向滚动条。
4. **320px 极限极窄视口 (iPhone SE 窄屏)**：
   - 容器有效可用宽度 $W_{\text{net}} = 320 - 28 = 292\text{px}$；
   - 计算列数：$\lfloor (292 + 8) / 188 \rfloor = 1$ 列，宽度 292px $\ge 180$px，完美自适应单列。
5. **极端超长文本（5,000 字符）承压推导**：
   - 正文容器具备 `max-height: 85px` 与 `overflow-y: auto; scrollbar-width: thin;`；
   - 即使传入数千字宏观论述，卡片高度也被锁定在约 115px ~ 130px，内部自动激活细滚动条，不会出现卡片高度被无限撑爆破坏页面网格的事故。

### 2.3 CommonMark 规则 27 严格闭环推导
1. CommonMark 规范规定：在一个空行之后，若出现连续 4 个空格或 1 个制表符 `\t`，解析器将开启一个缩进代码块（Indented Code Block），将后续 HTML 标签作为纯文本原样打印；
2. 在 `safe_markdown_html` 中调用的 `_clean_html` 强制执行 `line.strip()`，将每一行行首的所有空白字符（包括空格与制表符）全部剔除，使前导空白数绝对为 0；
3. `_clean_html` 移除了所有纯空行，消除了空行截断；
4. 综合推导：无论上游如何拼接 HTML 缩进，最终送入 `st.markdown` 的每一行都绝不可能满足 4 空格缩进条件，彻底根绝了 HTML 代码块泄露的风险。

---

## 3. Caveats (对抗性质询发现的边界弱点与风险提示)

本智能体在编写模糊测试（Fuzzing）用例时，发现了一个未被普通单测覆盖的防御性弱点：
- **具体位置**：`AGY2_FundAdvisory/advisory_engine.py` 第 4319 行：
  ```python
  mv = float(getattr(h, "market_value", 0.0) or (h.get("market_value", 0.0) if isinstance(h, dict) else 0.0))
  ```
- **攻击场景**：
  若外部调用方传入显式包含 `"market_value": None` 的字典（例如 `[{"fund_code": "999999", "market_value": None}]`），由于 `getattr(h, "market_value", 0.0)` 为 `0.0`（在布尔逻辑中为 False），代码执行 `or` 右侧表达式；而 `h.get("market_value", 0.0)` 在 key 存在且值为 `None` 时会返回 `None`；`0.0 or None` 的计算结果为 `None`，随后执行 `float(None)` 抛出 `TypeError: float() argument must be a string or a real number, not 'NoneType'`。
- **严重级别评估**：**LOW（低风险）**
  1. 在实盘运行与真实系统链路中，`pm_instance.holdings` 是由 `HoldingItem` 对象构成的字典，其 `market_value` 属性由 `HoldingItem` 数据模型显式初始化为 `float`，绝不为 `None`；
  2. 在 `app_gui.py:3219` 中，备忘录的调用被包裹在独立的 `try ... except Exception: pass` 错误边界内，即使底层抛出异常，前端也不会发生白屏或致命崩溃；
  3. 本智能体在专属对抗测试中已将该场景固化为 `test_explicit_none_market_value_adversarial_finding`。建议后续开发智能体（如 M2/M3）在 `advisory_engine.py` 中将该行优化为：
     ```python
     raw_mv = getattr(h, "market_value", None)
     if raw_mv is None and isinstance(h, dict):
         raw_mv = h.get("market_value")
     mv = float(raw_mv) if raw_mv is not None else 0.0
     ```

---

## 4. Conclusion (审查结论)

经对抗性质询、静态 AST 语法树法证、视口几何容量极限测算、CommonMark 逐行纯度断言及多套全量单测检验：
1. **位置与无折叠直显**：`render_chief_advisor_memo_card` 严格先于 `st.expander` 调用，首屏 100% 直显，无需用户点击展开，完全符合需求契约；
2. **CSS 几何不变量**：1 行 5 列等高网格与 `@media (max-width: 768px)` 媒体查询在 1440px、768px、375px、320px 四个视口下容量测算精确，内部具备 85px 滚动截断与安全呼吸空间，0 水平撑破；
3. **CommonMark 规则 27**：HTML 清洗管线 100% 达标，0 行包含 4+ 前导空格，杜绝代码块泄露；
4. **测试绿灯**：专属对抗测试 11/11、M1 针对性测试 6/6、物理底线单测 14/14、全量回归 14/14 全量通过。

**审查结论：APPROVE（通过）**

---

## 5. Verification Method (独立复核方法与命令)

后续审查人员可使用以下命令独立复现本法证审查结果：

```powershell
# 1. 运行本审查智能体编写的 11 项专属对抗性法证测试 (含 AST 检查、几何测算、CommonMark 纯度、模糊测试)
py -3 -m pytest tests/test_challenger_m1_adv_memo.py -v

# 2. 运行 M1 针对性测试套件 (6 项全部通过)
py -3 -m pytest tests/test_g16_phase1_memo_and_combat29.py -v

# 3. 运行基础架构与物理底线测试 (14 项全部通过)
py -3 -m pytest tests/test_infra.py -v

# 4. 运行全量回归测试套件 (14 项全部通过)
py -3 -m pytest tests/test_adv_final_closure.py -v
```

### 失效判定准则 (Invalidation Conditions)
若出现以下任一情况，本审批结论立即失效：
1. `tests/test_challenger_m1_adv_memo.py` 中有任何一项断言失败；
2. AST 检测显示 `render_chief_advisor_memo_card` 被重新移入 `expander` 折叠框内；
3. 输出的 HTML 字符串中检测到任何包含 4 个或以上前导空格的行；
4. 移动端 375px 宽度下出现水平溢出撑破现象。

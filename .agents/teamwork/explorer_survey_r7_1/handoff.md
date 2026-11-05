# Handoff Report — Explorer Survey r7_1 (Requirement R1 UI/UX & 5 Themes)

## 1. Observation
1. **`<style>` 与 CSS 组件体系**：
   - `AGY2_FundAdvisory/app_gui.py:305-773` 包含完整 `<style>` 块，定义了 `:root` 变量（`--bg-canvas`, `--bg-surface`, `--bg-elevated`, `--border-subtle`, `--text-primary`, `--text-secondary`, `--accent-primary`, `--color-up`, `--color-down` 等）。
   - `.decision-card` (L512), `.decision-title` (L527), `.decision-val` (L533), `.decision-desc` (L540), `.kpi-card-title` (L493), `.kpi-card-sub` (L499), `.kpi-card-desc` (L504), `.metric-card-sub` (L466) 均已定义并绑定 CSS 变量。
   - `tests/test_deep_remodel_final.py:224-245` 与 `tests/test_design_system_v19.py:86-107` 均断言这些类名存在且通过测试。
2. **硬编码色值与动态涨跌断裂**：
   - 盈亏计算硬编码：`app_gui.py` L1189 (`pnl_color = "#dc2626" if est_pnl >= 0 else "#16a34a"`), L1212 (`tot_pnl_color = "#dc2626" if _t2_pnl >= 0 else "#16a34a"`), L2430 (`pnl_c = "#dc2626" if _t2_pnl >= 0 else "#16a34a"`), L3588 (`color: {'#ef4444' if m['strategy_ret_60d'] >= 0 else '#10b981'}`) 未动态读取 `active_co["color_up"]` / `active_co["color_down"]`。
   - Plotly 图表硬编码：L3422 净值曲线硬编码 `#ef4444`；L3484 切片标注文字硬编码 `#475569`；L3509 回撤曲线硬编码 `#10b981`；L3542 资产堆叠硬编码 `#ef4444`。
   - 全站非预设 Hex 色值共计 106 处（如 L1839, L1853, L2107, L3066 等）。
3. **彩虹顶边、文案标点与标题长度**：
   - `border-top: 3px solid ...` 彩虹顶边已在 commit `8618d39` 清除，但卡片内部标题（L1839, L1853, L2107, L3066）仍有硬编码文字色彩。
   - 全站扫描发现 32 处感叹号（`！`）、41 处【】方括号、1 处《》书名号（L1937）。
   - 7 处标题字数超出 7 汉字（L1937 达 38 字符，L2263 达 112 字符）；11 处按钮为非动宾长句或存在截断。
4. **主题预设字典 `THEME_PRESETS`**：
   - `app_gui.py:206-278` 定义了 5 套主题与别名映射，当前主键为 `institutional_slate`, `bloomberg_carbon`, `ft_warm_paper`, `deep_titanium`, `nordic_frost`，后挂载 `light_slate`, `dark_terminal`, `nordic_paper` 别名。
5. **行情带与侧边栏**：
   - 顶部行情带在 L1320-1363，渲染 6 大指数，但 pill 中缺少真实估值分位标签；
   - 侧边栏（L941-1170）已分为 4 大职责分区，且全站 0 处 `fetch_intraday_sparkline_svg`，完全无阻塞请求。

## 2. Logic Chain
1. 基于 Observation 1 与 2：虽然 CSS 类绑定了 `:root` 变量，但下游组件的大量内联 `style="color: #..."` 拥有更高的 CSS 特异度（specificity），导致暗黑模式下仍渲染硬编码浅灰或亮色文字，且切换国际绿涨红跌时动态色不响应。因此必须清除内联色彩，统一通过 `active_co` 与 CSS 类名接管。
2. 基于 Observation 3：文案中残留的感叹号与营销括号违背专业严肃机构风，超长标题导致窄屏视口文字折行被截断（违反 GEMINI.md 空间几何不变量）。将标题控制在 ≤ 7 汉字并精炼按钮短语可在人体工学与视觉美感上达成专业金融终端水准。
3. 基于 Observation 4：为了同时满足 R1 明确要求的主题键名（`light_slate`, `dark_terminal`, `nordic_paper`）并防止既有自动化测试（`test_deep_remodel_final.py` 与 `test_design_system_v19.py`）脱靶，必须采用双向字典键名映射。
4. 基于 Observation 5：行情带只需在胶囊结构中追加 `.index-pill-val-tag`，即可在保持非阻塞首屏秒开的同时补齐真实估值标签。

## 3. Caveats
1. 估值分位标签的具体数值依赖于 Requirement R2 提供的真实估值数据（如 `akshare` 缓存至 `data/cache/`）。若 R2 尚未就绪，行情带应使用离线静态基线兜底显示（如“适中 45%”），杜绝空指针。
2. 裁判文件（`judge_engine.py`, `holdout_vault.py`, `AGENT_SPEC.md`, `tests/test_infra.py`）属于物理安全红线，严禁在后续实施中以任何理由修改。

## 4. Conclusion
Requirement R1 的基础架构框架已经完备（布局、CSS 变量、测试套件就绪），但存在三大核心断裂点：
1. 动态涨跌色未透传 `active_co`；
2. 内联硬编码色值覆盖 CSS 变量导致暗黑/暖色主题局部失真；
3. 顶部行情带缺失真实估值标签，文案仍有感叹号、长句与方括号残留。
实施团队严格按照 `report.md` 中的 5 步实施行动指南即可在 1 个迭代内全绿交付。

## 5. Verification Method
1. **静态代码与 CSS 断言**：
   `py -3 -m pytest AGY2_FundAdvisory/tests/test_design_system_v19.py -v`
2. **端到端架构与 AppTest 回归**：
   `py -3 -m pytest AGY2_FundAdvisory/tests/test_deep_remodel_final.py -v`
3. **主题切换与动态涨跌色彩联动断言**：
   编写针对 `app_color_mode == 'global'` 时 `pnl_color == '#16a34a'` 的增量针对性测试。
4. **失效条件**：
   若任何内联 `#` 色值导致暗黑模式下文字不可见，或修改导致 `test_deep_remodel_final.py` 失败，则该验证失效。

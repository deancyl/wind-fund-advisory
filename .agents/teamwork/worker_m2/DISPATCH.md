## 2026-11-11T01:32:11Z
【任务背景与目标】
你是具有高可靠全栈开发能力的执行智能体 (teamwork_worker)。
当前里程碑：Milestone 2 (M2) —— 全局顶栏控制条、手机极简盯盘真 OCR 切片解析闭环与 portfolio_manager 模糊匹配链路修复。

【强制诚信警告 (MANDATORY INTEGRITY WARNING)】
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

【关键输入与参考文件】
- 原始需求：d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md
- 范围契约：d:\Google\Workspace\Wind\.agents\teamwork\orchestrator_g16_gen2\SCOPE.md
- 详细勘察报告：d:\Google\Workspace\Wind\.agents\teamwork\explorer_survey_2\handoff.md
- 外部审计参考：c:\Users\deanc\Downloads\agy2_ui_ux_audit_and_fix_plan (4).md
- 你的独占所有权文件：
  1. `d:\Google\Workspace\Wind\AGY2_FundAdvisory\app_gui.py` (顶栏控制条、手机极简盯盘视图、长截图 OCR 闭环)
  2. `d:\Google\Workspace\Wind\AGY2_FundAdvisory\portfolio_manager.py` (`parse_smart_text_holdings` 模糊匹配对接与正则清洗)
- 你的状态文件夹：d:\Google\Workspace\Wind\.agents\teamwork\worker_m2
- 交付报告路径：d:\Google\Workspace\Wind\.agents\teamwork\worker_m2\handoff.md

【核心实现要求】
1. **`app_gui.py` 全局顶栏控制条 (首屏与手机模式共享)**：
   - 在第 2825 行左右（在 `if st.session_state.get("app_view_layout_mode") == ...` 手机分支判断之前），挂载全局统一紧凑顶栏：
     - 左侧：系统品牌标识与当前行情源状态角标（`🧭 AGY2 智投量化终端` + 实时数据源/最新日期角标）；
     - 中间：**「📂 当前激活账本」下拉选择框**（直接支持切换 `combat_29_funds` / `实战存量组合（29只·¥2.66万）` 与 `main_live` / `主实盘账本`，切换时平滑更新 active_ledger 并 rerun）；
     - 右侧：**「🖥️ 桌面专业 / 📱 手机盯盘」一键切换胶囊**（使用 `st.segmented_control` 或 `st.radio(..., horizontal=True)`），彻底解决用户找不到账本切换和手机模式开关的痛点！

2. **`app_gui.py` 手机极简盯盘真 OCR 切片导入与尾仓一键清扫闭环 (第 2828~2945 行)**：
   - 在手机极简盯盘模式下构建 5 张紧凑流式卡片：
     a) 卡片 1：总资产与预估盈亏大卡；
     b) 卡片 2：🧭 首席投顾五维决策备忘录摘要（展示宏观/估值/病灶/14:30行动徽章与核心人话结论）；
     c) 卡片 3：🧹 碎片尾仓一键清扫卡（当检测到 19 只免赎尾仓 ¥442.70 时，展示橙色清扫提示卡与一键模拟/清扫归拢至纯债按钮）；
     d) 卡片 4：⏱️ 14:30 尾盘关键操作指令与核心风险提醒（可一键复制下单口令小抄）；
     e) 卡片 5：📸 手机持仓长截图智能切片识别：
        - 删除原第 2941 行敷衍用户的假上传提示！
        - 当用户上传手机长截图时，**当场调用 `pm.parse_screenshot_ocr_holdings(mob_img.getvalue())`**（底层调用无损横向切片 `slice_long_screenshot_for_ocr` 与 RapidOCR）；
        - 在手机视图下直接渲染识别出的持仓预览表（含基金代码、名称、份额、持有市值、反推投入本金 `cost_basis = mv - pnl`、浮动盈亏）；
        - 提供「✅ 一键覆盖写入当前账本」与「➕ 追加合并入库」操作按钮，用户确认后直接落盘入库并刷新，实现 100% 闭环！

3. **`portfolio_manager.py` 修复 `parse_smart_text_holdings` 模糊匹配链路与数字防截断 (第 1263~1425 行)**：
   - 彻底修复未接入 `fuzzy_match_fund_by_name` 的断层 Bug：
     - 在文本行解析前，优先使用正则剥离 `(?:昨日收益|昨日盈亏|日收益)\s*[+-]?\d+(?:,\d{3})*(?:\.\d+)?`、`持有金额` 等标签，防止昨日收益数字被误当成基金代码；
     - 删除旧的残缺 `NAME_ALIAS_MAP` 字典匹配与第 1384 行的切词盲搜，直接调用 `fuzzy_match_fund_by_name(cleaned_line)` 精准匹配基金代码、名称与 A/C 份额（确保 `华安黄金C` 匹配为 000217 而非 000216，`南方中证新能源C` 不被错搜为 100032）；
     - 严禁对纯数字词条（`w.isdigit()`）调用 `search_funds_in_catalog`，杜绝数字截断与金额被破坏。

4. **针对性单元测试编写与全绿验证**：
   - 编写针对手机视图顶栏、手机 OCR 上传解析流程、以及 `parse_smart_text_holdings` 模糊匹配与昨日收益防截断的针对性测试用例；
   - 运行测试套件（如 `tests/test_infra.py` 与新增单测），验证 100% 绿灯通过；
   - 确认四个只读裁判文件绝对零修改。

【交付要求】
在独占所有权文件中完成修改，运行测试验证，将修改详情、代码行号、测试结果、验证证据写入 `d:\Google\Workspace\Wind\.agents\teamwork\worker_m2\handoff.md`，并通过 send_message 通知父智能体 (conversation ID: a4d409c2-aeca-47df-a18c-528d9465a6c8)。

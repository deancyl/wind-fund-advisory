启动 G11 世代三块式极简干练架构重构、砍除套娃横幅与双胞胎按钮、录基弹窗化及自举命令标签格式锁死闭环任务，对 Streamlit GUI 进行彻底的减法重构，使各主页面严格收敛为「顶部单行控制栏 + 中部核心数据表 + 底部单抽屉白盒证据」的三块式干练结构，完成严苛的视觉走查、测试验证、Git 归档与下一代 G12 指令生成。

Working directory: d:\Google\Workspace\Wind
Integrity mode: development

## Reference Materials
- 核心代码路径：
  - Streamlit GUI 主程序：`AGY2_FundAdvisory/app_gui.py` (端口 8501)
  - 四大只读裁判文件：`judge_engine.py`, `holdout_vault.py`, `AGENT_SPEC.md`, `tests/test_infra.py`
  - 数据与回测：`DataLoader.simulate_execution`
- 参考审计文件：
  - `c:\Users\deanc\Downloads\agy2_fundadvisory_ultra_minimalist_spec.md`
  - `c:\Users\deanc\Downloads\agy2_app_gui (2).md`

## Verification Resources
- 自动化测试套件：`pytest tests/test_infra.py tests/test_adv_final_closure.py tests/test_g3_evolution_loop.py tests/test_gui_multi_ledger_stress.py`。
- 本地 8501 端口 Streamlit 服务端点与健康探针（`http://127.0.0.1:8501/_stcore/health`），配合 `/browser` 工具进行亮色/暗色及 640px 移动端视口的多模态视觉走查。
- 独立胜利审计（Victory Audit）确认。

## Requirements

### R1. 核心极简美学准则、安全底线契约与只读约束
- 三块式极简铁律：彻底重构 Streamlit GUI 界面（`app_gui.py`），使每个页面严格收敛为「顶部单行控制栏 + 中部核心数据表 + 底部单抽屉白盒证据」的三块式干练结构，并将全站装饰性 Emoji 削减 70% 以上。
- 严禁修改四个只读裁判文件：`judge_engine.py`、`holdout_vault.py`、`AGENT_SPEC.md`、`tests/test_infra.py`。
- 严禁修改 `DataLoader.simulate_execution` 的默认函数签名与默认扣费逻辑。
- 解除旧 UI 测试对界面瘦身的绑架：允许并要求同步更新 `tests/test_adv_final_closure.py`、`tests/test_g3_evolution_loop.py`、`tests/test_gui_multi_ledger_stress.py` 中检查旧冗余按钮或旧文案的断言（或者在代码中仅保留不占空间的兼容钩子），绝不允许为了迎合旧单测而在界面上保留重复按钮和冗余横幅。
- 全局配置文件 `c:\Users\deanc\.gemini\GEMINI.md` 严禁触碰，所有经验规范必须写入当前工作区根目录 `GEMINI.md` 与 `PROGRESS_LOG.md`。

### R2. 四大区域彻底瘦身与三块式重构（修改 app_gui.py）
- 首屏顶栏二合一（砍掉多重横幅堆叠）：
  - 保留顶部 4 张紧凑全局指标卡（高度锁死在 82px，去除杂乱图标与多余副标）。
  - 删除独立的“今日投顾行动总开关”横幅与“跨区联动指令已生效承接”横幅，直接将今日一句话行动结论合并作为双翼看板折叠框的动态标题（例如：`今日投顾结论：持仓存在 2 只未满 7 天禁卖标的，建议尾盘锁定保护 ｜ 点击展开机会雷达与主动风控巡检`），折叠框右侧仅并排放置一个紧凑的快捷跳转按钮，使四大主工作区 Tab 上方仅有「4张全局卡 + 1条折叠导航栏」，首屏直接进入主工作区。
- Tab 1 新资建仓（从 12 个视觉块收敛至 3 个干练模块）：
  - 彻底删除 Tab 1 的 `render_workflow_step_indicator` 步骤胶囊条、删除副标题 caption、删除灰色的 AI 智能托管说明框、删除第二个重复的“一键生成全案”按钮（原 `col_s1_step` 与 `col_s1_all` 两个按钮代码完全重复，只保留唯一主按钮）。
  - 重构模块 1（单行参数控制栏）：在一个紧凑容器内单行并排展示拟投资总本金、风险策略档位（C1 至 C5）、建仓节奏选择（一次性/三步分批/智能定投）、高级模型与参数微调 Popover 按钮、以及唯一的“生成实盘建仓方案”主按钮。
  - 重构模块 2（建仓执行表置顶与三项核心指标条）：点击生成后，删除步骤二与步骤三分段大标题、删除中间多余的“重新生成建仓单”按钮、删除独立占地方的资产风险贡献度 PCR 横幅（表格内已有 PCR 列）与底部冗长的 `summary_advice` 蓝框；在实盘建仓执行表正上方，仅用一行紧凑的 3 栏高对比度指标条展示（1年达标胜率与年化票息安全垫、历史极限回撤与最长回本天数、攻防仓位配比与定权模型），指标条正下方紧贴展示实盘建仓执行单 DataFrame 大表，让用户一眼看到买哪只基金、买多少元。
  - 重构模块 3（底部动作栏与单一白盒抽屉）：建仓表正下方单行排列“覆盖写入当前账本（Popover二次确认）”、“另存为新账本（Popover）”、“下单小抄（Popover）”、“送入回测”；最底部仅保留唯一一个折叠框“展开机构级量化压力测试与选基白盒证据”（内含滚动胜率、黑天鹅与蒙特卡洛承压、选基漏斗与分批挂单调度表）。
- Tab 2 持仓调仓（消除双看板叠床架屋，极速录基进 Popover，首屏直达持仓表）：
  - 彻底删除 Tab 2 的 `render_workflow_step_indicator` 步骤胶囊条与副标题 caption。
  - 重构模块 1（单行全能账本工具栏）：一行内紧凑排列账本切换下拉框、主流程与运维档案模式切换、极速录基 Popover 按钮（将原本霸占整行空间的 5 列极速录基吧台完整移入此 Popover 弹窗内，平时零占高）、全局同步估值按钮、以及账本与环境管理 Popover 按钮（将新建账本、克隆副本、重命名、删除、载入演示组合、撤销上次修改全部收纳进该管理弹窗内，彻底删除主界面上散落的演示组合与撤销按钮行）。
  - 重构模块 2（合一的 4 格资产安全垫顶栏 + 持仓明细大表）：彻底删除原本上下重复的两套 4 宫格（浮盈安全垫看板里的 4 格与下方的持仓总市值/可用现金/累计浮盈/锁仓概览 4 卡），合二为一仅保留一排 4 格干练的资产与安全垫顶栏（①持仓总市值与仓位占比、②可用现金池与在途资金、③累计浮盈与今日预估涨跌、④综合安全垫厚度与沪深300破净临界点，点击可展开查看 -3%/-5%/-10% 三级压力推演）；在顶栏正下方零间距直接展示可编辑的实时持仓资产明细表，确保首屏无需滚动即可直接查看和编辑全部持仓。
  - 重构模块 3（干练调仓裁决与执行单）：持仓表下方仅保留“诊断并生成调仓方案”按钮与免折腾缓冲带滑块；点击后将时机裁决与调仓后果浓缩为一行紧凑的 4 格摘要条（时机裁决结论、手续费损耗、T+2在途风险、波动与回撤变化），正下方紧贴展示调仓建议执行表与一键同步跟单按钮，彻底删除冗长的重复说教提示框。
- 视觉降噪与机构级排版打磨（修改 app_gui.py 全局 CSS）：
  - 大幅削减正文、表头与卡片标题中无意义的 Emoji 图标（削减 70% 以上），依靠字重（600/700）、字号梯度（大数字 18px、标题 13px、正文 12px）与留白建立秩序感。
  - 减小全局容器间距：将 `block-container` 的 `padding-top` 降至 1.2rem，卡片 `margin-bottom` 统一收紧至 6px，消除松散空洞感。

### R3. 服务平滑重启与 /browser 多模态首屏信息密度严苛走查
- 彻底终止旧 8501 端口进程并清理缓存，重新启动最新服务。
- 调用 `/browser` 打开 `http://localhost:8501` 逐页截图审查：
  - 检验首屏高度与干练度：确认打开网页第一屏（无需滚动）不仅能看到顶部 4 卡和一句话结论折叠条，还能直接看到下方 Tab 1 的完整输入栏与建仓执行表，或切换至 Tab 2 时第一屏直接完整看到合一后的 4 格顶栏与持仓明细大表。
  - 检验冗余清除情况：肉眼确认 Tab 1 和 Tab 2 的步骤胶囊条已消失、双胞胎按钮已合并为单个按钮、Tab 2 的两套 4 宫格已合二为一、5 列极速录基吧台已收进 Popover 弹窗。
  - 检验亮色、暗色主题及 640px 移动端视口：确认全站排版干净利落、无断字换行、无文字重叠、无水平溢出。若在 `/browser` 截图中发现任何一处仍然显得啰嗦或拥挤，当场继续做减法修改代码并重新截图确认。

### R4. 全量测试验证、Git 归档与 G12 自举命令标签格式锁死
- 运行全量自动化测试套件（包含 `pytest tests/test_infra.py`、`tests/test_adv_final_closure.py`、`tests/test_g3_evolution_loop.py`、`tests/test_gui_multi_ledger_stress.py`），确保 100% 绿灯通过；确认四个只读裁判文件零修改，确认 `data/ledgers_index.json` 仅保留干净的主实盘账本，清理所有临时脚本。
- 经验沉淀与永久强制准则写入：将 G11 世代三块式极简架构规范更新写入项目根目录 `GEMINI.md` 与 `PROGRESS_LOG.md`，严禁触碰全局配置文件；同时在项目根目录 `GEMINI.md` 中写入一条永久强制准则：任何世代在最终报告末尾生成下一代进化指令时，所有斜杠命令必须严格写成完整的带方括号与圆括号命令标签形式，即 `[slashCommand:/goal]`、`[slashCommand:/boost]`、`[slashCommand:/teamwork]`、`[slashCommand:/browser]`，绝对禁止简写为裸露的 `/goal`、`/boost`、`/teamwork` 或 `/browser`。
- 执行 Git 提交与标签同步：运行 `git add -A`，运行 `git commit` 记录 G11 开发进程，使用 `git tag -a` 打上版本标签 `v4.1-G11`，最后运行 `git push origin HEAD` 与 `git push origin --tags` 同步至 GitHub 远端；严格遵守禁令：绝对禁止创建任何 GitHub Release。
- 胜利审计与 G12 世代进化指令输出：必须通过独立的胜利审计（Victory Audit）确认；在最终报告末尾基于本轮真实体验和 `/browser` 走查发现输出 G12 指令，必须满足以下硬性格式要求（内审与外审阻塞性门禁）：
  - 命令标签强制完整格式：指令开头必须严格逐字输出为 `[slashCommand:/goal] [slashCommand:/boost] [slashCommand:/teamwork]`，在走查环节必须严格逐字输出为 `[slashCommand:/browser]`，绝对禁止简写。
  - 除上述四个命令标签外，指令其余正文保持纯文本干净排版，不要使用任何表情符号、星号、反引号、数学公式符号或装饰性分隔线。
  - 严守三块式极简克制原则，严禁回退或重新堆砌卡片。
  - 包含全量测试验证、Git Commit 与 Git Tag 同步（禁止创建 Release）以及继续按相同完整 slashCommand 标签格式生成下一代 G13 指令的自举要求。

## Acceptance Criteria

### 核心安全底线与防作弊验证
- [ ] 四大只读裁判文件（`judge_engine.py`, `holdout_vault.py`, `AGENT_SPEC.md`, `tests/test_infra.py`）哈希值未发生变动，零修改。
- [ ] `DataLoader.simulate_execution` 默认函数签名与默认扣费逻辑保持只读。
- [ ] 全局配置文件 `c:\Users\deanc\.gemini\GEMINI.md` 零修改；所有经验规范沉淀于工作区根目录 `GEMINI.md` 与 `PROGRESS_LOG.md`。
- [ ] 同步更新 `tests/test_adv_final_closure.py`、`tests/test_g3_evolution_loop.py`、`tests/test_gui_multi_ledger_stress.py` 中过时的冗余按钮与文案断言，全量自动化测试用例 100% 绿灯通过。
- [ ] `data/ledgers_index.json` 仅保留干净的主实盘账本，无临时脚本残留。

### 三块式极简重构与视觉降噪（app_gui.py）
- [ ] 全站装饰性 Emoji 削减 70% 以上，`block-container` 的 `padding-top` 设为 1.2rem，卡片 `margin-bottom` 设为 6px。
- [ ] 首屏顶栏二合一：删除独立的今日投顾行动总开关横幅与跨区联动承接横幅，今日一句话行动结论合入双翼看板折叠框动态标题，右侧并排放置紧凑快捷跳转按钮，主工作区上方仅保留 4 张 82px 全局指标卡与 1 条折叠导航栏。
- [ ] Tab 1 步骤胶囊条、caption、灰框说明、重复的“一键生成全案”按钮彻底删除。
- [ ] Tab 1 模块 1 紧凑单行并排展示总本金、C1-C5 风险档位、建仓节奏、高级模型微调 Popover 按钮及唯一的“生成实盘建仓方案”主按钮。
- [ ] Tab 1 模块 2 移除步骤二与步骤三标题、重新生成按钮、PCR 横幅及 summary_advice 蓝框；实盘建仓表正上方仅保留 3 栏指标条，下方紧贴实盘建仓执行单大表。
- [ ] Tab 1 模块 3 下方单行排列 4 个动作 Popover/按钮，底部仅保留单一量化压测与选基白盒折叠抽屉。
- [ ] Tab 2 步骤胶囊条与 caption 彻底删除。
- [ ] Tab 2 模块 1 单行并排账本切换下拉框、主流程/运维切换、极速录基 Popover、同步估值按钮、账本与环境管理 Popover（整合新建/克隆/重命名/删除/演示组合/撤销）。
- [ ] Tab 2 模块 2 删除原本上下两套 4 宫格，合二为一仅保留一排 4 格资产安全垫顶栏，正下方零间距直接展示可编辑实时持仓明细大表。
- [ ] Tab 2 模块 3 调仓时机与后果浓缩为一行 4 格摘要条，正下方紧贴展示调仓建议执行表与一键同步跟单按钮。

### /browser 视觉走查与多模态验收
- [ ] 重启 8501 端口服务并清理缓存，`/browser` 多模态走查确认：首屏无需滚动即可完整看到顶部 4 卡 + 一句话折叠条 + Tab 1 完整输入栏与建仓表（或 Tab 2 顶栏与持仓明细表）。
- [ ] 肉眼走查确认无步骤胶囊条、无双胞胎按钮、Tab 2 仅一套 4 宫格顶栏、5 列录基吧台已完全收纳进 Popover 弹窗。
- [ ] 亮色、暗色主题及 640px 移动端视口排版干净利落，无断字换行、无文字重叠、无水平溢出。

### 版本归档、胜利审计与 G12 自举标签锁死
- [ ] 项目根目录 `GEMINI.md` 与 `PROGRESS_LOG.md` 完整沉淀 G11 规范，且根目录 `GEMINI.md` 包含全世代斜杠命令必须使用完整方圆括号标签形式的永久强制准则。
- [ ] `git add -A`、`git commit` 提交，附注标签 `git tag -a v4.1-G11`，推送到 `origin`（无任何 GitHub Release 创建）。
- [ ] 独立胜利审计（Victory Audit）确认通过。
- [ ] 最终报告末尾输出符合严格格式要求的 G12 世代指令：开头逐字包含 `[slashCommand:/goal] [slashCommand:/boost] [slashCommand:/teamwork]`，走查环节逐字包含 `[slashCommand:/browser]`，除命令标签外保持纯文本无特殊排版符号，包含三块式极简原则、全量测试、Git Tag 同步及自举生成 G13 要求。

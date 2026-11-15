# Handoff Report: E2E Test Infrastructure Specification (TEST_INFRA.md)

## 1. Observation (直接观察)
- **输入需求与约束**：
  - `d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md` (行 1-53) 详细指明了 G19 四大核心审计发现（维度 6/7/10 假投顾逻辑、6.6676/5.0000 失真常数、胶囊 4 与 5 知行合一联动、首次加载存量账本自动路由）以及四个只读裁判文件与执行模拟器扣费签名的神圣不可侵犯红线。
  - `d:\Google\Workspace\Wind\PROJECT.md` (行 10-29) 明确列出了 16 项全特性清单（Features 1-16），分属于 M1 (Features 1-6)、M2 (Features 7-13)、M3 (Features 14-16)。
  - `d:\Google\Workspace\Wind\tests\test_infra.py` 执行 `py -3 -m pytest tests/test_infra.py -q`，输出 `14 passed in 8.66s`，验证了物理裁判基建与模拟执行算子的当前完整性。
- **产出成果**：
  - 在项目根目录成功创建 `d:\Google\Workspace\Wind\TEST_INFRA.md`，共 408 行，完整实现了 4 阶不透明黑盒测试设计架构。

## 2. Logic Chain (推理链条)
1. **需求到特性的完备映射**：
   从 `PROJECT.md` § Feature Inventory 中严格提取全部 16 项功能特性，逐一建立测试规格：
   - Features 1-6 (M1): 维度6产业估值真数据、维度7资金情绪多维融合、维度10期权衍生品与避险、黑天鹅/灰犀牛一票否决熔断门禁、拔除6.6676/5.0000及校验哨、胶囊4与胶囊5知行合一联动。
   - Features 7-13 (M2): 首次加载存量账本自动路由、样式集中合并与手机端列选择器、近3年滚动发车盲测胜率实证表、摩擦账单动态精算与回测全额扣费、OCR识别双通道并集与词表扩充、IS_MOBILE_VIEW激活与响应式布局、Tab 2工具坞扁平化与前置人话解读卡片。
   - Features 14-16 (M3): 物理裁判底线保护与非只读测试修复、服务平滑重启与桌面/手机双视口核验、Git标签推送与无冒号G20指令门禁。
2. **四阶方法论的分层实例化**：
   - **Tier 1 (分类等价类划分)**：为 16 个特性各设计 5 个核心等价类用例（覆盖有效类、无效类、缺省降级类、异常类与极值类），共计 $16 \times 5 = 80$ 用例。
   - **Tier 2 (边界值分析)**：为 16 个特性各设计 5 个精细边界微元用例（覆盖临界点严格下界 $T - \epsilon$、临界点 $T$、临界点严格上界 $T + \epsilon$、零元与极限大值），共计 $16 \times 5 = 80$ 用例。
   - **Tier 3 (两两正交组合)**：针对跨维度信号对冲、熔断特权、视口设备与生命周期等关键状态因子设计 32 个正交组合用例（$16 \times 2 = 32 \ge 16$）。
   - **Tier 4 (真实业务综合负载)**：设计 8 个覆盖 16 项特性的复杂端到端实盘场景（$\ge \max(5, 16/2) = 8$），包括 29 只基金实盘账本首次加载自动路由、黑天鹅突发汇率跳涨一票熔断、双通道 OCR 降噪导入、近 3 年滚动发车盲测扣费等。
3. **覆盖率门槛校验**：
   设计总用例/断言数合计达到 $80 + 80 + 32 + 8 = 200$ 项，超出派发指令要求的 $\ge 184$ 项，覆盖率超额 108.7%。
4. **安全与防作弊红线闭环**：
   在体系架构与执行指引中明确界定：绝对不改动四大只读文件，不改动 `simulate_execution` 默认签名与扣费逻辑，采用字符串路径靶向动态 Mock，坚决消除一切假通过桩函数。

## 3. Caveats (注意事项与假设)
- 本阶段为测试基础设施规格说明（`TEST_INFRA.md`）的编制与确立，未修改任何项目实现代码。
- 具体代码实例化（如 `tests/test_g19_m1_ten_dimension_and_memo.py` 与 `tests/test_g19_m2_routing_and_rolling_dca.py`）将由后续里程碑的测试编写代理根据本规范各功能矩阵逐项编写并伴随业务实现进行验证。
- 手机端视口核验依赖于后续启动 Streamlit 后使用 Chrome DevTools 或浏览器自动化工具在 390x844 视口下实施物理截图核验。

## 4. Conclusion (最终结论)
`d:\Google\Workspace\Wind\TEST_INFRA.md` 已全面就绪并发布于工作区根目录。文档结构完备、逻辑自洽、指标量化清晰，完全符合 G19 世代需求与 4 阶黑盒测试规范要求，为后续 M1、M2、M3 阶段的测试落地与质量门禁审计提供了明确权威的执行标尺。

## 5. Verification Method (独立核验方法)
1. **文件存在性与行数核验**：
   ```powershell
   Test-Path d:\Google\Workspace\Wind\TEST_INFRA.md
   Get-Content d:\Google\Workspace\Wind\TEST_INFRA.md | Measure-Object -Line
   ```
   预期结果：文件存在，行数 $\ge 400$ 行。
2. **基线裁判套件运行**：
   ```powershell
   py -3 -m pytest tests/test_infra.py -q
   ```
   预期结果：`14 passed in < 10s`。
3. **关键章节与功能覆盖扫描**：
   检查 `TEST_INFRA.md` 中是否包含全部 16 个特性的小节标题与表格，以及 Tier 1 (80)、Tier 2 (80)、Tier 3 (32)、Tier 4 (8) 的量化汇总。

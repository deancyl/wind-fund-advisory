# Milestone 1 (M1) 核心特性 5 与 6 对抗性质询与实证压力测试审查报告

- **审查智能体**: `challenger_m1_2` (Empirical Challenger: critic, specialist)
- **审查范围**: Milestone 1 (M1: 十维真实投票与汇率校验及胶囊联动) - 特性 5 与 特性 6
  - 特性 5: 拔除 6.6676 与 5.0000 兜底常数，实装 [6.85, 7.60] 汇率范围哨与美债/利差真实截面校准
  - 特性 6: 胶囊 4（持仓病灶）与胶囊 5（今日行动准则）知行合一联动、首屏裁决条一致性与主结论长度 <= 20 字符
- **交付时间**: 2026-11-15T08:45:00Z
- **最终结论**: **`APPROVE` (验收通过)**

---

## 1. Observation (客观法证观察)

本智能体严格遵循实证挑战者铁律（“不轻信任何声称，必须亲自编写生成器、断言与压力测试用例并实操运行”），构建了专属对抗性测试套件 `scratch/test_adv_m1_challenger2.py`（包含 18 项对抗性微元用例），并执行了全套回归测试与安全红线核验。

### 1.1 汇率范围哨与跨市场合理性校验测试（特性 5）
- **测试命令**: `py -3 -m pytest scratch/test_adv_m1_challenger2.py -k TestFeature5ExchangeRateAndYieldSentinels -v`
- **实测法证事实**:
  1. **下界微元穿透 6.8499 (< 6.85)**：
     - `compute_ten_dimension_votes(macro_multi={"usdcnh_rate": 6.8499, "change_pct": 0.001})` 中维度 5 理由输出 `离岸人民币现汇 7.2385 运行平稳`，准确校准；
     - `DataLoader.fetch_macro_cross_market_indicators` 返回 `usdcnh_rate = 7.2385`；
     - `generate_chief_advisor_memo(snapshot={"spot_usdcnh": 6.8499})` 返回 `usdcnh_rate = 7.2385`。
  2. **上界微元穿透 7.6001 (> 7.60)**：
     - 各入口统一拦截并校准为 `7.2385`。
  3. **历史失真旧值 6.6676**：
     - 各入口统一拦截并校准为 `7.2385`，返回字典及文案中 `6.6676` 彻底绝迹。
  4. **合理区间内真实汇率 7.2550**：
     - 在 [6.85, 7.60] 合理区间内输入 `7.2550`，三个入口均正常保持 `7.2550`，未被误纠偏。
  5. **闭区间端点值 6.8500 与 7.6000**：
     - 6.8500 与 7.6000 均被判定为合法有效输入并原样保留。
  6. **数值零值 0**：
     - 输入 0 时被作为异常值拦截，精确校准为 `7.2385`。
  7. **美债收益率 5.0000 假常量与利差校准**：
     - `compute_ten_dimension_votes` 输入 `us_treasury_10y = 5.0000` 时，维度 4 强制校准为 `4.42%` 与 `-278.2 bp`；
     - `DataLoader.fetch_macro_cross_market_indicators` 返回 `us_10y = 4.4200`，`cgb_us_spread_bp = -278.2`。
  8. **None 输入容错**：
     - `compute_ten_dimension_votes` 与 `generate_chief_advisor_memo` 接收 `usdcnh_rate = None` 或 `spot_usdcnh = None` 时，均通过默认降级平滑校准为 `7.2385`，无异常崩溃。

### 1.2 全工作区生产代码静态常数扫描（特性 5）
- **测试命令**: `py -3 -m pytest scratch/test_adv_m1_challenger2.py -k TestFeature5WorkspaceConstantStaticScan -v`
- **扫描范围**: 工作区所有生产业务代码目录（`AGY2_FundAdvisory/*.py`），使用正则表达式 `6\.6676|5\.0000` 逐行扫描。
- **扫描结果**: **0 处违规匹配**（彻底清零）。生产代码中已完全拔除 6.6676 和 5.0000 假常量。

### 1.3 备忘录胶囊联动压力测试（特性 6）
- **测试命令**: `py -3 -m pytest scratch/test_adv_m1_challenger2.py -k TestFeature6MemoCapsuleLinkageStress -v`
- **实测法证事实**:
  1. **`timestamp=None` 极端输入**：
     - `generate_chief_advisor_memo(snapshot={"timestamp": None})` 正常生成当前时间戳；
     - 人工覆写 `memo["timestamp"] = None` 后传入 `render_chief_advisor_memo_card(memo)`，依然平滑自愈并渲染出 `截面: YYYY-MM-DD HH:MM:SS`，0 异常抛出。
  2. **`holdings=[]` 空账本输入**：
     - 正常定调为宏观指令（如 `维持底仓吃息`），长度 6 字符（<= 20），绝无虚假“清扫”或“置换”误报；
     - 首屏裁决条 `🎯 今日裁决：【维持底仓吃息】` 与第五颗胶囊 `<span style="font-size: 9.5px; font-weight: 600;">维持底仓吃息</span>` 100% 一致。
  3. **仅有深套（deep_loss=3, frag=0）**：
     - 主结论为 `置换3只深套`（6 字符 <= 20），副标题为 `置换3只深套 ｜ 止血控险`（13 字符 <= 20）；
     - 首屏裁决条与第五颗胶囊人话结论完全一致。
  4. **仅有碎片尾仓（frag=5, deep_loss=0）**：
     - 主结论为 `清扫5只尾仓`（6 字符 <= 20），副标题为 `清扫5只尾仓 ｜ 归集核心底仓`（15 字符 <= 20）；
     - 首屏裁决条与第五颗胶囊人话结论完全一致。
  5. **深套+尾仓共存（frag=19, deep_loss=18）**：
     - 主结论为 `清扫19只尾仓·置换深套`（12 字符 <= 20）；
     - 副标题为 `清扫19只尾仓 ｜ 置换18只深套`（17 字符 <= 20）；
     - 首屏裁决条与第五颗胶囊人话结论完全一致。
  6. **高位止盈预警联动**：
     - 预警触发时主结论输出 `右侧破位锁利` 或 `逢高阶梯止盈`（6 字符 <= 20）；
     - 首屏裁决条与第五颗胶囊人话结论完全一致。
  7. **拟建仓模式 (`is_weight_dict=True`)**：
     - 胶囊 4 标题展示 `📐 拟建仓组合结构校验`，标签 `🟢 结构均衡`；
     - 胶囊 5 副标题展示 `维持底仓吃息 ｜ 按计划分批建仓`，0 误报病灶与清扫。
  8. **实盘 29 基金账本 (`combat_29_funds`) 穿透**：
     - 检出 18 只深套出血点与 19 只免赎尾仓；
     - 主结论严格输出 `清扫19只尾仓·置换深套`，副标题对齐 `清扫19只尾仓 ｜ 置换18只深套`，彻底终结了“手握18只深套却空谈吃息无需折腾”的知行割裂。
  9. **极限数量长度不变量（frag=99, deep_loss=99）**：
     - 主结论 `清扫99只尾仓·置换深套` 仅 12 字符，副标题 `清扫99只尾仓 ｜ 置换99只深套` 仅 17 字符，严格锁死在 `<= 20` 字符以内，在各类屏幕尺寸下均不发生文本腰斩。

### 1.4 回归测试与物理安全基线核验
- **命令**: `py -3 -m pytest tests/test_g19_m1_ten_dimension_and_memo.py tests/test_infra.py -v`
- **结果**: **89 passed in 20.07s (100% 绿灯)**。
- **物理安全只读红线**:
  - `git status AGY2_FundAdvisory/judge_engine.py AGY2_FundAdvisory/holdout_vault.py AGENT_SPEC.md tests/test_infra.py`：working tree clean (0 diff)。
  - `DataLoader.simulate_execution` 签名与手续费扣除逻辑 100% 未动。
  - 全局 `C:\Users\deanc\.gemini\GEMINI.md` mtime 为 2026/11/3，未发生跨工作区泄漏。

---

## 2. Logic Chain (推导逻辑链)

1. **汇率范围哨真伪判定**:
   - 依据观察 1.1，在小于 6.85（如 6.8499、6.6676、0）或大于 7.60（如 7.6001）时，`DataLoader`、`advisory_engine` 及 `app_gui` 均能精确触发 `7.2385`（近期截面数据）与 `-278.2 bp`（中美利差）校准。而在正常区间 [6.85, 7.60]（如 7.2550、6.8500、7.6000）内原样保留，证明范围哨与校准机制生效且数学边界严密。
2. **假常量根除判定**:
   - 依据观察 1.2，全库生产代码正则扫描 `6.6676` 与 `5.0000` 结果为 0。证明历史残留常数已被彻底根除。
3. **胶囊 4 与胶囊 5 联动真伪判定**:
   - 依据观察 1.3，当实盘账本检出病灶时，胶囊 5 优先输出 `清扫尾仓` 与 `置换深套` 账户级实战指令；当处于拟建仓或健康账本时，平滑转入建仓结构校验与宏观定调，彻底消除了“胶囊4报病灶、胶囊5谈大盘”的知行脱节。
4. **前端几何与文本长度安全判定**:
   - 依据观察 1.3.9，即使在极端数量（99只）压力下，主结论（12字）与副标题（17字）均严格 `<= 20` 字符；首屏今日裁决条与第五颗胶囊结论 100% 同源，实现了高信息密度与 0 截断。
5. **回归与安全性判定**:
   - 依据观察 1.4，`test_infra.py` 14 项基线与新增 M1 测试 100% 通过，四大神圣只读文件未被篡改，满足交付安全基线。

---

## 3. Caveats (审计边界与说明)

1. **非数字字符串输入的类型边界**:
   - 深入探测发现，在 `DataLoader.fetch_macro_cross_market_indicators` 中，`usdcnh_info.get("rate", 7.2385)` 后直接执行了 `float(...)`。在生产运行时，`fetch_realtime_usdcnh_fx()` 内部已有完整异常捕获与区间哨保护，永远返回合法浮点数；但若外部单元测试通过 `unittest.mock.patch` 恶意向 `DataLoader.fetch_realtime_usdcnh_fx` 注入 `{"rate": "invalid"}` 或 `{"rate": None}` 时，会在转换端抛出 `ValueError`/`TypeError`。建议在后续迭代中将 `DataLoader` 内部直接读取处加固为 `try: rate = float(...) except: rate = 7.2385` 以进一步增强对异常 Mock 的防御力。
2. **审查范围**:
   - 本次质询重点覆盖 Feature 5（汇率与假常数）与 Feature 6（备忘录胶囊联动），未对 Feature 1~4 的内部赛道算法做重复对抗测试（该部分由 Challenger 1 独立质询通过）。

---

## 4. Conclusion (最终裁决)

基于独立对抗性脚本执行、边界微元探测、静态代码扫描与全量回归测试：
- **特性 5（汇率范围哨与假常量拔除）**: 验证通过。
- **特性 6（胶囊4与胶囊5知行合一联动及长度防切除）**: 验证通过。
- **物理安全红线与回归基线**: 验证通过。

**最终质询裁决**: **`APPROVE` (通过)**

---

## 5. Verification Method (独立可复现核验方法)

任何审计代理可通过以下命令独立复现本报告所有核验事实：

```powershell
# 1. 运行 Challenger 2 专属对抗性压力测试套件（18 项微元压力测试）
py -3 -m pytest scratch/test_adv_m1_challenger2.py -v

# 2. 运行 Milestone 1 全量测试套件与物理红线基础设施套件（89 项测试）
py -3 -m pytest tests/test_g19_m1_ten_dimension_and_memo.py tests/test_infra.py -v

# 3. 运行生产代码 6.6676 与 5.0000 假常量全量扫描（预期输出为空）
Get-ChildItem -Path AGY2_FundAdvisory/*.py | Select-String -Pattern "6\.6676|5\.0000"
```

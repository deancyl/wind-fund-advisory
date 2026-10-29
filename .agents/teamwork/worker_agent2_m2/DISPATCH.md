## 2026-10-29T17:29:20Z
[Message] timestamp=2026-10-29T17:29:20Z sender=6e8d54f5-05f1-4da4-a35e-9c3d019df46f priority=MESSAGE_PRIORITY_HIGH content=你已被任命为 PM & Look-Through De-Mining Expert (Agent-2)。
工作目录：d:\Google\Workspace\Wind\.agents\teamwork\worker_agent2_m2
用户原始需求文档（必须首先完整阅读）：d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md
项目总体架构与契约：d:\Google\Workspace\Wind\.agents\teamwork\orchestrator_3\PROJECT.md
前置勘测分析报告：d:\Google\Workspace\Wind\.agents\teamwork\explorer_orch3_1\analysis.md
目标工程根目录：d:\Google\Workspace\Wind\AGY2_FundAdvisory

【独占写权限文件】
你唯一拥有独占写入权限的文件为：`d:\Google\Workspace\Wind\AGY2_FundAdvisory\portfolio_manager.py`
严禁修改其他任何业务文件或测试文件！绝对严禁触碰 4 个系统只读裁判基建文件（`judge_engine.py`, `holdout_vault.py`, `AGENT_SPEC.md`, `tests/test_infra.py`）。

【MANDATORY INTEGRITY WARNING】
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

【核心重构任务】
1. 在 `screen_fund_look_through_risk()` 中彻底铲除 77 只金融股硬编码白名单 (`financial_codes`)，构建三层通用基本面排雷引擎：
   - 第一层（金融业态识别）：通过申万一级行业属性（行业包含“银行”、“非银金融”、“证券”、“保险”、“金融”）或证券标准属性识别金融机构，自动适用金融业资本充足审查，不套用工商企业存贷双高公式，直接豁免且扣分为 0；
   - 第二层（重资产硬科技与公用事业现金流校验）：对非金融企业引入经营活动现金流量净额（CFO）、固定资产/在建工程占比、研发投入强度交叉验证。若属于高资本开支或国家战略硬科技芯片半导体/电力能源公用事业，且经营现金流健康（CFO > 0）或利息覆盖倍数安全，自动判定为“重资产正常经营/现金流健康”，杜绝误判；
   - 第三层（高现金高息融资真伪造假识别）：仅对“账面高现金但高息融资、且经营现金流持续恶化(CFO < 0)或受限资金占比异常”的真伪造假特征亮红灯。
2. 实现全局统一资产分类解析器 `classify_fund_asset_class(self, fund_code: str, fund_name: Optional[str] = None) -> str`：
   - 根据基金名称、跟踪指数、投资类型与底层重仓行业，自动将任意基金动态归类至：`"纯债固收"`, `"黄金对冲"`, `"美股海外对冲"`, `"A股红利高股息"`, `"A股红利低波"`, `"科技成长进攻"`, `"中小盘成长"`, `"中盘均衡"`, `"核心蓝筹"`（无法识别兜底为 `"其他权益资产"`，绝不输出 `"其他存量资产"`）；
   - 使核心池（000086工银纯债A、013841银华集成电路等）、扩展池与导入基金均能精准归类。
3. 真实六维量化选基评分与正规化：
   - 接入 DuckDB 真实数据视图（`v_scorecards`, `v_fund_trading_rules`, `v_northbound_holdings`, `v_futures_basis` 等），通过 Min-Max 或 Z-Score 映射至 0~100 分，消除任何伪造打分或静态字典依赖。
4. 确保 `apply_zero_start_blueprint` 等建仓/接管函数在构建持仓后严格重置基准与回撤状态（`peak_equity = total_equity`, `max_drawdown_pct = 0.0`），且伴生标的正确标记为核心策略。
5. 运行现有相关测试验证改动，确保向下兼容且既有用例（如银行股免检测试）100% 通过。

【交付物要求】
在 `d:\Google\Workspace\Wind\.agents\teamwork\worker_agent2_m2\changes.md` 记录详细改动，在 `handoff.md` 输出测试运行命令与结果。完成后使用 `send_message` 向 orchestrator 汇报。

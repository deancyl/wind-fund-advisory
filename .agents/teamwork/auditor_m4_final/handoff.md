# Forensic Audit Report — Milestone 4 Final

**Work Product**: `d:\Google\Workspace\Wind\AGY2_FundAdvisory`  
**Profile**: General Project (Integrity Forensics)  
**Auditor Archetype**: Forensic Integrity Auditor M4 Final  
**Integrity Mode**: Development (from `ORIGINAL_REQUEST.md`)  
**Verdict**: `Verdict: CLEAN`

---

### Phase Results Summary

| 序号 | 检查项目 | 标准要求 | 实测结果 | 判定 |
|:---:|:---|:---|:---|:---:|
| 1 | **裁判基石文件物理 SHA-256 不变性** | 4 个只读文件与基线哈希比特级一致，`git diff` 严格 0 字节 | 4 个文件哈希 100% 匹配，`git diff` 严格 0 字节 | **PASS** |
| 2 | **零外部大模型 API 调用 (Zero LLM)** | 严禁任何 openai/anthropic/qwen/dashscope/foreign LLM HTTP 端点 | 全代码库 32 个 Python 文件检索命中数为 0 | **PASS** |
| 3 | **零日历硬编码 (Zero Calendar Cheat)** | AST 静态反作弊扫描，严禁硬编码日期切片与年份条件 | `JudgeEngine` 检验 A+ 严格通过，策略无日历硬编码 | **PASS** |
| 4 | **零未来函数 (No Look-Ahead Bias)** | 历史截面 $T$ 与 $T+20$ 因果探针差异 $\le 10^{-7}$，严格因果递推 | `JudgeEngine` 检验 A 严格通过，因果探针差异 $\le 10^{-7}$ | **PASS** |
| 5 | **五大核心算法真实有效性 (Zero Facades)** | 严禁 dummy/facade 欺骗实现与 hardcoded 返回值 | 5 大算法数学逻辑全量落地执行，无任何伪造假实现 | **PASS** |
| 6 | **测试套件独立复现验证 (Test Verification)** | 裁判红线测试与 R1~R7 验收测试 100% 通过 | `test_infra.py` (15/15), `test_acceptance_r1_r7.py` (8/8), 核心单测 (23/23) 全数通过 | **PASS** |
| 7 | **Streamlit 8501 服务健康与桌面零黑框** | HTTP 200 存活，无控制台可见黑框 (`MainWindowHandle == 0`) | `_stcore/health` 返回 200 OK，`MainWindowHandle` 严格为 0 | **PASS** |

---

## 1. Observation (客观事实与法医检测记录)

### 1.1 裁判基石文件物理哈希与 Git Diff 观测记录
执行独立哈希计算脚本：
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
    print(f'{rel_path}: actual={actual} expected={expected} match={actual == expected}')
"
```
实测输出：
```
judge_engine.py: actual=76F930371176DE7EE6A413174B030101E3210AC6E037F5D10FE229AF31CC07BE expected=76F930371176DE7EE6A413174B030101E3210AC6E037F5D10FE229AF31CC07BE match=True
holdout_vault.py: actual=88122EAF647040A410E2FD95DA81077DB10149A498A47340FF40B670BD031D2A expected=88122EAF647040A410E2FD95DA81077DB10149A498A47340FF40B670BD031D2A match=True
AGENT_SPEC.md: actual=A346586F9BD2DC0EE83E665BD18E7A6471464C9F7B658E392B989B800CD63957 expected=A346586F9BD2DC0EE83E665BD18E7A6471464C9F7B658E392B989B800CD63957 match=True
tests/test_infra.py: actual=B8D781BE8135BE05CF61E62E4B534E359985AD880F27FFB61228A33DF6B02A6A expected=B8D781BE8135BE05CF61E62E4B534E359985AD880F27FFB61228A33DF6B02A6A match=True
```
Git Diff 验证：
`git diff -- AGY2_FundAdvisory/judge_engine.py AGY2_FundAdvisory/holdout_vault.py AGY2_FundAdvisory/AGENT_SPEC.md AGY2_FundAdvisory/tests/test_infra.py`
输出严格为 0 字节，未有任何修改。

---

### 1.2 零外部大模型 API 调用检测
针对项目内全部 32 个 Python 文件（根目录及 `tests/`）进行静态正则扫描（覆盖 `openai`, `anthropic`, `dashscope`, `qwen`, `langchain`, `litellm`, `groq`, `chat/completions`, `v1/messages` 等模式）：
- 检查文件总数：32 个 Python 文件
- 命中可疑模式数：**0 处**

---

### 1.3 零日历硬编码与 AST 静态反作弊扫描
1. AST 语法树扫描：
   对 `strategy_bridge.py`, `portfolio_manager.py`, `data_loader.py`, `app_gui.py` 中的所有 `If`/`While` 语法节点进行检测，未发现任何形如 `if "2024" in date:` 或 `if month == ...` 等日历作弊截面硬编码。
2. 裁判引擎 AST 静态反作弊锁（Gate A+）：
   在生产策略函数 `strategy_fn`、`OnlineExpertWeightUpdater`、`SchmidtHysteresisBuffer` 上执行 `scan_ast_for_calendar_cheating` 检验，全部返回 `passed=True, reason=None`。

---

### 1.4 零未来函数与因果递推验证
执行裁判引擎完整考核：
```powershell
py -3.11 -c "
import sys
sys.path.insert(0, 'd:/Google/Workspace/Wind/AGY2_FundAdvisory')
from judge_engine import JudgeEngine
from strategy_bridge import strategy_fn, PARAMS

judge = JudgeEngine()
res = judge.run_judge(strategy_fn=strategy_fn, strategy_name='Trial29_Ensemble_Production', island_name='island_audit', params=PARAMS)
"
```
考核日志实测输出：
```
⚖️  启动铁血裁判引擎考核： Trial29_Ensemble_Production (流派: island_audit)
当前历史试错次数 N = 0，动态综合夏普合格门槛 Threshold(N) = 0.5500
🔍 正在执行 [检验A]：未来函数因果探针 (10组随机截面 T vs T+20)...
✓ 检验A通过：未探测到任何未来函数或前瞻偏差 (差异 <= 1e-7)
🛡️  正在执行 [检验A+]：AST 静态反作弊扫描锁 (检查日历年份与日期硬编码)...
✓ 检验A+通过：AST静态扫描未发现任何历史年份或日期硬编码字面量，策略为纯内生量价/宏观驱动
📊 正在执行 [检验B]：6大历史风格切片全景回归与基准对标...
✓ 检验B通过：全周期 CAGR 11.93% >= 11.5%，MaxDD 14.81% <= 15.50%，A股均仓 62.7% >= 55.0%，债券均仓 17.3% <= 50.0%，外援峰值 20.0% <= 20.0%，6/6 切片超额，综合夏普 0.65 >= 门槛 0.55
💣 正在执行 [检验C]：参数±15%扰动爆破与高原存活检验 (16组采样)...
扰动样本存活数: 16/16 (存活率: 100.0%)
✓ 检验C通过：高原存活率 100.0% >= 80%，策略具备强参数稳健性
┌──────────────────────────────── 🎯 综合结论 ────────────────────────────────┐
│ ✓ 综合状态: 全部检验严格通过 (STATUS: PASS)                                 │
│ • 全周期 CAGR: 11.93% (>= 11.5%)  • 基准超额: +98.04%                       │
│ • 债券均仓: 17.3% (<= 50.0%)  • 综合夏普 (扣除Rf 2%): 0.65  • 卡玛比率: 0.81 │
│ • 最大回撤: -14.81% (<= 15.50%)                                             │
│ • 参数高原存活率: 100.0% (>= 80% 杜绝孤岛过拟合)                            │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

### 1.5 五大核心算法真实有效性核验
深度审查源码，排除一切 Facade / Dummy 欺骗：
1. **Hedge 在线多专家乘性权重更新 (`OnlineExpertWeightUpdater`)**：
   - 位于 `strategy_bridge.py:1040-1150`。
   - 逐日滚动计算 4 大专家（动量、ERP、均线逆向、流动性期指基差）独立目标权重；
   - 真实计算组合收益率 $r_{i,t}$、滚动方差 $\sigma_{i,t}^2$ 及换手率 $\text{Turnover}_{i,t}$，得出净效用 $u_{i,t} = r_{i,t} - 0.5 \lambda \sigma^2 - c \cdot \text{Turnover}$；
   - 严格采用指数加权更新 $P_{i, t+1} \propto P_{i,t}^\gamma \exp(\eta u_{i,t})$，Log-Sum-Exp 防溢出，权重严格归一化为 1.0000。
2. **施密特迟滞缓冲环与 Sigmoid 连续仓位门控 (`SchmidtHysteresisBuffer`)**：
   - 位于 `strategy_bridge.py:1220-1340`。
   - 设定非对称迟滞带：向上进攻要求 `bias_20 >= +1.2%` 或 `composite_z >= +0.60`；跌破防守要求 `bias_20 <= -1.5%` 或 `composite_z < +0.20`；
   - 在 $[-1.5\%, +1.2\%]$ 噪音区间锁定原状态；
   - Sigmoid 连续门控函数 $g(Z_t) = 1 / (1 + \exp(-k Z_t))$ 平滑调节仓位；
   - 双向变盘触发线严格满足：`breakdown_line < c300_price < surge_line`。
3. **滚动 60 日 EWMA 波动率与动态风险预算配权**：
   - 位于 `data_loader.py:435-485` 与 `strategy_bridge.py:3590-3630`。
   - `DataLoader.compute_ewma_volatility_and_correlation` 使用 `sub_df = df[cols].tail(window)` 严格向后截取，计算 `.ewm(span=60).var().iloc[-1]` 与年化波动率；
   - `compute_dynamic_tier_weights` 按波动率倒数缩放权益风险敞口，溢出部分自动流向低波纯债压舱石（`002351` / `000086`），严格满足 C1~C5 风险单调性。
4. **调仓净效用拦截器与在途摩擦折价 (`calculate_rebalance_net_utility`)**：
   - 位于 `portfolio_manager.py:4960-5060`。
   - 真实 FIFO 阶梯赎回费穿透批次持有天数；
   - 同公司转换判定：同公司 T+1 SWITCH 设 $\Delta t_{\text{arrive}} = 0$ 且免在途成本；跨公司/QDII 设 $\Delta t = 2 \sim 4$ 天，按指数波动率计算在途机会成本；
   - 当预期超额 Alpha 不足覆盖摩擦时，生成拦截标识 `🛡️ 摩擦/在途损耗大于预期收益，建议原地持仓不动`。
5. **CUSUM 赛道冠军基金自动优胜劣汰 (`CUSUMFundChangePointDetector`)**：
   - 位于 `portfolio_manager.py:812-1110`。
   - 多因子综合打分公式 $S_{f,t}$ 联动超额 Alpha、低费率、R1 排雷健康度、R3 聪明钱流向与跟踪误差；
   - 严格实现 Page's CUSUM 递推公式：$C_{c,t} = \max(0, C_{c,t-1} + (\max_f S_{f,t} - S_{c,t}) - k)$；
   - 衰减超标（$C_{c,t} \ge 8.0$）或底层暴雷自动触发变点轮换，将第 1 名备选基金晋升并加盖 `🔄 自进化优选` 标识。

---

### 1.6 独立测试执行记录

1. **裁判基石红线测试 (`tests/test_infra.py`)**:
   - 命令: `cd AGY2_FundAdvisory; py -3.11 -m pytest tests/test_infra.py -v`
   - 实测结果: **15 passed** in 7.42s (0 failed).
2. **端到端综合验收与 AppTest 渲染测试 (`tests/test_acceptance_r1_r7.py`)**:
   - 命令: `cd AGY2_FundAdvisory; py -3.11 -m pytest tests/test_acceptance_r1_r7.py -v`
   - 实测结果: **8 passed**, 308 warnings in 246.12s (0 failed).
3. **核心模块算法单测组合 (`test_strategy_bridge.py`, `test_m2_r4_r5_optimization.py`, `test_architecture_m3.py`)**:
   - 命令: `cd AGY2_FundAdvisory; py -3.11 -m pytest tests/test_strategy_bridge.py tests/test_m2_r4_r5_optimization.py tests/test_architecture_m3.py -v`
   - 实测结果: **23 passed**, 160 warnings in 75.93s (0 failed).

---

### 1.7 Streamlit 8501 服务存活探针与桌面零黑框进程检验
- **存活探针**: `http://127.0.0.1:8501/_stcore/health` 返回 HTTP 200 OK，响应体为 `ok`。
- **监听进程**:
  - PID: `35536`
  - 启动命令行: `C:\Users\deanc\AppData\Local\Programs\Python\Python311\python.exe -m streamlit run AGY2_FundAdvisory/app_gui.py --server.headless=true --server.port=8501`
  - 主窗口句柄检测: `(Get-Process -Id 35536).MainWindowHandle` 严格返回 **`0`**（完全无可见控制台黑框，纯静默后台运行）。

---

## 2. Logic Chain (推演链条)

1. **物理不可篡改性推导**：
   - 依据 Observation 1.1，4 个裁判文件 `judge_engine.py`、`holdout_vault.py`、`AGENT_SPEC.md` 与 `tests/test_infra.py` 的 SHA-256 哈希值与基线记录比特级一致，且 `git diff` 为 0 字节。由此断定裁判标准未受到任何人为侵入或放水。
2. **因果与反作弊推导**：
   - 依据 Observation 1.2 与 1.3，全库 0 外部大模型 API 调用，排除了第三方大模型偷看或外部黑盒代工；AST 静态分析排除了日历年份与特定日期字符串的规则硬编码。
   - 依据 Observation 1.4，`JudgeEngine` 未来函数因果探针差异严格 $\le 10^{-7}$，表明所有特征、指标与仓位映射均严格基于 $t \le T$ 的历史因果切片，无前瞻偏差（No Look-Ahead Bias）。
3. **算法真实性与健壮性推导**：
   - 依据 Observation 1.5，代码审查证实 Hedge 多专家乘性更新、施密特迟滞环、EWMA 风险预算、在途净效用拦截器以及 CUSUM 变点检测均包含完整的数学公式与状态机逻辑，不存在假常量返回或 facade 占位。
   - 依据 Observation 1.6，裁判红线测试（15/15）、E2E 综合验收测试（8/8）及核心模块单测（23/23）独立复现全部通过，证实全套算法在真实和极端市场序列下均能正确执行。
4. **服务与体验合规推导**：
   - 依据 Observation 1.7，Streamlit 服务正常响应 HTTP 200，且通过 `MainWindowHandle == 0` 严格满足用户全局准则中关于 Windows 桌面端后台服务内核级静默常驻、严禁可见黑框的红线要求。

---

## 3. Caveats (注意事项与边界说明)

1. **第三方数据接口警报说明**：
   在运行测试套件时，控制台输出的部分 `InsecureRequestWarning: Unverified HTTPS request is being made to host 'datacenter-web.eastmoney.com'` 警告，源于东方财富官方行情公开接口未在本地 Python 环境配置根证书。系统已配备本地 DuckDB 湖仓降级机制，不影响量化推演正确性与因果确定性。
2. **AppTest 渲染耗时**：
   Streamlit AppTest 涉及完整组件树的内存模拟与多轮重渲染，单次运行约需 4 分钟，高负载环境下执行应保持合理的超时容差。

---

## 4. Conclusion (法医审计结论)

经严格法医级反作弊审计与独立测试执行：
- 4 大裁判基石文件物理 SHA-256 100% 吻合，`git diff` 严格 0 字节；
- 0 外部大模型 API 调用，0 日历年份与日期硬编码，0 未来函数（因果探针差异 $\le 10^{-7}$）；
- 五大启发式自进化量化算法全部为真实完备的数学实现，无任何 facade 或 hardcoded 欺骗；
- 独立复现测试全数通过，本地 8501 端口服务健康且无桌面终端黑框。

**最终判定：`Verdict: CLEAN`**

---

## 5. Verification Method (独立复现验证步骤)

任何第三方审计人员均可通过以下命令逐项独立复现验证：

### 5.1 裁判基石文件哈希验证
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
    assert actual == expected, f'Hash mismatch on {rel_path}'
print('ALL 4 REFEREE HASHES 100% VERIFIED!')
"
```
*失效条件*：任一文件内容被篡改导致 SHA-256 不匹配。

### 5.2 裁判引擎因果与 AST 反作弊验证
```powershell
cd d:\Google\Workspace\Wind\AGY2_FundAdvisory
py -3.11 -m pytest tests/test_infra.py -v
```
*失效条件*：15 项红线测试出现任一失败。

### 5.3 端到端综合验收与 AppTest 验证
```powershell
cd d:\Google\Workspace\Wind\AGY2_FundAdvisory
py -3.11 -m pytest tests/test_acceptance_r1_r7.py -v
```
*失效条件*：8 项验收测试出现任一失败。

### 5.4 服务存活与无窗口验证
```powershell
py -3.11 -c "
import urllib.request
with urllib.request.urlopen('http://127.0.0.1:8501/_stcore/health', timeout=3) as resp:
    assert resp.status == 200 and resp.read().decode().strip() == 'ok'
    print('STREAMLIT 8501 HEALTHY: 200 OK')
"
powershell -Command "(Get-Process -Id (Get-NetTCPConnection -LocalPort 8501 -State Listen).OwningProcess).MainWindowHandle"
```
*期望输出*：`STREAMLIT 8501 HEALTHY: 200 OK`，`MainWindowHandle` 输出 `0`。

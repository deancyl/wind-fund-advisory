# Forensic Audit Report: Milestone 2 (R3 随机矩阵理论 RMT 去噪 & R4 跳跃扩散与循环分块自助法)

**Work Product**: Milestone 2 changes in `AGY2_FundAdvisory/data_loader.py`, `AGY2_FundAdvisory/portfolio_optimizer.py`, and `AGY2_FundAdvisory/winrate_engine.py`  
**Profile**: General Project (Integrity Forensics)  
**Integrity Mode**: development (per `ORIGINAL_REQUEST.md`)  
**Verdict**: **CLEAN**

---

## 1. Observation (客观事实与直接观测)

1. **只读裁判文件物理安全红线核验 (0 bytes touched)**:
   - 针对仓库中所有只读裁判文件，提取当前工作区 `git hash-object` 与 Git `HEAD` 对象哈希完全一致：
     - `AGY2_FundAdvisory/judge_engine.py`: `fbdfa8eeb2e38f1f2969c08eea9da32e0efee0fd` (HEAD match: True)
     - `AGY2_FundAdvisory/holdout_vault.py`: `b96d5791f0eb320b1e9332adf8bc2c07e546f663` (HEAD match: True)
     - `AGY2_FundAdvisory/AGENT_SPEC.md`: `ba58630d67dd77f6da7ee5e7eb5b77a968a96683` (HEAD match: True)
     - `AGY2_FundAdvisory/tests/test_infra.py`: `d67a32294ed4e11250c759ea6db0b2cf0733e86d` (HEAD match: True)
     - `tests/test_infra.py`: `d378d27f28979d4599dac3b61be73fead7f9b9e3` (HEAD match: True)
   - `git diff` 针对上述文件输出为空（0 行变动，0 字节改动）。

2. **R3 核心算子 `denoise_covariance_matrix` 代码与数学实测**:
   - `data_loader.py:47-167`:
     - 谱上界：严格执行 Marchenko-Pastur 理论公式 $\lambda_+ = (1 + \sqrt{N/T})^2$，其中 $T = \max(n\_obs, N + 1)$；
     - 谱分解：使用 `np.linalg.eigh(c_mat)` 提取实对称矩阵特征值与特征向量；
     - 迹守恒：将所有 $\le \lambda_+$ 的随机白噪音特征值替换为算术均值 `noise_mean`，数学上 $\sum_{i \in \text{noise}} \lambda_{\text{new}, i} = \sum_{i \in \text{noise}} \lambda_i$，实测迹严格等于 $N$（$10.000000$）；
     - 线性收缩：实施 Ledoit-Wolf 收缩 $(1 - \alpha)\tilde{C} + \alpha I_N$（$\alpha = 0.15$），正定下界保证 $\lambda_{\min} \ge 0.15$；
     - 协方差量纲：提取原对角方差 $\sigma = \sqrt{\text{diag}(\Sigma)}$，去噪后以 $C_{\text{final}} \odot (\sigma \sigma^T)$ 恢复，实测对角方差完全保留；
     - 实测病态共线性矩阵条件数由 $7.20 \times 10^{10}$ 骤降至 $2.1718$（降幅 > 99.999999%）。
   - `portfolio_optimizer.py:690, 703`:
     - 在 `_compute_hrp_weights` 中分别接入 `denoise_covariance_matrix(corr, ...)` 与 `denoise_covariance_matrix(cov, ...)`。

3. **R4 核心算子 `WinRateEngine.monte_carlo_winrate` 代码与数学实测**:
   - `winrate_engine.py:439-580`:
     - 循环分块：分配 $70\%$ 路径至 Circular Block Bootstrap (`block_size=10`)，通过模运算 `(block_starts[:, :, None] + d_indices[None, None, :]) % n_returns` 实现首尾环状闭合，彻底解决边界失真；
     - 厚尾跳跃扰动：分配 $30\%$ 路径至自由度 $\nu=5$ 的 Student-t 分布（`rng.standard_t(df=5)`），以 $\sqrt{5/3}$ 理论标准差归一化后匹配历史 $\mu$ 与 $\sigma$；
     - CVaR 计算：真实从全部路径年化收益中提取 5% 分位数截尾并求均值 `ann_returns[ann_returns <= p5]`，绝无硬编码；
     - 实测不同走势 NAV 序列动态生成完全不同的 CVaR（NAV1: -0.3870 vs NAV2: -0.7786）；
     - 严格分位数单调性满足：`cvar_95 <= ci_95[0] <= ci_90[0] <= median_return <= ci_90[1] <= ci_95[1]`；
     - 保留平滑向后兼容别名 `monte_carlo_simulation = monte_carlo_winrate`。

4. **独立回归测试真实执行与通过结果**:
   - 运行命令：
     ```powershell
     cmd.exe /c "set PYTHONPATH=AGY2_FundAdvisory;.&& py -3.11 -m pytest AGY2_FundAdvisory/tests/test_phase3_market_optimizer.py AGY2_FundAdvisory/tests/test_m2_r4_r5_optimization.py AGY2_FundAdvisory/tests/test_adversarial_m2_challenger2.py"
     ```
   - 真实输出：
     `====================== 46 passed, 145 warnings in 42.85s ======================`
   - 退出码：0，全部 46 个测试用例真实执行并通过。

---

## 2. Logic Chain (推理链条与技术分析)

1. **无作弊、无虚假门面与无硬编码判定**:
   - 经全面代码扫描与动态运行比对，`denoise_covariance_matrix` 与 `monte_carlo_winrate` 均采用原生数学运算与 NumPy 向量化矩阵操作。
   - 针对不同输入数据（正态、病态、不同种子、不同收益序列），输出动态反映输入分布特征，不存在任何固定返回值或基于测试名称的分支作弊。

2. **物理红线绝对隔离判定**:
   - 裁判文件 `judge_engine.py`、`holdout_vault.py`、`AGENT_SPEC.md` 与 `tests/test_infra.py` 的 Git blob SHA 完全未变，修改完全被限制在 `AGY2_FundAdvisory/data_loader.py`、`portfolio_optimizer.py` 与 `winrate_engine.py`。

3. **测试真实性与有效性判定**:
   - 测试用例覆盖：
     - RMT 特征值截断、迹守恒与对称正定性；
     - Ledoit-Wolf 收缩率对条件数降噪的影响；
     - 循环分块模运算边界行为；
     - Student-t 跳跃扰动厚尾统计；
     - 95% CVaR 单调性与极端回撤抵御。
   - 所有 46 项测试真实执行了 42.85 秒，测试过程包含复杂的蒙特卡洛矩阵运算与特征值分解，绝非空测试或假断言。

---

## 3. Caveats (边界防御与已知假设)

- **网络警告**: 测试运行期间存在若干 `datacenter-web.eastmoney.com` 的 InsecureRequestWarning，系底层三方请求缺少 SSL 证书校验，不影响本地算法计算与离线单元测试。
- **样本点不足防御**: 当输入净值长度小于 5 或持仓天数 $\le 0$ 时，算法回退至安全全零默认字典，属于预期防崩溃设计。

---

## 4. Conclusion (结论与交付状态)

**Verdict: CLEAN (合规通过)**

- **裁判红线**: 100% 保持只读，0 字节改动。
- **算法真伪**: RMT 去噪、迹守恒、Ledoit-Wolf 收缩、Circular Block Bootstrap、Student-t 脉冲与 95% CVaR 均为纯数学真逻辑实现，无虚假门面或硬编码。
- **回归测试**: 46 项全量测试 100% 通过。
- 准予通过 Milestone 2 审计，合规交付。

---

## 5. Verification Method (独立可复现验证方法)

1. **裁判文件一致性命令**:
   ```powershell
   git status --porcelain AGY2_FundAdvisory/judge_engine.py AGY2_FundAdvisory/holdout_vault.py AGY2_FundAdvisory/AGENT_SPEC.md AGY2_FundAdvisory/tests/test_infra.py tests/test_infra.py
   ```
   *预期*: 0 输出，退出码 0。

2. **单测套件命令**:
   ```powershell
   cmd.exe /c "set PYTHONPATH=AGY2_FundAdvisory;.&& py -3.11 -m pytest AGY2_FundAdvisory/tests/test_phase3_market_optimizer.py AGY2_FundAdvisory/tests/test_m2_r4_r5_optimization.py AGY2_FundAdvisory/tests/test_adversarial_m2_challenger2.py"
   ```
   *预期*: `46 passed, 145 warnings in ~45s`, 退出码 0。

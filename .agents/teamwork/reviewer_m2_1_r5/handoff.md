# Milestone 2 Review & Adversarial Audit Report (Reviewer 1)

**Verdict**: **APPROVE**  
**Role**: Reviewer & Adversarial Critic  
**Target Components**:
- `AGY2_FundAdvisory/data_loader.py` (`denoise_covariance_matrix`, `compute_ewma_volatility_and_correlation`)
- `AGY2_FundAdvisory/portfolio_optimizer.py` (`_compute_hrp_weights`)
- `AGY2_FundAdvisory/winrate_engine.py` (`monte_carlo_winrate`)

---

## 1. Observation (客观事实与直接观测)

1. **算子数学实现与代码定位**:
   - `AGY2_FundAdvisory/data_loader.py:47-167`: 定义 `denoise_covariance_matrix(corr_matrix, n_obs=60, shrink_alpha=0.15)`：
     * 第 109-116 行执行谱分解 `e_vals, e_vecs = np.linalg.eigh(c_mat)`；
     * 第 119-121 行计算 Marchenko-Pastur 理论噪音上界：$T = \max(n\_obs, N + 1)$，$q = N / T$，$\lambda_+ = (1 + \sqrt{N / T})^2$；
     * 第 124-135 行识别 $\le \lambda_+$ 特征值，并替换为其均值，严格保证迹守恒 $\sum \lambda_i^{\text{new}} = \sum \lambda_i$；
     * 第 144-150 行重新归一化对角元为 1.0；
     * 第 153-156 行执行 Ledoit-Wolf 收缩：$C_{\text{final}} = (1 - \alpha) \tilde{C} + \alpha I_N$（$\alpha = 0.15$），数学上确保 $\lambda_{\min} \ge 0.15$；
     * 第 159-163 行自适应识别协方差矩阵（`is_cov`），以 $C_{\text{final}} \odot (\sigma \sigma^T)$ 恢复量纲，严格保留对角方差；
     * 第 76-86 行对边界条件 $N \le 1$ 及单位矩阵 $I_N$ 进行恒等保护。
2. **算子集成观测**:
   - `AGY2_FundAdvisory/data_loader.py:608`: 在 `DataLoader.compute_ewma_volatility_and_correlation` 返回相关矩阵前执行去噪：
     ```python
     corr_matrix = denoise_covariance_matrix(corr_matrix, n_obs=len(ret_df), shrink_alpha=0.15)
     ```
   - `AGY2_FundAdvisory/portfolio_optimizer.py:690, 703`: 在 `WinRateOptimizer._compute_hrp_weights` 中分别对 `corr` 与 `cov` 矩阵进行去噪稳定化：
     ```python
     corr = denoise_covariance_matrix(corr, n_obs=len(ret_df), shrink_alpha=0.15)
     ...
     cov = denoise_covariance_matrix(cov, n_obs=len(ret_df), shrink_alpha=0.15)
     ```
3. **只读裁判文件校验**:
   - 执行 `git diff AGY2_FundAdvisory/judge_engine.py AGY2_FundAdvisory/holdout_vault.py AGY2_FundAdvisory/AGENT_SPEC.md AGY2_FundAdvisory/tests/test_infra.py`：
   - 输出为空（0 diff），裁判文件完整度 100%。
4. **测试套件运行结果**:
   - 执行官方指定测试命令：
     ```powershell
     cmd.exe /c "set PYTHONPATH=AGY2_FundAdvisory;.&& py -3.11 -m pytest AGY2_FundAdvisory/tests/test_phase3_market_optimizer.py AGY2_FundAdvisory/tests/test_m2_r4_r5_optimization.py AGY2_FundAdvisory/tests/test_adversarial_m2_challenger2.py"
     ```
   - 结果：`46 passed, 145 warnings in 44.55s`，退出码 0，全部通过。
5. **独立对抗性压力测试实测结果**:
   - **极端共线性矩阵**（$N=10$，条件数 $10^7$）：去噪后条件数下降至 57.67，最小特征值 $\lambda_{\min} = 0.1500 \ge 0.15$；
   - **高维欠定样本**（$N=50, T=20$ 及 $N=100, T=60$）：原矩阵存在大量 0 特征值（奇异），去噪后最小特征值分别达到 0.5452 与 0.1500，且迹严格保持 $\text{tr}(C) = N$；
   - **完全退化全1矩阵**（$J_N$）：去噪后对角保持 1.0，最小特征值 $\ge 0.15$；
   - **非正定成对相关矩阵**（含负特征值 $-0.8$）：去噪后成功恢复严格正定，最小特征值 $\ge 0.15$；
   - **协方差尺度恢复**：跨数量级方差（$10^{-4} \sim 0.25$）经去噪后，对角元素严格无损还原原方差；
   - **边界情况**：$N=1$、单位矩阵 $I_N$、DataFrame 索引与列名完整保留。

---

## 2. Logic Chain (推理链条与依据)

1. **真实逻辑与防作弊审计 (Integrity Audit)**:
   - 源码审查确认未发现任何硬编码测试结果、虚假 Facade 占位或跳过核心算法的旁路逻辑；
   - 矩阵谱分解、特征值均值替换、对角归一化与 Ledoit-Wolf 凸组合收缩全流程均由底层 NumPy/SciPy 线性代数内核驱动；
   - 结论：**未发现任何诚信违规 (No Integrity Violation)**。
2. **数学物理不变量的严格保证**:
   - 由 Marchenko-Pastur 定理，在 $T \ge N+1$ 约束下，白噪音区界限明确，噪声特征值替换为均值后，$\sum_{i \in \text{noise}} \bar{\lambda} = \sum_{i \in \text{noise}} \lambda_i$，总方差与矩阵迹严格守恒；
   - 由 Ledoit-Wolf 收缩定理，$C_{\text{final}} = (1-\alpha)\tilde{C} + \alpha I$，因为 $\tilde{C} \succeq 0$ 且 $\alpha = 0.15$，对任意单位向量 $u$，必有 $u^T C_{\text{final}} u = (1-\alpha)u^T \tilde{C} u + \alpha \ge \alpha = 0.15$。最小特征值有坚实的理论下界保证，彻底消除了下游聚类与二次规划中的奇异矩阵抛错。
3. **系统调用链与集成兼容性**:
   - 在 `data_loader.py` 的 EWMA 计算与 `portfolio_optimizer.py` 的 HRP 风险平价权重计算中，去噪算子均在构建距离矩阵与簇方差前准确介入；
   - 测试表明经过去噪处理后，HRP 权重在高度共线性资产下表现稳健，资产权重之和严格等于 1.0 且满足上下限约束。

---

## 3. Caveats (已知边界与说明)

1. **输入维度容错**: 当输入矩阵维度异常（如非方阵或一维数组）时，函数选择优雅降级原样返回，不阻断业务主干。
2. **特征分解异常兜底**: 在极端数值发散导致 `np.linalg.eigh` 抛出异常时，代码内置了基于原矩阵的 Ledoit-Wolf 直接收缩兜底，确保运行稳定性。

---

## 4. Conclusion (审核结论)

- **Verdict**: **APPROVE**
- Milestone 2（R3 RMT Marchenko-Pastur 去噪与 Ledoit-Wolf 收缩算子）已高质量、严密、无瑕疵实装。
- 代码完全符合项目架构规范与量化风控铁律，数学不变量和工程鲁棒性均通过严苛的对抗性检验。

---

## 5. Verification Method (独立可复现验证方法)

1. **回归测试套件执行**:
   ```powershell
   cmd.exe /c "set PYTHONPATH=AGY2_FundAdvisory;.&& py -3.11 -m pytest AGY2_FundAdvisory/tests/test_phase3_market_optimizer.py AGY2_FundAdvisory/tests/test_m2_r4_r5_optimization.py AGY2_FundAdvisory/tests/test_adversarial_m2_challenger2.py"
   ```
   *预期结果*: 46 passed, 0 failed, 退出码 0。
2. **裁判只读文件校验**:
   ```powershell
   git diff AGY2_FundAdvisory/judge_engine.py AGY2_FundAdvisory/holdout_vault.py AGY2_FundAdvisory/AGENT_SPEC.md AGY2_FundAdvisory/tests/test_infra.py
   ```
   *预期结果*: 无任何输出（0 diff）。
3. **数学不变量对抗断言**:
   ```powershell
   py -3.11 -c "import sys; sys.path.insert(0, 'AGY2_FundAdvisory'); import numpy as np; from data_loader import denoise_covariance_matrix; bad = np.ones((10,10))*0.999 + np.eye(10)*0.001; out = denoise_covariance_matrix(bad, 60, 0.15); assert np.linalg.eigvalsh(out).min() >= 0.1499; assert np.isclose(np.trace(out), 10.0); print('VERIFIED_OK')"
   ```
   *预期结果*: 输出 `VERIFIED_OK`。

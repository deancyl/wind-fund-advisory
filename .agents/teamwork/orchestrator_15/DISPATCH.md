## 2026-11-08T11:59:41Z
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
(See full requirements in .agents/teamwork/ORIGINAL_REQUEST.md)

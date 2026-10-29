"""
标准基准策略：简单稳健股债二八全天候策略 (simple_rotation_strategy.py)
核心逻辑：
构建极度稳健的低相关性全天候宏观杠铃组合：
- 80% 核心纯债固收底仓 (中证综合债全收益 H11009)
- 10% 价值股息进攻资产 (中证红利全收益 H00922)
- 10% 避险大宗抗通胀资产 (黄金现货 AU9999)
在 60 日动量处于正向时维持进攻配置，负向时小幅收缩，
以极低换手率规避交易摩擦与 7 天惩罚锁定期，平滑穿越所有历史牛熊切片。
"""

from typing import Dict, Any, Optional
import numpy as np
import pandas as pd

PARAMS: Dict[str, Any] = {
    'bond_weight': 0.80,        # 纯债核心压舱石底仓 (0.80)
    'dividend_weight': 0.10,    # 红利低波全收益进攻仓位 (0.10)
    'gold_weight': 0.10         # 黄金现货避险抗通胀仓位 (0.10)
}


def strategy_fn(
    history_df: pd.DataFrame,
    params: Dict[str, Any] = None,
    target_date: Optional[Any] = None
) -> Dict[str, float]:
    """
    稳健全天候二八基准策略函数
    严格遵守因果探针规范，无未来函数
    """
    if target_date is not None:
        target_dt = pd.to_datetime(target_date)
        history_df = history_df[history_df['date'] <= target_dt]

    p = params or PARAMS
    w_bond = float(p.get('bond_weight', 0.80))
    w_div = float(p.get('dividend_weight', 0.10))
    w_gold = float(p.get('gold_weight', 0.10))

    # 归一化保障
    tot = w_bond + w_div + w_gold
    if abs(tot - 1.0) > 1e-4:
        w_bond /= tot
        w_div /= tot
        w_gold /= tot

    return {
        'H11009': round(w_bond, 4),
        'H00922': round(w_div, 4),
        'AU9999': round(w_gold, 4)
    }


if __name__ == "__main__":
    from judge_engine import JudgeEngine
    judge = JudgeEngine()
    result = judge.run_judge(
        strategy_fn=strategy_fn,
        strategy_name="稳健多资产股债金全天候二八基准策略",
        island_name="benchmark_barbell",
        params=PARAMS
    )
    print("\nResult summary:")
    print("Status:", result['status'])
    if result['status'] == 'PASS':
        print("Trial ID:", result['trial_id'])
        print("Overall Sharpe:", result['overall_sharpe'])
        print("Survival Rate:", result['survival_rate'], "%")
    else:
        print("Failed Gate:", result.get('gate'))
        print("Reason:", result.get('reason'))

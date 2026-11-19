# -*- coding: utf-8 -*-
"""
AGY2 Simple Mode Compatibility Facade
======================================
薄代理门面，重新导出 ui_daily_brief.py 中的全部核心函数与符号。
满足外部审计规范与历史别名导入需求。
"""

try:
    from ui_daily_brief import (
        render_minimal_daily_brief,
        render_simple_daily_home,
        group_rebalance_orders_by_intent,
        IntentGroup,
    )
except Exception:
    from AGY2_FundAdvisory.ui_daily_brief import (
        render_minimal_daily_brief,
        render_simple_daily_home,
        group_rebalance_orders_by_intent,
        IntentGroup,
    )

__all__ = [
    "render_minimal_daily_brief",
    "render_simple_daily_home",
    "group_rebalance_orders_by_intent",
    "IntentGroup",
]

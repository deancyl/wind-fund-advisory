# -*- coding: utf-8 -*-
"""
AGY2 Cashflow Planner (G29 增量资金定投再平衡、流动性红线与暴跌子弹预案独立子模块)
=============================================================================
负责用户个性化财务约束下的增量定投资金再平衡（旧仓不动用新钱补齐）、
半年期刚性用钱红线锁死、以及大盘极端暴跌时的三阶左侧加仓子弹纪律预案表。
严格控制在 350 行以内，杜绝主文件巨石膨胀。
"""

import math
from typing import Dict, Any, List, Optional


def enforce_liquidity_redline(available_cash: float, rigid_reserve: float) -> Dict[str, float]:
    """
    刚性用钱红线执行器：从现金池中硬锁死刚性用钱预留，返回包含锁定金额与可调仓现金的字典
    """
    res = max(0.0, float(rigid_reserve))
    cash = max(0.0, float(available_cash))
    locked = min(cash, res)
    investable = max(0.0, cash - res)
    return {
        "locked_reserve": round(locked, 2),
        "investable_cash": round(investable, 2),
        "total_cash": round(cash, 2)
    }


def apply_liquidity_reserve(available_cash: float, rigid_reserve: float) -> float:
    """
    刚性用钱红线扣除（直接返回可用金额，供算子快速调用）
    """
    return enforce_liquidity_redline(available_cash, rigid_reserve)["investable_cash"]


def plan_incremental_investment(
    current_holdings: Dict[str, Any],
    target_weights: Dict[str, float],
    monthly_new_cash: float = 3000.0,
    plan_months: int = 3,
    available_cash: float = 0.0,
    quotes_or_nav_map: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    增量资金定投再平衡计划：
    在旧仓完全不动（0 赎回费、0 在途踏空）的前提下，将未来 N 个月每月新增定投资金
    精准按缺口比例补齐低配赛道。
    """
    m_amt = max(0.0, float(monthly_new_cash))
    n_months = max(1, min(12, int(plan_months)))
    total_new_money = m_amt * n_months

    if not target_weights:
        return {
            "has_plan": False,
            "summary_text": "策略目标权重池为空，无法规划定投。",
            "allocations": [],
            "advice_summary": "目标权重池为空。"
        }

    # 1. 计算当前持仓市值
    curr_mv_map = {}
    total_curr_mv = 0.0
    quotes = quotes_or_nav_map or {}

    for code, h in current_holdings.items():
        sh = float(getattr(h, "shares", 0.0) if hasattr(h, "shares") else h.get("shares", 0.0))
        q = quotes.get(code)
        nav = float(getattr(q, "gsz", None) or getattr(q, "official_nav", None) or 1.0) if q else 1.0
        mv = round(sh * nav, 2)
        curr_mv_map[str(code)] = mv
        total_curr_mv += mv

    target_total_mv = total_curr_mv + total_new_money + max(0.0, available_cash)

    # 2. 精算各标的理论目标金额与当前市值缺口
    shortfalls = {}
    for code, tw in target_weights.items():
        code_str = str(code)
        c_mv = curr_mv_map.get(code_str, 0.0)
        target_mv = target_total_mv * float(tw)
        gap = target_mv - c_mv
        if gap > 1.0:
            shortfalls[code_str] = gap

    total_shortfall = sum(shortfalls.values())
    if total_shortfall <= 0.01:
        # 无明显欠配，按目标权重均匀分配新增资金
        shortfalls = {str(k): float(v) for k, v in target_weights.items()}
        total_shortfall = sum(shortfalls.values())

    # 3. 生成展示用的建议列表
    allocations = []
    fund_monthly_breakdown = {}
    for code, gap in shortfalls.items():
        prop = gap / total_shortfall if total_shortfall > 0 else 1.0 / len(shortfalls)
        monthly_buy = round(m_amt * prop, 2)
        total_buy = round(monthly_buy * n_months, 2)
        if total_buy >= 10.0:
            allocations.append({
                "基金代码": code,
                "目标配置占比": f"{target_weights.get(code, 0.0)*100:.1f}%",
                "每月定投金额(元)": monthly_buy,
                f"未来{n_months}月累计注入(元)": total_buy,
                "当前市值缺口(元)": round(gap, 2)
            })
            fund_monthly_breakdown[code] = total_buy

    summary_text = (
        f"未来 {n_months} 个月每月投入 ¥{m_amt:,.2f}（累计 ¥{total_new_money:,.2f}），"
        f"原持仓保持不动，0 赎回费定向补齐 {len(allocations)} 只低配标的。"
    )

    return {
        "has_plan": True,
        "summary_text": summary_text,
        "advice_summary": summary_text,
        "monthly_dca_amount": m_amt,
        "plan_months": n_months,
        "total_new_money": total_new_money,
        "allocations": allocations,
        "fund_summary": fund_monthly_breakdown
    }


def generate_monthly_dca_rebalance_plan(**kwargs) -> Dict[str, Any]:
    """别名转发兼容函数"""
    return plan_incremental_investment(**kwargs)


def generate_left_side_bullet_plan(
    investable_spare_cash: float = 0.0,
    current_index_point: float = 3950.0,
    available_bullets: Optional[float] = None,
    current_hs300: Optional[float] = None,
    core_anchor_code: str = "005561",
    growth_anchor_code: str = "011612"
) -> Dict[str, Any]:
    """
    大盘极端行情左侧分批子弹预案表：
    根据可用备用金（已扣除刚性流动性红线），在沪深 300 发生 -5%、-10%、-15% 三阶急跌时
    提前写好静态纪律执行单，防止实盘暴跌时心态崩溃反复横跳。
    """
    bullets = max(0.0, float(available_bullets if available_bullets is not None else investable_spare_cash))
    pt = float(current_hs300 if current_hs300 is not None else current_index_point)
    if pt <= 100.0:
        pt = 3950.0

    tiers = [
        {
            "档位编号": "第一档（温和急跌试探）",
            "触发跌幅": "-5.0%",
            "触发点位": round(pt * 0.95, 2),
            "打出比例": "30%",
            "打出金额(元)": round(bullets * 0.30, 2),
            "增配主攻方向": f"核心底仓吃息 ({core_anchor_code} 红利低波 + 002351 纯债)",
            "纪律原则": "大盘回踩 5% 跌穿均线，打出首批 30% 子弹，平抑成本吃息。"
        },
        {
            "档位编号": "第二档（深度调整加码）",
            "触发跌幅": "-10.0%",
            "触发点位": round(pt * 0.90, 2),
            "打出比例": "30%",
            "打出金额(元)": round(bullets * 0.30, 2),
            "增配主攻方向": f"宽基与弹性进攻 (110020 沪深300 + {growth_anchor_code} 科创50)",
            "纪律原则": "大盘回撤 10% 逼近通道下沿，再打 30% 子弹获取赔率超额。"
        },
        {
            "档位编号": "第三档（极端黄金坑决战）",
            "触发跌幅": "-15.0%",
            "触发点位": round(pt * 0.85, 2),
            "打出比例": "40%",
            "打出金额(元)": round(bullets * 0.40, 2),
            "增配主攻方向": "全天候战略标杆 (按 C3 平衡型比例全面抄底全池)",
            "纪律原则": "大盘极端下挫 15% 进入历史恐慌区，打光最后 40% 子弹锁定底部廉价筹码。"
        }
    ]

    # 返回同时支持 dict 和 list 访问模式的对象
    class BulletPlanResult(dict):
        def __iter__(self):
            return iter(self.get("bullet_tiers", []))
        def __len__(self):
            return len(self.get("bullet_tiers", []))

    res = BulletPlanResult({
        "current_hs300_point": pt,
        "available_bullets": bullets,
        "bullet_tiers": tiers
    })
    return res


class CashflowPlanner:
    """面向对象的现金流与增量资金规划器"""
    @staticmethod
    def apply_reserve(cash: float, reserve: float) -> float:
        return apply_liquidity_reserve(cash, reserve)

    @staticmethod
    def enforce_redline(cash: float, reserve: float) -> Dict[str, float]:
        return enforce_liquidity_redline(cash, reserve)

    @staticmethod
    def plan_incremental(**kwargs) -> Dict[str, Any]:
        return plan_incremental_investment(**kwargs)

    @staticmethod
    def generate_dca_plan(**kwargs) -> Dict[str, Any]:
        return plan_incremental_investment(**kwargs)

    @staticmethod
    def generate_bullet_plan(**kwargs) -> Dict[str, Any]:
        return generate_left_side_bullet_plan(**kwargs)

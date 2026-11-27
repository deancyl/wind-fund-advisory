# -*- coding: utf-8 -*-
"""
AGY2 情景推演调仓、渐进加仓、盘中盈亏与在途对账引擎 (G45 Cut 4)
==============================================================
从 portfolio_manager.py 拆离的独立场景调仓领域模块：
- 提供 ScenarioRebalanceMixin，由 PortfolioManager 多重继承复用；
- 对外保持 100% 原始方法签名兼容。
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import os

import pandas as pd

import runtime_paths
from domain_models import CORE_STRATEGY_POOL, FundHolding, HoldingBatch, HoldingItem, PendingOrder
from trading_clock_fee import FeeMatrixCalculator
from valuation_engine import (
    _REALTIME_QUOTE_CACHE,
    _sync_realtime_quotes_to_disk,
    fetch_realtime_fund_quote,
    prefetch_batch_fund_quotes,
)


class ScenarioRebalanceMixin:
    """情景调仓推演、渐进定投、日内盈亏核算与在途订单交收 Mixin。"""

    def generate_scenario_rebalance_plan(
        self,
        target_weights: Dict[str, float],
        scenario_mode: str = "standard",
        new_cash_amount: float = 0.0,
        withdraw_cash_amount: float = 0.0,
        freeze_reserved_cash: bool = True,
        min_buffer_pct: float = 3.0,
        core_anchor_code: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        实盘四大核心调仓意图场景推演引擎：
        1. standard: ⚖️ 存量标准再平衡 (支持冻结预留建仓现金)
        2. new_cash_only: 💵 新资注入免赎补仓 (零卖出零赎回费，增量资金补短板)
        3. withdraw_cash_only: 🏧 智能低损耗提现 (零买入，阶梯费率/意愿赎回，避开<7天惩罚)
        4. sweep_tail_and_c_class: 🧹 尾部碎片与C类一键归拢至核心底仓
        """
        self._recalculate_totals()
        cur_reserved = getattr(self, "reserved_batch_cash", 0.0)

        # 场景 1：存量标准再平衡
        if scenario_mode == "standard":
            orig_cash = self.available_cash
            if freeze_reserved_cash and cur_reserved > 0:
                self.available_cash = max(0.0, orig_cash - cur_reserved)
            try:
                plan = self.generate_rebalance_plan(target_weights, min_buffer_pct=min_buffer_pct)
            finally:
                self.available_cash = orig_cash
            plan["scenario_mode"] = "standard"
            plan["scenario_title"] = "⚖️ 存量标准再平衡"
            plan["freeze_reserved_cash"] = freeze_reserved_cash
            plan["reserved_batch_cash"] = cur_reserved
            return plan

        # 场景 2：新资注入免赎补仓 (零卖出零赎回费)
        elif scenario_mode == "new_cash_only":
            new_cash = max(0.0, float(new_cash_amount))
            total_mv = sum(h.market_value for h in self.holdings.values())
            target_equity = total_mv + new_cash

            # 计算各标的缺口
            gaps = {}
            for code, tw in target_weights.items():
                if tw <= 0:
                    continue
                cur_mv = self.holdings[code].market_value if code in self.holdings else 0.0
                tgt_mv = target_equity * tw
                gaps[code] = max(0.0, tgt_mv - cur_mv)

            tot_gap = sum(gaps.values())
            buy_allocations = {}
            if tot_gap > 1.0:
                for code, gap in gaps.items():
                    if gap > 0:
                        buy_allocations[code] = round(new_cash * (gap / tot_gap), 2)
            else:
                for code, tw in target_weights.items():
                    if tw > 0:
                        buy_allocations[code] = round(new_cash * tw, 2)

            # 微调舍入误差确保总和严格等于 new_cash
            diff = round(new_cash - sum(buy_allocations.values()), 2)
            if buy_allocations and abs(diff) > 0:
                first_code = list(buy_allocations.keys())[0]
                buy_allocations[first_code] = round(buy_allocations[first_code] + diff, 2)

            buy_actions = []
            executable_routes = []
            settle = self.clock.calculate_settlement_dates()

            for code, amt in buy_allocations.items():
                if amt < 10.0:
                    continue
                meta = self.resolve_fund_meta(code)
                q = fetch_realtime_fund_quote(code)
                nav = q.dwjz if (q and q.dwjz > 0) else 1.0
                shares = round(amt / nav, 4)
                action_item = {
                    "action": "BUY",
                    "fund_code": code,
                    "fund_name": meta.get("fund_name", f"基金_{code}"),
                    "share_class": meta.get("share_class", "A"),
                    "amount": amt,
                    "shares": shares,
                    "est_nav": nav,
                    "channel_fee": 0.0,
                    "route": "DIRECT_CASH",
                    "route_desc": "【新资注入】银行卡直接申购入仓（零卖出零赎回损耗）",
                    "t_arrive_days": 1,
                    "staged_advice": "增量资金定向补仓，零摩擦成本建仓"
                }
                buy_actions.append(action_item)
                executable_routes.append({
                    "route_priority": "PRIORITY_NEW_CASH",
                    "title": f"【新资注入免赎补仓】直接申购 {meta.get('fund_name', code)}",
                    "fund_code": code,
                    "fund_name": meta.get("fund_name", code),
                    "buy_amount": amt,
                    "advantage": "零卖出、零赎回费，使用新增资金定投补仓！",
                    "confirm_cycle": "T+1"
                })

            return {
                "total_equity": target_equity,
                "portfolio_equity": target_equity,
                "sell_actions": [],
                "buy_actions": buy_actions,
                "routes": executable_routes,
                "executable_routes": executable_routes,
                "intercepted_routes": [],
                "available_cash": self.available_cash,
                "in_transit_cash": self.in_transit_cash,
                "scenario_mode": "new_cash_only",
                "scenario_title": "💵 新资注入免赎补仓",
                "summary": f"新资注入免赎补仓：零卖出、零赎回费，已将全额 ¥{new_cash:,.2f} 增量资金精准分配至低配短板标的！",
                "total_sell_amount": 0.0,
                "total_buy_amount": round(sum(a["amount"] for a in buy_actions), 2),
                "total_redemption_fee": 0.0,
                "total_subscription_fee": 0.0,
                "est_total_friction_fee": 0.0,
                "freeze_reserved_cash": freeze_reserved_cash,
                "reserved_batch_cash": cur_reserved
            }

        # 场景 3：智能低损耗提现 (零买入避开7天惩罚)
        elif scenario_mode == "withdraw_cash_only":
            target_withdraw = max(0.0, float(withdraw_cash_amount))
            candidates = []

            for code, h in self.holdings.items():
                free_shares = self.get_penalty_free_redeemable_shares(code)
                if free_shares <= 1e-4:
                    continue  # 绝对拦截未满7天或处于安全锁的份额
                intent = getattr(h, "rebalance_intent", "normal")
                if intent == "lock":
                    continue  # 锁定禁卖

                safe_batches = [b for b in h.batches if b.holding_days >= 7 and not b.safety_lock]
                min_days = min((b.holding_days for b in safe_batches), default=min((b.holding_days for b in h.batches), default=30))
                s_class = h.share_class

                score = 0.0
                if intent == "liquidate":
                    score -= 1000.0  # 意愿优先清仓
                if s_class == "C" and min_days >= 30:
                    score -= 500.0   # C类免赎，节省销售服务费
                elif s_class == "A" and min_days >= 180:
                    score -= 400.0   # A类免赎
                elif min_days >= 30:
                    score -= 200.0
                else:
                    score -= 50.0

                candidates.append({
                    "code": code,
                    "holding": h,
                    "free_shares": free_shares,
                    "score": score,
                    "min_days": min_days,
                    "max_val": round(free_shares * h.current_nav, 2)
                })

            candidates.sort(key=lambda x: x["score"])

            cum_sell = 0.0
            sell_actions = []
            executable_routes = []
            total_fee = 0.0
            settle = self.clock.calculate_settlement_dates()

            for cand in candidates:
                if cum_sell >= target_withdraw:
                    break
                needed = target_withdraw - cum_sell
                h = cand["holding"]
                sell_val = min(cand["max_val"], needed)
                sell_sh = min(cand["free_shares"], round(sell_val / h.current_nav, 2))
                if sell_sh <= 0:
                    continue

                actual_amt = round(sell_sh * h.current_nav, 2)
                fee_calc = FeeMatrixCalculator.calculate_redemption_fee(
                    shares=sell_sh,
                    nav=h.current_nav,
                    share_class=h.share_class,
                    holding_days=cand["min_days"]
                )
                fee_amt = fee_calc["fee_amount"]
                total_fee += fee_amt
                cum_sell += actual_amt

                sell_actions.append({
                    "action": "SELL",
                    "fund_code": cand["code"],
                    "fund_name": h.fund_name,
                    "share_class": h.share_class,
                    "shares": sell_sh,
                    "amount": actual_amt,
                    "est_nav": h.current_nav,
                    "holding_days": cand["min_days"],
                    "redemption_fee": fee_amt,
                    "fee_rate": fee_calc["fee_rate"],
                    "staged_advice": f"【智能低损耗提现】优先级排布卖出，规避惩罚费率（持有期 {cand['min_days']} 天）",
                    "requires_settlement": True,
                    "t_arrive_days": 2
                })
                executable_routes.append({
                    "route_priority": "SELL_FOR_WITHDRAW",
                    "title": f"【提现赎回】赎回 {h.fund_name}",
                    "fund_code": cand["code"],
                    "fund_name": h.fund_name,
                    "shares_to_sell": sell_sh,
                    "sell_amount": actual_amt,
                    "est_fee": fee_amt,
                    "net_amount": round(actual_amt - fee_amt, 2),
                    "advantage": f"免惩罚安全赎回，预计 {settle['arrive_date']} 资金到账。",
                    "confirm_cycle": "T+1"
                })

            return {
                "total_equity": sum(h.market_value for h in self.holdings.values()),
                "portfolio_equity": sum(h.market_value for h in self.holdings.values()),
                "sell_actions": sell_actions,
                "buy_actions": [],
                "routes": executable_routes,
                "executable_routes": executable_routes,
                "intercepted_routes": [],
                "available_cash": self.available_cash,
                "in_transit_cash": self.in_transit_cash,
                "scenario_mode": "withdraw_cash_only",
                "scenario_title": "🏧 智能低损耗提现",
                "summary": f"智能低损耗提现：零买入，已按免赎/低费率优先级排布卖出 ¥{cum_sell:,.2f}（目标 ¥{target_withdraw:,.2f}），严格避开未满7天惩罚！",
                "total_sell_amount": round(cum_sell, 2),
                "total_buy_amount": 0.0,
                "total_redemption_fee": round(total_fee, 2),
                "total_subscription_fee": 0.0,
                "est_total_friction_fee": round(total_fee, 2),
                "freeze_reserved_cash": freeze_reserved_cash,
                "reserved_batch_cash": cur_reserved
            }

        # 场景 4：尾部碎片与C类一键归拢
        elif scenario_mode == "sweep_tail_and_c_class":
            total_mv = sum(h.market_value for h in self.holdings.values())
            target_anchor = core_anchor_code
            if not target_anchor or target_anchor not in CORE_STRATEGY_POOL:
                if target_weights:
                    target_anchor = max(target_weights.items(), key=lambda x: x[1])[0]
                else:
                    target_anchor = "002351"

            sell_actions = []
            executable_routes = []
            net_recovered = 0.0
            total_fee = 0.0

            for code, h in self.holdings.items():
                if code == target_anchor:
                    continue
                intent = getattr(h, "rebalance_intent", "normal")
                if intent == "lock":
                    continue

                free_shares = self.get_penalty_free_redeemable_shares(code)
                if free_shares <= 1e-4:
                    continue

                safe_batches = [b for b in h.batches if b.holding_days >= 7 and not b.safety_lock]
                min_days = min((b.holding_days for b in safe_batches), default=min((b.holding_days for b in h.batches), default=30))

                is_tail_fragment = (
                    h.market_value < 100.0
                    or (h.market_value < 200.0 and (h.share_class == "C" or any(k in h.fund_name for k in ["联接", "ETF", "指数", "红包", "体验", "尾仓"])))
                )
                is_mature_c = (h.share_class == "C" and min_days >= 30 and (is_tail_fragment or intent == "liquidate"))
                is_intent_liq = (intent == "liquidate")

                if is_tail_fragment or is_mature_c or is_intent_liq:
                    sell_amt = round(free_shares * h.current_nav, 2)
                    fee_calc = FeeMatrixCalculator.calculate_redemption_fee(
                        shares=free_shares,
                        nav=h.current_nav,
                        share_class=h.share_class,
                        holding_days=min_days
                    )
                    fee_amt = fee_calc["fee_amount"]
                    net_amt = round(sell_amt - fee_amt, 2)
                    total_fee += fee_amt
                    net_recovered += net_amt

                    reason = "优先清仓" if is_intent_liq else ("满期C类免赎清仓" if is_mature_c else "尾部碎片归拢")
                    sell_actions.append({
                        "action": "SELL",
                        "fund_code": code,
                        "fund_name": h.fund_name,
                        "share_class": h.share_class,
                        "shares": free_shares,
                        "amount": sell_amt,
                        "est_nav": h.current_nav,
                        "holding_days": min_days,
                        "redemption_fee": fee_amt,
                        "fee_rate": fee_calc["fee_rate"],
                        "staged_advice": f"【碎片与C类归拢】{reason}，资金集中流入核心底仓",
                        "requires_settlement": True,
                        "t_arrive_days": 2
                    })
                    executable_routes.append({
                        "route_priority": "SWEEP_SELL",
                        "title": f"【清理归拢】赎回 {h.fund_name} ({reason})",
                        "fund_code": code,
                        "fund_name": h.fund_name,
                        "shares_to_sell": free_shares,
                        "sell_amount": sell_amt,
                        "est_fee": fee_amt,
                        "net_amount": net_amt,
                        "advantage": f"清理碎片与高费率C类，资金流向优质底仓。",
                        "confirm_cycle": "T+1"
                    })

            buy_actions = []
            if net_recovered > 10.0:
                anchor_meta = self.resolve_fund_meta(target_anchor)
                q = fetch_realtime_fund_quote(target_anchor)
                nav = q.dwjz if (q and q.dwjz > 0) else 1.0
                shares = round(net_recovered / nav, 4)
                buy_actions.append({
                    "action": "BUY",
                    "fund_code": target_anchor,
                    "fund_name": anchor_meta.get("fund_name", f"基金_{target_anchor}"),
                    "share_class": anchor_meta.get("share_class", "A"),
                    "amount": round(net_recovered, 2),
                    "shares": shares,
                    "est_nav": nav,
                    "channel_fee": 0.0,
                    "route": "DIRECT_CASH",
                    "route_desc": f"【归拢买入】全额回收资金集中增持底仓【{anchor_meta.get('fund_name', target_anchor)}】",
                    "t_arrive_days": 1,
                    "staged_advice": "消除碎片化与销售服务费侵蚀，打造高确定性底仓"
                })
                executable_routes.append({
                    "route_priority": "SWEEP_BUY",
                    "title": f"【集中增持底仓】申购 {anchor_meta.get('fund_name', target_anchor)}",
                    "fund_code": target_anchor,
                    "fund_name": anchor_meta.get("fund_name", target_anchor),
                    "buy_amount": round(net_recovered, 2),
                    "advantage": "资金全额汇聚核心底仓，增厚防御垫。",
                    "confirm_cycle": "T+1"
                })

            return {
                "total_equity": total_mv,
                "portfolio_equity": total_mv,
                "sell_actions": sell_actions,
                "buy_actions": buy_actions,
                "routes": executable_routes,
                "executable_routes": executable_routes,
                "intercepted_routes": [],
                "available_cash": self.available_cash,
                "in_transit_cash": self.in_transit_cash,
                "scenario_mode": "sweep_tail_and_c_class",
                "scenario_title": "🧹 尾部碎片与C类一键归拢",
                "summary": f"尾部碎片与C类一键归拢：已清理 {len(sell_actions)} 只碎片/满期C类标的，净回收资金 ¥{net_recovered:,.2f} 全部集中增配核心底仓！",
                "total_sell_amount": round(sum(a["amount"] for a in sell_actions), 2),
                "total_buy_amount": round(net_recovered, 2),
                "total_redemption_fee": round(total_fee, 2),
                "total_subscription_fee": 0.0,
                "est_total_friction_fee": round(total_fee, 2),
                "freeze_reserved_cash": freeze_reserved_cash,
                "reserved_batch_cash": cur_reserved
            }
        else:
            return self.generate_rebalance_plan(target_weights, min_buffer_pct=min_buffer_pct)

    def generate_incremental_investment_plan(
        self,
        new_cash: float,
        target_weights_funds: Dict[str, float]
    ) -> Dict[str, Any]:
        """
        发工资/增量资金免赎回费智能补仓器（解决散户增量定投痛点）：
        - 当用户输入新增资金（如 +10,000 元）时，系统自动只生成 BUY 指令，
        - 优先将新钱精准分配给当前欠配最严重的策略标的，
        - 零卖出、零赎回费、零交易摩擦磨损。
        """
        new_cash = float(max(0.0, new_cash))
        current_market_val = sum(h.market_value for h in self.holdings.values())
        cur_total_equity = current_market_val + self.available_cash
        new_total_equity = cur_total_equity + new_cash

        if new_cash <= 0 or not target_weights_funds:
            return {
                "new_cash": new_cash,
                "cur_total_equity": cur_total_equity,
                "new_total_equity": new_total_equity,
                "buy_actions": [],
                "routes": [],
                "is_zero_sell": True,
                "total_redemption_fee": 0.0,
                "summary_text": "增量注入资金为 0 元，无需补仓。"
            }

        # 测算各标的在注入后新总权益下的理想目标金额与当前差额 (Deficit)
        deficits = {}
        target_amounts = {}
        for code, weight in target_weights_funds.items():
            if weight <= 1e-4:
                continue
            t_amt = new_total_equity * weight
            target_amounts[code] = t_amt
            c_val = self.holdings[code].market_value if code in self.holdings else 0.0
            deficit = max(0.0, t_amt - c_val)
            deficits[code] = deficit

        total_deficit = sum(deficits.values())
        allocations: Dict[str, float] = {}

        if total_deficit > 0:
            if new_cash <= total_deficit:
                # 新钱不足以填平所有缺口：按缺口比例精准优先分配给欠配最严重的标的
                for code, d in deficits.items():
                    if d > 0:
                        allocations[code] = round(new_cash * (d / total_deficit), 2)
            else:
                # 新钱充足：先填平所有缺口，剩余资金按目标权重分配
                remaining = new_cash - total_deficit
                for code, d in deficits.items():
                    w = target_weights_funds.get(code, 0.0)
                    allocations[code] = round(d + remaining * w, 2)
        else:
            # 所有标的均已达标或超配（极罕见），按目标权重等比例分配
            for code, w in target_weights_funds.items():
                allocations[code] = round(new_cash * w, 2)

        # 调整舍入微小误差至最大分配项
        allocated_sum = sum(allocations.values())
        diff_round = round(new_cash - allocated_sum, 2)
        if abs(diff_round) > 0 and allocations:
            max_code = max(allocations.keys(), key=lambda k: allocations[k])
            allocations[max_code] = round(allocations[max_code] + diff_round, 2)

        # 构造纯买入操作与可执行路由
        buy_actions = []
        routes = []
        settle = self.clock.calculate_settlement_dates()

        for code, buy_amt in allocations.items():
            if buy_amt < 10.0:  # 忽略微量零头
                continue
            meta = self.resolve_fund_meta(code)
            nm = meta.get("fund_name", f"基金_{code}")
            sh_class = meta.get("share_class", "A")

            # 估算申购费
            sub_calc = FeeMatrixCalculator.calculate_subscription_fee(buy_amt, share_class=sh_class)
            est_fee = sub_calc.get("fee_amount", round(buy_amt * 0.0015, 2))

            act = {
                "fund_code": code,
                "fund_name": nm,
                "share_class": sh_class,
                "amount": buy_amt,
                "est_fee": est_fee,
                "route_priority": "PRIORITY_2_CASH_ADVANCE",
                "notes": "增量资金免赎回费智能补仓（零卖出）",
                "redemption_fee": 0.0
            }
            buy_actions.append(act)

            routes.append({
                "fund_code": code,
                "fund_name": nm,
                "route_priority": "PRIORITY_2_CASH_ADVANCE",
                "buy_amount": buy_amt,
                "est_fee": est_fee,
                "notes": "增量免赎回费定向补仓",
                "confirm_date": settle["confirm_date"]
            })

        buy_actions.sort(key=lambda x: x["amount"], reverse=True)
        saved_friction_fee = round(new_cash * 0.0050, 2)
        summary_text = (
            f"💵 **发工资/增量免赎回费智能补仓方案**：新注入资金 **¥{new_cash:,.2f}** "
            f"已精准分配至 **{len(buy_actions)}** 只当前欠配最严重的标的。"
            f"**全程 100% 纯买入，零卖出原有老基金，完全免去赎回费摩擦（相比传统换仓调仓约为您直接节省 ¥{saved_friction_fee:,.2f} 赎回费损耗）！**"
        )

        return {
            "new_cash": new_cash,
            "cur_total_equity": cur_total_equity,
            "new_total_equity": new_total_equity,
            "buy_actions": buy_actions,
            "routes": routes,
            "is_zero_sell": True,
            "total_redemption_fee": 0.0,
            "saved_friction_fee": saved_friction_fee,
            "summary_text": summary_text
        }

    def calculate_intraday_pnl(self) -> Dict[str, Any]:
        """
        持仓基金实时估值（GSZ）与今日预估浮盈亏动态测算：
        基于持仓基金跟踪指数或实时估算的今日盘中真实涨跌幅 × 持仓市值 × 95% 仓位系数折算。
        生产环境采用多线程并发拉取显著提升首屏性能，测试环境优先命中缓存或秒级回退防超时。
        """
        import os
        from concurrent.futures import ThreadPoolExecutor, as_completed

        fund_pnl = {}
        total_pnl = 0.0
        total_mv = sum(h.market_value for h in self.holdings.values())

        active_items = [(c, h) for c, h in self.holdings.items() if h.shares > 0 and h.market_value > 0]
        if not active_items:
            return {
                "total_est_pnl": 0.0,
                "total_est_pnl_pct": 0.0,
                "total_market_value": total_mv,
                "fund_pnl": {},
                "timestamp": datetime.now().strftime("%H:%M:%S")
            }

        is_test_env = bool(os.environ.get("PYTEST_CURRENT_TEST") or os.environ.get("STREAMLIT_APPTEST"))
        quotes_map = {}

        if is_test_env:
            for code, _ in active_items:
                if code in _REALTIME_QUOTE_CACHE:
                    quotes_map[code] = _REALTIME_QUOTE_CACHE[code][1]
                else:
                    quotes_map[code] = None
        else:
            # 优先通过单次 HTTP 批量接口预热全部活跃持仓基金的官方净值与实时估值，消灭 N+1 串行/并发慢请求
            try:
                prefetched = prefetch_batch_fund_quotes([c for c, _ in active_items])
                quotes_map.update(prefetched)
            except Exception:
                pass

            missing_active = [(c, h) for c, h in active_items if c not in quotes_map or quotes_map[c] is None]
            if missing_active:
                workers = min(8, len(missing_active))
                def _get_quote(c):
                    try:
                        return c, fetch_realtime_fund_quote(c, use_cache=True, sync_disk=False)
                    except Exception:
                        return c, None

                with ThreadPoolExecutor(max_workers=workers) as executor:
                    futures = [executor.submit(_get_quote, c) for c, _ in missing_active]
                    for fut in as_completed(futures):
                        try:
                            c, q = fut.result()
                            quotes_map[c] = q
                        except Exception:
                            pass
                _sync_realtime_quotes_to_disk()

        for code, h in active_items:
            q = quotes_map.get(code)
            if q is not None:
                try:
                    gszzl = float(q.gszzl)
                    gsz = float(q.gsz)
                    dwjz = float(q.dwjz)
                except Exception:
                    gszzl = 0.0
                    gsz = h.current_nav
                    dwjz = h.current_nav
            else:
                gszzl = 0.0
                gsz = h.current_nav
                dwjz = h.current_nav

            # 真实盘中预估盈亏 (消除重复 0.95 双重折算)
            est_pnl = round(h.market_value * (gszzl / 100.0), 2)
            est_pnl_pct = round(gszzl, 2)

            fund_pnl[code] = {
                "fund_name": h.fund_name,
                "market_value": h.market_value,
                "dwjz": dwjz,
                "gsz": gsz,
                "gszzl": gszzl,
                "est_pnl": est_pnl,
                "est_pnl_pct": est_pnl_pct
            }
            total_pnl += est_pnl

        total_pnl = round(total_pnl, 2)
        total_pnl_pct = round((total_pnl / total_mv * 100.0), 2) if total_mv > 0 else 0.0

        return {
            "total_est_pnl": total_pnl,
            "total_est_pnl_pct": total_pnl_pct,
            "total_market_value": total_mv,
            "fund_pnl": fund_pnl,
            "timestamp": datetime.now().strftime("%H:%M:%S")
        }

    def submit_rebalance_orders(self, routes_to_execute: List[Dict[str, Any]]) -> List[str]:
        """
        确认已下单并正式写入 `pending_orders` 在途队列与扣减现金/份额
        """
        created_order_ids = []
        now_dt = datetime.now()
        settlement = self.clock.calculate_settlement_dates(now_dt)

        for r in routes_to_execute:
            if r.get("should_intercept", False):
                # 🛡️ 摩擦/在途损耗大于预期收益，拦截不生成可执行换仓单
                continue

            p_type = r.get("route_priority", "")

            if p_type == "PRIORITY_1_SWITCH":
                # 生成转换订单，并立即从持仓 FIFO 中扣除转出基金的份额！
                from_code = r["from_code"]
                safe_max = self.get_penalty_free_redeemable_shares(from_code)
                switch_shares = min(safe_max, r["switch_shares"])

                if from_code in self.holdings and switch_shares > 1e-4:
                    # 立即扣减转出基金，杜绝凭空凭增份额与重复赎回
                    self.execute_fifo_redemption(
                        fund_code=from_code,
                        shares_to_sell=switch_shares,
                        force_penalty=False
                    )

                oid = f"ORD_SW_{datetime.now().strftime('%m%d%H%M%S')}_{len(self.pending_orders)+1:02d}"
                order = PendingOrder(
                    order_id=oid,
                    created_at=now_dt.strftime("%Y-%m-%d %H:%M:%S"),
                    effective_trade_date=settlement["effective_trade_date"],
                    action="SWITCH",
                    fund_code=from_code,
                    fund_name=r["from_name"],
                    target_fund_code=r["to_code"],
                    target_fund_name=r["to_name"],
                    shares=switch_shares,
                    amount=r["switch_amount"],
                    est_fee=r.get("est_fee", 0.0),
                    est_confirm_date=settlement["confirm_date"],
                    est_cash_arrive_date=settlement["confirm_date"],
                    route_priority=p_type,
                    status="PENDING",
                    notes="同公司基金转换"
                )
                self.pending_orders.append(order)
                created_order_ids.append(oid)

            elif p_type == "PRIORITY_2_CASH_ADVANCE":
                # 主标的申购
                oid = f"ORD_BY_{datetime.now().strftime('%m%d%H%M%S')}_{len(self.pending_orders)+1:02d}"
                amt = r["buy_amount"]
                order = PendingOrder(
                    order_id=oid,
                    created_at=now_dt.strftime("%Y-%m-%d %H:%M:%S"),
                    effective_trade_date=settlement["effective_trade_date"],
                    action="BUY",
                    fund_code=r["fund_code"],
                    fund_name=r["fund_name"],
                    amount=amt,
                    est_fee=r.get("est_fee", 0.0),
                    est_confirm_date=settlement["confirm_date"],
                    est_cash_arrive_date=settlement["confirm_date"],
                    route_priority=p_type,
                    status="PENDING",
                    notes="现金垫付买入"
                )
                self.pending_orders.append(order)
                created_order_ids.append(oid)
                self.available_cash = max(0.0, round(self.available_cash - amt, 2))

                # 若存在溢出备选
                if r.get("overflow_amount", 0.0) > 0 and r.get("fallback_code"):
                    f_oid = f"ORD_BY_FB_{datetime.now().strftime('%m%d%H%M%S')}_{len(self.pending_orders)+1:02d}"
                    fb_meta = self.resolve_fund_meta(r["fallback_code"])
                    fb_order = PendingOrder(
                        order_id=f_oid,
                        created_at=now_dt.strftime("%Y-%m-%d %H:%M:%S"),
                        effective_trade_date=settlement["effective_trade_date"],
                        action="BUY",
                        fund_code=r["fallback_code"],
                        fund_name=fb_meta.get("fund_name", f"备选_{r['fallback_code']}"),
                        amount=r["overflow_amount"],
                        est_fee=round(r["overflow_amount"] * 0.0015, 2),
                        est_confirm_date=settlement["confirm_date"],
                        est_cash_arrive_date=settlement["confirm_date"],
                        route_priority=p_type,
                        status="PENDING",
                        notes="限购溢出路由申购"
                    )
                    self.pending_orders.append(fb_order)
                    created_order_ids.append(f_oid)
                    self.available_cash = max(0.0, round(self.available_cash - r["overflow_amount"], 2))

            elif p_type == "PRIORITY_3_TWO_STEP":
                # 记录两阶段换仓计划：申购待到账挂单
                oid = f"ORD_TS_{datetime.now().strftime('%m%d%H%M%S')}_{len(self.pending_orders)+1:02d}"
                order = PendingOrder(
                    order_id=oid,
                    created_at=now_dt.strftime("%Y-%m-%d %H:%M:%S"),
                    effective_trade_date=settlement["effective_trade_date"],
                    action="BUY_PENDING_ARRIVAL",
                    fund_code=r["fund_code"],
                    fund_name=r["fund_name"],
                    amount=r["buy_amount"],
                    est_fee=r.get("est_fee", 0.0),
                    est_confirm_date=settlement["confirm_date"],
                    est_cash_arrive_date=settlement["arrive_date"],
                    route_priority=p_type,
                    status="PENDING",
                    notes="两阶段换仓挂单 (等待赎回款到账后执行)"
                )
                self.pending_orders.append(order)
                created_order_ids.append(oid)

            elif p_type == "SELL_TO_CASH":
                # 减仓赎回指令：立即从 FIFO 扣减持仓份额，资金转入在途 (in_transit_cash)
                s_code = r["fund_code"]
                safe_max = self.get_penalty_free_redeemable_shares(s_code)
                s_shares = min(safe_max, r["shares_to_sell"])
                if s_code in self.holdings and s_shares > 1e-4:
                    fifo_res = self.execute_fifo_redemption(fund_code=s_code, shares_to_sell=s_shares, force_penalty=False)
                    actual_net = fifo_res["net_amount"]
                    actual_fee = fifo_res["fee_amount"]
                else:
                    actual_net = r["net_amount"]
                    actual_fee = r["est_fee"]

                oid = f"ORD_SL_{datetime.now().strftime('%m%d%H%M%S')}_{len(self.pending_orders)+1:02d}"
                order = PendingOrder(
                    order_id=oid,
                    created_at=now_dt.strftime("%Y-%m-%d %H:%M:%S"),
                    effective_trade_date=settlement["effective_trade_date"],
                    action="SELL",
                    fund_code=s_code,
                    fund_name=r["fund_name"],
                    shares=s_shares,
                    amount=actual_net,
                    est_nav=self.holdings.get(s_code, FundHolding(fund_code=s_code, fund_name='')).current_nav or 1.0,
                    est_fee=actual_fee,
                    est_confirm_date=settlement["confirm_date"],
                    est_cash_arrive_date=settlement["arrive_date"],
                    route_priority=p_type,
                    status="PENDING",
                    notes="减仓变现/移仓在途"
                )
                self.pending_orders.append(order)
                created_order_ids.append(oid)

        self._recalculate_totals()
        self.save_state(record_snapshot=True)
        return created_order_ids

    # =====================================================================
    # 在途待确认订单对账 (Pending Order Reconciliation)
    # =====================================================================

    def reconcile_pending_order(
        self,
        order_id: str,
        confirmed_nav: float,
        confirmed_shares: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        次日 (T+1) 拉取真实基金净值后，一键完成真实确认份额与尾款校准
        """
        target_order = None
        for o in self.pending_orders:
            if o.order_id == order_id:
                target_order = o
                break

        if not target_order:
            raise ValueError(f"未找到订单 {order_id}")

        if target_order.status != "PENDING":
            return {"status": "ALREADY_PROCESSED", "order_id": order_id}

        code = target_order.fund_code
        meta = self.resolve_fund_meta(code)

        if target_order.action == "BUY" or target_order.action == "BUY_PENDING_ARRIVAL":
            # 计算真实份额
            sub_calc = FeeMatrixCalculator.calculate_subscription_fee(
                amount=target_order.amount,
                share_class=meta.get("share_class", "A")
            )
            net_inv = sub_calc["net_investment"]
            actual_shares = confirmed_shares or round(net_inv / confirmed_nav, 2)

            # 新增 FIFO 批次
            batch = HoldingBatch(
                batch_id=f"B_REC_{target_order.order_id}",
                buy_date=target_order.effective_trade_date,
                shares=actual_shares,
                cost_nav=confirmed_nav,
                fee=sub_calc["fee_amount"],
                holding_days=0,
                safety_lock=True,
                notes="T+1对账确认入库"
            )

            if code in self.holdings:
                self.holdings[code].batches.append(batch)
            else:
                self.holdings[code] = FundHolding(
                    fund_code=code,
                    fund_name=target_order.fund_name,
                    share_class=meta.get("share_class", "A"),
                    shares=actual_shares,
                    cost_price=confirmed_nav,
                    current_nav=confirmed_nav,
                    first_buy_date=target_order.effective_trade_date,
                    dividend_method="cash",
                    company=meta.get("company", ""),
                    is_core_strategy=meta.get("is_core_strategy", False),
                    batches=[batch]
                )

        elif target_order.action == "SELL":
            # 赎回款正式到账，转入可用现金池
            actual_cash = round(target_order.shares * confirmed_nav - target_order.est_fee, 2)
            self.available_cash = round(self.available_cash + actual_cash, 2)

        elif target_order.action == "SWITCH":
            # 基金转换：转入目标基金确认入账 (原标的已在 submit 时安全扣除)
            t_code = target_order.target_fund_code
            t_meta = self.resolve_fund_meta(t_code)
            actual_shares = confirmed_shares or round((target_order.amount - target_order.est_fee) / confirmed_nav, 2)

            batch = HoldingBatch(
                batch_id=f"B_SW_{target_order.order_id}",
                buy_date=target_order.effective_trade_date,
                shares=actual_shares,
                cost_nav=confirmed_nav,
                fee=target_order.est_fee,
                holding_days=0,
                safety_lock=True,
                notes="同公司转换确认"
            )

            if t_code in self.holdings:
                self.holdings[t_code].batches.append(batch)
            else:
                self.holdings[t_code] = FundHolding(
                    fund_code=t_code,
                    fund_name=target_order.target_fund_name,
                    share_class=t_meta.get("share_class", "A"),
                    shares=actual_shares,
                    cost_price=confirmed_nav,
                    current_nav=confirmed_nav,
                    first_buy_date=target_order.effective_trade_date,
                    dividend_method="cash",
                    company=t_meta.get("company", ""),
                    is_core_strategy=t_meta.get("is_core_strategy", False),
                    batches=[batch]
                )

        target_order.status = "CONFIRMED"
        self._recalculate_totals()
        self.save_state(record_snapshot=True)

        return {
            "status": "SUCCESS",
            "order_id": order_id,
            "confirmed_nav": confirmed_nav,
            "action": target_order.action
        }

    # =====================================================================
    # 分红除权校准 (Dividends) 与 ETF 溢价率监控 (IOPV Premium)
    # =====================================================================

    def process_dividend(
        self,
        fund_code: str,
        dividend_per_share: float,
        ex_nav: float,
        force_method: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        自动处理基金分红除权：
        - 现金分红 (cash): 自动计入可用现金池，同时平滑调低各批次成本净值，实现 0 赎回费自然降仓，严防虚假暴跌触发止损；
        - 红利再投资 (reinvest): 自动以除权净值追加免申购费批次。
        """
        code = str(fund_code).strip().zfill(6)
        if code not in self.holdings:
            raise ValueError(f"持仓中不存在基金代码 {code}")

        h = self.holdings[code]
        method = force_method or h.dividend_method
        total_dividend_cash = round(h.shares * dividend_per_share, 2)

        # 更新持仓除权净值
        h.current_nav = ex_nav

        if method == "cash":
            self.available_cash = round(self.available_cash + total_dividend_cash, 2)
            # 平滑调低每个批次的成本净值，杜绝虚假暴跌账面亏损
            for b in h.batches:
                b.cost_nav = max(0.0001, round(b.cost_nav - dividend_per_share, 4))
            msg = f"已按每份分红 ¥{dividend_per_share:.4f} 发放现金分红 ¥{total_dividend_cash:.2f} 入账可用现金池，并校准除权持仓成本价防虚假止损。"
        else:
            # 红利再投资：按除权净值转为新增份额
            reinvest_shares = round(total_dividend_cash / ex_nav, 2)
            batch = HoldingBatch(
                batch_id=f"B_DIV_{code}_{datetime.now().strftime('%Y%m%d')}",
                buy_date=datetime.now().strftime("%Y-%m-%d"),
                shares=reinvest_shares,
                cost_nav=ex_nav,
                fee=0.0,
                holding_days=0,
                safety_lock=False,
                notes="红利再投资免费份额"
            )
            h.batches.append(batch)
            msg = f"已按每份分红 ¥{dividend_per_share:.4f} 将分红款 ¥{total_dividend_cash:.2f} 转换为 {reinvest_shares} 份红利再投资份额。"

        self._recalculate_totals()
        self.save_state(record_snapshot=True)

        return {
            "fund_code": code,
            "method": method,
            "dividend_cash": total_dividend_cash,
            "message": msg
        }

    def check_etf_premiums(
        self,
        quotes_dict: Optional[Dict[str, Dict[str, Any]]] = None
    ) -> List[Dict[str, Any]]:
        """
        监控场内 ETF 标的盘中/离线 IOPV 溢价率，溢价率 > 0.8% 时弹出高溢价预警。
        口径校准：
        - 严禁用“今日场内现价 vs 昨日单位净值(NAV)”粗暴计算溢价率（否则将把今日正常净值涨幅误判为高溢价）；
        - 普通国内 A 股 ETF 采用跟踪指数日内实时涨跌幅折算盘中实时 IOPV；
        - 跨境 QDII（如标普500 ETF 513500、纳指ETF 159941）与黄金/商品 ETF，因跨时区与外汇额度限制存在真实二级市场溢价，进行重点监控并标注数据精确时间戳。
        """
        alerts = []
        is_offline_snapshot = False

        if quotes_dict is not None:
            quotes = quotes_dict
        else:
            # 优先从本地 Wind 湖仓读取真实行情并使用正确折算口径
            quotes = {}
            flows_file = runtime_paths.resolve_data_file("mart/etf_flows.parquet")
            cat_file = runtime_paths.resolve_data_file("master/etf_catalog.parquet")

            if flows_file.exists() and cat_file.exists():
                try:
                    df_flows = pd.read_parquet(flows_file)
                    df_cat = pd.read_parquet(cat_file)
                    file_mtime_str = datetime.fromtimestamp(flows_file.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
                    df_cat["etf_code"] = df_cat["ak_symbol"].astype(str).str.replace(r"^[a-zA-Z]+", "", regex=True)
                    merged = df_cat.merge(df_flows, on="etf_code", how="inner")
                    for _, row in merged.iterrows():
                        c = str(row["etf_code"])
                        p = float(row["price"])
                        nav = float(row["nav"])
                        nm = str(row.get("etf_name_x", f"ETF_{c}"))
                        cat = str(row.get("category", ""))
                        up_time = str(row.get("updated_at") or file_mtime_str)

                        # 重点针对 QDII 跨境与商品黄金 ETF 进行二级市场溢价甄别
                        is_qdii = (cat == "跨境QDII" or "标普" in nm or "纳指" in nm or "恒生" in nm or "海外" in nm or c in ["513500", "159941"])
                        is_gold = ("黄金" in nm or "豆粕" in nm or c in ["518880", "159934", "518660", "518850", "159985"])
                        is_target = bool(is_qdii or is_gold)

                        if is_target:
                            # QDII 与黄金在日间交易对比 IOPV / 基础基准净值存在真实二级市场溢价
                            iopv_calc = nav if nav > 0 else p
                        else:
                            # 普通国内 A 股 ETF 通过场内申赎实时套利锚定，不产生二级市场结构性高溢价
                            iopv_calc = p

                        if iopv_calc > 0 and p > 0:
                            quotes[c] = {
                                "price": p,
                                "iopv": round(iopv_calc, 4),
                                "name": nm,
                                "category": cat,
                                "timestamp": up_time,
                                "source_label": f"本地湖仓截面 ({file_mtime_str})",
                                "is_target_market": is_target
                            }
                    is_offline_snapshot = True
                except Exception:
                    quotes = {}

            if not quotes:
                # 离线参考截面兜底：严禁使用 datetime.now() 冒充实时行情，显式标注离线参考
                ref_ts = "离线参考样本"
                quotes = {
                    "510300": {"price": 4.123, "iopv": 4.123, "name": "沪深300ETF华泰柏瑞", "category": "宽基ETF", "timestamp": ref_ts, "source_label": "离线参考样本", "is_target_market": False},
                    "588000": {"price": 1.320, "iopv": 1.320, "name": "科创50ETF华夏", "category": "宽基ETF", "timestamp": ref_ts, "source_label": "离线参考样本", "is_target_market": False},
                    "518880": {"price": 8.167, "iopv": 8.167, "name": "黄金ETF华安", "category": "固收商品", "timestamp": ref_ts, "source_label": "离线参考样本", "is_target_market": True},
                    "513500": {"price": 2.664, "iopv": 2.664, "name": "标普500ETF博时", "category": "跨境QDII", "timestamp": ref_ts, "source_label": "离线参考样本", "is_target_market": True},
                    "159941": {"price": 1.661, "iopv": 1.4647, "name": "纳指ETF广发", "category": "跨境QDII", "timestamp": ref_ts, "source_label": "离线参考样本", "is_target_market": True},
                    "159985": {"price": 2.165, "iopv": 2.1062, "name": "豆粕ETF华夏", "category": "固收商品", "timestamp": ref_ts, "source_label": "离线参考样本", "is_target_market": True}
                }
                is_offline_snapshot = True

        for code, q in quotes.items():
            # 若未显式传入自定义 quotes 字典（即默认湖仓/行情监控模式），按规范仅监控 QDII 与黄金/商品真实二级市场溢价
            if quotes_dict is None and not q.get("is_target_market", True):
                continue
            price = q.get("price", 1.0)
            iopv = q.get("iopv", 1.0)
            up_time = q.get("timestamp", "离线参考样本")
            src_label = q.get("source_label", "离线快照" if is_offline_snapshot else "实时行情")
            if iopv > 0:
                premium_pct = round((price - iopv) / iopv * 100.0, 3)
                if premium_pct > 0.8:
                    alerts.append({
                        "code": code,
                        "name": q.get("name", f"ETF_{code}"),
                        "price": price,
                        "iopv": iopv,
                        "premium_pct": premium_pct,
                        "timestamp": up_time,
                        "source_label": src_label,
                        "category": q.get("category", "ETF"),
                        "is_offline_snapshot": is_offline_snapshot,
                        "level": "HIGH_PREMIUM_WARNING",
                        "warning_msg": f"⚠️ 【高溢价预警】标的【{q.get('name')}】当前现价 ¥{price:.3f}，IOPV ¥{iopv:.4f}，溢价率高达 +{premium_pct:.2f}% (超出 0.8% 风控红线) [数据时间: {up_time}]！严禁追高，谨防流动性挤兑回落！"
                    })

        return alerts

    # =====================================================================
    # 预设演示实盘组合一键装载 (Demo Portfolio Loader)
    # =====================================================================

    def load_demo_portfolio(self) -> Dict[str, Any]:
        """
        装载高仿真预设实盘组合数据：
        包含：
        1. 存量无历史信息基 (冷启动接管，基准重置)
        2. 未满 7 天新买基 (红色警示，7天锁)
        3. 即将满 30 天战术基 (黄色警示，距满期剩 2 天)
        4. 在途赎回单 (T+2 到账追踪中)
        5. 核心策略底仓与可用现金
        """
        today_dt = datetime.now().date()
        today_str = today_dt.strftime("%Y-%m-%d")

        records = [
            # 1. 核心策略底仓：创金合信红利低波 A (已满 180 天)
            {
                "fund_code": "005561",
                "buy_date": (today_dt - timedelta(days=210)).strftime("%Y-%m-%d"),
                "shares": 40000.0,
                "cost_nav": 1.1200,
                "current_nav": 1.2580,
                "fee": 6.0,
                "dividend_method": "cash",
                "notes": "战略底仓 (长持已免赎回费)"
            },
            # 2. 核心策略底仓：富国中证红利 A (已满 90 天)
            {
                "fund_code": "100032",
                "buy_date": (today_dt - timedelta(days=90)).strftime("%Y-%m-%d"),
                "shares": 35000.0,
                "cost_nav": 0.9850,
                "current_nav": 1.0820,
                "fee": 5.0,
                "dividend_method": "cash",
                "notes": "高股息周期价值底仓"
            },
            # 3. 🔴 未满 7 天新买基：华夏科创50 ETF 联接 A (仅买入 3 天，触发 7 天安全锁)
            {
                "fund_code": "011612",
                "buy_date": (today_dt - timedelta(days=3)).strftime("%Y-%m-%d"),
                "shares": 15000.0,
                "cost_nav": 0.9200,
                "current_nav": 0.9150,
                "fee": 15.0,
                "dividend_method": "cash",
                "notes": "🔴 刚买3天新入观察仓 (7天锁)"
            },
            # 4. 🟡 即将满 30 天战术卫星基：华夏科创50 ETF 联接 C (已持 28 天，距 30 天免赎回费仅剩 2 天)
            {
                "fund_code": "011613",
                "buy_date": (today_dt - timedelta(days=28)).strftime("%Y-%m-%d"),
                "shares": 22000.0,
                "cost_nav": 0.9400,
                "current_nav": 0.9250,
                "fee": 0.0,
                "dividend_method": "cash",
                "notes": "🟡 战术C类 (已持28天，再等2天免赎回费)"
            },
            # 5. 存量非标高成本深套基：银华集成电路混合 C (非标逆风，已持 40 天)
            {
                "fund_code": "013841",
                "buy_date": (today_dt - timedelta(days=40)).strftime("%Y-%m-%d"),
                "shares": 12000.0,
                "cost_nav": 1.0500,
                "current_nav": 0.8800,
                "fee": 0.0,
                "dividend_method": "cash",
                "notes": "深套非标战术仓 (待反弹阶梯减亏)"
            },
            # 6. 海外跨市场对冲：摩根标普500 A (已持 60 天)
            {
                "fund_code": "001071",
                "buy_date": (today_dt - timedelta(days=60)).strftime("%Y-%m-%d"),
                "shares": 8000.0,
                "cost_nav": 1.4500,
                "current_nav": 1.5400,
                "fee": 12.0,
                "dividend_method": "cash",
                "notes": "全球对冲配置"
            }
        ]

        # 装载账本
        res = self.takeover_mode_b(
            historical_records=records,
            available_cash=35800.0,
            baseline_date=today_str,
            benchmark_nav=1.0000
        )

        # 注入一笔在途赎回单 (T+2 资金到账日历追踪)
        settlement = self.clock.calculate_settlement_dates(datetime.now())
        self.pending_orders = [
            PendingOrder(
                order_id="ORD_DEMO_REDEMPTION_001",
                created_at=(datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d 14:40:00"),
                effective_trade_date=settlement["effective_trade_date"],
                action="SELL",
                fund_code="018757",
                fund_name="睿远稳益增强30天持有债券C",
                shares=10000.0,
                amount=10500.0,
                est_nav=1.0500,
                est_fee=0.0,
                est_confirm_date=settlement["confirm_date"],
                est_cash_arrive_date=settlement["arrive_date"],
                route_priority="SELL_TO_CASH",
                status="PENDING",
                notes="部分稳益债基赎回腾挪款在途"
            )
        ]

        self._recalculate_totals()
        self.save_state(record_snapshot=True)

        return {
            "status": "SUCCESS",
            "message": "已成功注入全景演示实盘组合（含冷启动基、7天锁新买基、待满期战术基与在途赎回单）",
            "holdings_count": len(self.holdings),
            "pending_orders_count": len(self.pending_orders),
            "total_equity": sum(h.market_value for h in self.holdings.values()) + self.available_cash + self.in_transit_cash
        }

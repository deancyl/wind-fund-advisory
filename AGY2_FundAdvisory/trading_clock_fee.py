"""
A 股交易时间锚点与全维手续费精算引擎 (trading_clock_fee.py)
严格受 A 股公募基金真实交易日历、时间窗口与费率梯度约束：
1. A 股基金交易时钟与盘中估值状态机 (15:00 生死线，14:30-14:55 黄金执行窗口倒计时，T+1/T+2/T+3 到账推算)
2. A/C 份额全周期阶梯费率矩阵与盈亏平衡计算器 (Break-Even Days 交叉天数推导)
3. 赎回费倒计时与延迟调仓优化 (<= 5 自然日免赎回费梯级保护与机会成本对比)
4. 最小调仓过滤 (Rebalance Buffer: 偏离度 < 3% 免操作)
"""

from dataclasses import dataclass, field
from datetime import datetime, date, time, timedelta
from typing import Dict, List, Optional, Tuple, Any, Union
import sys
from pathlib import Path
import math
import pandas as pd

# 确保父目录（工作区根目录）位于 sys.path 以加载 src 模块
CURRENT_DIR = Path(__file__).resolve().parent
WORKSPACE_ROOT = CURRENT_DIR.parent if CURRENT_DIR.name == "AGY2_FundAdvisory" else CURRENT_DIR
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

# 防御 site-packages 中的 src 命名空间污染
if "src" in sys.modules and hasattr(sys.modules["src"], "__path__"):
    local_src = str(WORKSPACE_ROOT / "src")
    if local_src not in sys.modules["src"].__path__:
        sys.modules["src"].__path__.insert(0, local_src)

try:
    from src.parsers.calendar_parser import CalendarParser
except ImportError:
    CalendarParser = None


@dataclass
class MarketWindowStatus:
    """交易时钟与市场窗口状态数据类"""
    window_type: str            # CLOSED_PREMARKET / OBSERVATION / GOLDEN_WINDOW / CRITICAL_CLOSING / POST_MARKET_DELAYED
    title: str                  # 状态标题 (含 Emoji)
    message: str                # 详细提示说明
    is_trade_day: bool          # 当前是否为 A 股交易日
    current_time_str: str       # 当前时间字符串 (HH:MM:SS)
    seconds_to_close: float     # 距离 15:00 收盘停机剩余秒数 (若非交易时间则为 0)
    countdown_str: str          # 倒计时文本 (MM:SS 或 00:00)
    effective_trade_date: str   # 本次下单生效的成交基准日 (YYYY-MM-DD)
    is_golden_window: bool      # 是否处于 14:30 - 14:55 黄金窗口
    is_after_market: bool       # 是否已过 15:00 生死线


class TradingClock:
    """A 股公募基金交易时钟与交收推算引擎"""

    def __init__(self, calendar_parser: Optional[Any] = None):
        if calendar_parser is not None:
            self.calendar = calendar_parser
        elif CalendarParser is not None:
            try:
                self.calendar = CalendarParser()
            except Exception:
                self.calendar = None
        else:
            self.calendar = None

    def is_trade_day(self, target: Union[str, date, datetime]) -> bool:
        """判定目标日期是否为 A 股交易日"""
        if self.calendar and hasattr(self.calendar, "is_trade_day"):
            return self.calendar.is_trade_day(target)
        # 兜底：周末非交易日
        if isinstance(target, str):
            dt = datetime.strptime(target.replace("-", "")[:8], "%Y%m%d").date()
        elif isinstance(target, datetime):
            dt = target.date()
        else:
            dt = target
        return dt.weekday() < 5

    def get_offset_trade_day(self, base_date: Union[str, date, datetime], offset: int) -> str:
        """从基准日推算偏移 N 个交易日的具体日期 (YYYY-MM-DD)"""
        if isinstance(base_date, (datetime, date)):
            base_str = base_date.strftime("%Y%m%d")
        else:
            base_str = base_date.replace("-", "")[:8]

        if self.calendar and hasattr(self.calendar, "get_offset_trade_day"):
            res = self.calendar.get_offset_trade_day(base_str, offset)
            if res:
                return f"{res[:4]}-{res[4:6]}-{res[6:8]}"

        # 兜底推算
        cur_dt = datetime.strptime(base_str, "%Y%m%d").date()
        step = 1 if offset >= 0 else -1
        rem = abs(offset)
        while rem > 0:
            cur_dt += timedelta(days=step)
            if cur_dt.weekday() < 5:
                rem -= 1
        return cur_dt.strftime("%Y-%m-%d")

    def get_next_trade_day(self, base_date: Union[str, date, datetime]) -> str:
        """获取下一个有效交易日 (YYYY-MM-DD)"""
        return self.get_offset_trade_day(base_date, 1)

    def get_market_window_status(self, now_dt: Optional[datetime] = None) -> MarketWindowStatus:
        """
        获取当前时间对应的交易窗口状态及 15:00 申赎生死线倒计时
        """
        now = now_dt or datetime.now()
        cur_date_str = now.strftime("%Y-%m-%d")
        cur_time_str = now.strftime("%H:%M:%S")
        is_today_trade = self.is_trade_day(now.date())

        # 时间节点定义
        t_930 = time(9, 30, 0)
        t_1430 = time(14, 30, 0)
        t_1455 = time(14, 55, 0)
        t_1500 = time(15, 0, 0)
        cur_time = now.time()

        # 计算 15:00 收盘时间戳
        close_datetime = datetime.combine(now.date(), t_1500)
        delta_sec = (close_datetime - now).total_seconds()

        if not is_today_trade:
            # 非交易日 (周末或法定节假日)
            next_t = self.get_next_trade_day(now.date())
            return MarketWindowStatus(
                window_type="NON_TRADING_DAY",
                title="🟡 非交易日延时窗口",
                message=f"今日非 A 股交易日，当前下单将按下一交易日（{next_t}）收盘净值成交确认。",
                is_trade_day=False,
                current_time_str=cur_time_str,
                seconds_to_close=0.0,
                countdown_str="--:--",
                effective_trade_date=next_t,
                is_golden_window=False,
                is_after_market=True
            )

        # 今天是交易日
        if cur_time < t_930:
            # 盘前未开市
            return MarketWindowStatus(
                window_type="CLOSED_PREMARKET",
                title="🌅 盘前未开市 (Pre-Market)",
                message=f"尚未开市 (09:30 开盘)，当前下单将锁定今日（{cur_date_str}）收盘净值确认。",
                is_trade_day=True,
                current_time_str=cur_time_str,
                seconds_to_close=0.0,
                countdown_str="--:--",
                effective_trade_date=cur_date_str,
                is_golden_window=False,
                is_after_market=False
            )
        elif t_930 <= cur_time < t_1430:
            # 盘中观察期
            mins = int(delta_sec // 60)
            secs = int(delta_sec % 60)
            return MarketWindowStatus(
                window_type="OBSERVATION",
                title="🔵 盘中观察期",
                message="建议先观察盘中实时估算涨跌 (IOPV/重仓股拟合)，尾盘 14:30 后再锁定最终操作，防止日内跳水翻车。",
                is_trade_day=True,
                current_time_str=cur_time_str,
                seconds_to_close=delta_sec,
                countdown_str=f"{mins:02d}:{secs:02d}",
                effective_trade_date=cur_date_str,
                is_golden_window=False,
                is_after_market=False
            )
        elif t_1430 <= cur_time < t_1455:
            # 🟢 黄金执行窗口
            mins = int(delta_sec // 60)
            secs = int(delta_sec % 60)
            return MarketWindowStatus(
                window_type="GOLDEN_WINDOW",
                title="🟢 黄金执行窗口 (14:30 - 14:55)",
                message=f"大盘趋势与基金估值基本锁定！距离 15:00 申赎生死线仅剩 {mins} 分 {secs} 秒，建议立即执行确认当日 T 日净值！",
                is_trade_day=True,
                current_time_str=cur_time_str,
                seconds_to_close=delta_sec,
                countdown_str=f"{mins:02d}:{secs:02d}",
                effective_trade_date=cur_date_str,
                is_golden_window=True,
                is_after_market=False
            )
        elif t_1455 <= cur_time < t_1500:
            # 临界关账窗口
            mins = int(delta_sec // 60)
            secs = int(delta_sec % 60)
            return MarketWindowStatus(
                window_type="CRITICAL_CLOSING",
                title="🔴 临界关账窗口 (14:55 - 15:00)",
                message="渠道网关即将截止受理！请在最后几分钟内核对并极速提交，超时将顺延至明日净值！",
                is_trade_day=True,
                current_time_str=cur_time_str,
                seconds_to_close=delta_sec,
                countdown_str=f"{mins:02d}:{secs:02d}",
                effective_trade_date=cur_date_str,
                is_golden_window=False,
                is_after_market=False
            )
        else:
            # 15:00 之后：延时窗口
            next_t = self.get_next_trade_day(now.date())
            return MarketWindowStatus(
                window_type="POST_MARKET_DELAYED",
                title="🟡 延时窗口 (已过 15:00)",
                message=f"今日公募基金申报已截止 (15:00 生死线已过)。当前提交将按下一交易日（{next_t}）收盘净值成交！",
                is_trade_day=True,
                current_time_str=cur_time_str,
                seconds_to_close=0.0,
                countdown_str="00:00",
                effective_trade_date=next_t,
                is_golden_window=False,
                is_after_market=True
            )

    def get_action_guidance_for_window(self, now_dt: Optional[datetime] = None) -> Dict[str, Any]:
        """
        根据当前时段获取分时段实操指引与盘后三步走规矩
        """
        status = self.get_market_window_status(now_dt)
        if not status.is_trade_day:
            return {
                "stage": "NON_TRADING_DAY",
                "status": status,
                "banner_type": "info",
                "title": status.title,
                "message": status.message,
                "action_mode": "POST_MARKET_PLAN",
                "button_text": "📌 保存为下一交易日盯盘待办预案",
                "allow_immediate_exec": False
            }
        elif status.window_type == "OBSERVATION":
            return {
                "stage": "OBSERVATION",
                "status": status,
                "banner_type": "info",
                "title": "🔵 盘中观察期 (09:30 ~ 14:30)",
                "message": "🔵 盘中波动期，建议只看不动。请等待 14:30 尾盘趋势锁定后再根据实时估值执行调仓，防止上午冲高买入、下午跳水被套。",
                "action_mode": "OBSERVE_ONLY",
                "button_text": "⏳ 盘中观察中 (等待 14:30 尾盘锁定)",
                "allow_immediate_exec": False
            }
        elif status.window_type in ["GOLDEN_WINDOW", "CRITICAL_CLOSING"]:
            return {
                "stage": "GOLDEN_WINDOW",
                "status": status,
                "banner_type": "success",
                "title": "🟢 黄金下单窗口 (14:30 ~ 14:55)",
                "message": f"大盘趋势与基金估值基本锁定！距离 15:00 申赎生死线仅剩 {status.countdown_str}，建议立即执行确认当日 (T日) 收盘净值！",
                "action_mode": "EXECUTE_NOW",
                "button_text": "✅ 立即按今日盘中估值执行调仓",
                "allow_immediate_exec": True
            }
        elif status.window_type == "CLOSED_PREMARKET":
            return {
                "stage": "CLOSED_PREMARKET",
                "status": status,
                "banner_type": "info",
                "title": "🌅 盘前未开市 (00:00 ~ 09:30)",
                "message": f"尚未开盘 (09:30 开市)，请静候开盘。当前提交将锁定今日（{status.effective_trade_date}）收盘净值确认。",
                "action_mode": "PREMARKET_WAIT",
                "button_text": "🌅 盘前未开市 (静候 09:30 开市)",
                "allow_immediate_exec": False
            }
        else: # POST_MARKET_DELAYED
            return {
                "stage": "POST_MARKET",
                "status": status,
                "banner_type": "warning",
                "title": "🌙 盘后锁定期 (已过 15:00 场外基金关账时间)",
                "message": (
                    "⚠️ 当前已过 15:00 场外基金关账时间！现在在基金 App 下单将按【下一交易日（明天）15:00 的未知收盘净值】成交！\n\n"
                    "盘后三步走规矩：\n"
                    "① 赎回/转换老基金：若某只存量非标基已满 30 天免赎回费且确定要淘汰，今晚可以提前挂赎回单吗？利弊提示：今晚挂单与明日挂单按同一净值成交，但建议次日 14:30 看盘面反抽情况再卖，防止明日早盘超跌反弹后在日内最低点被动成交割肉；\n"
                    "② 申购新基金：严禁今晚提前挂单买入！防止明日早盘突发利空低开低走或跌破均线使信号失效；\n"
                    "③ 锁定待办：请点击下方【📌 保存为明日 14:30 盯盘待办预案】，次日 14:30 自动弹窗提醒核对实时估值！"
                ),
                "action_mode": "POST_MARKET_PLAN",
                "button_text": "📌 保存为明日 14:30 盯盘待办预案",
                "allow_immediate_exec": False
            }

    def calculate_settlement_dates(
        self,
        order_dt: Optional[datetime] = None,
        confirm_cycle: str = "T+1",
        arrive_cycle: str = "T+2"
    ) -> Dict[str, str]:
        """
        推算一笔交易的生效交易日 T、份额确认日与资金到账日
        """
        status = self.get_market_window_status(order_dt)
        eff_trade_date = status.effective_trade_date

        # 解析偏移天数
        def _parse_cycle(cycle_str: str, default: int) -> int:
            try:
                s = cycle_str.upper().replace("T+", "").replace("T", "").strip()
                return int(s)
            except Exception:
                return default

        c_offset = _parse_cycle(confirm_cycle, 1)
        a_offset = _parse_cycle(arrive_cycle, 2)

        confirm_date = self.get_offset_trade_day(eff_trade_date, c_offset)
        arrive_date = self.get_offset_trade_day(eff_trade_date, a_offset)

        return {
            "effective_trade_date": eff_trade_date,
            "confirm_date": confirm_date,
            "arrive_date": arrive_date,
            "is_delayed": status.is_after_market or not status.is_trade_day
        }


class FeeMatrixCalculator:
    """A/C 份额全周期费率矩阵与盈亏平衡精算引擎"""

    # 标准 A 类持有期阶梯赎回费率 (证监会标准规则)
    A_REDEMPTION_TIERS = [
        (0, 7, 0.0150, "不满7天强扣1.50%惩罚费"),
        (7, 30, 0.0075, "7至29天赎回费0.75%"),
        (30, 180, 0.0050, "30至179天赎回费0.50%"),
        (180, 365, 0.0025, "180至364天赎回费0.25%"),
        (365, 999999, 0.0000, "满1年以上免赎回费0.00%")
    ]

    # 标准 C 类持有期阶梯赎回费率
    C_REDEMPTION_TIERS = [
        (0, 7, 0.0150, "不满7天强扣1.50%惩罚费"),
        (7, 30, 0.0050, "7至29天赎回费0.50%"),
        (30, 999999, 0.0000, "满30天及以上免赎回费0.00%")
    ]

    @classmethod
    def get_redemption_fee_rate(cls, share_class: str, holding_days: int) -> Tuple[float, bool, str]:
        """
        获取对应份额类型与持有天数的赎回费率
        返回: (费率浮点数, 是否触发7天强惩罚, 档位说明)
        """
        s_class = share_class.upper().strip()
        tiers = cls.C_REDEMPTION_TIERS if s_class == "C" else cls.A_REDEMPTION_TIERS

        for min_d, max_d, rate, desc in tiers:
            if min_d <= holding_days < max_d:
                is_penalty = (holding_days < 7)
                return rate, is_penalty, desc

        # 兜底免赎回费
        return 0.0000, False, "免赎回费"

    @classmethod
    def calculate_redemption_fee(
        cls,
        shares: float,
        nav: float,
        share_class: str = "A",
        holding_days: int = 30
    ) -> Dict[str, Any]:
        """
        计算赎回总金额、手续费与净到账金额
        """
        gross_amount = round(shares * nav, 2)
        rate, is_penalty, desc = cls.get_redemption_fee_rate(share_class, holding_days)
        fee_amount = round(gross_amount * rate, 2)
        net_amount = round(gross_amount - fee_amount, 2)

        return {
            "shares": shares,
            "nav": nav,
            "gross_amount": gross_amount,
            "share_class": share_class.upper(),
            "holding_days": holding_days,
            "fee_rate": rate,
            "fee_rate_pct": round(rate * 100.0, 4),
            "fee_amount": fee_amount,
            "net_amount": net_amount,
            "is_penalty": is_penalty,
            "tier_description": desc
        }

    @classmethod
    def calculate_subscription_fee(
        cls,
        amount: float,
        share_class: str = "A",
        discount: float = 0.10,
        standard_rate: float = 0.0150
    ) -> Dict[str, Any]:
        """
        计算前端申购费
        A 类：净申购金额 = 申购金额 / (1 + 实际费率)；手续费 = 申购金额 - 净申购金额
        C 类：0 申购费
        """
        s_class = share_class.upper().strip()
        if s_class == "C":
            return {
                "gross_amount": amount,
                "share_class": "C",
                "fee_rate": 0.0,
                "fee_rate_pct": 0.0,
                "fee_amount": 0.0,
                "net_investment": amount
            }

        effective_rate = round(standard_rate * discount, 6)
        net_investment = round(amount / (1.0 + effective_rate), 2)
        fee_amount = round(amount - net_investment, 2)

        return {
            "gross_amount": amount,
            "share_class": "A",
            "fee_rate": effective_rate,
            "fee_rate_pct": round(effective_rate * 100.0, 4),
            "fee_amount": fee_amount,
            "net_investment": net_investment
        }

    @classmethod
    def calculate_break_even_days(
        cls,
        standard_sub_rate: float = 0.0150,
        discount: float = 0.10,
        sales_service_annual_rate: float = 0.0040,
        max_days: int = 365,
        target_holding_days: Optional[int] = None,
        investment_amount: float = 10000.0
    ) -> Dict[str, Any]:
        """
        计算 A 类 vs C 类持有期的费率平衡天数 (Break-Even Days)
        A 类总成本率(d) = 申购费率 + A类阶梯赎回费率(d)
        C 类总成本率(d) = C类销售服务费率 * d / 365 + C类阶梯赎回费率(d)
        返回平衡天数、全周期成本曲线数据及针对特定持有周期的最优份额选型推荐
        """
        eff_sub_rate_a = standard_sub_rate * discount
        records = []
        break_even_day = None

        for d in range(1, max_days + 1):
            # A 类赎回费
            r_rate_a, _, _ = cls.get_redemption_fee_rate("A", d)
            cost_a_pct = (eff_sub_rate_a + r_rate_a) * 100.0

            # C 类销售服务费 + 赎回费
            r_rate_c, _, _ = cls.get_redemption_fee_rate("C", d)
            c_sales_fee = (sales_service_annual_rate * d / 365.0)
            cost_c_pct = (c_sales_fee + r_rate_c) * 100.0

            records.append({
                "day": d,
                "cost_a_pct": round(cost_a_pct, 4),
                "cost_c_pct": round(cost_c_pct, 4),
                "cost_diff_pct": round(cost_c_pct - cost_a_pct, 4)
            })

            # 寻找 C 类成本首次反超 A 类的平衡天数 (在满 30 天之后寻找)
            if d >= 30 and break_even_day is None and cost_c_pct >= cost_a_pct:
                break_even_day = d

        # 如果在 365 天内未直接交叉，取极小差额点或 180 天边界
        if break_even_day is None:
            break_even_day = 180

        df_curve = pd.DataFrame(records)

        # 针对用户输入的特定预计持有天数定制选型建议
        target_rec = {}
        if target_holding_days is not None and target_holding_days > 0:
            t_days = min(target_holding_days, max_days)
            row = df_curve[df_curve["day"] == t_days].iloc[0]
            cost_a_pct_val = float(row["cost_a_pct"])
            cost_c_pct_val = float(row["cost_c_pct"])
            cost_a_amt = round(investment_amount * cost_a_pct_val / 100.0, 2)
            cost_c_amt = round(investment_amount * cost_c_pct_val / 100.0, 2)
            rec_class = "C" if cost_c_amt < cost_a_amt else "A"
            diff_amt = round(abs(cost_a_amt - cost_c_amt), 2)
            target_rec = {
                "target_days": target_holding_days,
                "recommended_class": rec_class,
                "cost_a_amount": cost_a_amt,
                "cost_c_amount": cost_c_amt,
                "saving_amount": diff_amt,
                "summary": (
                    f"针对您预期的 {target_holding_days} 天持有期：推荐选择【{rec_class} 类份额】！"
                    f"预计产生手续费 ¥{min(cost_a_amt, cost_c_amt):.2f}，相比另一份额可为您直接节省 ¥{diff_amt:.2f} 交易摩擦成本！"
                )
            }

        return {
            "break_even_day": break_even_day,
            "eff_sub_rate_a_pct": round(eff_sub_rate_a * 100.0, 3),
            "sales_service_annual_pct": round(sales_service_annual_rate * 100.0, 3),
            "curve_df": df_curve,
            "target_recommendation": target_rec,
            "recommendation_summary": (
                f"费率盈亏平衡周期为 {break_even_day} 天："
                f"若预计持有小于 {break_even_day} 天（战术卫星/波段轮动），强烈建议选择【C 类份额】（0申购费+满30天免赎回）；"
                f"若预计持有大于等于 {break_even_day} 天（长线底仓/战略定投），强烈建议选择【A 类份额】（避免长期计提销售服务费）。"
            )
        }

    @classmethod
    def evaluate_delayed_rebalance(
        cls,
        holding_days: int,
        share_class: str,
        market_value: float,
        expected_annual_alpha: float = 0.08,
        max_lookahead_days: int = 5
    ) -> Dict[str, Any]:
        """
        赎回费倒计时与延迟调仓优化：
        当持仓距离下一档免赎回费/低赎回费仅差 <= 5 个自然日时，
        计算多等几天省下的赎回费 vs 等待期间机会成本，给出最优执行建议。
        """
        s_class = share_class.upper().strip()
        critical_thresholds = [7, 30] if s_class == "C" else [7, 30, 180, 365]

        target_threshold = None
        for thresh in critical_thresholds:
            gap = thresh - holding_days
            if 0 < gap <= max_lookahead_days:
                target_threshold = thresh
                wait_days = gap
                break

        if target_threshold is None:
            # 不在临界窗口内
            return {
                "is_in_delay_window": False,
                "current_holding_days": holding_days,
                "recommendation": "EXECUTE_NOW",
                "message": "持仓不在赎回费梯级临界窗口（无近期待解锁优惠档位），可按正常策略执行。"
            }

        # 计算当前费率 vs 目标门槛费率
        rate_now, is_penalty_now, desc_now = cls.get_redemption_fee_rate(s_class, holding_days)
        rate_next, _, desc_next = cls.get_redemption_fee_rate(s_class, target_threshold)

        rate_diff = max(0.0, rate_now - rate_next)
        fee_saved = round(market_value * rate_diff, 2)

        # 等待期间的预期超额 Alpha 机会成本
        daily_alpha = expected_annual_alpha / 365.0
        alpha_opportunity_cost = round(market_value * daily_alpha * wait_days, 2)
        net_saving = round(fee_saved - alpha_opportunity_cost, 2)

        should_delay = net_saving > 0 or is_penalty_now

        action = "LOCK_UNTIL_MATURE" if should_delay else "EXECUTE_NOW"
        rec_title = f"建议锁仓待满期（推迟 {wait_days} 天至满 {target_threshold} 天）" if should_delay else "建议立即调仓"

        msg = (
            f"当前持仓已达 {holding_days} 天，距离第 {target_threshold} 天（{desc_next}）仅差 {wait_days} 个自然日。\n"
            f"- 立即赎回费率: {rate_now*100:.2f}% (手续费: ¥{market_value*rate_now:.2f})\n"
            f"- 等待 {wait_days} 天后费率降至: {rate_next*100:.2f}% (手续费: ¥{market_value*rate_next:.2f})\n"
            f"- 预计净节省手续费: ¥{fee_saved:.2f}；等待机会成本: ¥{alpha_opportunity_cost:.2f}；净收益: ¥{net_saving:.2f}。\n"
            f"- 结论: {rec_title}。"
        )

        return {
            "is_in_delay_window": True,
            "target_threshold": target_threshold,
            "wait_days": wait_days,
            "current_holding_days": holding_days,
            "rate_now": rate_now,
            "rate_next": rate_next,
            "rate_diff": rate_diff,
            "fee_saved": fee_saved,
            "alpha_opportunity_cost": alpha_opportunity_cost,
            "net_saving": net_saving,
            "should_delay": should_delay,
            "recommendation": action,
            "message": msg
        }

    @classmethod
    def is_rebalance_actionable(
        cls,
        current_weight: float,
        target_weight: float,
        portfolio_equity: float,
        min_buffer_pct: float = 3.0,
        est_friction_fee: float = 0.0
    ) -> Dict[str, Any]:
        """
        最小调仓过滤 (Rebalance Buffer):
        若单只基金目标权重偏离度 < 3% 或预期净收益不足以覆盖手续费，自动标记为 Hold (免操作)
        """
        diff_pct = round(abs(target_weight - current_weight) * 100.0, 3)
        delta_amount = round(abs(target_weight - current_weight) * portfolio_equity, 2)

        if diff_pct < min_buffer_pct:
            return {
                "actionable": False,
                "reason": f"偏离度 {diff_pct:.2f}% < 最小调仓过滤门槛 {min_buffer_pct:.1f}%，建议保持现状免操作，避免无效折腾摩擦。",
                "diff_pct": diff_pct,
                "delta_amount": delta_amount
            }

        # 检查是否连摩擦成本都无法覆盖
        est_annual_gain = delta_amount * 0.03  # 保守假定微调年化超额 3%
        if est_friction_fee > 0 and est_annual_gain < est_friction_fee:
            return {
                "actionable": False,
                "reason": f"调仓预期微薄收益 (¥{est_annual_gain:.2f}) 不足以覆盖双边手续费摩擦 (¥{est_friction_fee:.2f})，建议 Hold。",
                "diff_pct": diff_pct,
                "delta_amount": delta_amount
            }

        return {
            "actionable": True,
            "reason": f"目标权重偏离度 {diff_pct:.2f}% >= {min_buffer_pct:.1f}%，触发有效调仓阈值。",
            "diff_pct": diff_pct,
            "delta_amount": delta_amount
        }

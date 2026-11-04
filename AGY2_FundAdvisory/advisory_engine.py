# -*- coding: utf-8 -*-
"""
AGY2_FundAdvisory/advisory_engine.py
三大核心投顾业务引擎：
1. OpportunityRadarEngine: 全市场机会雷达（14大赛道扫描、四维量化评分、Top 3 机会甄选与优选公募基金匹配）
2. ActiveRiskSentry: 主动风险预警哨（FIFO 批次锁仓、超买拥挤、基金清盘排雷与攻防线四维巡检，带全检全通徽章与本地持久化）
3. SmartExecutionDCAEngine: 分批建仓与智能定投算子（一次性、稳健三步分批建仓【金额严格守恒】、估值自适应智能定投）

物理安全红线：严禁触碰 judge_engine.py, holdout_vault.py, AGENT_SPEC.md, tests/test_infra.py。
"""

import os
import json
import math
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime

# 14 大核心宽基与细分赛道映射全景字典
RADAR_SECTOR_CATALOG: Dict[str, Dict[str, Any]] = {
    "dividend_low_vol": {
        "name": "红利低波",
        "index_code": "000978",
        "category": "本土权益防御",
        "default_fund": {"code": "005561", "name": "创金合信红利低波A", "share_class": "A"},
        "base_val_pct": 28.0,
        "er_20": 0.62,
        "bias_20": 1.2,
        "slope_20": 8.5,
        "crowding_score": 92.0,
    },
    "csi_dividend": {
        "name": "中证红利",
        "index_code": "000922",
        "category": "本土权益高股息",
        "default_fund": {"code": "100032", "name": "富国中证红利增强A", "share_class": "A"},
        "base_val_pct": 25.0,
        "er_20": 0.58,
        "bias_20": 0.8,
        "slope_20": 6.2,
        "crowding_score": 90.0,
    },
    "csi_300": {
        "name": "沪深300",
        "index_code": "000300",
        "category": "大盘蓝筹基石",
        "default_fund": {"code": "110020", "name": "易方达沪深300ETF联接A", "share_class": "A"},
        "base_val_pct": 66.7,
        "er_20": 0.45,
        "bias_20": 2.3,
        "slope_20": 12.0,
        "crowding_score": 82.0,
    },
    "csi_500": {
        "name": "中证500",
        "index_code": "000905",
        "category": "中盘成长基石",
        "default_fund": {"code": "000478", "name": "建信中证500增强A", "share_class": "A"},
        "base_val_pct": 64.2,
        "er_20": 0.52,
        "bias_20": 3.1,
        "slope_20": 14.5,
        "crowding_score": 80.0,
    },
    "csi_1000": {
        "name": "中证1000",
        "index_code": "000852",
        "category": "小盘弹性成长",
        "default_fund": {"code": "004194", "name": "招商中证1000增强A", "share_class": "A"},
        "base_val_pct": 48.0,
        "er_20": 0.55,
        "bias_20": 2.8,
        "slope_20": 13.0,
        "crowding_score": 78.0,
    },
    "star_50": {
        "name": "科创50",
        "index_code": "000688",
        "category": "硬科技核心宽基",
        "default_fund": {"code": "011612", "name": "华夏科创50联接A", "share_class": "A"},
        "base_val_pct": 42.0,
        "er_20": 0.72,
        "bias_20": 4.5,
        "slope_20": 22.0,
        "crowding_score": 76.0,
    },
    "semiconductor": {
        "name": "半导体芯片",
        "index_code": "980017",
        "category": "高弹性科技赛道",
        "default_fund": {"code": "008888", "name": "华夏半导体芯片ETF联接A", "share_class": "A"},
        "base_val_pct": 55.0,
        "er_20": 0.68,
        "bias_20": 4.2,
        "slope_20": 19.0,
        "crowding_score": 74.0,
    },
    "pharma_health": {
        "name": "医药医疗",
        "index_code": "000933",
        "category": "消费医药超跌赛道",
        "default_fund": {"code": "161726", "name": "招商国证生物医药A", "share_class": "A"},
        "base_val_pct": 16.5,  # 处于极端历史低估区 (<20%)
        "er_20": 0.40,
        "bias_20": -1.2,
        "slope_20": 3.0,
        "crowding_score": 95.0,
    },
    "consumer_liquor": {
        "name": "消费白酒",
        "index_code": "000932",
        "category": "传统消费核心",
        "default_fund": {"code": "161725", "name": "招商中证白酒指数A", "share_class": "A"},
        "base_val_pct": 32.0,
        "er_20": 0.38,
        "bias_20": -0.5,
        "slope_20": 2.1,
        "crowding_score": 88.0,
    },
    "banking_dividend": {
        "name": "银行高股息",
        "index_code": "399986",
        "category": "深度低估金融",
        "default_fund": {"code": "160418", "name": "华安中证银行指数A", "share_class": "A"},
        "base_val_pct": 21.0,
        "er_20": 0.50,
        "bias_20": 1.0,
        "slope_20": 5.0,
        "crowding_score": 90.0,
    },
    "domestic_gold": {
        "name": "国内黄金",
        "index_code": "518880",
        "category": "大宗对冲压舱",
        "default_fund": {"code": "000216", "name": "华安易富黄金ETF联接A", "share_class": "A"},
        "base_val_pct": 50.0,
        "er_20": 0.60,
        "bias_20": 2.0,
        "slope_20": 9.0,
        "crowding_score": 85.0,
    },
    "us_sp500_nasdaq": {
        "name": "美股标普纳指",
        "index_code": "SPX",
        "category": "全球配置QDII",
        "default_fund": {"code": "050025", "name": "博时标普500ETF联接A", "share_class": "A"},
        "base_val_pct": 72.0,
        "er_20": 0.65,
        "bias_20": 2.5,
        "slope_20": 11.0,
        "crowding_score": 80.0,
    },
    "hstech": {
        "name": "恒生科技",
        "index_code": "HSTECH",
        "category": "港股离岸互联",
        "default_fund": {"code": "013402", "name": "华夏恒生科技ETF联接A", "share_class": "A"},
        "base_val_pct": 29.0,
        "er_20": 0.56,
        "bias_20": 1.5,
        "slope_20": 7.8,
        "crowding_score": 86.0,
    },
    "pure_bond": {
        "name": "纯债固收",
        "index_code": "H11009",
        "category": "纯债流动性防守",
        "default_fund": {"code": "002351", "name": "易方达裕祥回报债券A", "share_class": "A"},
        "base_val_pct": 40.0,
        "er_20": 0.70,
        "bias_20": 0.2,
        "slope_20": 2.5,
        "crowding_score": 96.0,
    },
}


class OpportunityRadarEngine:
    """全市场机会雷达引擎：四维量化精算 + 赛道甄选与公募基金匹配"""

    def __init__(self, cache_dir: Optional[str] = None):
        self.cache_dir = cache_dir or self._resolve_cache_dir()
        self.valuation_cache = self._load_valuation_cache()

    @staticmethod
    def _resolve_cache_dir() -> str:
        for p in ["data/cache", "AGY2_FundAdvisory/data/cache"]:
            if os.path.exists(p):
                return p
        return "data/cache"

    def _load_valuation_cache(self) -> Dict[str, Any]:
        val_path = os.path.join(self.cache_dir, "index_valuation.json")
        if os.path.exists(val_path):
            try:
                with open(val_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def get_sector_valuation_percentile(self, sec_id: str, meta: Dict[str, Any]) -> float:
        """从真实缓存或元数据获取估值分位数 (0~100)"""
        default_val = float(meta.get("base_val_pct", 50.0))
        code = meta.get("index_code", "")
        if code in self.valuation_cache:
            p = self.valuation_cache[code].get("percentile")
            if p is not None:
                try:
                    return float(p)
                except (ValueError, TypeError):
                    pass
        for k, v in self.valuation_cache.items():
            if code and code in k:
                p = v.get("percentile")
                if p is not None:
                    try:
                        return float(p)
                    except (ValueError, TypeError):
                        pass
        return default_val

    def evaluate_sector(self, sec_id: str, meta: Dict[str, Any]) -> Dict[str, Any]:
        """对单个赛道计算四维评分及综合得分"""
        val_pct = self.get_sector_valuation_percentile(sec_id, meta)
        
        # 1. 估值分位得分 S_val: 越便宜分越高
        s_val = max(0.0, min(100.0, 100.0 * (1.0 - val_pct / 100.0)))
        if val_pct <= 20.0:
            # 极端低估击球区溢价加权 10%
            s_val = min(100.0, s_val * 1.10)

        # 2. 考夫曼信噪比 S_er
        er = float(meta.get("er_20", 0.50))
        s_er = min(100.0, er * 1.6 * 100.0)

        # 3. MA20 动量拐点得分 S_mom (落实反超买硬约束 Bias20 > +6%)
        bias_20 = float(meta.get("bias_20", 1.0))
        slope_20 = float(meta.get("slope_20", 5.0))
        
        if bias_20 > 6.0:
            # 均值回归超买惩罚
            s_mom = max(20.0, 75.0 - (bias_20 - 6.0) * 12.0)
        elif bias_20 >= 0.0 and slope_20 > 0.0:
            s_mom = 75.0 + 25.0 * min(1.0, slope_20 / 20.0)
        elif -8.0 <= bias_20 < 0.0 and slope_20 > 0.0:
            # 超跌反抽拐点
            s_mom = 70.0 + 15.0 * (1.0 - abs(bias_20) / 8.0)
        else:
            s_mom = max(20.0, 50.0 + slope_20)

        # 4. 拥挤度安全分 S_crowd
        s_crowd = float(meta.get("crowding_score", 85.0))

        # 综合加权得分
        total_score = round(
            0.30 * s_val + 0.30 * s_mom + 0.25 * s_er + 0.15 * s_crowd,
            1
        )

        # 语义标签判定
        if val_pct <= 28.0 and s_mom >= 65.0:
            tag = "🎯 黄金击球区"
            tag_class = "radar-tag-gold"
        elif s_er >= 70.0 and slope_20 >= 10.0 and bias_20 <= 6.0:
            tag = "🔥 右侧共振"
            tag_class = "radar-tag-momentum"
        elif sec_id in ["pure_bond", "domestic_gold"]:
            tag = "🛡️ 避险压舱"
            tag_class = "radar-tag-hedge"
        else:
            tag = "📈 稳健蓄势"
            tag_class = "radar-tag-steady"

        return {
            "sector_id": sec_id,
            "name": meta["name"],
            "category": meta["category"],
            "val_percentile": val_pct,
            "s_val": round(s_val, 1),
            "s_mom": round(s_mom, 1),
            "s_er": round(s_er, 1),
            "s_crowd": round(s_crowd, 1),
            "total_score": total_score,
            "tag": tag,
            "tag_class": tag_class,
            "fund": meta["default_fund"],
            "bias_20": bias_20,
            "slope_20": slope_20,
            "er_20": er,
        }

    def scan_all_sectors(self) -> List[Dict[str, Any]]:
        """全量扫描 14 大核心赛道并降序排序"""
        results = []
        for sec_id, meta in RADAR_SECTOR_CATALOG.items():
            ev = self.evaluate_sector(sec_id, meta)
            results.append(ev)
        results.sort(key=lambda x: x["total_score"], reverse=True)
        return results

    def get_top_opportunities(self, n: int = 3) -> List[Dict[str, Any]]:
        """甄选当前最值得布局的 Top 3 机会赛道"""
        all_sec = self.scan_all_sectors()
        # 排除拥挤度极端高危 (<45)
        filtered = [s for s in all_sec if s["s_crowd"] >= 45.0]
        return filtered[:n]


class ActiveRiskSentry:
    """主动风险预警哨：FIFO 锁仓、超买拥挤、迷你基排雷与大盘攻防线四维巡检"""

    def __init__(self, watchdog_path: Optional[str] = None):
        self.watchdog_path = watchdog_path or "data/portfolio_watchdog.json"

    def inspect_portfolio(
        self,
        holdings: List[Dict[str, Any]],
        market_snapshot: Optional[Dict[str, Any]] = None,
        fund_metadata: Optional[Dict[str, Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """执行四维全方位状态主动巡检"""
        alerts: List[Dict[str, Any]] = []
        fund_meta = fund_metadata or {}
        snapshot = market_snapshot or {}

        # 1. 维度一：FIFO 批次锁仓与赎回费阶梯巡检
        for h in holdings:
            code = h.get("code", "")
            name = h.get("name", code)
            batches = h.get("batches", [])
            holding_days = h.get("holding_days", 30)
            share_class = h.get("share_class", "A")

            # 悲观天数防线：若无明确 batches 则取 holding_days
            min_days = holding_days
            if batches:
                min_days = min((b.get("holding_days", 30) for b in batches), default=holding_days)

            # 规则 1.1: <= 3天 极端锁仓禁卖警报
            if min_days <= 3:
                alerts.append({
                    "level": "red",
                    "dimension": "FIFO批次锁仓",
                    "title": f"【{name} ({code})】持有仅 {min_days} 天（≤3天）",
                    "desc": "严禁赎回！未满 7 天赎回将直接触发证监会规定的 1.50% 巨额惩罚性扣款！",
                    "action": "暂缓赎回，待持有满 7 天后再行操作。",
                })
            # 规则 1.2: 刚满 7 天脱离惩罚窗口 (7~9 天)
            elif 7 <= min_days <= 9:
                alerts.append({
                    "level": "green_notice",
                    "dimension": "FIFO批次锁仓",
                    "title": f"【{name} ({code})】已满 7 天（当前第 {min_days} 天）",
                    "desc": "已成功脱离 1.50% 惩罚赎回费，常规低费率/免赎通道已安全开启。",
                    "action": "可根据调仓需要正常执行减持或置换。",
                })

            # 规则 1.3: C 类满 30 天 0 赎回费窗口开启 (30~35 天)
            if share_class == "C" and 30 <= min_days <= 35:
                alerts.append({
                    "level": "yellow",
                    "dimension": "FIFO批次锁仓",
                    "title": f"【{name} ({code})】C类份额已满 30 天（第 {min_days} 天）",
                    "desc": "赎回费已归零！建议在反弹阻力位择机全额置换清理，避免长期计提销售服务费。",
                    "action": "建议逢高置换为优质 A 类底仓或无费率标的。",
                })

        # 2. 维度二：赛道拥挤与超买预警
        for h in holdings:
            code = h.get("code", "")
            name = h.get("name", code)
            bias_20 = float(h.get("bias_20", 0.0))
            if bias_20 > 6.0:
                alerts.append({
                    "level": "red",
                    "dimension": "超买拥挤",
                    "title": f"【{name} ({code})】短期暴涨超买 (Bias20: +{bias_20:.1f}%)",
                    "desc": "短期正乖离率超过 +6.0% 阈值，处于结构性情绪过热区，警惕高位均值回归！",
                    "action": "严禁单笔满仓追高，建议逢高阶梯兑现利润或设置止盈。",
                })

        # 3. 维度三：基金本体排雷预警 (迷你基规模 < 0.5亿)
        for h in holdings:
            code = h.get("code", "")
            name = h.get("name", code)
            meta = fund_meta.get(code, {})
            aum = meta.get("aum_billion", 2.5)  # 默认 2.5 亿安全
            if aum < 0.50:
                alerts.append({
                    "level": "red",
                    "dimension": "本体排雷",
                    "title": f"【{name} ({code})】规模仅 {aum:.2f} 亿元 (<0.5亿清盘警戒线)",
                    "desc": "最新资产净值低于 5,000 万元法定警戒线，面临清盘终止运作的严重法律与流动性风险！",
                    "action": "择机置换为同赛道规模适中（10~50亿）的标杆公募基金。",
                })

        # 4. 维度四：大盘攻防线预警
        trigger_lines = snapshot.get("trigger_lines", {})
        surge_line = float(trigger_lines.get("surge_line", 4192.0))
        breakdown_line = float(trigger_lines.get("breakdown_line", 4034.0))
        c300_point = float(snapshot.get("c300_point", 4101.34))

        if c300_point < breakdown_line:
            alerts.append({
                "level": "red",
                "dimension": "大盘攻防线",
                "title": f"沪深300点位 ({c300_point:,.1f}) 跌破防守底线 ({breakdown_line:,.0f})",
                "desc": "大盘有效跌破防守均线支撑，市场转入弱势防守格局，空头压制动量加大。",
                "action": "启动防守预案，暂停重权益追加，增量资金定向配置纯债/黄金压舱石。",
            })
        elif c300_point > surge_line:
            alerts.append({
                "level": "green_notice",
                "dimension": "大盘攻防线",
                "title": f"沪深300点位 ({c300_point:,.1f}) 放量突破进攻线 ({surge_line:,.0f})",
                "desc": "指数有效突破上方关键阻力带，右侧进攻主升浪窗口开启，信噪比显著提升。",
                "action": "右侧共振信号确立，可逢回踩增配高弹性科创与成长板块。",
            })

        has_danger = any(a["level"] == "red" for a in alerts)
        has_warning = any(a["level"] == "yellow" for a in alerts)
        all_passed = (not has_danger) and (not has_warning)

        report = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "all_passed": all_passed,
            "has_danger": has_danger,
            "has_warning": has_warning,
            "alerts": alerts,
            "summary": "主动风控巡检全通" if all_passed else f"发现 {len(alerts)} 项风险与提示项",
        }

        # 持久化落盘至 data/portfolio_watchdog.json
        self._persist_watchdog(report)
        return report

    def _persist_watchdog(self, report: Dict[str, Any]):
        try:
            os.makedirs(os.path.dirname(self.watchdog_path) or ".", exist_ok=True)
            with open(self.watchdog_path, "w", encoding="utf-8") as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
        except Exception:
            pass


class SmartExecutionDCAEngine:
    """分批建仓与智能定投算子：严格金额守恒 + 动态自适应乘数"""

    @staticmethod
    def plan_lump_sum(
        total_capital: float,
        allocations: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """模式一：⚡ 一次性建仓（按目标比例今日全额买入，资金分厘守恒）"""
        total_c = float(total_capital)
        total_w = sum(a.get("weight", 0.0) for a in allocations)
        if total_w <= 0:
            total_w = 1.0

        orders = []
        allocated_sum = 0.0
        for i, a in enumerate(allocations):
            w = a.get("weight", 0.0) / total_w
            # 最后一只标的吸收尾差
            if i == len(allocations) - 1:
                amt = round(total_c - allocated_sum, 2)
            else:
                amt = round(total_c * w, 2)
                allocated_sum += amt

            orders.append({
                "code": a.get("code", ""),
                "name": a.get("name", ""),
                "target_weight": round(w * 100.0, 2),
                "order_amount": amt,
                "action": "今日立即申购",
                "execution_timing": "今日 15:00 前",
            })

        # 严格守恒校验
        sum_orders = round(sum(o["order_amount"] for o in orders), 2)
        assert abs(sum_orders - total_c) < 1e-4, f"金额守恒违背: {sum_orders} != {total_c}"

        return {
            "mode": "lump_sum",
            "mode_name": "⚡ 一次性建仓",
            "total_capital": total_c,
            "orders": orders,
            "total_orders_amount": sum_orders,
        }

    @staticmethod
    def plan_three_step_batches(
        total_capital: float,
        allocations: List[Dict[str, Any]],
        market_snapshot: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        模式二：🌊 稳健三步分批建仓（底仓 50% + 逢低网格 30% + 右侧趋势 20%）
        严格保证：batch_1 + batch_2 + batch_3 == total_capital（金额守恒不变量）
        """
        total_c = float(total_capital)
        snapshot = market_snapshot or {}
        trigger_lines = snapshot.get("trigger_lines", {})
        surge_line = float(trigger_lines.get("surge_line", 4192.0))
        breakdown_line = float(trigger_lines.get("breakdown_line", 4034.0))

        # 1. 拆解总本金：50% / 30% / 20%
        c1 = round(total_c * 0.50, 2)
        c2 = round(total_c * 0.30, 2)
        c3 = round(total_c - c1 - c2, 2)  # 严格补齐尾差，分厘不差

        # 第一批：今日底仓（买满纯债、黄金、红利压舱石及半仓权益）
        b1_orders = []
        b1_sum = 0.0
        n_alloc = len(allocations)
        for i, a in enumerate(allocations):
            w = a.get("weight", 1.0 / max(1, n_alloc))
            if i == n_alloc - 1:
                amt = round(c1 - b1_sum, 2)
            else:
                amt = round(c1 * w, 2)
                b1_sum += amt
            b1_orders.append({
                "code": a.get("code", ""),
                "name": a.get("name", ""),
                "amount": amt,
                "strategy": "压舱防守与核心底仓",
            })

        # 第二批：逢低网格挂单（沪深300回踩支撑位触发）
        b2_orders = []
        b2_sum = 0.0
        for i, a in enumerate(allocations):
            w = a.get("weight", 1.0 / max(1, n_alloc))
            if i == n_alloc - 1:
                amt = round(c2 - b2_sum, 2)
            else:
                amt = round(c2 * w, 2)
                b2_sum += amt
            b2_orders.append({
                "code": a.get("code", ""),
                "name": a.get("name", ""),
                "amount": amt,
                "trigger_condition": f"沪深300回踩至 {breakdown_line:,.0f} 附近时分批补入",
            })

        # 第三批：右侧趋势进攻单（放量站上进攻线确认触发）
        b3_orders = []
        b3_sum = 0.0
        for i, a in enumerate(allocations):
            w = a.get("weight", 1.0 / max(1, n_alloc))
            if i == n_alloc - 1:
                amt = round(c3 - b3_sum, 2)
            else:
                amt = round(c3 * w, 2)
                b3_sum += amt
            b3_orders.append({
                "code": a.get("code", ""),
                "name": a.get("name", ""),
                "amount": amt,
                "trigger_condition": f"沪深300放量站上 {surge_line:,.0f} 进攻线确认时加仓",
            })

        # 守恒断言校验
        batch_sum = round(c1 + c2 + c3, 2)
        assert abs(batch_sum - total_c) < 1e-4, f"资金守恒破坏: {batch_sum} != {total_c}"

        return {
            "mode": "three_step_batches",
            "mode_name": "🌊 稳健三步分批建仓",
            "total_capital": total_c,
            "batches": [
                {
                    "step": 1,
                    "title": "第一批 · 今日稳健底仓 (50%)",
                    "amount": c1,
                    "timing": "今日 15:00 前直接执行",
                    "orders": b1_orders,
                    "notes": "买满纯债、黄金防守与核心红利，高弹性权益建半仓，锁定基础安全边际。",
                },
                {
                    "step": 2,
                    "title": "第二批 · 逢低网格补仓单 (30%)",
                    "amount": c2,
                    "timing": f"大盘回踩 {breakdown_line:,.0f} 支撑位触发",
                    "orders": b2_orders,
                    "notes": "未触发前停泊于低波短债/货基赚取票息，回踩支撑线时挂单吸筹。",
                },
                {
                    "step": 3,
                    "title": "第三批 · 右侧趋势加仓单 (20%)",
                    "amount": c3,
                    "timing": f"大盘突破 {surge_line:,.0f} 进攻线触发",
                    "orders": b3_orders,
                    "notes": "未突破前停泊吃息，放量站上进攻线右侧确认时全额进攻。",
                },
            ],
            "total_batch_amount": batch_sum,
        }

    @staticmethod
    def plan_smart_dca(
        total_capital: float,
        allocations: List[Dict[str, Any]],
        erp_percentile: float = 78.0,
        bias_20: float = 1.0,
        periods: int = 12
    ) -> Dict[str, Any]:
        """
        模式三：📅 估值自适应智能定投（根据 ERP 与 Bias20 输出 0.0x~2.0x 乘数）
        """
        total_c = float(total_capital)
        base_per_period = round(total_c / max(1, periods), 2)
        pct_erp = float(erp_percentile) / 100.0
        bias = float(bias_20)

        # 动态自适应乘数计算
        if pct_erp >= 0.75 and bias <= 0.0:
            # 极度低估超跌期: 1.5x ~ 2.0x
            bonus = min(1.0, (pct_erp - 0.75) / 0.25 + (-bias) / 10.0)
            multiplier = round(1.5 + 0.5 * bonus, 2)
            valuation_status = "极度低估水下超跌 (加速收集廉价筹码)"
            multiplier_tag = "🚀 2.0x 逆向猛扣" if multiplier >= 1.8 else "⚡ 1.5x 加速吸筹"
        elif pct_erp < 0.35 or bias > 6.0:
            # 高估过热或严重超买期: 0.0x ~ 0.5x
            penalty = (0.35 - pct_erp) / 0.35 if pct_erp < 0.35 else (bias - 6.0) / 10.0
            multiplier = round(max(0.0, 1.0 - penalty), 2)
            multiplier = min(0.5, multiplier)
            valuation_status = "高估过热或严重超买 (减速定投并分批止盈)"
            multiplier_tag = "⏸️ 0.0x 暂停扣款" if multiplier <= 0.1 else "🟡 0.5x 防守微扣"
        else:
            # 估值合理中性期: 1.0x 标准定投
            multiplier = 1.00
            valuation_status = "估值适中中性 (基准平稳定投)"
            multiplier_tag = "🟢 1.0x 标准定投"

        # 确保乘数在 [0.0, 2.0] 范围内
        multiplier = max(0.0, min(2.0, multiplier))
        actual_deduction = round(base_per_period * multiplier, 2)

        # 各基金本期扣款明细
        n_alloc = len(allocations)
        fund_orders = []
        allocated_sum = 0.0
        for i, a in enumerate(allocations):
            w = a.get("weight", 1.0 / max(1, n_alloc))
            if i == n_alloc - 1:
                amt = round(actual_deduction - allocated_sum, 2)
            else:
                amt = round(actual_deduction * w, 2)
                allocated_sum += amt
            fund_orders.append({
                "code": a.get("code", ""),
                "name": a.get("name", ""),
                "target_weight": round(w * 100.0, 1),
                "period_amount": amt,
            })

        return {
            "mode": "smart_dca",
            "mode_name": "📅 估值自适应智能定投",
            "total_capital": total_c,
            "periods": periods,
            "base_per_period": base_per_period,
            "multiplier": multiplier,
            "multiplier_tag": multiplier_tag,
            "actual_deduction": actual_deduction,
            "valuation_status": valuation_status,
            "erp_percentile": erp_percentile,
            "bias_20": bias_20,
            "fund_orders": fund_orders,
        }

"""
研报“听话听音”语义与一致预期差量化模型 (BetweenTheLinesAnalyzer):
针对国内卖方研报“遵从主旋律、极少出具卖出评级”的特殊行业生态，
构建买方机构视角的研报潜台词挖掘、隐性情绪量化与一致预期分歧度测算。

核心能力：
1. 潜台词隐性情绪评分 (Subtext Tone Score: -100 ~ +100)
2. 踩刹车与警示潜台词自动解码 (如“短期承压”->毛利率坍塌/价格战；“静待拐点”->仍在周期下行通道)
3. 真金白银做多特征过滤 (如“超预期”、“拐点确立”、“盈利弹性释放”)
4. 一致预期差与分析师预测分歧度测算 (Consensus EPS, PE, Divergence STD)
5. 研报原文 PDF 直读链接集成与终端交互卡片
"""

import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
import numpy as np
import pandas as pd
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

from ..storage.lakehouse import LakehouseManager
from ..parsers.research_report_collector import ResearchReportCollector


@dataclass
class SubtextKeywordRule:
    """潜台词特征词规则"""
    keyword: str
    weight: float
    category: str  # "cautious" (警示/看空), "bullish" (真看多), "neutral" (中性)
    explanation: str  # 买方人话潜台词解读


# 权威买方“听话听音”特征词典
SUBTEXT_LEXICON: List[SubtextKeywordRule] = [
    # --- 警示 / 隐晦看空潜台词 (权重为负) ---
    SubtextKeywordRule("短期承压", -3.0, "cautious", "毛利率受侵蚀或价格战激烈，短期业绩难以见底"),
    SubtextKeywordRule("盈利承压", -3.5, "cautious", "增收不增利甚至扣非转负，经营利润率被大幅压制"),
    SubtextKeywordRule("利润承压", -3.5, "cautious", "净利润大幅下滑，费用端与成本端失控"),
    SubtextKeywordRule("毛利承压", -3.0, "cautious", "上游涨价或下游压价，定价权丧失"),
    SubtextKeywordRule("业绩承压", -3.0, "cautious", "季度业绩可能低于此前机构共识"),
    SubtextKeywordRule("静待拐点", -3.0, "cautious", "目前仍处于下行或衰退期，拐点遥遥无期，切勿盲目抄底"),
    SubtextKeywordRule("静待复苏", -2.5, "cautious", "行业需求疲软，复苏进程严重不及预期"),
    SubtextKeywordRule("静待企稳", -2.5, "cautious", "订单下滑尚未止跌"),
    SubtextKeywordRule("静待需求", -2.0, "cautious", "下游客户砍单，产能利用率低迷"),
    SubtextKeywordRule("关注后续验证", -2.5, "cautious", "管理层给出的展望与指引虚高，可能存在无法兑现的暴雷风险"),
    SubtextKeywordRule("仍需观察", -2.0, "cautious", "商业模式或新业务未被市场证明"),
    SubtextKeywordRule("有待验证", -2.0, "cautious", "技术路线或海外扩张存在重大不确定性"),
    SubtextKeywordRule("等待靴子落地", -2.0, "cautious", "存在监管处罚、重组不确定性或大额解禁减持风险"),
    SubtextKeywordRule("低速稳态", -2.5, "cautious", "成长股逻辑彻底破灭，沦为低增速公用事业股，估值中枢将下移"),
    SubtextKeywordRule("进入新常态", -2.5, "cautious", "高增长时代结束，行业天花板显现"),
    SubtextKeywordRule("增长中枢下移", -3.0, "cautious", "未来年化增速从高位永久性回落"),
    SubtextKeywordRule("充分反映预期", -2.0, "cautious", "利好已全部出尽，性价比极差，建议机构获利了结"),
    SubtextKeywordRule("估值合理", -1.5, "cautious", "股价已透支未来业绩，向上弹性微弱"),
    SubtextKeywordRule("去库周期", -2.5, "cautious", "存货积压严重，面临大额存货跌价减值准备"),
    SubtextKeywordRule("渠道去库存", -2.5, "cautious", "下游经销商爆仓，出货放缓"),
    SubtextKeywordRule("业务结构调整", -2.0, "cautious", "传统支柱业务熄火，转型阵痛尚未跨越"),
    SubtextKeywordRule("战略阵痛期", -2.5, "cautious", "研发与销售费用剧增，短期吞噬利润"),
    SubtextKeywordRule("下调盈利预测", -4.0, "cautious", "硬核利空信号！分析师推翻此前模型，下砍业绩预期"),
    SubtextKeywordRule("调低目标价", -4.0, "cautious", "硬核利空信号！机构对中长期估值中枢全面看空"),
    SubtextKeywordRule("下修", -3.0, "cautious", "指引或预期下修"),
    SubtextKeywordRule("维持谨慎", -2.5, "cautious", "研报措辞罕见防御，暗示买方客户规避"),
    SubtextKeywordRule("审慎", -2.0, "cautious", "提示资金注意风险控制"),
    SubtextKeywordRule("竞争加剧", -2.0, "cautious", "行业进入价格战恶性竞争，护城河受冲击"),
    SubtextKeywordRule("汇兑扰动", -1.5, "cautious", "海外敞口出现汇兑损失，侵蚀财务报表"),

    # --- 强推 / 真做多信号 (权重为正) ---
    SubtextKeywordRule("大超预期", +4.0, "bullish", "业绩真金白银爆发，大幅超越卖方模型最乐观上限"),
    SubtextKeywordRule("超预期", +3.0, "bullish", "超越市场悲观共识，基本面强劲反弹"),
    SubtextKeywordRule("超市场预期", +3.0, "bullish", "打破机构保守预期，业绩具备持续超预期动能"),
    SubtextKeywordRule("拐点确立", +3.5, "bullish", "行业出清完成，最差时刻已过，龙头重回上行通道"),
    SubtextKeywordRule("量价齐升", +3.5, "bullish", "量增利增，具备极强定价权与扩产顺风"),
    SubtextKeywordRule("盈利弹性释放", +3.0, "bullish", "经营杠杆效应显现，利润增速远超收入增速"),
    SubtextKeywordRule("第二曲线", +2.5, "bullish", "新业务开辟成功并开始贡献规模化增量利润"),
    SubtextKeywordRule("格局优化", +2.5, "bullish", "中小产能出清，行业集中度提升，龙头尽享溢价"),
    SubtextKeywordRule("重申买入", +3.0, "bullish", "首席分析师亲自背书，坚定看好多头仓位"),
    SubtextKeywordRule("重点推荐", +2.5, "bullish", "列入券商月度金股或核心组合推介"),
    SubtextKeywordRule("坚定看好", +2.5, "bullish", "机构多头共识极强"),
    SubtextKeywordRule("业绩爆发", +3.0, "bullish", "单季利润爆发式增长"),
    SubtextKeywordRule("订单充沛", +2.5, "bullish", "在手订单饱和，未来业绩锁定度极高"),
    SubtextKeywordRule("上调盈利预测", +3.5, "bullish", "硬核利好！分析师上修盈利模型与未来现金流折现"),
    SubtextKeywordRule("上调目标价", +3.5, "bullish", "硬核利好！调升估值空间"),

    # --- 中性 / 稳健推进 ---
    SubtextKeywordRule("符合预期", +0.5, "neutral", "业绩符合既定指引，按部就班无突发意外"),
    SubtextKeywordRule("稳健经营", +0.5, "neutral", "经营风格保守防御，防御属性优于弹性属性"),
    SubtextKeywordRule("平稳推进", +0.5, "neutral", "项目与业务进度正常"),
    SubtextKeywordRule("如期兑现", +0.5, "neutral", "承诺业绩按期落地")
]


@dataclass
class BetweenTheLinesResult:
    """听话听音量化诊断结果"""
    symbol: str
    wind_code: str
    stock_name: str
    total_reports_analyzed: int
    recent_month_coverage: int
    subtext_tone_score: float  # -100 ~ +100
    tone_level: str
    cautious_hits: List[Dict[str, Any]] = field(default_factory=list)
    bullish_hits: List[Dict[str, Any]] = field(default_factory=list)
    subtext_warnings: List[str] = field(default_factory=list)
    consensus_eps_this_year: Optional[float] = None
    consensus_eps_next_year: Optional[float] = None
    consensus_pe_this_year: Optional[float] = None
    consensus_pe_next_year: Optional[float] = None
    eps_divergence_std: Optional[float] = None
    reports_detail: List[Dict[str, Any]] = field(default_factory=list)


class BetweenTheLinesAnalyzer:
    """卖方研报‘听话听音’量化与潜台词透视引擎"""

    def __init__(self, lakehouse: Optional[LakehouseManager] = None):
        self.lakehouse = lakehouse or LakehouseManager()
        self.collector = ResearchReportCollector(lakehouse=self.lakehouse)
        self.console = Console()

    def analyze(self, symbol: str, limit: int = 30, auto_fetch: bool = True) -> BetweenTheLinesResult:
        """
        深度透视单只标的的研报流，挖掘“主旋律”背后的潜台词与一致预期分歧
        """
        clean_code = re.sub(r"[^\d]", "", symbol).zfill(6)
        
        # 1. 优先从湖仓读取
        df = self.lakehouse.get_stock_reports(clean_code, limit=limit)
        
        # 若本地未缓存或少于 3 篇且允许自动获取，在线同步
        if (df.empty or len(df) < 3) and auto_fetch:
            self.console.print(f"[cyan]ℹ 正在为 {clean_code} 采集全市场卖方研报流与一致预期数据...[/cyan]")
            fetched = self.collector.fetch_stock_reports(clean_code, limit=limit)
            if fetched:
                self.collector.sync_reports_to_lakehouse([clean_code])
                df = self.lakehouse.get_stock_reports(clean_code, limit=limit)

        if df.empty:
            # 兜底返回空对象
            return BetweenTheLinesResult(
                symbol=clean_code,
                wind_code=f"{clean_code}.SH" if clean_code.startswith("6") else f"{clean_code}.SZ",
                stock_name="未知标的",
                total_reports_analyzed=0,
                recent_month_coverage=0,
                subtext_tone_score=0.0,
                tone_level="无研报覆盖",
                subtext_warnings=["该标的近期暂无主流卖方机构出具深度研报"]
            )

        stock_name = df.iloc[0]["stock_name"] if "stock_name" in df.columns and pd.notna(df.iloc[0]["stock_name"]) else clean_code
        wind_code = df.iloc[0]["wind_code"] if "wind_code" in df.columns else clean_code

        # 2. 潜台词挖掘与隐性情绪打分
        total_weight = 0.0
        cautious_hits = []
        bullish_hits = []
        reports_detail = []

        cautious_keywords_set = {r.keyword: r for r in SUBTEXT_LEXICON if r.category == "cautious"}
        bullish_keywords_set = {r.keyword: r for r in SUBTEXT_LEXICON if r.category == "bullish"}

        for _, row in df.iterrows():
            title = str(row.get("title", ""))
            rating = str(row.get("rating", "买入"))
            org = str(row.get("org_name", "机构"))
            analyst = str(row.get("analyst_name", ""))
            pub_date = str(row.get("publish_date", ""))
            pdf_url = str(row.get("pdf_url", ""))
            info_code = str(row.get("report_id", ""))

            single_score = 0.0
            found_cautious = []
            found_bullish = []

            # 匹配警示词
            for kw, rule in cautious_keywords_set.items():
                if kw in title:
                    single_score += rule.weight
                    found_cautious.append(kw)
                    cautious_hits.append({
                        "keyword": kw,
                        "title": title,
                        "org": org,
                        "date": pub_date,
                        "explanation": rule.explanation
                    })

            # 匹配多头词
            for kw, rule in bullish_keywords_set.items():
                if kw in title:
                    single_score += rule.weight
                    found_bullish.append(kw)
                    bullish_hits.append({
                        "keyword": kw,
                        "title": title,
                        "org": org,
                        "date": pub_date,
                        "explanation": rule.explanation
                    })

            total_weight += single_score

            # 提取潜台词标签
            if found_cautious:
                tag = f"⚠️ [隐性警示] 踩刹车: {', '.join(found_cautious)}"
            elif found_bullish:
                tag = f"🔥 [真做多] 强推: {', '.join(found_bullish)}"
            else:
                tag = "⚖️ [常规合规] 表面跟踪"

            reports_detail.append({
                "date": pub_date,
                "org": org,
                "analyst": analyst,
                "rating": rating,
                "title": title,
                "pdf_url": pdf_url,
                "tag": tag,
                "eps_this": row.get("predict_eps_this_year"),
                "eps_next": row.get("predict_eps_next_year"),
                "pe_this": row.get("predict_pe_this_year")
            })

        # 归一化潜台词得分 (-100 ~ +100)
        n = max(1, len(df))
        raw_score = (total_weight / n) * 25.0
        tone_score = round(float(np.clip(raw_score, -100.0, 100.0)), 1)

        # 评定等级
        if tone_score >= 40.0:
            tone_level = "极度看多 (强推共振 / 拐点确立)"
        elif tone_score >= 10.0:
            tone_level = "真看多 (基本面景气超预期)"
        elif tone_score >= -10.0:
            tone_level = "中性稳健 (表面合规常规跟踪)"
        elif tone_score >= -40.0:
            tone_level = "表面买入实则谨慎 (隐晦踩刹车 / 提示风险)"
        else:
            tone_level = "深度预警 (密集出现下修与承压)"

        # 3. 生成买方人话潜台词解读 (Subtext Warnings)
        subtext_warnings = []
        if cautious_hits:
            # 统计最高频的警示词
            kw_counts = {}
            for h in cautious_hits:
                kw = h["keyword"]
                kw_counts[kw] = kw_counts.get(kw, 0) + 1
            sorted_kw = sorted(kw_counts.items(), key=lambda x: x[1], reverse=True)
            top_kw_desc = ", ".join([f"'{k}'({v}次)" for k, v in sorted_kw[:3]])

            # 针对性人话解读
            first_rule = cautious_keywords_set.get(sorted_kw[0][0])
            expl = first_rule.explanation if first_rule else "基本面承压"
            subtext_warnings.append(
                f"【听话听音预警】研报表面评级维持“买入/增持”，但标题密集出现 {top_kw_desc}。"
                f"买方真实潜台词：{expl}。当前仍处于消化期，盲目抄底易接飞刀。"
            )

        if bullish_hits and not cautious_hits:
            subtext_warnings.append(
                "【真金白银看好】标题密集采用“超预期/拐点确立/量价齐升”，无隐性踩刹车词汇，机构基本面认可度高。"
            )

        if not cautious_hits and not bullish_hits:
            subtext_warnings.append(
                "【常规例行报告】研报措辞高度规范中性，缺乏强烈的主动做多动能，属于例行覆盖跟踪。"
            )

        # 4. 一致预期差与分歧度计算
        eps_this = pd.to_numeric(df["predict_eps_this_year"], errors="coerce").dropna()
        eps_next = pd.to_numeric(df["predict_eps_next_year"], errors="coerce").dropna()
        pe_this = pd.to_numeric(df["predict_pe_this_year"], errors="coerce").dropna()
        pe_next = pd.to_numeric(df["predict_pe_next_year"], errors="coerce").dropna()

        consensus_eps_this = round(float(eps_this.mean()), 2) if not eps_this.empty else None
        consensus_eps_next = round(float(eps_next.mean()), 2) if not eps_next.empty else None
        consensus_pe_this = round(float(pe_this.mean()), 1) if not pe_this.empty else None
        consensus_pe_next = round(float(pe_next.mean()), 1) if not pe_next.empty else None

        # 分歧度：当年预测 EPS 标准差 / 均值 (变异系数 CV)
        eps_std = None
        if len(eps_this) >= 2 and consensus_eps_this and consensus_eps_this > 0:
            eps_std = round(float(eps_this.std() / consensus_eps_this * 100.0), 1)

        recent_cov = int(df.iloc[0].get("recent_month_reports_count", len(df)))

        return BetweenTheLinesResult(
            symbol=clean_code,
            wind_code=wind_code,
            stock_name=stock_name,
            total_reports_analyzed=len(df),
            recent_month_coverage=recent_cov,
            subtext_tone_score=tone_score,
            tone_level=tone_level,
            cautious_hits=cautious_hits,
            bullish_hits=bullish_hits,
            subtext_warnings=subtext_warnings,
            consensus_eps_this_year=consensus_eps_this,
            consensus_eps_next_year=consensus_eps_next,
            consensus_pe_this_year=consensus_pe_this,
            consensus_pe_next_year=consensus_pe_next,
            eps_divergence_std=eps_std,
            reports_detail=reports_detail
        )

    def print_terminal_card(self, res: BetweenTheLinesResult):
        """在终端输出精致的‘听话听音’研报透视卡片"""
        # 1. 颜色与标签
        if res.subtext_tone_score >= 10:
            score_color = "bold green"
        elif res.subtext_tone_score <= -10:
            score_color = "bold red"
        else:
            score_color = "bold yellow"

        lines = [
            f"[bold white]{res.stock_name} ({res.wind_code})[/bold white] | 研报深度透视与潜台词解码",
            f"• 样本研报数: [cyan]{res.total_reports_analyzed} 篇[/cyan]  • 近一月覆盖密度: [cyan]{res.recent_month_coverage} 篇/月[/cyan]",
            f"• 听话听音隐性情绪分: [{score_color}]{res.subtext_tone_score:+.1f} / 100[/{score_color}]  • 真实定性: [{score_color}]{res.tone_level}[/{score_color}]",
            ""
        ]

        if res.consensus_eps_this_year:
            lines.append(
                f"[bold]• 机构一致预期[/bold]: 当年EPS [cyan]¥{res.consensus_eps_this_year:.2f}[/cyan] (PE: [yellow]{res.consensus_pe_this_year or '-'}x[/yellow]) | "
                f"次年EPS [cyan]¥{res.consensus_eps_next_year or '-:.2f'}[/cyan] (PE: [yellow]{res.consensus_pe_next_year or '-'}x[/yellow]) | "
                f"预测分歧度CV: [magenta]{res.eps_divergence_std or 0.0}%[/magenta]"
            )

        for w in res.subtext_warnings:
            lines.append(f"\n[bold yellow]💡 {w}[/bold yellow]")

        self.console.print(Panel("\n".join(lines), title="🔍 卖方研报“听话听音”隐性情绪与预期差透视", border_style="cyan"))

        # 2. 研报明细与 PDF 直链
        table = Table(title=f"📑 {res.stock_name} 最新研报流与原文 PDF 直读通道", border_style="dim")
        table.add_column("发布日期", style="cyan", width=11)
        table.add_column("券商机构", style="magenta", width=10)
        table.add_column("分析师", style="white", width=10)
        table.add_column("表面评级", style="green", width=8)
        table.add_column("研报标题", style="bold white", width=36)
        table.add_column("听话听音潜台词标签", style="yellow", width=26)
        table.add_column("PDF 原文直链", style="blue underline", width=38)

        for r in res.reports_detail[:10]:
            table.add_row(
                r["date"],
                r["org"],
                r["analyst"][:10],
                r["rating"],
                r["title"][:34],
                r["tag"],
                r["pdf_url"]
            )

        self.console.print(table)

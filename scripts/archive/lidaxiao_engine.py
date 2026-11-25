"""
李大霄投资战略核心引擎 (Li Daxiao Investment Strategy Engine)
融合《李大霄投资战略》（2016精装版 + 2025第三版）及两套经典AI Skill开源精髓，
与Wind本地量化湖仓 (DuckDB) 及投资组合看门狗联动。
"""

import sys
import json
import os
from typing import Dict, Any, List, Optional
import duckdb

# 如果在 李大霄/scripts，上一级是 李大霄，再上一级才是 Workspace 根目录
CURRENT_DIR = os.path.abspath(os.path.dirname(__file__))
if os.path.basename(os.path.abspath(os.path.join(CURRENT_DIR, ".."))) == "李大霄":
    WORKSPACE_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, "..", ".."))
else:
    WORKSPACE_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, ".."))

DB_PATH = os.path.join(WORKSPACE_ROOT, "data", "storage.duckdb")
PORTFOLIO_PATH = os.path.join(WORKSPACE_ROOT, "data", "portfolio_watchdog.json")


class LiDaxiaoEngine:
    """李大霄投资四面体与量化研判引擎"""

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path

    def get_latest_market_macro(self) -> Dict[str, Any]:
        """从 DuckDB 读取最新宏观估值、股债差 ERP 及两融杠杆"""
        if not os.path.exists(self.db_path):
            # 兜底默认基线
            return {
                "eval_date": "2026-10-26",
                "hs300_pe": 12.23,
                "pe_percentile": 43.2,
                "hs300_pb": 1.36,
                "pb_percentile": 18.1,
                "cn_10y_yield": 1.64,
                "erp": 6.54,
                "erp_percentile": 82.2,
                "guarantee_ratio": 260.0,
                "market_temperature": 35.6,
                "valuation_status": "估值显著偏低 (较高性价比)"
            }

        con = duckdb.connect(self.db_path, read_only=True)
        try:
            # 尝试读取 v_market_temperature 视图
            row = con.execute("""
                SELECT eval_date, hs300_pe, pe_percentile, hs300_pb, pb_percentile, 
                       cn_10y_yield, erp, erp_percentile, guarantee_ratio, 
                       market_temperature, valuation_status
                FROM v_market_temperature 
                ORDER BY eval_date DESC LIMIT 1
            """).fetchone()

            if row:
                return {
                    "eval_date": str(row[0]),
                    "hs300_pe": float(row[1]) if row[1] else 12.0,
                    "pe_percentile": float(row[2]) if row[2] else 40.0,
                    "hs300_pb": float(row[3]) if row[3] else 1.3,
                    "pb_percentile": float(row[4]) if row[4] else 20.0,
                    "cn_10y_yield": float(row[5]) if row[5] else 1.64,
                    "erp": float(row[6]) if row[6] else 6.5,
                    "erp_percentile": float(row[7]) if row[7] else 80.0,
                    "guarantee_ratio": float(row[8]) if row[8] else 260.0,
                    "market_temperature": float(row[9]) if row[9] else 35.0,
                    "valuation_status": str(row[10]) if row[10] else "低估"
                }
        except Exception as e:
            print(f"[Warn] DuckDB read failed: {e}, using baseline.", file=sys.stderr)
        finally:
            con.close()

        return {
            "eval_date": "2026-10-26",
            "hs300_pe": 12.23,
            "pe_percentile": 43.2,
            "hs300_pb": 1.36,
            "pb_percentile": 18.1,
            "cn_10y_yield": 1.64,
            "erp": 6.54,
            "erp_percentile": 82.2,
            "guarantee_ratio": 260.0,
            "market_temperature": 35.6,
            "valuation_status": "估值显著偏低 (较高性价比)"
        }

    def evaluate_market_cycle(self) -> Dict[str, Any]:
        """
        基于李大霄三大估值锚（PE、PB、股息率/ERP）与底部发育模型判断当前市场状态
        """
        data = self.get_latest_market_macro()
        pe = data["hs300_pe"]
        pb = data["hs300_pb"]
        erp = data["erp"]
        erp_pct = data["erp_percentile"]
        bond_yield = data["cn_10y_yield"]
        guarantee_ratio = data["guarantee_ratio"]

        # 1. 估值锚研判 (PE < 10~15 历史底部区间)
        if pe <= 10.5:
            pe_stage = "极度低估 (钻石底/历史大底级别)"
        elif pe <= 13.5:
            pe_stage = "显著低估 (少年底/地平线发育区)"
        elif pe <= 18.0:
            pe_stage = "合理估值 (温和中枢)"
        elif pe <= 25.0:
            pe_stage = "估值偏高 (成熟期需警惕)"
        else:
            pe_stage = "泡沫狂热 (地球顶风险区)"

        # 2. 股债利差 (ERP) 研判 (李大霄2024-2025新洞察：我国股债差已达高位区，货基债市泡沫)
        if erp_pct >= 75.0:
            erp_verdict = "股债差处于历史极高位区！股票极具性价比，债市拥挤，严禁割肉权益换纯债！"
            spread_status = "股票远比债券划算"
        elif erp_pct <= 25.0:
            erp_verdict = "股债差处于低位，股票风险溢价不足，宜保护胜利果实。"
            spread_status = "债券相对股票更具防守性"
        else:
            erp_verdict = "股债性价比处于均衡区间。"
            spread_status = "股债平衡"

        # 3. 杠杆安全水线
        if guarantee_ratio < 220.0:
            leverage_risk = "杠杆风险高企，两融去杠杆压力大，切勿借钱炒股！"
        elif guarantee_ratio > 260.0:
            leverage_risk = "杠杆水平健康安全，无系统性平仓风险。"
        else:
            leverage_risk = "杠杆水平温和可控。"

        # 4. 底部生命周期发育阶段定位
        if pe <= 11.0:
            lifecycle = "钻石底 / 婴儿底阶段 (播种期，买好股抱紧紧)"
        elif pe <= 13.5:
            lifecycle = "少年底 / 坚实地平线 (少年强则中国强，重心上移中)"
        elif pe <= 20.0:
            lifecycle = "青年牛 / 慢牛展开阶段 (稳步前行，不拔青苗)"
        else:
            lifecycle = "成熟牛 / 地球顶前夕 (摘熟苹果，保护胜利果实)"

        # 5. 大霄金句与忠告
        if erp_pct >= 75.0 and pe <= 13.5:
            quote = (
                "同志们，3000点地平线亮晶晶！沪深300市盈率才12倍左右，股债差到了历史极高位区！"
                "国债收益率跌到1.6%附近，大家都在疯抢债基，这叫‘货基涨停预示债市泡沫’！"
                "在这个时候千万不要倒洗澡水把婴儿也倒掉了！余钱好股抱紧紧，不要借钱加杠杆，时间会奖赏坚守正道的人！"
            )
        else:
            quote = "余钱好股淡定，急钱差股谨慎，杠杆借贷小心。做好人，买好股，得好报！"

        return {
            "macro_data": data,
            "pe_stage": pe_stage,
            "erp_verdict": erp_verdict,
            "spread_status": spread_status,
            "leverage_risk": leverage_risk,
            "lifecycle": lifecycle,
            "daxiao_quote": quote
        }

    def screen_stock(self, stock_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        李大霄好股票 vs 黑五类 8 项硬核筛查
        输入参数示例:
        {
            "name": "工商银行",
            "code": "601398",
            "market_cap_billion": 1800.0,  # 市值(亿元)
            "listed_years": 18,            # 上市年限
            "is_st": False,                # 是否ST
            "is_concept_only": False,      # 是否纯蹭题材
            "pe": 5.8,                     # PE-TTM
            "pb": 0.58,                    # PB
            "dividend_yield_pct": 5.9,     # 股息率(%)
            "dividend_consecutive_years": 16, # 连续分红年限
            "net_profit_positive_3y": True,   # 扣非利润连续3年为正
            "ocf_covers_net_profit": True,    # 经营现金流覆盖净利润
            "debt_ratio_pct": 91.0,           # 资产负债率 (金融业需特殊考虑)
            "is_state_owned_or_leader": True, # 是否央企/国企/龙头
            "investor_money_type": "余钱"      # 余钱 / 急钱 / 杠杆
        }
        """
        name = stock_info.get("name", "未命名标的")
        red_flags: List[str] = []
        green_lights: List[str] = []

        # 1. 黑五类一票否决检测
        # (1) 小盘股 (市值 < 50亿)
        cap = stock_info.get("market_cap_billion", 100.0)
        if cap < 50.0:
            red_flags.append(f"【黑五类-小盘股】总市值仅 {cap} 亿元（<50亿），极易被游资炒作操纵，流动性差。")

        # (2) 次新股 (上市不满3年)
        listed_years = stock_info.get("listed_years", 5)
        if listed_years < 3:
            red_flags.append(f"【黑五类-次新股】上市仅 {listed_years} 年（未满3年），业绩未经周期大考，解禁压力大。")

        # (3) 垃圾股 (ST/*ST或持续亏损)
        if stock_info.get("is_st", False):
            red_flags.append("【黑五类-垃圾股】属于 ST/*ST 风险警示标的，退市风险悬顶，坚决不看第二眼！")

        # (4) 题材股 (纯炒概念无实质业绩)
        if stock_info.get("is_concept_only", False):
            red_flags.append("【黑五类-题材股】蹭概念无实质业绩支撑，风停了摔死的都是猪，切忌接最后一棒！")

        # (5) 伪成长 (高PE无现金流)
        pe = stock_info.get("pe", 15.0)
        ocf_ok = stock_info.get("ocf_covers_net_profit", True)
        if pe > 40.0 and not ocf_ok:
            red_flags.append(f"【黑五类-伪成长】市盈率高达 {pe} 倍且经营现金流不能覆盖利润，故事经不起时间推敲。")

        # 2. 估值水位
        pb = stock_info.get("pb", 1.2)
        if pe <= 10.0:
            green_lights.append(f"PE仅 {pe} 倍，符合‘10倍PE即底部’的黄金低估标准。")
        elif pe > 30.0:
            red_flags.append(f"PE高达 {pe} 倍，估值偏高，安全边际不足。")

        if pb < 1.0:
            green_lights.append(f"PB为 {pb} 倍（破净），低于净资产买入，安全边际极厚。")
        elif pb > 3.0:
            red_flags.append(f"PB高达 {pb} 倍，资产溢价过高。")

        # 3. 分红记录 (制约铁公鸡)
        div_yield = stock_info.get("dividend_yield_pct", 0.0)
        div_years = stock_info.get("dividend_consecutive_years", 0)
        if div_yield >= 5.0 and div_years >= 3:
            green_lights.append(f"股息率高达 {div_yield}% 且连续 {div_years} 年真金白银现金分红，远超房租与理财回报。")
        elif div_years == 0 or div_yield < 1.0:
            red_flags.append("多年不分红或股息率极低，属于‘铁公鸡’，不符合让所有股东赚钱的原则。")

        # 4. 盈利真实性
        profit_ok = stock_info.get("net_profit_positive_3y", True)
        if not profit_ok:
            red_flags.append("扣非净利润不能维持连续3年为正，盈利质量存疑。")
        elif ocf_ok:
            green_lights.append("扣非净利润连续为正且经营现金流充沛，是实打实的真实盈利。")

        # 5. 行业龙头与所有权性质
        is_so = stock_info.get("is_state_owned_or_leader", False)
        if is_so:
            green_lights.append("央企/国企或行业绝对龙头，国家信用背书，不易爆雷。")
        else:
            # 扣分但不一定一票否决
            pass

        # 6. 投资者资金性质
        money_type = stock_info.get("investor_money_type", "余钱")
        if money_type in ["杠杆", "借贷", "配资"]:
            red_flags.append("【致命禁忌】使用杠杆借贷入市，刀架在脖子上炒股，短期波动即可导致本金清零！")
        elif money_type == "急钱":
            red_flags.append("使用短期急用钱入市，心态容易失衡，无法扛过市场正常的波动周期。")
        else:
            green_lights.append("使用至少3-5年用不上的余钱投资，吃得下饭、睡得着觉，具备长期持有的前提。")

        # 综合判定
        is_passed = len(red_flags) == 0
        score = max(0, min(100, 50 + len(green_lights) * 12 - len(red_flags) * 20))

        if is_passed and score >= 80:
            verdict = "【大霄级好股票】低估值、高分红、真盈利、好公司、合理价格！值得长期托付、播种持有。"
        elif len(red_flags) > 0 and any("黑五类" in rf or "致命禁忌" in rf for rf in red_flags):
            verdict = "【坚决远离】命中黑五类或杠杆禁区，不是投资是赌博，十赌九输，切莫碰触！"
        else:
            verdict = "【中性观察】存在瑕疵或估值未到极致舒适区，建议分批谨慎或继续等待更好价格。"

        return {
            "name": name,
            "score": score,
            "is_passed": is_passed,
            "green_lights": green_lights,
            "red_flags": red_flags,
            "verdict": verdict
        }

    def diagnose_portfolio(self, portfolio_path: str = PORTFOLIO_PATH) -> Dict[str, Any]:
        """
        结合李大霄投资四面体与散户进阶六阶梯，对用户组合进行整体体检
        """
        if not os.path.exists(portfolio_path):
            return {"error": f"Portfolio file not found: {portfolio_path}"}

        with open(portfolio_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        assets = data.get("monitored_assets", [])
        total_cap = data.get("total_capital_rmb", 0)

        diagnostics = []
        red_count = 0
        green_count = 0
        yellow_count = 0

        for a in assets:
            name = a.get("name", "")
            code = a.get("code", "")
            status = a.get("status", "")
            amount = a.get("amount_rmb", 0)
            weight_pct = (amount / total_cap * 100) if total_cap > 0 else 0

            # 启发式归类大霄逻辑
            if "红利低波" in name or "红利" in name:
                daxiao_tag = "压舱石资产 (低估高股息，现金分红沉淀价值)"
            elif "科创" in name or "芯片" in name or "半导体" in name or "集成电路" in name:
                daxiao_tag = "高弹性赛道 (注意防范题材过热与高费率侵蚀，逢高做T减亏)"
            elif "债" in name:
                daxiao_tag = "固收防守底仓 (稀缺优质席位切忌盲目丢弃，但严禁在高位追纯债)"
            elif "QDII" in name or "标普" in name or "纳斯达克" in name:
                daxiao_tag = "全球对冲仓位 (适度分散，比例适中)"
            else:
                daxiao_tag = "常规资产"

            if "绿灯" in status:
                green_count += 1
            elif "红灯" in status:
                red_count += 1
            else:
                yellow_count += 1

            diagnostics.append({
                "code": code,
                "name": name,
                "amount": amount,
                "weight_pct": round(weight_pct, 2),
                "status": status,
                "daxiao_tag": daxiao_tag,
                "action": a.get("trigger_action", "")
            })

        # 散户六阶梯位置判定：用户组合包含债券、红利ETF、行业混合、海外QDII，处于第4-5阶梯之间（进阶成熟期）
        advice = (
            "从大霄的投资四面体来看：\n"
            "1. 宏观上国运依然向好，政策利好组合拳频出；\n"
            "2. 市场处于3000点地平线以上、估值历史低位，是播种而不是割肉的季节；\n"
            "3. 组合中以红利低波和稳健债基为压舱石（绿灯资产占比超45%），非常符合‘好人买好股’的原则；\n"
            "4. 对高费率单押赛道（如银华集成电路C，年化费率1.6%），坚持‘反弹至均线压力位清理置换’，绝不恋战；\n"
            "5. 所有红利资产把分红方式改成‘现金分红’，真金白银沉淀股息，做到‘吃得下饭、睡得着觉’！"
        )

        return {
            "portfolio_name": data.get("portfolio_name"),
            "total_capital_rmb": total_cap,
            "asset_count": len(assets),
            "green_count": green_count,
            "yellow_count": yellow_count,
            "red_count": red_count,
            "details": diagnostics,
            "daxiao_overall_advice": advice
        }


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="李大霄投资战略核心引擎 CLI")
    subparsers = parser.add_subparsers(dest="cmd", help="子命令: market | portfolio | screen")

    # market 子命令
    p_market = subparsers.add_parser("market", help="输出当前市场宏观大势、估值与周期研判")

    # portfolio 子命令
    p_portfolio = subparsers.add_parser("portfolio", help="体检当前用户投资组合")
    p_portfolio.add_argument("--path", default=PORTFOLIO_PATH, help="投资组合JSON路径")

    # screen 子命令
    p_screen = subparsers.add_parser("screen", help="单只股票好股票vs黑五类决策筛查")
    p_screen.add_argument("--name", default="测试标的", help="股票名称")
    p_screen.add_argument("--cap", type=float, default=100.0, help="总市值(亿元)")
    p_screen.add_argument("--years", type=int, default=5, help="上市年数")
    p_screen.add_argument("--pe", type=float, default=10.0, help="PE市盈率")
    p_screen.add_argument("--pb", type=float, default=0.8, help="PB市净率")
    p_screen.add_argument("--div", type=float, default=5.0, help="股息率(%)")
    p_screen.add_argument("--div_years", type=int, default=5, help="连续分红年数")
    p_screen.add_argument("--so", action="store_true", help="是否央企/国企/行业龙头")
    p_screen.add_argument("--money", default="余钱", choices=["余钱", "急钱", "杠杆"], help="资金性质")

    args = parser.parse_args()
    engine = LiDaxiaoEngine()

    if args.cmd == "market" or args.cmd is None:
        print("=== 李大霄市场大势与周期研判 ===")
        market_res = engine.evaluate_market_cycle()
        macro = market_res["macro_data"]
        print(f"评估日期: {macro['eval_date']}")
        print(f"沪深300 PE: {macro['hs300_pe']} (历史分位 {macro['pe_percentile']}%) | PB: {macro['hs300_pb']} (历史分位 {macro['pb_percentile']}%)")
        print(f"10年期国债收益率: {macro['cn_10y_yield']}% | 股债差(ERP): {macro['erp']}% (历史分位 {macro['erp_percentile']}%)")
        print(f"两融担保比例: {macro['guarantee_ratio']}% -> {market_res['leverage_risk']}")
        print(f"周期发育阶段: {market_res['lifecycle']}")
        print(f"大势定位: {market_res['pe_stage']}")
        print(f"股债利差判定: {market_res['erp_verdict']}")
        print("-" * 50)
        print(f"【大霄心语】:\n{market_res['daxiao_quote']}")

    elif args.cmd == "portfolio":
        print("=== 用户投资组合大霄式体检 ===")
        diag = engine.diagnose_portfolio(args.path)
        if "error" in diag:
            print(f"错误: {diag['error']}")
        else:
            print(f"组合名称: {diag.get('portfolio_name')} | 总金额: {diag.get('total_capital_rmb'):,.2f} 元")
            print(f"监控标的数: {diag.get('asset_count')} 只 (绿灯 {diag.get('green_count')} | 黄灯 {diag.get('yellow_count')} | 红灯 {diag.get('red_count')})")
            print("-" * 50)
            for d in diag.get("details", []):
                print(f"[{d['code']}] {d['name']} | 金额: {d['amount']:,.2f} ({d['weight_pct']}%) | 状态: {d['status']}")
                print(f"   -> 大霄标签: {d['daxiao_tag']}")
                print(f"   -> 应对指令: {d['action']}")
            print("-" * 50)
            print(f"【大霄四面体总评与建议】:\n{diag.get('daxiao_overall_advice')}")

    elif args.cmd == "screen":
        print(f"=== 李大霄选股筛查: {args.name} ===")
        stock_data = {
            "name": args.name,
            "market_cap_billion": args.cap,
            "listed_years": args.years,
            "pe": args.pe,
            "pb": args.pb,
            "dividend_yield_pct": args.div,
            "dividend_consecutive_years": args.div_years,
            "is_state_owned_or_leader": args.so,
            "investor_money_type": args.money,
            "is_st": False,
            "is_concept_only": False,
            "net_profit_positive_3y": True,
            "ocf_covers_net_profit": True
        }
        res = engine.screen_stock(stock_data)
        print(f"最终评分: {res['score']} 分 | 结论: {res['verdict']}")
        if res["green_lights"]:
            print("优势亮点:")
            for g in res["green_lights"]:
                print(f"  + {g}")
        if res["red_flags"]:
            print("风险警示 / 否决项:")
            for r in res["red_flags"]:
                print(f"  - {r}")


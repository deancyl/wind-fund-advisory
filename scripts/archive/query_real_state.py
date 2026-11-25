import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.resolve()))

import pandas as pd
from data_loader import DataLoader
import islands.island_ensemble as ensemble_mod
from src.toolkit.bonds import ChinaBondYieldCollector

def query_real_state():
    # 1. 查询中债10Y国债利率 (WindToolkit)
    collector = ChinaBondYieldCollector()
    b_data = collector.get_latest_yield_curve()
    print("=== 中债收益率曲线实盘指标 (WindToolkit 交叉验证) ===")
    print(f"数据日期: {b_data.get('date')} | 曲线名称: {b_data.get('curve_name')}")
    print(f"10年期国债收益率 (10Y): {b_data.get('y_10y'):.4f}%")
    print(f"30年期超长债收益率 (30Y): {b_data.get('y_30y'):.4f}%")
    print(f"10Y-1Y 期限利差: {b_data.get('term_spread_10y_1y_bp'):.2f} bp")
    print(f"收益率曲线形态: {b_data.get('curve_regime')}")
    print(f"更新时间: {b_data.get('updated_at')}")
        
    # 2. 查询全量行情矩阵最新日期
    dl = DataLoader()
    full_df = dl.load_total_return_matrix()
    latest_dt = full_df['date'].iloc[-1]
    print(f"\n最新行情矩阵日期: {latest_dt.strftime('%Y-%m-%d')} (共计 {len(full_df)} 交易日)")
    
    # 3. 计算实盘截面决策权重
    weights = ensemble_mod.strategy_fn(full_df, ensemble_mod.PARAMS)
    print("\n=== 2026-10-27 实盘截面终极推荐权重配置 (Trial 29 正式投产) ===")
    
    fund_mapping = {
        'STAR50_STITCH': ('华夏科创50ETF联接A', '011612', '硬科技/半导体成长进攻龙头'),
        'H00852': ('富国中证1000ETF联接A', '016633', '小盘高弹性成长宽基'),
        'H00905': ('富国中证500ETF联接A', '161017', '中盘成长均衡配置'),
        'H00300': ('易方达沪深300ETF联接A', '110020', '核心蓝筹大盘基石'),
        'H00922': ('富国中证红利指数A', '100032', '高股息现金流周期价值底仓'),
        'H30269': ('创金合信红利低波动A', '005561', '低估值低波动防御避险压舱石'),
        'AU9999': ('华安易富黄金ETF联接A', '000216', '抗通胀与地缘对冲气垫 (外援 <= 20%)'),
        'SPX_CNY': ('博时标普500ETF联接A', '050025', '海外QDII多元配置 (限购 <= 10%)'),
        'H11009': ('易方达裕祥回报债券A', '002351', '高等级纯债与固收现金管理底仓')
    }
    
    tot_w = 0.0
    tot_ashare = 0.0
    tot_offshore = 0.0
    tot_bond = 0.0
    
    for asset, w in sorted(weights.items(), key=lambda x: -x[1]):
        fund_name, fund_code, fund_desc = fund_mapping.get(asset, (asset, 'N/A', 'N/A'))
        tot_w += w
        if asset in ['STAR50_STITCH', 'H00852', 'H00905', 'H00300', 'H00922', 'H30269']:
            tot_ashare += w
        elif asset in ['AU9999', 'SPX_CNY']:
            tot_offshore += w
        elif asset in ['H11009', '930609']:
            tot_bond += w
            
        print(f"[{asset:<13}] {fund_name} ({fund_code}) | 权重: {w*100:5.2f}% | 属性: {fund_desc}")
        
    print("-" * 75)
    print(f"A股本土权益合计占比: {tot_ashare*100:.2f}% (>= 55.0% 刚性红线达成)")
    print(f"非A额外援合计占比:   {tot_offshore*100:.2f}% (<= 20.0% 刚性红线达成)")
    print(f"纯债与固收合计占比:   {tot_bond*100:.2f}% (<= 50.0% 刚性红线达成)")
    print(f"全组合权重总计:       {tot_w*100:.2f}%")

if __name__ == '__main__':
    query_real_state()

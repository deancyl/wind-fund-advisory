import sys
sys.path.insert(0, ".")
import json
from AGY2_FundAdvisory.multi_ledger_manager import MultiLedgerManager
from AGY2_FundAdvisory.advisory_engine import ActiveRiskSentry
from AGY2_FundAdvisory.portfolio_manager import (
    slice_long_screenshot_for_ocr,
    fuzzy_match_fund_by_name,
    parse_smart_text_holdings,
    parse_batch_fund_text_input,
    PortfolioManager,
)

def run_checks():
    with open('data/ledgers/combat_29_funds.json', 'r', encoding='utf-8') as f:
        d = json.load(f)
    h = d['holdings']
    print(f'Total count: {len(h)}')
    tot_mv = sum(x['market_value'] for x in h)
    print(f'Total MV: {tot_mv:.2f}')

    core = h[:7]
    waist = h[7:10]
    tail = h[10:]

    core_mv = sum(x['market_value'] for x in core)
    waist_mv = sum(x['market_value'] for x in waist)
    tail_mv = sum(x['market_value'] for x in tail)
    print(f'Core (7) MV: {core_mv:.2f}')
    print(f'Waist (3) MV: {waist_mv:.2f}')
    print(f'Tail (19) MV: {tail_mv:.2f}')

    pnl_map = {x['fund_code']: x['floating_pnl'] for x in h}
    deep_loss_sum = pnl_map['100032'] + pnl_map['011613'] + pnl_map['161725']
    print(f'Deep loss sum (100032, 011613, 161725): {deep_loss_sum:.2f}')

    min_days = min(min(b['holding_days'] for b in x['batches']) for x in h)
    print(f'Min holding days: {min_days}')

    mlm = MultiLedgerManager.get_instance()
    pm = mlm.get_pm('combat_29_funds')
    sentry = ActiveRiskSentry()
    rep = sentry.inspect_portfolio(pm.holdings)
    tail_alerts = [a for a in rep['alerts'] if a.get('dimension') == '碎片尾仓清理']
    print(f'Tail alerts count: {len(tail_alerts)}')
    if tail_alerts:
        alert = tail_alerts[0]
        cnt = alert['tail_count']
        cash = alert['recoverable_cash']
        codes = alert['tail_codes']
        print(f'Tail count detected: {cnt}')
        print(f'Recoverable cash: {cash:.2f}')
        print(f'Tail codes: {codes}')

    plan = pm.generate_scenario_rebalance_plan({}, scenario_mode='sweep_tail_and_c_class', core_anchor_code='002351')
    act_cnt = len(plan['sell_actions'])
    s_amt = plan['total_sell_amount']
    fee = plan['total_redemption_fee']
    print(f'Plan sell actions count: {act_cnt}')
    print(f'Plan total sell amount: {s_amt:.2f}')
    print(f'Plan redemption fee: {fee:.2f}')

if __name__ == '__main__':
    run_checks()

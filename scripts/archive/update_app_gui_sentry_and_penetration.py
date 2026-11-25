# -*- coding: utf-8 -*-
from pathlib import Path

p = Path("AGY2_FundAdvisory/app_gui.py")
content = p.read_text(encoding="utf-8")

# 1. 替换 1940 行附近的 4 个缓存函数
old_caches = '''@st.cache_data(ttl=300)
def _cached_look_through_industry(holdings_repr: str):
    return pm.calculate_look_through_industry_exposure()

@st.cache_data(ttl=300)
def _cached_stock_overlap(holdings_repr: str):
    return pm.calculate_stock_overlap_matrix()

@st.cache_data(ttl=300)
def _cached_penetration_risk(holdings_repr: str):
    return pm.calculate_portfolio_penetration_risk()

@st.cache_data(ttl=300)
def _cached_stocks_df(holdings_repr: str):
    return pm.get_portfolio_look_through_stocks_df()'''

new_caches = '''@st.cache_data(ttl=300)
def _cached_look_through_industry(holdings_items: tuple):
    cur_pm = st.session_state.get("pm") or pm
    h_dict = {c: HoldingItem(fund_code=c, fund_name=fn, shares=sh, cost_nav=cn, current_nav=nav) for c, fn, sh, cn, nav in holdings_items} if holdings_items else None
    return cur_pm.calculate_look_through_industry_exposure(holdings_override=h_dict)

@st.cache_data(ttl=300)
def _cached_stock_overlap(holdings_items: tuple):
    cur_pm = st.session_state.get("pm") or pm
    h_dict = {c: HoldingItem(fund_code=c, fund_name=fn, shares=sh, cost_nav=cn, current_nav=nav) for c, fn, sh, cn, nav in holdings_items} if holdings_items else None
    return cur_pm.calculate_stock_overlap_matrix(holdings_override=h_dict)

@st.cache_data(ttl=300)
def _cached_penetration_risk(holdings_items: tuple):
    cur_pm = st.session_state.get("pm") or pm
    h_dict = {c: HoldingItem(fund_code=c, fund_name=fn, shares=sh, cost_nav=cn, current_nav=nav) for c, fn, sh, cn, nav in holdings_items} if holdings_items else None
    return cur_pm.calculate_portfolio_penetration_risk(holdings_override=h_dict)

@st.cache_data(ttl=300)
def _cached_stocks_df(holdings_items: tuple):
    cur_pm = st.session_state.get("pm") or pm
    h_dict = {c: HoldingItem(fund_code=c, fund_name=fn, shares=sh, cost_nav=cn, current_nav=nav) for c, fn, sh, cn, nav in holdings_items} if holdings_items else None
    return cur_pm.get_portfolio_look_through_stocks_df(holdings_override=h_dict)'''

if old_caches in content:
    content = content.replace(old_caches, new_caches, 1)
    print("1. Successfully replaced 4 penetration cache functions")
else:
    print("1. FAILED to replace 4 penetration cache functions")

# 2. 替换 Tab 4 中对 4 个缓存函数的调用实参：把 _h_repr 换为 _h_items
old_h_repr_def = '''        with col_chart_right:
            st.markdown("##### 🏭 行业穿透暴露")
            _h_repr = str(sorted((c, h.shares, h.current_nav) for c, h in active_examine_holdings.items()))
            df_ind = _cached_look_through_industry(_h_repr)'''

new_h_repr_def = '''        with col_chart_right:
            st.markdown("##### 🏭 行业穿透暴露")
            _h_items = tuple(sorted((c, getattr(h, "fund_name", c), float(getattr(h, "shares", 0.0)), float(getattr(h, "cost_price", getattr(h, "cost_nav", 1.0))), float(getattr(h, "current_nav", 1.0))) for c, h in active_examine_holdings.items()))
            df_ind = _cached_look_through_industry(_h_items)'''

if old_h_repr_def in content:
    content = content.replace(old_h_repr_def, new_h_repr_def, 1)
    print("2. Successfully replaced _h_repr def")
else:
    print("2. FAILED to replace _h_repr def")

# 替换 overlap 与 risk、df_scr
old_other_calls = '''        overlap_res = _cached_stock_overlap(_h_repr)'''
new_other_calls = '''        overlap_res = _cached_stock_overlap(_h_items)'''
if old_other_calls in content:
    content = content.replace(old_other_calls, new_other_calls, 1)
    print("3. Successfully replaced _cached_stock_overlap call")

old_risk_call = '''        if len(active_examine_holdings) > 0:
            port_risk = _cached_penetration_risk(_h_repr)'''
new_risk_call = '''        if len(active_examine_holdings) > 0:
            port_risk = _cached_penetration_risk(_h_items)'''
if old_risk_call in content:
    content = content.replace(old_risk_call, new_risk_call, 1)
    print("4. Successfully replaced _cached_penetration_risk call")

old_stocks_call = '''            df_scr = _cached_stocks_df(_h_repr)'''
new_stocks_call = '''            df_scr = _cached_stocks_df(_h_items)'''
if old_stocks_call in content:
    content = content.replace(old_stocks_call, new_stocks_call, 1)
    print("5. Successfully replaced _cached_stocks_df call")

# 3. 替换聪明钱中的 pm.holdings 为 active_examine_holdings
old_crowd_loop = '''        # 聪明钱与机构抱团监控
        st.markdown("---")
        st.markdown("#### 📡 聪明钱与拥挤")
        if len(active_examine_holdings) > 0:
            crowd_rows = []
            for code, h in pm.holdings.items():
                c_info = pm.get_fund_smart_money_crowding(code)'''

new_crowd_loop = '''        # 聪明钱与机构抱团监控
        st.markdown("---")
        st.markdown("#### 📡 聪明钱与拥挤")
        if len(active_examine_holdings) > 0:
            crowd_rows = []
            cur_pm = st.session_state.get("pm") or pm
            for code, h in active_examine_holdings.items():
                c_info = cur_pm.get_fund_smart_money_crowding(code)'''

if old_crowd_loop in content:
    content = content.replace(old_crowd_loop, new_crowd_loop, 1)
    print("6. Successfully replaced smart money holdings loop")
else:
    print("6. FAILED to replace smart money holdings loop")

p.write_text(content, encoding="utf-8")
print("Done updating Tab 4 penetration calls!")

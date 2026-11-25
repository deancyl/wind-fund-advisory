from pathlib import Path
import re

def patch():
    target = Path("AGY2_FundAdvisory/app_gui.py")
    code = target.read_text(encoding="utf-8")

    # Replace sub-tab 2
    old_t2 = '''    # Sub-tab 2: 14 大赛道量化温度计总表
    with box_tab2:
        st.markdown("#### 🌡️ 全市场 14 大赛道量化温度计总表")'''
    
    new_t2 = '''    # Sub-tab 2: 14 大赛道量化温度计总表
    with box_tab2:
        with st.expander("📊 查看全市场 14 大赛道量化温度计总表 (向下展开)", expanded=True):'''

    # Replace sub-tab 3
    old_t3 = '''    # Sub-tab 3: 场内ETF与场外联接 14:45 尾盘折溢价套利感知 + 核心场内 ETF 溢价预警哨
    with box_tab3:
        st.markdown("#### ⚡ 场内ETF与场外联接 14:45 尾盘折溢价套利感知")'''

    new_t3 = '''    # Sub-tab 3: 场内ETF与场外联接 14:45 尾盘折溢价套利感知 + 核心场内 ETF 溢价预警哨
    with box_tab3:
        with st.expander("⚡ 场内ETF与场外联接 14:45 尾盘折溢价套利感知", expanded=True):'''

    # Replace sub-tab 4
    old_t4 = '''    # Sub-tab 4: 50ETF与300ETF认沽期权隐含波动率防暴跌哨
    with box_tab4:
        st.markdown("#### 🛡️ 50ETF与300ETF认沽期权隐含波动率防暴跌哨")'''

    new_t4 = '''    # Sub-tab 4: 50ETF与300ETF认沽期权隐含波动率防暴跌哨
    with box_tab4:
        with st.expander("🛡️ 50ETF与300ETF认沽期权隐含波动率防暴跌哨", expanded=True):'''

    # Replace sub-tab 5
    old_t5 = '''    # Sub-tab 5: 跨境QDII溢价与外汇期货锁汇成本套利精算
    with box_tab5:
        st.markdown("#### 🌐 跨境QDII溢价与外汇期货锁汇成本套利精算")'''

    new_t5 = '''    # Sub-tab 5: 跨境QDII溢价与外汇期货锁汇成本套利精算
    with box_tab5:
        with st.expander("🌐 跨境QDII溢价与外汇期货锁汇成本套利精算", expanded=True):'''

    for old, new in [(old_t2, new_t2), (old_t3, new_t3), (old_t4, new_t4), (old_t5, new_t5)]:
        if old in code:
            code = code.replace(old, new, 1)
            print(f"Replaced {old[:30]}...")
        else:
            print(f"Not found: {old[:30]}...")

    target.write_text(code, encoding="utf-8")
    print("Patch complete.")

if __name__ == "__main__":
    patch()

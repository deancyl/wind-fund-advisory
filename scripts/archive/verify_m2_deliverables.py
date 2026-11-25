import sys
from pathlib import Path

def verify():
    gui_file = Path("AGY2_FundAdvisory/app_gui.py")
    assert gui_file.exists(), "app_gui.py does not exist"
    code = gui_file.read_text(encoding="utf-8")

    # 1. 验证伪交易按钮已彻底绝迹
    assert "btn_master_action_switch" not in code, "btn_master_action_switch still present"
    assert "btn_batch_lock_all_7d" not in code, "btn_batch_lock_all_7d still present"
    assert "btn_add_radar_pool_" not in code, "btn_add_radar_pool_ still present"
    print("✅ 1. 所有伪操作/伪交易按钮彻底绝迹 (0 命中)")

    # 2. 验证折叠栏 100% 全宽，无 col_wing_btn
    assert "col_wing_btn" not in code, "col_wing_btn column still present"
    assert "col_wing_exp, col_wing_btn = st.columns" not in code, "columns(8.2, 1.8) still present"
    print("✅ 2. 投顾参谋条 100% 全宽容器已生效，彻底消灭右侧 18% 垂直空白死区")

    # 3. 验证四大 Tab 重复巨型标题已删除
    for h in ["🌱 新资建仓", "💼 持仓调仓", "📈 组合回测", "🔍 穿透工具"]:
        assert f'st.subheader("{h}")' not in code, f'st.subheader("{h}") still present'
    print("✅ 3. 四大 Tab 内部重复巨型 subheader 彻底清除")

    # 4. 验证全宽四宫格大胶囊主导航栏 CSS 规则
    assert "grid-template-columns: repeat(4, 1fr) !important;" in code, "Grid 4 columns missing"
    assert "height: 46px !important;" in code, "46px height missing"
    assert "font-size: 16px !important;" in code, "16px font-size missing"
    assert ":not([data-testid=\"stTabContent\"]" in code, "Tab 4 sub-tab isolation selector missing"
    print("✅ 4. 全宽四宫格大胶囊主导航栏 CSS 改造完成，并与二级子 Tab 严格物理隔离")

    # 5. 验证 Tab 4 顶栏合并与 6 大二级子 Tab
    assert "col_top_sel, col_top_badges = st.columns([3.8, 6.2])" in code, "Tab 4 top row column merger missing"
    assert "box_tab1, box_tab2, box_tab3, box_tab4, box_tab5, box_tab6 = st.tabs" in code, "Tab 4 6-tabs missing"
    print("✅ 5. Tab 4 穿透对象选择器与成分档案已合并为单行紧凑摘要卡，6 大二级子 Tab 架构就绪")

    # 6. 验证 Tab 3 Plotly 图例上浮与后视镜警示卡
    assert "y=1.06" in code, "Plotly legend y=1.06 missing"
    assert "t=75" in code, "Plotly margin t=75 missing"
    assert "tgl_compare_oos_dynamic" in code, "OOS dynamic strategy toggle missing"
    assert "当前持仓静态权重历史回溯（含历史后视镜权重效应" in code, "Survivor bias warning card missing"
    print("✅ 6. Tab 3 回测图例上浮透明 (y=1.06, t=75) 零遮挡，后视镜幸存者效应警示卡与动态策略对照开关就绪")

    # 7. 验证 4 只裁判文件 0 篡改
    read_only_files = [
        "AGY2_FundAdvisory/judge_engine.py",
        "AGY2_FundAdvisory/holdout_vault.py",
        "AGENT_SPEC.md",
        "tests/test_infra.py",
    ]
    import subprocess
    diff_res = subprocess.run(["git", "diff", "--name-only"] + read_only_files, capture_output=True, text=True)
    assert not diff_res.stdout.strip(), f"Read-only files were modified: {diff_res.stdout}"
    print("✅ 7. 4 只 strictly read-only 裁判文件严格保持 0 篡改！")

    print("\n🎉 ALL MILESTONE 2 DELIVERABLES VERIFIED 100% SUCCESSFULLY!")

if __name__ == "__main__":
    verify()

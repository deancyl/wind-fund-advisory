import sys
from pathlib import Path
import pytest
import pandas as pd
import numpy as np
from streamlit.testing.v1 import AppTest

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
AGY_PATH = WORKSPACE_ROOT / "AGY2_FundAdvisory"
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))
if str(AGY_PATH) not in sys.path:
    sys.path.insert(0, str(AGY_PATH))

from AGY2_FundAdvisory.app_gui import project_responsive_table_4col

EXPECTED_COLS = ["基金名称与代码", "当前或建议金额", "累计盈亏或目标占比", "今日明确操作指令"]

BOUNDARY_INPUTS = [
    ("empty_df", pd.DataFrame(), 0),
    ("single_col", pd.DataFrame([{"基金代码": "000001"}]), 1),
    ("extra_cols", pd.DataFrame([{"基金代码": "000001", "额外列1": 123, "额外列2": "foo", "额外列3": [1, 2]}]), 1),
    ("all_none", pd.DataFrame([{"基金代码": None, "基金名称": None, "精确买入金额(元)": None, "当前市值(元)": None, "建议调仓金额(元)": None}]), 1),
    ("empty_str", pd.DataFrame([{"基金代码": "", "基金名称": "", "精确买入金额(元)": "", "当前市值(元)": "", "建议调仓金额(元)": ""}]), 1),
    ("placeholder_dash", pd.DataFrame([{"基金代码": "-", "基金名称": "-", "精确买入金额(元)": "-", "当前市值(元)": "-", "建议调仓金额(元)": "-"}]), 1),
    ("nan_row", pd.DataFrame([{"基金代码": np.nan, "基金名称": np.nan, "精确买入金额(元)": np.nan, "当前市值(元)": np.nan, "建议调仓金额(元)": np.nan}]), 1),
    ("text_in_numeric", pd.DataFrame([{"基金代码": "000001", "精确买入金额(元)": "invalid_text", "当前市值(元)": "abc", "建议调仓金额(元)": "xyz"}]), 1),
    ("dict_values", pd.DataFrame([{"基金代码": "000001", "精确买入金额(元)": {"nested": 123}, "当前市值(元)": {"k": "v"}, "建议调仓金额(元)": {}}]), 1),
    ("empty_list", pd.DataFrame([{"基金代码": "000001", "精确买入金额(元)": [], "当前市值(元)": [], "建议调仓金额(元)": []}]), 1),
    ("multi_element_list", pd.DataFrame([{"基金代码": "000001", "精确买入金额(元)": [1000, 2000], "当前市值(元)": [100, 200], "建议调仓金额(元)": [50, 60]}]), 1),
    ("numpy_arrays", pd.DataFrame([{"基金代码": "000001", "精确买入金额(元)": np.array([1, 2]), "当前市值(元)": np.array([]), "建议调仓金额(元)": np.array([3.0, 4.0])}]), 1),
]

TABLE_TYPES = ["creation", "holdings", "rebalance"]


@pytest.mark.parametrize("case_name,df_in,expected_rows", BOUNDARY_INPUTS)
@pytest.mark.parametrize("table_type", TABLE_TYPES)
def test_project_responsive_table_4col_boundary_cases(case_name, df_in, expected_rows, table_type):
    """
    Empirical boundary probe: verify all 36 boundary test cases execute with 0 exceptions,
    always return a DataFrame with exact 4 columns and expected row count.
    """
    res = project_responsive_table_4col(df_in, table_type=table_type)
    assert isinstance(res, pd.DataFrame), f"Expected DataFrame, got {type(res)}"
    assert list(res.columns) == EXPECTED_COLS, f"Columns mismatch: {list(res.columns)} vs {EXPECTED_COLS}"
    assert len(res) == expected_rows, f"Row count mismatch: {len(res)} vs {expected_rows}"


def test_streamlit_app_full_render():
    app_path = (Path(__file__).parent.parent / "AGY2_FundAdvisory" / "app_gui.py").resolve()
    at = AppTest.from_file(str(app_path), default_timeout=60)
    at.run()
    assert not at.exception, f"AppTest raised an exception: {at.exception}"
    assert len(at.error) == 0, f"Streamlit 运行时包含错误条目: {[e.value for e in at.error]}"
    print("Streamlit AppTest passed with 0 exceptions and 0 errors!")

# -*- coding: utf-8 -*-
import sys
from pathlib import Path

workspace = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(workspace))
sys.path.insert(0, str(workspace / "AGY2_FundAdvisory"))

from AGY2_FundAdvisory.strategy_bridge import StrategyBridge
from AGY2_FundAdvisory.app_gui import render_historical_inflection_ruler_html, _clean_html

ruler = StrategyBridge.get_historical_inflection_ruler(current_erp=70.0, current_bias=-2.0)
raw_html = render_historical_inflection_ruler_html(ruler)
print("raw_html lines starting with 4+ spaces:", any(line.startswith("    ") for line in raw_html.splitlines()))
cleaned = _clean_html(raw_html)
print("cleaned lines starting with 4+ spaces:", any(line.startswith("    ") for line in cleaned.splitlines()))

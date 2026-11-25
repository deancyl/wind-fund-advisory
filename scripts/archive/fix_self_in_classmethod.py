# -*- coding: utf-8 -*-
from pathlib import Path

p = Path("AGY2_FundAdvisory/portfolio_manager.py")
content = p.read_text(encoding="utf-8")

old_snippet = '''        if not name and code:
            if hasattr(self, "holdings") and code in self.holdings:
                name = self.holdings[code].fund_name
            elif code in CORE_STRATEGY_POOL:'''

new_snippet = '''        if not name and code:
            if code in CORE_STRATEGY_POOL:'''

if old_snippet in content:
    content = content.replace(old_snippet, new_snippet, 1)
    p.write_text(content, encoding="utf-8")
    print("Fixed self in classmethod!")
else:
    print("Target not found!")

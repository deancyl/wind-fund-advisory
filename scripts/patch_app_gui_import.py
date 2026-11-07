# -*- coding: utf-8 -*-
with open("AGY2_FundAdvisory/app_gui.py", "r", encoding="utf-8") as f:
    content = f.read()

target = "from data_loader import (\n    fetch_market_turnover_and_sentiment,"
replacement = "from data_loader import (\n    DataLoader,\n    fetch_realtime_market_news_and_catalysts,\n    fetch_market_turnover_and_sentiment,"

if target in content:
    new_content = content.replace(target, replacement, 1)
    with open("AGY2_FundAdvisory/app_gui.py", "w", encoding="utf-8") as f:
        f.write(new_content)
    print("Successfully patched app_gui.py with CRLF/LF normalization")
else:
    # try CRLF
    target_crlf = "from data_loader import (\r\n    fetch_market_turnover_and_sentiment,"
    replacement_crlf = "from data_loader import (\r\n    DataLoader,\r\n    fetch_realtime_market_news_and_catalysts,\r\n    fetch_market_turnover_and_sentiment,"
    if target_crlf in content:
        new_content = content.replace(target_crlf, replacement_crlf, 1)
        with open("AGY2_FundAdvisory/app_gui.py", "w", encoding="utf-8") as f:
            f.write(new_content)
        print("Successfully patched app_gui.py with CRLF")
    else:
        print("Target not found!")

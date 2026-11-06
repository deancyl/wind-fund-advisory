import sys
from pathlib import Path
ws = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(ws / "AGY2_FundAdvisory"))
sys.path.insert(0, str(ws))

from portfolio_manager import fetch_realtime_fund_quote

for fcode in ["005561", "011613", "002351", "000216", "510300", "110020"]:
    q = fetch_realtime_fund_quote(fcode)
    print(f"Fund {fcode}: name={q.name}, dwjz={q.dwjz}, gsz={q.gsz}, gszzl={q.gszzl}%, gztime={q.gztime}, corrected={q.valuation_corrected}")

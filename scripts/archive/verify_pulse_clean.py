import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from AGY2_FundAdvisory.strategy_bridge import StrategyBridge
from AGY2_FundAdvisory.app_gui import render_historical_inflection_ruler_html, _clean_html

ruler = StrategyBridge.get_historical_inflection_ruler(current_erp=4.5, current_bias=-2.1)
ruler_bar_html = render_historical_inflection_ruler_html(ruler)

pulse_card_html = f"""
<div class="decision-card" style="padding: 8px 12px; margin-bottom: 10px; border-left: 3px solid var(--accent-primary); background: var(--bg-surface);">
    <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 2px;">
        <span style="font-size: 11px; font-weight: 700; color: var(--accent-primary);">📢 今日市场脉搏晨报</span>
        <span style="font-size: 10px; color: var(--text-secondary);">全景量化串联 ｜ 历史拐点并列对照</span>
    </div>
    <div style="font-size: 11px; color: var(--text-primary); line-height: 1.4; margin-bottom: 4px;">
        全景量化串联
    </div>
    {ruler_bar_html}
</div>
"""

cleaned_pulse = _clean_html(pulse_card_html)
lines_with_4 = [l for l in cleaned_pulse.splitlines() if l.startswith('    ')]
print('Cleaned pulse lines with 4+ spaces:', len(lines_with_4))
assert len(lines_with_4) == 0
print('✅ Cleaned pulse card is 100% immune to CommonMark code block escape!')

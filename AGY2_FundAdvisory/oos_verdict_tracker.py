# -*- coding: utf-8 -*-
"""兼容薄代理：唯一实现位于 forward_audit_logger.py。"""
from forward_audit_logger import (
    OOSVerdictTracker,
    append_daily_decision_snapshot,
    load_decision_audit_log,
    record_daily_verdict_if_needed,
    evaluate_forward_performance,
)

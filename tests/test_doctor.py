"""
终端诊断与探针测试
"""

from src.core.terminal_probe import TerminalProbe
from src.core.session_manager import SessionManager
from src.config import WIND_CONFIG


def test_terminal_probe():
    probe = TerminalProbe(WIND_CONFIG)
    status = probe.detect_status()
    assert isinstance(status.is_running, bool)
    assert status.total_memory_mb >= 0.0


def test_session_manager():
    mgr = SessionManager(WIND_CONFIG)
    sid = mgr.get_session_id()
    # 至少能成功读取配置中的 sessionid 或 None
    assert sid is None or len(sid) > 20

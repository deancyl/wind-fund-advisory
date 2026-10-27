"""
WindPy 32位桥接子进程模块：通过进程间通信实现 64位现代 Python 与 32位 Wind 原生动态库互通。
"""

from .windpy_client import WindPyBridgeClient

__all__ = ["WindPyBridgeClient"]

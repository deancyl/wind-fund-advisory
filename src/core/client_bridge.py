"""
CEF 原生协议桥接模块：逆向解析与模拟 Wind CEF Web 视图与 C++ 宿主 (WMain/WBox)
之间的 window.external.ClientFunc(JSON) 交互协议。
"""

import json
from typing import Dict, Any, Optional

from ..config import WIND_CONFIG
from .session_manager import SessionManager


class WindClientBridge:
    """Wind 宿主-前端交互协议模拟器与解析器"""

    def __init__(self, config=WIND_CONFIG, session_mgr: Optional[SessionManager] = None):
        self.config = config
        self.session_mgr = session_mgr or SessionManager(config)

    def dispatch_command(self, cmd_payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        模拟原生 window.external.ClientFunc(cmd) 指令响应机制
        """
        func = cmd_payload.get("func")
        name = cmd_payload.get("name")

        if func == "querydata":
            if name == "sessionid":
                sid = self.session_mgr.get_session_id() or ""
                return {"func": "querydata", "name": "sessionid", "value": sid, "result": "1" if sid else "0"}
            elif name == "version2":
                return {"func": "querydata", "name": "version2", "result": "141337472"}
            elif name == "apptype":
                return {"func": "querydata", "name": "apptype", "apptype": "WFC", "result": "1"}
            elif name == "syscfg":
                return {
                    "func": "querydata",
                    "name": "syscfg",
                    "result": json.dumps({"language": "zh_CN", "theme": "black"})
                }

        elif func == "isauthorized":
            fid = cmd_payload.get("functionid")
            # 常见投顾权限：WFC_APL_FO, WFC_CRM, WFC_PORTFOLIO
            return {"func": "isauthorized", "functionid": fid, "result": "0"}

        elif func == "writeauditlog":
            return {"func": "writeauditlog", "result": "0"}

        return {"func": func or "unknown", "result": "-1", "error": "Unhandled command"}

    def format_bridge_call(self, cmd_dict: Dict[str, Any]) -> str:
        """生成前端直接调用的 JavaScript 注入代码"""
        return f"window.external.ClientFunc('{json.dumps(cmd_dict)}')"

"""
WindPy 32位 Worker 执行器：运行于 32位 Python 宿主内，
直接加载 C:\\Wind\\Wind.NET.Client\\WFC\\bin\\WindPy.dll，
通过 stdin/stdout 接收 JSON 请求并返回序列化数据。
"""

import sys
import json
import os

# 动态添加 Wind 原生 Python 接口路径
wind_bin = r"C:\Wind\Wind.NET.Client\WFC\bin"
if os.path.exists(wind_bin) and wind_bin not in sys.path:
    sys.path.insert(0, wind_bin)

try:
    from WindPy import w
    WINDPY_AVAILABLE = True
except Exception as e:
    WINDPY_AVAILABLE = False
    WINDPY_ERROR = str(e)


def handle_request(req: dict) -> dict:
    action = req.get("action")
    if not WINDPY_AVAILABLE:
        return {"status": "error", "message": f"WindPy not loadable: {WINDPY_ERROR}"}

    try:
        if action == "start":
            res = w.start(waitTime=int(req.get("waitTime", 60)))
            return {"status": "ok", "errorCode": res.ErrorCode}

        elif action == "isconnected":
            connected = w.isconnected()
            return {"status": "ok", "connected": connected}

        elif action == "wsd":
            codes = req.get("codes")
            fields = req.get("fields")
            beginTime = req.get("beginTime")
            endTime = req.get("endTime")
            options = req.get("options", "")
            res = w.wsd(codes, fields, beginTime, endTime, options)
            return {
                "status": "ok",
                "errorCode": res.ErrorCode,
                "codes": res.Codes,
                "fields": res.Fields,
                "times": [str(t) for t in res.Times] if res.Times else [],
                "data": res.Data
            }

        elif action == "wss":
            codes = req.get("codes")
            fields = req.get("fields")
            options = req.get("options", "")
            res = w.wss(codes, fields, options)
            return {
                "status": "ok",
                "errorCode": res.ErrorCode,
                "codes": res.Codes,
                "fields": res.Fields,
                "data": res.Data
            }

        return {"status": "error", "message": f"Unknown action: {action}"}
    except Exception as ex:
        return {"status": "error", "message": str(ex)}


def main():
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
            resp = handle_request(req)
            sys.stdout.write(json.dumps(resp, ensure_ascii=False) + "\n")
            sys.stdout.flush()
        except Exception as e:
            sys.stdout.write(json.dumps({"status": "error", "message": str(e)}) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()

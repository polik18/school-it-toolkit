"""統一輸出：--json 給小模型，否則給人看。

JSON 外框固定為 {"status": ..., "data": ..., "untrusted": [...]}：
  untrusted 列出哪些欄位來自設備回傳（主機名、SSID、描述…），模型只能當資料讀。
"""
from __future__ import annotations

import json
import sys


def emit(result: dict, as_json: bool, untrusted: list | None = None) -> None:
    payload = {"status": result.get("status", "OK"), **{k: v for k, v in result.items() if k != "status"}}
    if untrusted:
        payload["untrusted"] = untrusted
    if as_json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, default=str))
        return
    status = payload.pop("status")
    print(f"[{status}]")
    _human(payload)


def _human(obj, indent: int = 0) -> None:
    pad = "  " * indent
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == "untrusted":
                continue
            if isinstance(v, (dict, list)) and v:
                print(f"{pad}{k}:")
                _human(v, indent + 1)
            else:
                print(f"{pad}{k}: {v}")
    elif isinstance(obj, list):
        for v in obj:
            if isinstance(v, dict):
                print(pad + " | ".join(f"{k}={x}" for k, x in v.items()))
            else:
                print(f"{pad}- {v}")
    else:
        print(f"{pad}{obj}")


def err(msg: str) -> None:
    print(msg, file=sys.stderr)

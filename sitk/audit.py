"""稽核日誌：所有 --apply 動作寫入 append-only JSONL（誰、何時、目標、動作、結果）。"""
from __future__ import annotations

import getpass
import json
import os
import time
from pathlib import Path

from .site import Site

SENSITIVE_KEYS = {"password", "secret", "token", "psk", "key", "community", "secretkey"}


def _scrub(obj):
    if isinstance(obj, dict):
        return {k: ("***" if k.lower() in SENSITIVE_KEYS else _scrub(v)) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_scrub(v) for v in obj]
    return obj


def record(site: Site, domain: str, action: str, target: str, result: dict, apply: bool) -> None:
    path = site.resolve(site.section("audit").get("log", "logs/audit.jsonl"))
    path.parent.mkdir(parents=True, exist_ok=True)
    entry = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "user": getpass.getuser(), "domain": domain,
             "action": action, "target": target, "apply": apply, "result": _scrub(result)}
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass

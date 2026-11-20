"""批次長任務狀態機（JSON 落地、可中斷恢復）。

項目狀態：pending → running → done | failed
小模型只用：init / next / complete / fail / status，不自行推測進度。
"""
from __future__ import annotations

import json
import os
import tempfile
import time
from pathlib import Path

from .errors import FailClosed, SitkError

STATES = ("pending", "running", "done", "failed")


class StateStore:
    def __init__(self, directory: Path, run_id: str):
        if not run_id or "/" in run_id or run_id.startswith("."):
            raise FailClosed(f"run_id 不合法：{run_id!r}")
        self.path = Path(directory) / f"{run_id}.json"
        self.run_id = run_id

    # ---- 原子寫入 ----
    def _save(self, data: dict) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        data["updated"] = time.strftime("%Y-%m-%dT%H:%M:%S")
        fd, tmp = tempfile.mkstemp(dir=self.path.parent, prefix=".tmp-", suffix=".json")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, self.path)

    def load(self) -> dict:
        if not self.path.exists():
            raise SitkError(f"找不到批次任務 {self.run_id}", run_id=self.run_id)
        return json.loads(self.path.read_text(encoding="utf-8"))

    # ---- 操作 ----
    def init(self, workflow: str, items: list[str], overwrite: bool = False) -> dict:
        if not items:
            raise FailClosed("項目清單為空，拒絕建立批次任務")
        if len(set(items)) != len(items):
            raise FailClosed("項目清單有重複名稱")
        if self.path.exists() and not overwrite:
            raise FailClosed(f"批次任務 {self.run_id} 已存在；續跑請用 next，重建請加 --overwrite")
        data = {"run_id": self.run_id, "workflow": workflow, "created": time.strftime("%Y-%m-%dT%H:%M:%S"),
                "items": {i: {"state": "pending", "attempts": 0, "error": None, "verified": False} for i in items}}
        self._save(data)
        return self.summary(data)

    def next(self) -> dict:
        data = self.load()
        for name, it in data["items"].items():
            if it["state"] == "running":
                return {"status": "RESUME", "item": name, "attempts": it["attempts"],
                        "hint": "上次中斷在此項目，先確認現況再 complete 或 fail"}
        for name, it in data["items"].items():
            if it["state"] == "pending":
                it["state"] = "running"
                it["attempts"] += 1
                self._save(data)
                return {"status": "NEXT", "item": name, "attempts": it["attempts"]}
        return {"status": "ALL_DONE", **self.summary(data)}

    def _mark(self, item: str, state: str, error: str | None = None, verified: bool = False) -> dict:
        data = self.load()
        if item not in data["items"]:
            raise FailClosed(f"{item} 不在此批次任務中")
        it = data["items"][item]
        it.update(state=state, error=error, verified=verified)
        self._save(data)
        return {"status": "OK", "item": item, "state": state, **self.summary(data)}

    def complete(self, item: str, verified: bool) -> dict:
        if not verified:
            raise FailClosed("complete 需附 --verified：必須有實測回讀證據才算完成")
        return self._mark(item, "done", verified=True)

    def fail(self, item: str, error: str) -> dict:
        return self._mark(item, "failed", error=error or "unspecified")

    def retry_failed(self) -> dict:
        data = self.load()
        n = 0
        for it in data["items"].values():
            if it["state"] == "failed":
                it["state"], n = "pending", n + 1
        self._save(data)
        return {"status": "OK", "requeued": n, **self.summary(data)}

    def summary(self, data: dict | None = None) -> dict:
        data = data or self.load()
        counts = {s: 0 for s in STATES}
        for it in data["items"].values():
            counts[it["state"]] += 1
        return {"run_id": data["run_id"], "workflow": data["workflow"], "total": len(data["items"]),
                **counts, "complete": counts["done"] == len(data["items"])}

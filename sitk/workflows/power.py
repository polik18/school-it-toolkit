"""計畫性停電關機與復電驗收（依賴順序分階段，狀態落地 JSON）。

site.toml 範例：
  [[power.recover]]
  name = "核心網路"
  match = { kind = "switch", tag = "core" }
  check = "ping"                # ping 或 tcp:<port>

  [[power.recover]]
  name = "教室電腦喚醒"
  match = { kind = "endpoint" }
  action = "wake"               # 需 --apply
  check = "tcp:22"

  [[power.shutdown]]
  name = "儲存設備"
  manual = "請由管理介面關閉 NAS，完成後執行 sitk power done <階段序號>"

順序就是依賴順序（先網路、再儲存、再伺服器、最後端點）；前一階段未通過，後面不會執行。
"""
from __future__ import annotations

import socket
import subprocess
import time

from ..errors import FailClosed
from ..guard import require_apply, require_in_scope
from ..state import StateStore


def _match(registry, m: dict):
    devs = [d for d in registry.devices if d.status == "ACTIVE"]
    if m.get("kind"):
        devs = [d for d in devs if d.kind == m["kind"]]
    if m.get("tag"):
        devs = [d for d in devs if m["tag"] in d.tags]
    if m.get("space"):
        devs = [d for d in devs if d.space == m["space"]]
    return devs


def _check(site, dev, check: str) -> bool:
    require_in_scope(site, dev.ip)
    if check == "ping":
        return subprocess.run(["ping", "-c", "1", "-W", "1", dev.ip], capture_output=True).returncode == 0
    if check.startswith("tcp:"):
        try:
            with socket.create_connection((dev.ip, int(check[4:])), timeout=2):
                return True
        except OSError:
            return False
    raise FailClosed(f"不支援的檢查方式：{check}")


class PowerWorkflow:
    def __init__(self, site, registry, mode: str, adapters_loader=None):
        if mode not in ("recover", "shutdown"):
            raise FailClosed("mode 只能是 recover 或 shutdown")
        self.site, self.registry, self.mode = site, registry, mode
        self.phases = site.section("power").get(mode, [])
        if not self.phases:
            raise FailClosed(f"site.toml 未定義 [[power.{mode}]] 階段")
        self.load_adapter = adapters_loader
        run_id = f"power-{mode}-{time.strftime('%Y%m%d')}"
        self.store = StateStore(site.resolve(site.section("state").get("dir", "state")), run_id)

    def plan(self) -> dict:
        rows = []
        for i, ph in enumerate(self.phases, 1):
            devs = _match(self.registry, ph.get("match", {})) if ph.get("match") else []
            rows.append({"phase": i, "name": ph["name"], "devices": len(devs), "check": ph.get("check"),
                         "action": ph.get("action"), "manual": ph.get("manual")})
        return {"status": "OK", "mode": self.mode, "phases": rows}

    def _ensure_store(self):
        try:
            return self.store.load()
        except Exception:
            self.store.init(f"power-{self.mode}", [f"{i:02d}-{p['name']}" for i, p in enumerate(self.phases, 1)])
            return self.store.load()

    def run_phase(self, n: int, apply: bool) -> dict:
        data = self._ensure_store()
        keys = list(data["items"])
        if not 1 <= n <= len(keys):
            raise FailClosed(f"階段 {n} 不存在（共 {len(keys)} 階段）")
        for prev in keys[:n - 1]:
            if data["items"][prev]["state"] != "done":
                raise FailClosed(f"前一階段 {prev} 尚未完成，依賴順序不可跳過", blocking=prev)
        ph = self.phases[n - 1]
        key = keys[n - 1]
        if ph.get("manual"):
            return {"status": "MANUAL", "phase": key, "instruction": ph["manual"],
                    "next": f"完成後執行 sitk power done {n} --mode {self.mode}"}
        devs = _match(self.registry, ph.get("match", {}))
        if ph.get("action") == "wake":
            require_apply(apply, {"phase": key, "action": "wake", "devices": [d.name for d in devs]})
            ep = self.load_adapter("endpoint")
            for d in devs:
                ep.wake(d, apply=True)
            time.sleep(int(ph.get("wait_seconds", 60)))
        results = {d.name: _check(self.site, d, ph.get("check", "ping")) for d in devs}
        failed = [k for k, ok in results.items() if not ok]
        if failed:
            self.store.fail(key, f"{len(failed)} 台未通過檢查")
            return {"status": "PHASE_FAILED", "phase": key, "failed": failed, "passed": len(devs) - len(failed)}
        self.store.complete(key, verified=True)
        return {"status": "OK", "phase": key, "passed": len(devs)}

    def mark_done(self, n: int) -> dict:
        data = self._ensure_store()
        key = list(data["items"])[n - 1]
        if not self.phases[n - 1].get("manual"):
            raise FailClosed("只有人工階段可以手動標記完成；自動階段必須通過實測檢查")
        return self.store.complete(key, verified=True)

    def status(self) -> dict:
        self._ensure_store()
        return {"status": "OK", **self.store.summary()}

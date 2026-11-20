"""Linux iptables 防火牆，附「死人開關」安全套用。

site.toml：
  [adapters.firewall]
  driver = "linux_iptables"
  device = "fw-core-01"                 # 台帳中 kind=firewall 的設備
  user = "root"
  key = "~/.ssh/sitk_firewall"
  rules_script = "/etc/firewall/iptables.sh"   # 套用規則的腳本（由學校自行維護）
  lint_command = "sh -n /etc/firewall/iptables.sh"
  persist_command = "netfilter-persistent save" # 依發行版調整持久化指令

套用流程（apply_rules）：
  1. lint 語法預檢
  2. 遠端備份現行規則，啟動 N 秒自動回滾計時器
  3. 執行 rules_script；失敗立即回滾
  4. 重新建立一條新 SSH 連線當探針；成功才解除計時器
  5. 探針失敗 → 不做任何事，計時器到期自動回滾（管理通道斷了也能自救）
  持久化（persist_command）不在本流程內自動執行，需另行確認。
"""
from __future__ import annotations

import os

from ..errors import AdapterError, FailClosed
from ..guard import require_active, require_apply, require_in_scope
from ..transport import quote, ssh_run
from .base import FirewallAdapter

GUARD_DIR = "/run/sitk_fw_guard"


class LinuxIptablesFirewall(FirewallAdapter):
    def _dev(self):
        dev = self.registry.find_device(self.cfg.get("device", ""), kind="firewall")
        require_active(dev)
        require_in_scope(self.site, dev.ip)
        return dev

    def _ssh(self, command: str, timeout: int = 20) -> str:
        dev = self._dev()
        key = self.cfg.get("key")
        return ssh_run(dev.ip, self.cfg.get("user", "root"), command,
                       key=os.path.expanduser(key) if key else None, timeout=timeout)

    def status(self):
        out = self._ssh("iptables -S | wc -l; ip6tables -S | wc -l; iptables -t nat -S | wc -l")
        v4, v6, nat = (out.split() + ["?", "?", "?"])[:3]
        return {"status": "OK", "ipv4_rules": v4, "ipv6_rules": v6, "nat_rules": nat}

    def lint(self):
        cmd = self.cfg.get("lint_command")
        if not cmd:
            raise FailClosed("未設定 lint_command，拒絕在沒有語法預檢的情況下套用規則")
        try:
            self._ssh(cmd)
        except AdapterError as e:
            return {"status": "LINT_FAILED", "detail": e.details}
        return {"status": "OK", "errors": 0}

    def apply_rules(self, apply, timeout):
        script = self.cfg.get("rules_script")
        if not script:
            raise FailClosed("未設定 rules_script")
        if not 15 <= timeout <= 600:
            raise FailClosed("死人開關逾時須介於 15～600 秒")
        plan = {"action": "apply_rules", "script": script, "deadman_timeout": timeout,
                "steps": ["lint", "backup+arm", "run", "probe", "disarm"],
                "persist": "不自動持久化；確認無誤後另行執行 persist"}
        require_apply(apply, plan)
        lint = self.lint()
        if lint["status"] != "OK":
            return {"status": "FAIL_CLOSED", "stage": "lint", **lint}
        g = GUARD_DIR
        arm = (f"mkdir -p {g} && iptables-save > {g}/v4.bak && ip6tables-save > {g}/v6.bak && "
               f"touch {g}/active && "
               f"( sleep {int(timeout)}; if [ -f {g}/active ]; then iptables-restore < {g}/v4.bak; "
               f"ip6tables-restore < {g}/v6.bak; rm -f {g}/active; fi ) >/dev/null 2>&1 & echo $! > {g}/pid")
        self._ssh(arm)
        rollback = f"iptables-restore < {g}/v4.bak; ip6tables-restore < {g}/v6.bak; rm -f {g}/active"
        try:
            self._ssh(f"sh {quote(script)}", timeout=60)
        except AdapterError as e:
            try:
                self._ssh(rollback)
            except AdapterError:
                pass  # 連線若已斷，計時器仍會自動回滾
            return {"status": "ROLLED_BACK", "stage": "run", "detail": e.details}
        try:
            probe = self._ssh("echo SITK_PROBE_OK", timeout=10)
        except AdapterError:
            probe = ""
        if "SITK_PROBE_OK" not in probe:
            return {"status": "ROLLBACK_PENDING", "stage": "probe",
                    "detail": f"管理通道探針失敗，{timeout} 秒內將自動回滾，請勿再操作"}
        self._ssh(f"rm -f {g}/active; kill $(cat {g}/pid) 2>/dev/null; rm -f {g}/pid")
        return {"status": "OK", "applied": True, "probe": "PROBE_SUCCESS", "persisted": False,
                "next": "確認服務正常後，執行 sitk firewall persist --apply --confirm <設備名稱>"}

    def persist(self, apply):
        cmd = self.cfg.get("persist_command")
        if not cmd:
            raise FailClosed("未設定 persist_command")
        require_apply(apply, {"action": "persist", "command": cmd})
        self._ssh(cmd, timeout=60)
        return {"status": "OK", "persisted": True}

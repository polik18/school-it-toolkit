"""macOS 端點（SSH 金鑰 + Wake-on-LAN）。教學時段不打擾前台：只做背景唯讀查詢。

site.toml：
  [adapters.endpoint]
  driver = "macos"
  user = "itadmin"                       # 各校統一管理帳號（v1 的 ADMIN_USER）
  key = "~/.ssh/sitk_admin"
  wol_broadcast = "192.0.2.255"          # 跨 VLAN 喚醒時填目標網段廣播位址

Windows / ChromeOS 請依 base.EndpointAdapter 另建轉接器。
"""
from __future__ import annotations

import os
import re
import socket
import subprocess

from ..errors import AdapterError, FailClosed
from ..guard import require_apply, require_in_scope
from ..transport import ssh_run
from .base import EndpointAdapter

FACTS_CMD = ("sw_vers -productVersion; scutil --get ComputerName; "
             "df -g / | awk 'NR==2{print $4}'; stat -f %Su /dev/console")


class MacOSEndpoint(EndpointAdapter):
    def _ssh(self, dev, cmd: str, timeout: int = 12) -> str:
        require_in_scope(self.site, dev.ip)
        key = self.cfg.get("key")
        return ssh_run(dev.ip, self.cfg.get("user", "itadmin"), cmd,
                       key=os.path.expanduser(key) if key else None, timeout=timeout)

    def status(self, dev):
        require_in_scope(self.site, dev.ip)
        ping = subprocess.run(["ping", "-c", "1", "-W", "1000" if os.uname().sysname == "Darwin" else "1", dev.ip],
                              capture_output=True).returncode == 0
        try:
            self._ssh(dev, "true", timeout=8)
            ssh = True
        except AdapterError:
            ssh = False
        return {"status": "OK", "device": dev.name, "ping": ping, "ssh": ssh, "space": dev.space}

    def facts(self, dev):
        out = self._ssh(dev, FACTS_CMD).splitlines() + ["", "", "", ""]
        return {"status": "OK", "device": dev.name, "os": out[0], "hostname": out[1],
                "disk_free_gb": out[2], "console_user": out[3] or None,
                "note": "console_user 有值代表有人正在使用，請勿進行會打擾前台的操作"}

    def wake(self, dev, apply):
        if not re.fullmatch(r"[0-9a-f]{2}(:[0-9a-f]{2}){5}", dev.mac or ""):
            raise FailClosed(f"{dev.name} 台帳中沒有合法 MAC，無法喚醒")
        bcast = self.cfg.get("wol_broadcast")
        if not bcast:
            raise FailClosed("未設定 wol_broadcast")
        require_in_scope(self.site, bcast)
        require_apply(apply, {"action": "wake", "device": dev.name, "mac": dev.mac, "broadcast": bcast})
        payload = b"\xff" * 6 + bytes.fromhex(dev.mac.replace(":", "")) * 16
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            for _ in range(3):
                s.sendto(payload, (bcast, 9))
        return {"status": "OK", "device": dev.name, "magic_packet": "sent",
                "verify": f"約 60 秒後執行 sitk endpoint status {dev.name}"}

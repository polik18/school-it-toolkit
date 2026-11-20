"""BIND9 + ISC DHCP（經 SSH 唯讀查詢區域檔與 dhcpd.conf；可選擇在 Docker 容器內）。

site.toml：
  [adapters.dnsdhcp]
  driver = "bind9_isc"
  device = "srv-dns-01"                 # 台帳中 kind=dnsdhcp 的主機
  user = "itadmin"
  key = "~/.ssh/sitk_server"
  sudo = true
  dns_container = ""                    # 若 BIND 跑在容器內，填容器名稱（例如 bind9）
  dhcp_container = ""
  zone_dir = "/etc/bind"
  dhcpd_conf = "/etc/dhcp/dhcpd.conf"
  leases = "/var/lib/dhcp/dhcpd.leases"

搜尋字串只允許安全字元，並以 grep -F（固定字串）比對，避免注入。
"""
from __future__ import annotations

import os
import re

from ..errors import FailClosed
from ..guard import require_active, require_apply, require_in_scope
from ..transport import quote, ssh_run
from .base import DnsDhcpAdapter

SAFE_KEYWORD = re.compile(r"^[A-Za-z0-9.:_\-]{2,64}$")


class Bind9IscDnsDhcp(DnsDhcpAdapter):
    def _ssh(self, command: str, container: str = "", timeout: int = 20) -> str:
        dev = self.registry.find_device(self.cfg.get("device", ""), kind="dnsdhcp")
        require_active(dev)
        require_in_scope(self.site, dev.ip)
        if container:
            command = f"docker exec {quote(container)} sh -c {quote(command)}"
        if self.cfg.get("sudo"):
            command = f"sudo -n {command}"
        key = self.cfg.get("key")
        return ssh_run(dev.ip, self.cfg.get("user", "itadmin"), command,
                       key=os.path.expanduser(key) if key else None, timeout=timeout)

    @staticmethod
    def _kw(keyword: str) -> str:
        if not SAFE_KEYWORD.match(keyword or ""):
            raise FailClosed("搜尋字串只允許英數與 . : _ -（2～64 字元）")
        return keyword

    def dns_search(self, keyword):
        kw = self._kw(keyword)
        out = self._ssh(f"grep -rIn -F -i -- {quote(kw)} {quote(self.cfg.get('zone_dir', '/etc/bind'))} | head -50",
                        container=self.cfg.get("dns_container", ""))
        return {"status": "OK", "keyword": kw, "records": [{"record": ln} for ln in out.splitlines()]}

    def dhcp_search(self, keyword):
        kw = self._kw(keyword)
        files = f"{quote(self.cfg.get('dhcpd_conf', '/etc/dhcp/dhcpd.conf'))} {quote(self.cfg.get('leases', '/var/lib/dhcp/dhcpd.leases'))}"
        out = self._ssh(f"grep -In -F -i -B2 -A4 -- {quote(kw)} {files} | head -80",
                        container=self.cfg.get("dhcp_container", ""))
        return {"status": "OK", "keyword": kw, "matches": [{"lease": ln} for ln in out.splitlines()]}

    def dns_reload(self, apply):
        require_apply(apply, {"action": "dns_reload", "steps": ["named-checkconf", "rndc reload"]})
        c = self.cfg.get("dns_container", "")
        self._ssh("named-checkconf", container=c)
        out = self._ssh("rndc reload", container=c)
        return {"status": "OK", "reloaded": True, "detail": out.strip()[-200:]}

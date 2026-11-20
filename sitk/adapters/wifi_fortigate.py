"""FortiGate 無線控制器（FortiAP）— REST API。

site.toml：
  [adapters.wifi]
  driver = "fortigate"
  controller = "fw-wifi-01"          # 台帳中 kind=wifi_controller 的設備名稱
  auth = "token"                     # token（建議，REST API 管理員 + 唯讀/最小權限設定檔）或 session
  token_ref = "fortigate_api_token"
  user_ref = "fortigate_user"        # auth = "session" 時使用
  password_ref = "fortigate_password"
  verify_tls = true                  # 自簽憑證可改 false，但建議匯入 CA

重開 AP 為變更動作：需 --apply。
"""
from __future__ import annotations

import urllib.parse

from ..errors import AdapterError
from ..guard import require_active, require_apply, require_in_scope
from ..secrets import get_secret
from ..transport import HttpJson
from .base import WifiAdapter


class FortiGateWifi(WifiAdapter):
    def __init__(self, site, registry, cfg):
        super().__init__(site, registry, cfg)
        self._http = None

    def _client(self) -> HttpJson:
        if self._http:
            return self._http
        ctl = self.registry.find_device(self.cfg.get("controller", ""), kind="wifi_controller")
        require_active(ctl)
        require_in_scope(self.site, ctl.ip)
        http = HttpJson(f"https://{ctl.ip}", verify_tls=self.cfg.get("verify_tls", True))
        if self.cfg.get("auth", "token") == "token":
            http.headers["Authorization"] = "Bearer " + get_secret(self.site, self.cfg.get("token_ref", "fortigate_api_token"))
        else:
            form = urllib.parse.urlencode({
                "username": get_secret(self.site, self.cfg.get("user_ref", "fortigate_user")),
                "secretkey": get_secret(self.site, self.cfg.get("password_ref", "fortigate_password")),
                "ajax": "1"}).encode()
            body = http.request("POST", "/logincheck", form=form, raw=True)
            if not body.startswith("1"):
                raise AdapterError("FortiGate 登入失敗")
            for c in http.jar:
                if "ccsrftoken" in c.name:
                    http.headers["X-CSRFTOKEN"] = c.value.strip('"')
        self._http = http
        return http

    def _get(self, path: str) -> list:
        return self._client().request("GET", f"/api/v2/{path}").get("results", [])

    def aps(self, offline_only=False):
        mon = self._get("monitor/wifi/managed_ap")
        rows = []
        for ap in mon:
            state = ap.get("connection_state", "unknown")
            if offline_only and state.lower() == "connected":
                continue
            wtp = ap.get("wtp_id", "")
            known = next((d for d in self.registry.by_kind("ap", status=None)
                          if wtp and wtp.lower() in {d.name.lower(), *map(str.lower, d.aliases)}), None)
            rows.append({"wtp_id": wtp, "ap_name": ap.get("name") or wtp, "state": state,
                         "clients": ap.get("clients", 0), "ip": ap.get("local_ipv4_addr", ""),
                         "space": known.space if known else None, "in_registry": bool(known)})
        return {"status": "OK", "count": len(rows), "aps": rows,
                "unregistered": [r["wtp_id"] for r in rows if not r["in_registry"]]}

    def clients(self, ap=None):
        rows = self._get("monitor/wifi/client")
        out = []
        for c in rows:
            if ap and c.get("wtp_id", "").lower() not in {ap.name.lower(), *map(str.lower, ap.aliases)}:
                continue
            out.append({"mac": c.get("mac", "").lower(), "ip": c.get("ip", ""), "ssid": c.get("ssid", ""),
                        "wtp_id": c.get("wtp_id", ""), "hostname": c.get("host", c.get("hostname", ""))})
        return {"status": "OK", "ap": ap.name if ap else None, "count": len(out), "clients": out}

    def reboot_ap(self, ap, apply):
        wtp = next((a for a in [ap.name, *ap.aliases] if a), ap.name)
        require_apply(apply, {"action": "reboot_ap", "ap": ap.name, "wtp_id": wtp,
                              "impact": f"{ap.space or '該空間'} 的 Wi-Fi 使用者會短暫斷線"})
        res = self._client().request("POST", "/api/v2/monitor/wifi/managed_ap/restart", body={"wtpname": wtp})
        ok = res.get("status") == "success"
        return {"status": "OK" if ok else "ADAPTER_ERROR", "ap": ap.name, "controller_status": res.get("status")}

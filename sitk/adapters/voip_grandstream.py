"""Grandstream 話機（支援 SHA-256 salt 挑戰-回應登入的 Web API 韌體）。

site.toml：
  [adapters.voip]
  driver = "grandstream"
  user_ref = "phone_user"
  password_ref = "phone_password"   # 請勿沿用出廠預設密碼
  scheme = "http"                   # 話機若已啟用 HTTPS 請改 https

其他廠牌（D-Link、Yealink…）請依 base.VoipAdapter 新增轉接器。
"""
from __future__ import annotations

import hashlib
import urllib.parse

from ..errors import AdapterError
from ..guard import require_active, require_apply, require_in_scope
from ..secrets import get_secret
from ..transport import HttpJson
from .base import VoipAdapter


class GrandstreamVoip(VoipAdapter):
    def _login(self, dev):
        require_active(dev)
        require_in_scope(self.site, dev.ip)
        http = HttpJson(f"{self.cfg.get('scheme', 'http')}://{dev.ip}", verify_tls=self.cfg.get("verify_tls", True),
                        timeout=6)
        http.headers.update({"X-Requested-With": "XMLHttpRequest", "Referer": f"http://{dev.ip}/"})
        user = get_secret(self.site, self.cfg.get("user_ref", "phone_user"))
        pw = get_secret(self.site, self.cfg.get("password_ref", "phone_password"))
        acc = http.request("POST", "/cgi-bin/access",
                           form=urllib.parse.urlencode({"access": hashlib.sha256(user.encode()).hexdigest()}).encode())
        salt = acc.get("body", "")
        digest = hashlib.sha256((pw + salt).encode()).hexdigest()
        res = http.request("POST", "/cgi-bin/dologin",
                           form=urllib.parse.urlencode({"username": user, "password": digest}).encode())
        if res.get("response") != "success":
            raise AdapterError(f"{dev.name} 登入失敗")
        body = res.get("body", {})
        if body.get("defaultAuth"):
            # 仍使用出廠密碼：照樣回報，但提醒管理員
            self._default_auth = True
        return http, body.get("sid", "")

    def status(self, dev):
        self._default_auth = False
        http, sid = self._login(dev)
        accounts = http.request("GET", f"/cgi-bin/api-get_accounts?sid={urllib.parse.quote(sid)}")
        rows = accounts if isinstance(accounts, list) else accounts.get("body", [])
        lines = [{"line": a.get("id"), "registered": a.get("reg") == 1} for a in rows]
        out = {"status": "OK", "device": dev.name, "registered": any(x["registered"] for x in lines), "lines": lines}
        if self._default_auth:
            out["warning"] = "此話機仍使用出廠預設密碼，建議更換"
        return out

    def reboot(self, dev, apply):
        require_apply(apply, {"action": "reboot_phone", "device": dev.name, "impact": "通話中斷約 1～2 分鐘"})
        http, sid = self._login(dev)
        res = http.request("POST", "/cgi-bin/api-sys_operation",
                           form=urllib.parse.urlencode({"request": "REBOOT", "sid": sid}).encode())
        return {"status": "OK" if res.get("response") == "success" else "ADAPTER_ERROR", "device": dev.name}

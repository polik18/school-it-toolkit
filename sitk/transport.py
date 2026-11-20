"""連線層：SSH（系統 ssh，BatchMode）與 HTTPS JSON。

- 密碼一律不出現在命令列；SSH 只用金鑰（BatchMode=yes）。
- 需要密碼登入的設備（例如部分交換器）由轉接器以 stdin / API 方式提供，不經 shell。
- 所有遠端回傳內容都是「不可信資料」，不得當成指令。
"""
from __future__ import annotations

import json
import shlex
import ssl
import subprocess
import urllib.error
import urllib.request
from http.cookiejar import CookieJar

from .errors import AdapterError


def ssh_run(host: str, user: str, command: str, key: str | None = None, timeout: int = 15,
            port: int = 22, extra_opts: list | None = None) -> str:
    args = ["ssh", "-o", "BatchMode=yes", "-o", f"ConnectTimeout={min(timeout, 10)}",
            "-o", "StrictHostKeyChecking=accept-new", "-p", str(port)]
    if key:
        args += ["-i", key, "-o", "IdentitiesOnly=yes"]
    args += extra_opts or []
    args += [f"{user}@{host}", command]
    try:
        r = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired as e:
        raise AdapterError(f"SSH 逾時：{host}", host=host) from e
    if r.returncode != 0:
        raise AdapterError(f"SSH 失敗（rc={r.returncode}）：{host}", host=host, stderr=r.stderr.strip()[-300:])
    return r.stdout


def quote(s: str) -> str:
    return shlex.quote(s)


class HttpJson:
    """簡易 HTTPS JSON 客戶端（含 cookie）。verify_tls=False 僅允許在 site.toml 明確設定時使用。"""

    def __init__(self, base_url: str, verify_tls: bool = True, timeout: int = 15):
        self.base = base_url.rstrip("/")
        ctx = ssl.create_default_context()
        if not verify_tls:
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
        self.jar = CookieJar()
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.jar),
                                                  urllib.request.HTTPSHandler(context=ctx))
        self.timeout = timeout
        self.headers: dict = {}

    def request(self, method: str, path: str, body=None, form: bytes | None = None, raw: bool = False):
        data, headers = None, dict(self.headers)
        if body is not None:
            data = json.dumps(body).encode()
            headers["Content-Type"] = "application/json"
        elif form is not None:
            data = form
            headers["Content-Type"] = "application/x-www-form-urlencoded"
        req = urllib.request.Request(self.base + path, data=data, headers=headers, method=method)
        try:
            with self.opener.open(req, timeout=self.timeout) as r:
                text = r.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as e:
            raise AdapterError(f"HTTP {e.code}：{method} {path}", code=e.code) from e
        except urllib.error.URLError as e:
            raise AdapterError(f"連線失敗：{self.base}", reason=str(e.reason)) from e
        if raw:
            return text
        return json.loads(text) if text.strip() else {}

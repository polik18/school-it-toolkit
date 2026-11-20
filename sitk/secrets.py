"""憑證提供者：由工具自己取密碼，AI 與提示詞永遠看不到。

來源順序（site.toml [secrets] backend）：
  keychain : macOS `security find-generic-password -s sitk -a <ref> -w`
  env-file : 權限必須是 0600 的 KEY=value 檔（預設 site/secrets.env）
  env      : 環境變數 SITK_SECRET_<REF>

規則：
  - 不印出、不寫日誌、不放進命令列參數（ps 看得到）。
  - 找不到就 Fail-Closed，不使用任何預設密碼。
"""
from __future__ import annotations

import os
import re
import stat
import subprocess
import sys

from .errors import FailClosed
from .site import Site


class Secret(str):
    """repr 時遮蔽，避免意外出現在日誌或例外訊息。"""

    def __repr__(self) -> str:
        return "Secret('***')"


def _ref_env(ref: str) -> str:
    return "SITK_SECRET_" + re.sub(r"[^A-Za-z0-9]", "_", ref).upper()


def _from_env_file(site: Site, ref: str) -> str | None:
    path = site.resolve(site.section("secrets").get("env_file", "secrets.env"))
    if not path.exists():
        return None
    mode = stat.S_IMODE(path.stat().st_mode)
    if os.name == "posix" and mode & 0o077:
        raise FailClosed(f"憑證檔權限過寬（{oct(mode)}），請執行 chmod 600 {path}")
    key = re.sub(r"[^A-Za-z0-9]", "_", ref).upper()
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            if k.strip().upper() == key:
                return v.strip().strip('"').strip("'")
    return None


def _from_keychain(ref: str) -> str | None:
    if sys.platform != "darwin":
        return None
    r = subprocess.run(["security", "find-generic-password", "-s", "sitk", "-a", ref, "-w"],
                       capture_output=True, text=True)
    return r.stdout.rstrip("\n") if r.returncode == 0 else None


def get_secret(site: Site, ref: str) -> Secret:
    backend = site.section("secrets").get("backend", "env-file")
    order = {"keychain": [_from_keychain], "env-file": [], "env": []}.get(backend, [])
    val = None
    for fn in order:
        val = fn(ref)
        if val:
            break
    if not val and backend in ("env-file", "keychain"):
        val = _from_env_file(site, ref)
    if not val:
        val = os.environ.get(_ref_env(ref))
    if not val:
        raise FailClosed(f"找不到憑證「{ref}」（backend={backend}），不使用任何預設密碼",
                         hint=f"keychain: security add-generic-password -s sitk -a {ref} -w ；"
                              f"或在 secrets.env 設定 {re.sub(r'[^A-Za-z0-9]', '_', ref).upper()}=")
    return Secret(val)

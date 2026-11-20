"""通用 SSH CLI 交換器轉接器（唯讀），以「指令設定檔」支援不同廠牌。

site.toml：
  [adapters.switch]
  driver = "ssh_cli"
  profile = "cisco_ios"            # dell_os10 | cisco_ios | aruba_cx | hpe_comware | custom
  user_ref = "switch_user"         # 或 user = "..."
  password_ref = "switch_password" # 沒有金鑰時使用；以 sshpass -e 經環境變數傳入，不出現在命令列
  key = "~/.ssh/sitk_switch"       # 建議使用金鑰

  # profile = "custom" 時自行指定唯讀指令：
  [adapters.switch.commands]
  version = "show version"
  mac_table = "show mac address-table"
  lldp = "show lldp neighbors"
  running_config = "show running-config"

只送出 show / display 類唯讀指令；本轉接器不提供任何組態寫入。
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import time
from pathlib import Path

from ..errors import AdapterError, FailClosed
from ..guard import require_active, require_in_scope
from ..secrets import get_secret
from .base import SwitchAdapter

PROFILES = {
    "dell_os10": {"version": "show version", "mac_table": "show mac address-table",
                  "lldp": "show lldp neighbors", "running_config": "show running-configuration"},
    "cisco_ios": {"version": "show version", "mac_table": "show mac address-table",
                  "lldp": "show lldp neighbors", "running_config": "show running-config"},
    "aruba_cx": {"version": "show version", "mac_table": "show mac-address-table",
                 "lldp": "show lldp neighbor-info", "running_config": "show running-config"},
    "hpe_comware": {"version": "display version", "mac_table": "display mac-address",
                    "lldp": "display lldp neighbor-information list", "running_config": "display current-configuration"},
}
READ_ONLY_PREFIX = ("show ", "display ")

MAC_RE = re.compile(r"\b([0-9a-f]{2}(?:[:-][0-9a-f]{2}){5}|[0-9a-f]{4}\.[0-9a-f]{4}\.[0-9a-f]{4}|"
                    r"[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4})\b", re.I)
PORT_RE = re.compile(r"^(?:ethernet|eth|gi|te|fo|hu|fa|xe|ge|port-channel|po|lag|bagg|xge|mge|\d+/\d+)", re.I)


def normalize_mac(s: str) -> str:
    h = re.sub(r"[^0-9a-f]", "", s.lower())
    return ":".join(h[i:i + 2] for i in range(0, 12, 2)) if len(h) == 12 else s.lower()


def parse_mac_table(text: str) -> list[dict]:
    """廠牌無關的 MAC 表解析：每行找 MAC、VLAN（第一個純數字欄位）與埠（最像介面名稱的欄位）。"""
    rows = []
    for line in text.splitlines():
        m = MAC_RE.search(line)
        if not m:
            continue
        tokens = line.split()
        vlan = next((int(t) for t in tokens if t.isdigit() and int(t) < 4095), None)
        port = next((t for t in reversed(tokens) if PORT_RE.match(t) and not MAC_RE.fullmatch(t)), None)
        if port:
            rows.append({"vlan": vlan, "mac": normalize_mac(m.group(1)), "port": port})
    return rows


class SshCliSwitch(SwitchAdapter):
    def _commands(self) -> dict:
        profile = self.cfg.get("profile")
        if profile == "custom":
            cmds = self.cfg.get("commands", {})
        elif profile in PROFILES:
            cmds = {**PROFILES[profile], **self.cfg.get("commands", {})}
        else:
            raise FailClosed("請在 [adapters.switch] 設定 profile", available=sorted(PROFILES) + ["custom"])
        for k, v in cmds.items():
            if not str(v).lower().startswith(READ_ONLY_PREFIX):
                raise FailClosed(f"指令 {k} 不是 show/display 唯讀指令，拒絕使用", command=v)
        return cmds

    def _run(self, dev, key_name: str, timeout: int = 20) -> str:
        require_active(dev)
        require_in_scope(self.site, dev.ip)
        command = self._commands().get(key_name)
        if not command:
            raise FailClosed(f"設定檔缺少 {key_name} 指令")
        user = self.cfg.get("user") or get_secret(self.site, self.cfg.get("user_ref", "switch_user"))
        base = ["ssh", "-o", "StrictHostKeyChecking=accept-new", "-o", "ConnectTimeout=8",
                "-o", "NumberOfPasswordPrompts=1"]
        env = os.environ.copy()
        key = self.cfg.get("key")
        if key:
            args = base + ["-o", "BatchMode=yes", "-i", os.path.expanduser(key), f"{user}@{dev.ip}", command]
        else:
            if not shutil.which("sshpass"):
                raise FailClosed("密碼登入需要 sshpass（或改用 SSH 金鑰：設定 key）")
            env["SSHPASS"] = get_secret(self.site, self.cfg.get("password_ref", "switch_password"))
            args = ["sshpass", "-e"] + base + [f"{user}@{dev.ip}", command]
        try:
            r = subprocess.run(args, capture_output=True, text=True, timeout=timeout, env=env)
        except subprocess.TimeoutExpired as e:
            raise AdapterError(f"{dev.name} SSH 逾時") from e
        finally:
            env.pop("SSHPASS", None)
        if r.returncode != 0:
            raise AdapterError(f"{dev.name} 指令失敗（rc={r.returncode}）", stderr=r.stderr.strip()[-200:])
        return r.stdout

    def status(self, dev):
        out = self._run(dev, "version")
        ver = next((ln.split(":", 1)[1].strip() for ln in out.splitlines()
                    if re.search(r"(OS Version|Software Version|Version\s*:)", ln, re.I) and ":" in ln), "")
        up = next((ln.split(":", 1)[-1].strip() for ln in out.splitlines() if "up" in ln.lower() and "time" in ln.lower()), "")
        return {"status": "OK", "device": dev.name, "reachable": True, "os_version": ver, "uptime": up}

    def mac_table(self, dev):
        entries = parse_mac_table(self._run(dev, "mac_table"))
        return {"status": "OK", "device": dev.name, "count": len(entries), "entries": entries}

    def lldp(self, dev):
        out = self._run(dev, "lldp")
        rows = []
        for ln in out.splitlines():
            parts = ln.split()
            if len(parts) >= 3 and PORT_RE.match(parts[0]):
                rows.append({"local_port": parts[0], "lldp_neighbor": parts[1], "remote_port": parts[-1]})
        return {"status": "OK", "device": dev.name, "neighbors": rows}

    def backup(self, dev, dest_dir):
        out = self._run(dev, "running_config", timeout=60)
        dest = Path(dest_dir)
        dest.mkdir(parents=True, exist_ok=True)
        path = dest / f"{dev.name}_{time.strftime('%Y%m%d-%H%M%S')}.cfg"
        path.write_text(out, encoding="utf-8")
        os.chmod(path, 0o600)
        return {"status": "OK", "device": dev.name, "saved": str(path), "bytes": len(out),
                "warning": "設定備份含敏感資訊，請勿提交到 git 或貼給雲端模型"}

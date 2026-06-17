"""
schooltk — School IT Toolkit 共用設定載入器 / shared config loader.

所有工具都透過這個模組讀取設定，因此腳本本身**完全不含**任何學校專屬的
IP、帳號、密碼或金鑰路徑——這些一律來自本機（gitignored）的 config 檔。

All tools read settings through this module, so the scripts themselves contain
**no** school-specific IPs, accounts, passwords, or key paths. Those live only in
the local (gitignored) config files.
"""
import csv
import shlex
from pathlib import Path

# 用來定位 repo 根目錄的標記檔（一定被 git 追蹤）
# Marker file used to locate the repo root (always tracked by git).
_MARKER = "config/admin.conf.example"


def find_repo_root(start=None):
    start = Path(start or __file__).resolve()
    for parent in [start, *start.parents]:
        if (parent / _MARKER).exists():
            return parent
    raise RuntimeError(
        "找不到 repo 根目錄（缺少 config/admin.conf.example）。"
        " Cannot locate repo root (missing config/admin.conf.example)."
    )


ROOT = find_repo_root()


def _parse_kv(path):
    """解析 shell 風格的 KEY=\"value\" 檔；忽略註解與空行。"""
    values = {}
    path = Path(path)
    if not path.exists():
        return values
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        try:
            parsed = shlex.split(value.strip(), posix=True)
            values[key.strip()] = parsed[0] if parsed else ""
        except ValueError:
            values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def load_config():
    """讀取 config/admin.conf，套用通用預設值（不含任何學校真值）。"""
    cfg = _parse_kv(ROOT / "config" / "admin.conf")
    cfg.setdefault("ADMIN_USER", "schooladmin")
    cfg.setdefault("SSH_KEY", "keys/admin_ed25519")
    cfg.setdefault("SSH_PUBLIC_KEY", "keys/admin_ed25519.pub")
    cfg.setdefault("INVENTORY_CSV", "inventory/inventory.csv")
    cfg.setdefault("LOG_DIR", "logs")
    cfg.setdefault("SSH_TIMEOUT", "12")
    cfg.setdefault("CREDENTIALS_FILE", "config/credentials.env")
    return cfg


def load_credentials(cfg=None):
    cfg = cfg or load_config()
    return _parse_kv(resolve(cfg["CREDENTIALS_FILE"]))


def load_network_credentials():
    """讀取 config/network_credentials.env（交換器/PBX/話機憑證）。"""
    return _parse_kv(ROOT / "config" / "network_credentials.env")


def load_env(filename):
    """讀取 config/<filename>（任意 KEY=value 設定檔）。"""
    return _parse_kv(ROOT / "config" / filename)


def resolve(p):
    """把相對路徑接到 repo 根目錄；絕對路徑原樣回傳。"""
    p = Path(p)
    return p if p.is_absolute() else ROOT / p


def load_hosts(cfg=None):
    cfg = cfg or load_config()
    inv = resolve(cfg["INVENTORY_CSV"])
    if not inv.exists():
        raise FileNotFoundError(
            f"找不到清冊 {inv}。請先執行 setup/init-wizard.py 或匯出你的 ARD 清冊。\n"
            f"Inventory not found: {inv}. Run setup/init-wizard.py or export your ARD inventory first."
        )
    with inv.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def select_hosts(rows, group=None, host=None):
    """依 group（ARD 清單名）或 host（name/bonjour/hostname/ip）篩選，且需有 IP。"""
    selected = []
    for row in rows:
        if group and group.lower() != "all" and row.get("list", "") != group:
            continue
        if host and host not in (
            row.get("name"), row.get("bonjour_name"), row.get("ip"), row.get("hostname")
        ):
            continue
        if row.get("ip"):
            selected.append(row)
    return selected


def ssh_key_path(cfg=None):
    cfg = cfg or load_config()
    return resolve(cfg["SSH_KEY"])

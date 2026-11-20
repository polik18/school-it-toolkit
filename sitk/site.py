"""站點設定（site.toml）載入與驗證。

site.toml 是每所學校自己的檔案，永遠不提交到 git。
範例見 examples/demo-school/site.toml。
"""
from __future__ import annotations

import ipaddress
import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from .errors import FailClosed

ENV_SITE = "SITK_SITE"
REQUIRED_SECTIONS = ("school", "scope", "inventory")


@dataclass
class Site:
    path: Path
    raw: dict
    networks: list = field(default_factory=list)

    @property
    def root(self) -> Path:
        return self.path.parent

    @property
    def name(self) -> str:
        return self.raw["school"].get("name", "unnamed-site")

    def resolve(self, rel: str) -> Path:
        p = Path(os.path.expanduser(rel))
        return p if p.is_absolute() else (self.root / p)

    def section(self, name: str) -> dict:
        return self.raw.get(name, {})

    def adapter_config(self, kind: str) -> dict:
        """[adapters.<kind>] 區段，例如 [adapters.switch] driver = "ssh_cli"。"""
        return self.raw.get("adapters", {}).get(kind, {})

    def policy(self, key: str, default=None):
        return self.raw.get("policy", {}).get(key, default)


def find_site_file(explicit: str | None = None) -> Path:
    candidates = []
    if explicit:
        candidates.append(Path(explicit))
    if os.environ.get(ENV_SITE):
        candidates.append(Path(os.environ[ENV_SITE]))
    candidates += [Path.cwd() / "site" / "site.toml", Path.cwd() / "site.toml",
                   Path.home() / ".config" / "sitk" / "site.toml"]
    for c in candidates:
        c = Path(os.path.expanduser(str(c)))
        if c.is_file():
            return c.resolve()
    raise FailClosed(
        "找不到 site.toml。請先執行 `python3 setup/init.py`，或以 --site / 環境變數 SITK_SITE 指定。",
        searched=[str(c) for c in candidates],
    )


def load_site(explicit: str | None = None) -> Site:
    path = find_site_file(explicit)
    with path.open("rb") as f:
        raw = tomllib.load(f)
    missing = [s for s in REQUIRED_SECTIONS if s not in raw]
    if missing:
        raise FailClosed(f"site.toml 缺少必要區段：{', '.join(missing)}", path=str(path))
    nets = []
    for cidr in raw["scope"].get("allowed_networks", []):
        try:
            nets.append(ipaddress.ip_network(cidr, strict=False))
        except ValueError as e:
            raise FailClosed(f"scope.allowed_networks 格式錯誤：{cidr}", error=str(e)) from e
    if not nets:
        raise FailClosed("scope.allowed_networks 不可為空：工具不得對未定義網段動作。")
    return Site(path=path, raw=raw, networks=nets)

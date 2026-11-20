"""轉接器（adapters）：把各廠牌設備包成同一組動詞。

site.toml：
  [adapters.switch]   driver = "ssh_cli"  profile = "cisco_ios"
  [adapters.wifi]     driver = "fortigate"
  [adapters.firewall] driver = "linux_iptables"
  [adapters.dnsdhcp]  driver = "bind9_isc"
  [adapters.endpoint] driver = "macos"
  [adapters.voip]     driver = "grandstream"
任何類別都可設 driver = "mock" 進行演練與測試。
"""
from __future__ import annotations

import importlib

from ..errors import FailClosed

DRIVERS = {
    "switch": {"ssh_cli": "switch_ssh_cli:SshCliSwitch", "mock": "mock:MockSwitch"},
    "wifi": {"fortigate": "wifi_fortigate:FortiGateWifi", "mock": "mock:MockWifi"},
    "firewall": {"linux_iptables": "firewall_linux_iptables:LinuxIptablesFirewall", "mock": "mock:MockFirewall"},
    "dnsdhcp": {"bind9_isc": "dnsdhcp_bind9_isc:Bind9IscDnsDhcp", "mock": "mock:MockDnsDhcp"},
    "endpoint": {"macos": "endpoint_macos:MacOSEndpoint", "mock": "mock:MockEndpoint"},
    "voip": {"grandstream": "voip_grandstream:GrandstreamVoip", "mock": "mock:MockVoip"},
}


def load_adapter(kind: str, site, registry):
    cfg = site.adapter_config(kind)
    driver = cfg.get("driver")
    if not driver:
        raise FailClosed(f"site.toml 未設定 [adapters.{kind}] driver", available=sorted(DRIVERS.get(kind, {})))
    target = DRIVERS.get(kind, {}).get(driver)
    if not target:
        raise FailClosed(f"不支援的 {kind} driver：{driver}", available=sorted(DRIVERS.get(kind, {})),
                         hint="可依 docs/zh-TW/adapter-guide.md 自行新增轉接器")
    mod_name, cls_name = target.split(":")
    mod = importlib.import_module(f"{__name__}.{mod_name}")
    return getattr(mod, cls_name)(site, registry, cfg)

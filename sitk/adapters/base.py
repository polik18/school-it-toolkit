"""轉接器共同介面。每個方法回傳 dict（會被包成標準 JSON 輸出）。

變更類方法一律帶 apply 參數；apply=False 時只回傳預覽，不得產生任何副作用。
"""
from __future__ import annotations

from ..registry import Device, Registry
from ..site import Site


class Adapter:
    kind = "base"
    #: 設備回傳、需標示為不可信的欄位
    untrusted_fields: list = []

    def __init__(self, site: Site, registry: Registry, cfg: dict):
        self.site, self.registry, self.cfg = site, registry, cfg

    def device(self, query: str) -> Device:
        return self.registry.find_device(query, kind=self.kind)


class SwitchAdapter(Adapter):
    kind = "switch"
    untrusted_fields = ["description", "lldp_neighbor"]

    def status(self, dev: Device) -> dict: raise NotImplementedError
    def mac_table(self, dev: Device) -> dict: raise NotImplementedError
    def lldp(self, dev: Device) -> dict: raise NotImplementedError
    def backup(self, dev: Device, dest_dir) -> dict: raise NotImplementedError


class WifiAdapter(Adapter):
    kind = "ap"
    untrusted_fields = ["ap_name", "ssid", "hostname"]

    def aps(self, offline_only: bool = False) -> dict: raise NotImplementedError
    def clients(self, ap: Device | None = None) -> dict: raise NotImplementedError
    def reboot_ap(self, ap: Device, apply: bool) -> dict: raise NotImplementedError


class FirewallAdapter(Adapter):
    kind = "firewall"

    def status(self) -> dict: raise NotImplementedError
    def lint(self) -> dict: raise NotImplementedError
    def apply_rules(self, apply: bool, timeout: int) -> dict: raise NotImplementedError


class DnsDhcpAdapter(Adapter):
    kind = "dnsdhcp"
    untrusted_fields = ["record", "lease"]

    def dns_search(self, keyword: str) -> dict: raise NotImplementedError
    def dhcp_search(self, keyword: str) -> dict: raise NotImplementedError
    def dns_reload(self, apply: bool) -> dict: raise NotImplementedError


class EndpointAdapter(Adapter):
    kind = "endpoint"
    untrusted_fields = ["hostname", "console_user"]

    def status(self, dev: Device) -> dict: raise NotImplementedError
    def facts(self, dev: Device) -> dict: raise NotImplementedError
    def wake(self, dev: Device, apply: bool) -> dict: raise NotImplementedError


class VoipAdapter(Adapter):
    kind = "phone"

    def status(self, dev: Device) -> dict: raise NotImplementedError
    def reboot(self, dev: Device, apply: bool) -> dict: raise NotImplementedError

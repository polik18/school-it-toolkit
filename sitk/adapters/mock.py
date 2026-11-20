"""模擬轉接器：不連任何設備，依台帳回傳可預期的結果。用於演練、教學與自動測試。"""
from __future__ import annotations

from ..guard import require_apply
from .base import (DnsDhcpAdapter, EndpointAdapter, FirewallAdapter, SwitchAdapter, VoipAdapter,
                   WifiAdapter)


def _offline(dev) -> bool:
    return "mock-offline" in dev.tags


class MockSwitch(SwitchAdapter):
    def status(self, dev):
        return {"status": "OK", "device": dev.name, "reachable": not _offline(dev), "model": dev.model,
                "uptime": "mock"}

    def mac_table(self, dev):
        entries = [{"mac": d.mac, "port": f"1/1/{i + 1}", "vlan": 1}
                   for i, d in enumerate(self.registry.devices) if d.mac and d.kind != "switch"]
        return {"status": "OK", "device": dev.name, "entries": entries}

    def lldp(self, dev):
        return {"status": "OK", "device": dev.name, "neighbors": []}

    def backup(self, dev, dest_dir):
        return {"status": "OK", "device": dev.name, "saved": f"{dest_dir}/{dev.name}.mock.cfg"}


class MockWifi(WifiAdapter):
    def aps(self, offline_only=False):
        rows = [{"name": d.name, "space": d.space, "state": "offline" if _offline(d) else "connected"}
                for d in self.registry.by_kind("ap")]
        if offline_only:
            rows = [r for r in rows if r["state"] != "connected"]
        return {"status": "OK", "count": len(rows), "aps": rows}

    def clients(self, ap=None):
        return {"status": "OK", "ap": ap.name if ap else None, "clients": []}

    def reboot_ap(self, ap, apply):
        require_apply(apply, {"action": "reboot_ap", "ap": ap.name})
        return {"status": "OK", "ap": ap.name, "result": "mock reboot sent"}


class MockFirewall(FirewallAdapter):
    def status(self):
        return {"status": "OK", "rules": "mock", "persisted": True}

    def lint(self):
        return {"status": "OK", "errors": 0}

    def apply_rules(self, apply, timeout):
        require_apply(apply, {"action": "apply_rules", "deadman_timeout": timeout})
        return {"status": "OK", "applied": True, "probe": "PROBE_SUCCESS", "rollback_armed": False}

    def persist(self, apply):
        require_apply(apply, {"action": "persist"})
        return {"status": "OK", "persisted": True}


class MockDnsDhcp(DnsDhcpAdapter):
    def dns_search(self, keyword):
        hits = [{"name": d.name, "ip": d.ip} for d in self.registry.devices if keyword.lower() in d.name.lower()]
        return {"status": "OK", "records": hits}

    def dhcp_search(self, keyword):
        hits = [{"name": d.name, "ip": d.ip, "mac": d.mac} for d in self.registry.devices
                if keyword.lower() in f"{d.name} {d.ip} {d.mac}".lower()]
        return {"status": "OK", "reservations": hits}

    def dns_reload(self, apply):
        require_apply(apply, {"action": "dns_reload", "precheck": "named-checkconf"})
        return {"status": "OK", "reloaded": True}


class MockEndpoint(EndpointAdapter):
    def status(self, dev):
        return {"status": "OK", "device": dev.name, "ssh": not _offline(dev), "ping": not _offline(dev)}

    def facts(self, dev):
        return {"status": "OK", "device": dev.name, "os": "mock-os 1.0", "disk_free_gb": 100}

    def wake(self, dev, apply):
        require_apply(apply, {"action": "wake", "device": dev.name, "mac": dev.mac})
        return {"status": "OK", "device": dev.name, "magic_packet": "sent (mock)"}


class MockVoip(VoipAdapter):
    def status(self, dev):
        return {"status": "OK", "device": dev.name, "registered": not _offline(dev)}

    def reboot(self, dev, apply):
        require_apply(apply, {"action": "reboot_phone", "device": dev.name})
        return {"status": "OK", "device": dev.name, "result": "mock reboot sent"}

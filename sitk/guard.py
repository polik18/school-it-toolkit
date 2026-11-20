"""Fail-Closed 守門：安全邊界寫在程式裡，不依賴模型自律。"""
from __future__ import annotations

import ipaddress
import socket

from .errors import ConfirmationRequired, FailClosed, OutOfScope
from .registry import Device
from .site import Site


def require_in_scope(site: Site, ip: str) -> None:
    """目標 IP 必須落在 site.toml 的 scope.allowed_networks 內。"""
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError as e:
        raise FailClosed(f"不是合法 IP：{ip!r}") from e
    if not any(addr in n for n in site.networks):
        raise OutOfScope(f"{ip} 不在允許網段內，拒絕動作", allowed=[str(n) for n in site.networks])


def require_active(device: Device) -> None:
    """ACTIVE/STAGING 天條：非 ACTIVE 設備不得當作線上現況，也不得變更。"""
    if device.status != "ACTIVE":
        raise FailClosed(f"{device.name} 狀態為 {device.status}，不是 ACTIVE；請先人工確認現況",
                         device=device.name, status=device.status)


def require_apply(apply: bool, plan: dict) -> None:
    """變更類動作：沒有 --apply 時只回傳預覽（DRY_RUN），不執行。"""
    if not apply:
        raise ConfirmationRequired("預覽模式：未加 --apply，沒有做任何變更", plan=plan)


def require_confirm(site: Site, domain: str, confirm: str | None, target: str) -> None:
    """高風險領域（policy.confirm_required）必須帶 --confirm <目標名稱>，避免順手執行。"""
    if domain in site.policy("confirm_required", ["firewall", "core_switch", "power"]):
        if confirm != target:
            raise FailClosed(f"{domain} 屬高風險變更：須人工明確確認，並加上 --confirm {target}",
                             domain=domain, target=target)


def require_dns(name: str, resolver: str | None = None) -> str:
    """變更網域相關設定前，網域必須真的解析得到（防止小模型自造網域）。"""
    try:
        return socket.gethostbyname(name)
    except OSError as e:
        raise FailClosed(f"網域 {name} 無法解析，拒絕依此名稱變更設定", hint="先確認 DNS 紀錄，勿猜測網域") from e

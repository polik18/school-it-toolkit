"""資產白名單（台帳）：所有設備與空間只能從這裡查到。

台帳檔（CSV，欄位見 schemas/）：
  devices.csv：name, kind, ip, mac, model, space, status, aliases, tags
  spaces.csv ：code, name, building, floor, aliases

查不到就丟 UnknownAsset —— 絕不猜測或自造名稱。
"""
from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from pathlib import Path

from .errors import FailClosed, UnknownAsset
from .site import Site

DEVICE_FIELDS = ("name", "kind", "ip", "mac", "model", "space", "status", "aliases", "tags")
SPACE_FIELDS = ("code", "name", "building", "floor", "aliases")
VALID_STATUS = {"ACTIVE", "STAGING", "RETIRED", "SPARE"}


def norm(s: str) -> str:
    return re.sub(r"[\s_\-]", "", (s or "").strip().lower())


def split_aliases(s: str) -> list[str]:
    return [a.strip() for a in re.split(r"[|;]", s or "") if a.strip()]


@dataclass
class Device:
    name: str
    kind: str
    ip: str
    mac: str
    model: str
    space: str
    status: str
    aliases: list
    tags: list

    def to_dict(self) -> dict:
        return {k: getattr(self, k) for k in DEVICE_FIELDS}


@dataclass
class Space:
    code: str
    name: str
    building: str
    floor: str
    aliases: list

    def to_dict(self) -> dict:
        return {k: getattr(self, k) for k in SPACE_FIELDS}


def _read_csv(path: Path, fields: tuple) -> list[dict]:
    if not path.is_file():
        raise FailClosed(f"台帳不存在：{path}", hint="執行 setup/init.py 或依 schemas/ 建立台帳")
    with path.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        missing = [c for c in fields if c not in (reader.fieldnames or [])]
        if missing:
            raise FailClosed(f"台帳欄位缺少 {missing}：{path}")
        rows = [r for r in reader if any((v or "").strip() for v in r.values())]
    if not rows:
        raise FailClosed(f"台帳讀到 0 筆：{path}，拒絕以空白清單繼續")
    return rows


class Registry:
    def __init__(self, site: Site):
        inv = site.section("inventory")
        self.devices = [self._device(r) for r in _read_csv(site.resolve(inv["devices"]), DEVICE_FIELDS)]
        self.spaces = [self._space(r) for r in _read_csv(site.resolve(inv["spaces"]), SPACE_FIELDS)] \
            if inv.get("spaces") else []

    @staticmethod
    def _device(r: dict) -> Device:
        status = (r.get("status") or "ACTIVE").strip().upper()
        if status not in VALID_STATUS:
            raise FailClosed(f"設備 {r.get('name')} 的 status 不合法：{status}", allowed=sorted(VALID_STATUS))
        return Device(name=r["name"].strip(), kind=r["kind"].strip().lower(), ip=(r.get("ip") or "").strip(),
                      mac=(r.get("mac") or "").strip().lower(), model=(r.get("model") or "").strip(),
                      space=(r.get("space") or "").strip(), status=status,
                      aliases=split_aliases(r.get("aliases", "")), tags=split_aliases(r.get("tags", "")))

    @staticmethod
    def _space(r: dict) -> Space:
        return Space(code=r["code"].strip(), name=r["name"].strip(), building=(r.get("building") or "").strip(),
                     floor=(r.get("floor") or "").strip(), aliases=split_aliases(r.get("aliases", "")))

    # ---- 查詢 ----
    def find_space(self, query: str) -> Space:
        q = norm(query)
        for s in self.spaces:
            if q in {norm(s.code), norm(s.name), *map(norm, s.aliases)}:
                return s
        raise UnknownAsset(f"空間白名單中沒有「{query}」", query=query,
                           hint="請在 spaces.csv 的 aliases 欄補上別名，或請人工確認")

    def find_device(self, query: str, kind: str | None = None) -> Device:
        q = norm(query)
        for d in self.devices:
            if kind and d.kind != kind:
                continue
            if q in {norm(d.name), norm(d.ip), norm(d.mac), *map(norm, d.aliases)}:
                return d
        # 允許以空間找設備（例如「三年六班」→ 該教室的 AP）
        if self.spaces:
            try:
                sp = self.find_space(query)
            except UnknownAsset:
                sp = None
            if sp:
                hits = [d for d in self.devices if d.space == sp.code and (not kind or d.kind == kind)]
                if len(hits) == 1:
                    return hits[0]
                if len(hits) > 1:
                    raise UnknownAsset(f"空間 {sp.code} 有多台 {kind or '設備'}，請指定名稱",
                                       candidates=[h.name for h in hits])
        raise UnknownAsset(f"設備白名單中沒有「{query}」" + (f"（類型 {kind}）" if kind else ""), query=query)

    def by_kind(self, kind: str, status: str | None = "ACTIVE") -> list[Device]:
        return [d for d in self.devices if d.kind == kind and (status is None or d.status == status)]

    def in_space(self, code: str) -> list[Device]:
        return [d for d in self.devices if d.space == code]

"""sitk — AI 系管師一站式 CLI 門面。

  sitk [--site PATH] [--json] <領域> <動詞> [參數]

小模型只需要：呼叫這裡列出的子命令、讀取 JSON 的 status 欄位。
status 固定值：OK / DRY_RUN / UNKNOWN_ASSET / FAIL_CLOSED / OUT_OF_SCOPE / ADAPTER_ERROR / ...
"""
from __future__ import annotations

import argparse
import sys
import time

from . import __version__
from .adapters import load_adapter
from .audit import record
from .errors import SitkError
from .guard import require_active, require_confirm
from .output import emit
from .registry import Registry
from .secrets import get_secret
from .site import load_site
from .state import StateStore


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="sitk", description="School IT Toolkit v2 — AI 系管師 CLI 門面")
    p.add_argument("--site", help="site.toml 路徑（預設：./site/site.toml 或 $SITK_SITE）")
    p.add_argument("--json", action="store_true", help="輸出 JSON（小模型請一律加）")
    p.add_argument("--version", action="version", version=f"sitk {__version__}")
    sub = p.add_subparsers(dest="domain", required=True)

    sub.add_parser("doctor", help="自我檢查：站點設定、台帳、轉接器、憑證是否就緒（不連設備）")
    s = sub.add_parser("info", help="查設備或空間（只查白名單）")
    s.add_argument("query")
    s = sub.add_parser("room", help="查空間與其中的設備，例：sitk room 三年六班")
    s.add_argument("query")

    sw = sub.add_parser("switch", help="交換器（唯讀）").add_subparsers(dest="verb", required=True)
    for v in ("status", "mac-table", "lldp", "backup"):
        sw.add_parser(v).add_argument("device")
    sw.add_parser("find-mac", help="在所有 ACTIVE 交換器找 MAC 所在埠").add_argument("mac")

    wf = sub.add_parser("wifi", help="無線 AP").add_subparsers(dest="verb", required=True)
    wf.add_parser("aps").add_argument("--offline", action="store_true")
    wf.add_parser("clients").add_argument("ap", nargs="?")
    r = wf.add_parser("reboot", help="重開 AP，可用 AP 名稱或空間名稱")
    r.add_argument("ap")
    r.add_argument("--apply", action="store_true")

    fw = sub.add_parser("firewall", help="防火牆（變更需 --apply 與 --confirm）").add_subparsers(dest="verb", required=True)
    fw.add_parser("status")
    fw.add_parser("lint")
    for v in ("apply", "persist"):
        a = fw.add_parser(v)
        a.add_argument("--apply", action="store_true")
        a.add_argument("--confirm", help="必須等於防火牆設備名稱")
        if v == "apply":
            a.add_argument("--timeout", type=int, default=60, help="死人開關秒數（15～600）")

    dns = sub.add_parser("dns").add_subparsers(dest="verb", required=True)
    dns.add_parser("search").add_argument("keyword")
    dns.add_parser("reload").add_argument("--apply", action="store_true")
    dhcp = sub.add_parser("dhcp").add_subparsers(dest="verb", required=True)
    dhcp.add_parser("search").add_argument("keyword")

    ep = sub.add_parser("endpoint", help="教室電腦").add_subparsers(dest="verb", required=True)
    ep.add_parser("status").add_argument("device")
    ep.add_parser("facts").add_argument("device")
    w = ep.add_parser("wake")
    w.add_argument("device")
    w.add_argument("--apply", action="store_true")

    vp = sub.add_parser("voip", help="網路電話").add_subparsers(dest="verb", required=True)
    vp.add_parser("status").add_argument("device")
    rb = vp.add_parser("reboot")
    rb.add_argument("device")
    rb.add_argument("--apply", action="store_true")

    b = sub.add_parser("batch", help="批次長任務狀態機").add_subparsers(dest="verb", required=True)
    i = b.add_parser("init")
    i.add_argument("--run-id", required=True)
    i.add_argument("--kind", required=True, help="台帳 kind，例如 endpoint / switch / phone")
    i.add_argument("--space", help="只納入某空間")
    i.add_argument("--overwrite", action="store_true")
    for v in ("next", "status", "retry-failed"):
        b.add_parser(v).add_argument("--run-id", required=True)
    c = b.add_parser("complete")
    c.add_argument("--run-id", required=True)
    c.add_argument("--item", required=True)
    c.add_argument("--verified", action="store_true", help="已實測回讀確認")
    f = b.add_parser("fail")
    f.add_argument("--run-id", required=True)
    f.add_argument("--item", required=True)
    f.add_argument("--error", required=True)

    pw = sub.add_parser("power", help="停電關機／復電驗收（分階段）").add_subparsers(dest="verb", required=True)
    for v in ("plan", "status"):
        pw.add_parser(v).add_argument("--mode", choices=["recover", "shutdown"], required=True)
    rr = pw.add_parser("run")
    rr.add_argument("phase", type=int)
    rr.add_argument("--mode", choices=["recover", "shutdown"], required=True)
    rr.add_argument("--apply", action="store_true")
    d = pw.add_parser("done", help="人工階段完成")
    d.add_argument("phase", type=int)
    d.add_argument("--mode", choices=["recover", "shutdown"], required=True)
    return p


def cmd_doctor(site, reg) -> dict:
    kinds: dict = {}
    for d in reg.devices:
        kinds[d.kind] = kinds.get(d.kind, 0) + 1
    adapters = {k: site.adapter_config(k).get("driver", "未設定") for k in
                ("switch", "wifi", "firewall", "dnsdhcp", "endpoint", "voip")}
    missing = []
    for k, cfg in site.raw.get("adapters", {}).items():
        if cfg.get("driver") == "mock":
            continue
        for key, ref in cfg.items():
            if key.endswith("_ref"):
                try:
                    get_secret(site, ref)
                except SitkError:
                    missing.append(f"{k}.{key}={ref}")
    staging = [d.name for d in reg.devices if d.status == "STAGING"]
    return {"status": "OK" if not missing else "INCOMPLETE", "site": site.name,
            "allowed_networks": [str(n) for n in site.networks], "devices": kinds, "spaces": len(reg.spaces),
            "adapters": adapters, "missing_secrets": missing, "staging_devices": staging}


def lifecycle(dev, change: bool, res_fn):
    """ACTIVE/STAGING 天條（集中把關，不依賴各轉接器）：
    變更動作一律要求 ACTIVE；唯讀查詢可執行，但結果標記 NOT_ACTIVE，不得當作線上現況。"""
    if change:
        require_active(dev)
        return res_fn()
    res = res_fn()
    if dev.status != "ACTIVE":
        res = {**res, "status": "NOT_ACTIVE", "lifecycle": dev.status,
               "warning": f"{dev.name} 為 {dev.status}，以下結果不代表線上現況"}
    return res


def run(args) -> tuple[dict, list]:
    site = load_site(args.site)
    reg = Registry(site)
    A = lambda kind: load_adapter(kind, site, reg)  # noqa: E731
    dom, verb = args.domain, getattr(args, "verb", None)
    apply = getattr(args, "apply", False)

    if dom == "doctor":
        return cmd_doctor(site, reg), []
    if dom == "info":
        try:
            return {"status": "OK", "type": "device", **reg.find_device(args.query).to_dict()}, []
        except SitkError:
            sp = reg.find_space(args.query)
            return {"status": "OK", "type": "space", **sp.to_dict(),
                    "devices": [d.name for d in reg.in_space(sp.code)]}, []
    if dom == "room":
        sp = reg.find_space(args.query)
        return {"status": "OK", **sp.to_dict(), "devices": [d.to_dict() for d in reg.in_space(sp.code)]}, []

    if dom == "switch":
        ad = A("switch")
        if verb == "find-mac":
            mac = args.mac.lower().replace("-", ":")
            hits = []
            for sw in reg.by_kind("switch"):  # 只查 ACTIVE
                for e in ad.mac_table(sw)["entries"]:
                    if e["mac"] == mac:
                        hits.append({"switch": sw.name, **e})
            return {"status": "OK" if hits else "NOT_FOUND", "mac": mac, "hits": hits,
                    "hint": "同一 MAC 出現在多台時，非上聯埠（非 trunk）者才是實體掛載點"}, []
        dev = ad.device(args.device)
        fn = {"status": ad.status, "mac-table": ad.mac_table, "lldp": ad.lldp}.get(verb)
        if fn:
            return lifecycle(dev, False, lambda: fn(dev)), ad.untrusted_fields
        dest = site.resolve(site.section("backup").get("dir", "backups"))
        return lifecycle(dev, False, lambda: ad.backup(dev, dest)), []

    if dom == "wifi":
        ad = A("wifi")
        if verb == "aps":
            return ad.aps(offline_only=args.offline), ad.untrusted_fields
        if verb == "clients":
            return ad.clients(ad.device(args.ap) if args.ap else None), ad.untrusted_fields
        ap = ad.device(args.ap)
        res = lifecycle(ap, True, lambda: ad.reboot_ap(ap, apply))
        record(site, "wifi", "reboot", ap.name, res, apply)
        return res, []

    if dom == "firewall":
        ad = A("firewall")
        if verb in ("status", "lint"):
            return getattr(ad, verb)(), []
        target = site.adapter_config("firewall").get("device", "")
        if apply:
            require_confirm(site, "firewall", args.confirm, target)
        res = ad.apply_rules(apply, args.timeout) if verb == "apply" else ad.persist(apply)
        record(site, "firewall", verb, target, res, apply)
        return res, []

    if dom in ("dns", "dhcp"):
        ad = A("dnsdhcp")
        if verb == "search":
            return (ad.dns_search if dom == "dns" else ad.dhcp_search)(args.keyword), ad.untrusted_fields
        res = ad.dns_reload(apply)
        record(site, "dns", "reload", "dns", res, apply)
        return res, []

    if dom == "endpoint":
        ad = A("endpoint")
        dev = ad.device(args.device)
        if verb == "wake":
            res = lifecycle(dev, True, lambda: ad.wake(dev, apply))
            record(site, "endpoint", "wake", dev.name, res, apply)
            return res, []
        return lifecycle(dev, False, lambda: getattr(ad, verb)(dev)), ad.untrusted_fields

    if dom == "voip":
        ad = A("voip")
        dev = ad.device(args.device)
        if verb == "reboot":
            res = lifecycle(dev, True, lambda: ad.reboot(dev, apply))
            record(site, "voip", "reboot", dev.name, res, apply)
            return res, []
        return lifecycle(dev, False, lambda: ad.status(dev)), []

    if dom == "batch":
        store = StateStore(site.resolve(site.section("state").get("dir", "state")), args.run_id)
        if verb == "init":
            devs = reg.by_kind(args.kind)
            if args.space:
                devs = [d for d in devs if d.space == reg.find_space(args.space).code]
            return {"status": "OK", **store.init(f"batch-{args.kind}", [d.name for d in devs], args.overwrite)}, []
        if verb == "next":
            return store.next(), []
        if verb == "status":
            return {"status": "OK", **store.summary()}, []
        if verb == "retry-failed":
            return store.retry_failed(), []
        if verb == "complete":
            return store.complete(args.item, args.verified), []
        return store.fail(args.item, args.error), []

    if dom == "power":
        from .workflows.power import PowerWorkflow
        wf = PowerWorkflow(site, reg, args.mode, adapters_loader=A)
        if verb == "plan":
            return wf.plan(), []
        if verb == "status":
            return wf.status(), []
        if verb == "done":
            return wf.mark_done(args.phase), []
        res = wf.run_phase(args.phase, apply)
        record(site, "power", f"{args.mode}-phase-{args.phase}", args.mode, res, apply)
        return res, []
    raise SitkError(f"未知領域 {dom}")


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    t0 = time.time()
    try:
        res, untrusted = run(args)
        code = 0 if res.get("status") in ("OK", "NEXT", "RESUME", "ALL_DONE", "MANUAL", "INCOMPLETE") else 1
    except SitkError as e:
        res, untrusted, code = e.to_dict(), [], e.exit_code
    except KeyboardInterrupt:
        res, untrusted, code = {"status": "INTERRUPTED"}, [], 130
    res.setdefault("elapsed_s", round(time.time() - t0, 2))
    emit(res, args.json, untrusted)
    return code


if __name__ == "__main__":
    sys.exit(main())

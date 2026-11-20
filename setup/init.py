#!/usr/bin/env python3
"""v2 初始化精靈：建立 site/（站點設定、台帳、憑證檔）並產生本校專屬 AI 技能。

  python3 setup/init.py --example          以「示範國小」建立可立即演練的 site/（全部 mock）
  python3 setup/init.py                    互動式建立真實站點
  python3 setup/init.py --render-only      依現有 site.toml 重新產生技能

產物全部在 site/（已被 .gitignore 排除，永不提交）：
  site/site.toml、site/inventory/*.csv、site/secrets.env（0600）、site/skills/<技能>/SKILL.md
"""
from __future__ import annotations

import argparse
import ipaddress
import os
import re
import shutil
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEMPLATES = ROOT / "skills" / "templates"
DEMO = ROOT / "examples" / "demo-school"
DRIVER_CHOICES = {
    "switch": ["ssh_cli", "mock"], "wifi": ["fortigate", "mock"], "firewall": ["linux_iptables", "mock"],
    "dnsdhcp": ["bind9_isc", "mock"], "endpoint": ["macos", "mock"], "voip": ["grandstream", "mock"],
}
SECRET_REFS = {
    "switch": ["switch_user", "switch_password"], "wifi": ["fortigate_api_token"],
    "voip": ["phone_user", "phone_password"],
}


def ask(prompt: str, default: str = "", validator=None) -> str:
    while True:
        v = input(f"{prompt}" + (f" [{default}]" if default else "") + "：").strip() or default
        if not validator:
            return v
        err = validator(v)
        if not err:
            return v
        print(f"  ✗ {err}")


def valid_networks(v: str):
    try:
        nets = [ipaddress.ip_network(x.strip(), strict=False) for x in v.split(",") if x.strip()]
    except ValueError as e:
        return str(e)
    if not nets:
        return "至少需要一個網段"
    if any(n.prefixlen < 16 for n in nets if n.version == 4):
        return "網段過大（小於 /16），請縮小範圍以免誤動到其他網路"
    return None


def write_site_interactive(site_dir: Path) -> Path:
    print("== 建立站點設定（所有內容只存在本機 site/，不會提交到 git）==")
    name = ask("學校名稱（只用於本機產生的技能文字）", "我的學校")
    nets = ask("允許工具操作的管理網段（逗號分隔，CIDR）", "", valid_networks)
    drivers = {}
    for kind, choices in DRIVER_CHOICES.items():
        drivers[kind] = ask(f"{kind} 轉接器 {choices}", choices[-1],
                            lambda v, c=choices: None if v in c else f"請選 {c}")
    backend = ask("憑證來源 keychain / env-file", "keychain" if sys.platform == "darwin" else "env-file",
                  lambda v: None if v in ("keychain", "env-file", "env") else "請選 keychain / env-file / env")
    nets_toml = ", ".join(f'"{n.strip()}"' for n in nets.split(",") if n.strip())
    lines = [
        "[school]", f'name = "{name}"', "", "[scope]", f"allowed_networks = [{nets_toml}]", "",
        "[inventory]", 'devices = "inventory/devices.csv"', 'spaces = "inventory/spaces.csv"', "",
        "[secrets]", f'backend = "{backend}"', 'env_file = "secrets.env"', "",
        '[state]\ndir = "state"\n\n[backup]\ndir = "backups"\n\n[audit]\nlog = "logs/audit.jsonl"\n',
        "[policy]", 'confirm_required = ["firewall", "core_switch", "power"]',
        'teaching_hours = ["08:00-12:00", "13:20-16:00"]', "",
    ]
    for kind, drv in drivers.items():
        lines += [f"[adapters.{kind}]", f'driver = "{drv}"']
        if kind == "switch" and drv == "ssh_cli":
            prof = ask("交換器指令設定檔 dell_os10 / cisco_ios / aruba_cx / hpe_comware / custom", "cisco_ios")
            lines.append(f'profile = "{prof}"')
        lines += ["# 其他參數見 docs/zh-TW/adapters.md", ""]
    site_dir.mkdir(parents=True, exist_ok=True)
    (site_dir / "site.toml").write_text("\n".join(lines), encoding="utf-8")
    inv = site_dir / "inventory"
    inv.mkdir(exist_ok=True)
    for f in ("devices.csv", "spaces.csv"):
        header = (DEMO / "inventory" / f).read_text(encoding="utf-8").splitlines()[0]
        (inv / f).write_text(header + "\n", encoding="utf-8")
    env = site_dir / "secrets.env"
    refs = [r for k, d in drivers.items() if d != "mock" for r in SECRET_REFS.get(k, [])]
    env.write_text("# 只在 backend = env-file 時使用；權限必須 0600，永不提交\n" +
                   "".join(f"{r.upper()}=\n" for r in refs), encoding="utf-8")
    os.chmod(env, 0o600)
    print(f"✓ 已建立 {site_dir}/site.toml；請依 schemas/ 填寫 inventory/devices.csv 與 spaces.csv")
    return site_dir / "site.toml"


def render_skills(site_file: Path, out_dir: Path) -> list[Path]:
    with site_file.open("rb") as f:
        site = tomllib.load(f)
    drivers = ", ".join(f"{k}={v.get('driver', '未設定')}" for k, v in site.get("adapters", {}).items())
    tenets = site.get("tenets", [])
    tenet_md = ""
    if tenets:
        tenet_md = "## 六、本校專屬天條（來自 site.toml [[tenets]]）\n\n" + "\n".join(
            f"{i}. **{t['title']}**：{t['rule']}" for i, t in enumerate(tenets, 1)) + "\n"
    values = {
        "SCHOOL_NAME": site["school"].get("name", "本校"),
        "SITK_CMD": f"{ROOT / 'bin' / 'sitk'} --site {site_file}",
        "ALLOWED_NETWORKS": ", ".join(site["scope"]["allowed_networks"]),
        "DRIVERS": drivers or "未設定",
        "TEACHING_HOURS": "、".join(site.get("policy", {}).get("teaching_hours", [])) or "上課時段",
        "SITE_TENETS": tenet_md,
    }
    written = []
    for tmpl in sorted(TEMPLATES.glob("*/SKILL.md.tmpl")):
        text = tmpl.read_text(encoding="utf-8")
        for k, v in values.items():
            text = text.replace("{{" + k + "}}", v)
        left = re.findall(r"\{\{[A-Z_]+\}\}", text)
        if left:
            raise SystemExit(f"FAIL_CLOSED：{tmpl} 仍有未填佔位 {left}")
        dest = out_dir / tmpl.parent.name / "SKILL.md"
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(text, encoding="utf-8")
        written.append(dest)
    return written


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--example", action="store_true", help="以示範國小建立 site/")
    ap.add_argument("--render-only", action="store_true")
    ap.add_argument("--site-dir", default=str(ROOT / "site"))
    a = ap.parse_args()
    site_dir = Path(a.site_dir)
    site_file = site_dir / "site.toml"
    if not a.render_only:
        if site_file.exists():
            raise SystemExit(f"{site_file} 已存在；要重新產生技能請用 --render-only")
        if a.example:
            shutil.copytree(DEMO, site_dir, dirs_exist_ok=True)
            print(f"✓ 已用示範國小建立 {site_dir}（全部 mock 轉接器，可安全演練）")
        else:
            site_file = write_site_interactive(site_dir)
    if not site_file.exists():
        raise SystemExit(f"找不到 {site_file}")
    for p in render_skills(site_file, site_dir / "skills"):
        print(f"✓ 技能：{p}")
    print("\n下一步：\n"
          f"  1. {ROOT / 'bin' / 'sitk'} --site {site_file} doctor\n"
          "  2. 把 site/skills/ 下的資料夾連結到你的 AI 工具技能目錄，例如：\n"
          f"     ln -s {site_dir / 'skills' / 'sitk-sysadmin'} ~/.claude/skills/sitk-sysadmin")


if __name__ == "__main__":
    main()

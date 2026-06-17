#!/usr/bin/env python3
"""
init-wizard — School IT Toolkit 設定精靈 / setup wizard.

問幾個問題，就在「本機」生成：
  - config/admin.conf           （管理設定）
  - config/credentials.env      （sudo 密碼等）
  - config/network_credentials.env（選填：交換器/PBX）
  - keys/admin_ed25519(.pub)    （管理用 SSH 金鑰，本機生成）

⚠️ 以上全部都被 .gitignore 忽略，永遠不會進入 Git。
   None of these are ever committed — they are all gitignored.

用法 / Usage:
  python3 setup/init-wizard.py
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def ask(prompt, default=""):
    suffix = f" [{default}]" if default else ""
    try:
        ans = input(f"{prompt}{suffix}: ").strip()
    except EOFError:
        ans = ""
    return ans or default


def ask_secret(prompt):
    """讀密碼（不回顯）。非互動環境則略過。"""
    import getpass
    try:
        return getpass.getpass(f"{prompt}（直接 Enter 跳過）: ").strip()
    except (EOFError, Exception):
        return ""


def confirm_overwrite(path):
    if path.exists():
        return ask(f"⚠️ {path.relative_to(ROOT)} 已存在，覆蓋？(y/N)", "N").lower() == "y"
    return True


def write_file(rel, content):
    path = ROOT / rel
    if not confirm_overwrite(path):
        print(f"   略過 {rel}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    print(f"   ✅ 已寫入 {rel}")


def gen_ssh_key(key_rel):
    key_path = ROOT / key_rel
    if key_path.exists():
        print(f"   金鑰已存在，沿用 {key_rel}")
        return
    key_path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["ssh-keygen", "-t", "ed25519", "-N", "", "-C", "school-it-toolkit", "-f", str(key_path)],
        check=True,
    )
    print(f"   ✅ 已在本機生成金鑰 {key_rel}（私鑰不會入庫）")


def main():
    print("=" * 60)
    print(" School IT Toolkit 設定精靈 / setup wizard")
    print(" 所有產出都只存在本機，並已被 .gitignore 忽略。")
    print("=" * 60)

    # 1) 管理設定
    admin_user = ask("統一管理員帳號名稱 / unified admin account", "schooladmin")
    key_rel = ask("管理 SSH 金鑰路徑（相對 repo）", "keys/admin_ed25519")
    ssh_timeout = ask("SSH 連線逾時秒數（WiFi 建議 30）", "12")

    admin_conf = (ROOT / "config/admin.conf.example").read_text(encoding="utf-8")
    admin_conf = (admin_conf
                  .replace('ADMIN_USER="schooladmin"', f'ADMIN_USER="{admin_user}"')
                  .replace('SSH_KEY="keys/admin_ed25519"', f'SSH_KEY="{key_rel}"')
                  .replace('SSH_PUBLIC_KEY="keys/admin_ed25519.pub"', f'SSH_PUBLIC_KEY="{key_rel}.pub"')
                  .replace('SSH_TIMEOUT="12"', f'SSH_TIMEOUT="{ssh_timeout}"'))
    write_file("config/admin.conf", admin_conf)

    # 2) 金鑰
    print("\n[SSH 金鑰]")
    if ask("在本機生成新的 ed25519 管理金鑰？(Y/n)", "Y").lower() != "n":
        try:
            gen_ssh_key(key_rel)
        except Exception as e:
            print(f"   ⚠️ 金鑰生成失敗：{e}（可稍後手動 ssh-keygen）")

    # 3) 憑證
    print("\n[憑證 / credentials]")
    sudo_pass = ask_secret("管理員 sudo 密碼 ADMIN_SUDO_PASS")
    cred = (ROOT / "config/credentials.env.example").read_text(encoding="utf-8")
    cred = cred.replace('ADMIN_SUDO_PASS=""', f'ADMIN_SUDO_PASS="{sudo_pass}"')
    write_file("config/credentials.env", cred)

    # 4) 網路設備（選填）
    print("\n[網路設備憑證 / network gear，選填]")
    if ask("要現在設定交換器/PBX 憑證嗎？(y/N)", "N").lower() == "y":
        sw_user = ask("交換器帳號 SWITCH_USERNAME")
        sw_pass = ask_secret("交換器密碼 SWITCH_PASSWORD")
        net = (ROOT / "config/network_credentials.env.example").read_text(encoding="utf-8")
        net = (net.replace('SWITCH_USERNAME=""', f'SWITCH_USERNAME="{sw_user}"')
                  .replace('SWITCH_PASSWORD=""', f'SWITCH_PASSWORD="{sw_pass}"'))
        write_file("config/network_credentials.env", net)

    # 5) 清冊提示
    print("\n[機器清冊 / inventory]")
    inv = ROOT / "inventory/inventory.csv"
    if not inv.exists():
        print("   尚未有 inventory/inventory.csv。")
        print("   ‣ 已有 ARD：之後可用 tools/mac-fleet 的 export 工具匯出。")
        print("   ‣ 手動：複製 inventory/inventory.example.csv 為 inventory.csv 後填入。")

    print("\n" + "=" * 60)
    print(" ✅ 設定完成！後續：")
    print("   1. 確認 inventory/inventory.csv 已就緒")
    print("   2. 透過 ARD 佈署金鑰：見 docs/zh-TW/ssh-onboarding-via-ard.md")
    print("   3. 測試：tools/mac-fleet/school-ssh --group all -- uptime")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n已取消。")
        sys.exit(130)

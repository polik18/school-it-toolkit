---
title: "轉接器設定與自行擴充"
description: "說明 School IT Toolkit 各類設備轉接器（交換器、Wi-Fi、防火牆、DNS／DHCP、Mac 等）如何在 site.toml 設定、用 mock 演練，以及自行撰寫新轉接器的步驟。"
---

# 轉接器設定與自行擴充

每一類設備在 `site.toml` 用一個 `[adapters.<類別>]` 區段設定。任何類別都可以設 `driver = "mock"` 演練。

| 類別 | 台帳 kind | 內建 driver | 動詞 |
| :--- | :--- | :--- | :--- |
| switch | `switch` | `ssh_cli`（設定檔：`dell_os10` / `cisco_ios` / `aruba_cx` / `hpe_comware` / `custom`） | status、mac-table、lldp、backup、find-mac（唯讀） |
| wifi | `ap`、`wifi_controller` | `fortigate` | aps、clients、reboot |
| firewall | `firewall` | `linux_iptables` | status、lint、apply（死人開關）、persist |
| dnsdhcp | `dnsdhcp` | `bind9_isc` | dns search、dhcp search、dns reload |
| endpoint | `endpoint` | `macos` | status、facts、wake |
| voip | `phone` | `grandstream` | status、reboot |

## 各 driver 參數

### switch / ssh_cli

```toml
[adapters.switch]
driver = "ssh_cli"
profile = "cisco_ios"             # dell_os10 | cisco_ios | aruba_cx | hpe_comware | custom
user_ref = "switch_user"          # 或 user = "..."
password_ref = "switch_password"  # 沒有金鑰時才用，需安裝 sshpass
key = "~/.ssh/sitk_switch"        # 建議

# profile = "custom" 時自訂唯讀指令（只接受 show / display 開頭）
# [adapters.switch.commands]
# version = "show version"
# mac_table = "show mac address-table"
# lldp = "show lldp neighbors"
# running_config = "show running-config"
```

不同韌體輸出格式不同；MAC 表解析可辨識 `aa:bb:..`、`aabb.ccdd.eeff`、`aabb-ccdd-eeff` 三種格式。若你的設備解析不到，請用 `custom` 調整指令或提交新的設定檔。

### wifi / fortigate

```toml
[adapters.wifi]
driver = "fortigate"
controller = "fw-wifi-01"         # 台帳中 kind = wifi_controller
auth = "token"                    # 建議：REST API 管理員 + 最小權限設定檔
token_ref = "fortigate_api_token"
verify_tls = true
```

AP 的台帳列建議把 FortiAP 序號（WTP ID）填在 `aliases`，`wifi aps` 才能對應到空間。

### firewall / linux_iptables

```toml
[adapters.firewall]
driver = "linux_iptables"
device = "fw-core-01"
user = "root"
key = "~/.ssh/sitk_firewall"
rules_script = "/etc/firewall/iptables.sh"
lint_command = "sh -n /etc/firewall/iptables.sh"
persist_command = "netfilter-persistent save"   # 依發行版調整
```

### dnsdhcp / bind9_isc

```toml
[adapters.dnsdhcp]
driver = "bind9_isc"
device = "srv-dns-01"
user = "itadmin"
key = "~/.ssh/sitk_server"
sudo = true
dns_container = ""                # BIND 在 Docker 內時填容器名稱
dhcp_container = ""
zone_dir = "/etc/bind"
dhcpd_conf = "/etc/dhcp/dhcpd.conf"
leases = "/var/lib/dhcp/dhcpd.leases"
```

### endpoint / macos

```toml
[adapters.endpoint]
driver = "macos"
user = "itadmin"
key = "~/.ssh/sitk_admin"
wol_broadcast = "198.51.100.255"
```

### voip / grandstream

```toml
[adapters.voip]
driver = "grandstream"
user_ref = "phone_user"
password_ref = "phone_password"
scheme = "http"
```

## 新增一個 driver

1. 在 `sitk/adapters/` 新增檔案，繼承 `base.py` 中對應的類別（例如 `SwitchAdapter`）。
2. 實作同名動詞，回傳 `dict`，至少含 `status`。
3. 守則：
   - 連線前呼叫 `require_in_scope`；變更前呼叫 `require_apply`（並由 CLI 層處理 `--confirm`）。
   - 憑證只用 `get_secret`，不得把密碼放進命令列參數、日誌或例外訊息。
   - 遠端回傳的自由文字欄位列入 `untrusted_fields`。
   - 預設唯讀；寫入動作必須能 dry-run。
4. 在 `sitk/adapters/__init__.py` 的 `DRIVERS` 註冊。
5. 在 `tests/` 加入解析與 dry-run 測試（不需真實設備）。

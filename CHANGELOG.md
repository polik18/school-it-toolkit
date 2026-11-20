# Changelog

## 2.0.1

- 交換器轉接器改為通用 `ssh_cli`，以指令設定檔支援 Dell OS10、Cisco IOS、Aruba CX、HPE Comware 或自訂；只允許 show/display 唯讀指令；MAC 表解析支援三種 MAC 格式。
- 示範學校改用通用設備名稱；文件移除特定發行版細節。
- 新增「建議建立的可管理資源」文件。

## 2.0.0（v2 全面更新）

- 新增 `sitk` 核心框架與 CLI 門面：站點設定、白名單台帳、Fail-Closed 守門、憑證提供者、批次狀態機、稽核日誌。
- 新增轉接器：Dell OS10、FortiGate/FortiAP、Linux iptables（死人開關）、BIND9 + ISC DHCP、macOS、Grandstream，以及 mock。
- 新增停電／復電分階段流程。
- 新增 AI 技能模板與 `setup/init.py` 技能產生器（含十條通用維運天條）。
- 新增文件：快速開始、架構、資安、轉接器、v1→v2 遷移；`SECURITY.md`、`CONTRIBUTING.md`、CI（測試＋gitleaks）。
- v1 工具保留；範例管理帳號改為 `itadmin`；範例不再出現任何預設密碼；圖片清除 metadata。

## 1.0（凍結）

- Mac 機房 SSH/ARD 納管、Homebrew 大量佈署、交換器與網路電話盤點、本地 AI 工作站。

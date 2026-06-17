# 🌐 網路與拓撲盤點

> 把「全校網路長什麼樣」從工程師腦袋裡，變成可重複盤點、可稽核的清冊與報表。
> 適合接手一個沒有文件的網路環境時，快速建立交換器 / VLAN / 端點對應的全貌。

---

## 0. 概念

盤點分三層，由下而上建立全貌：
1. **清冊（你填）**：交換器、VLAN、地點 → `tools/network-discovery/inventory/*.csv`
2. **採集（工具抓）**：連到交換器抓 running-config / mac-table / arp / lldp → `reports/switch-raw/`
3. **彙整（你或工具）**：交叉比對得出「哪台機器接在哪台交換器哪個埠 / 哪個 VLAN」

> ⚠️ **廠牌差異**：不同交換器的 CLI prompt 與 `show` 指令不同。本工具用通用流程，
> 你可能需要依你的型號微調 `switch-collect` 裡的 `DEFAULT_COMMANDS` 與 prompt。

---

## 1. 標準流程

### 步驟一：填寫清冊
從範本複製並填入你的設備：
```bash
cd tools/network-discovery/inventory
cp switches.example.csv  switches.csv
cp vlans.example.csv     vlans.csv
cp locations.example.csv locations.csv
```
> 這些 `*.csv`（非 `.example`）已被 `.gitignore` 忽略，不會上 GitHub。

### 步驟二：填入交換器憑證
```bash
# 編輯 config/network_credentials.env（由精靈或手動）
SWITCH_USERNAME="..."
SWITCH_PASSWORD="..."
SWITCH_ENABLE_PASSWORD="..."
```

### 步驟三：採集交換器資料
```bash
tools/network-discovery/switch-collect            # 全部 telnet/ssh 交換器
tools/network-discovery/switch-collect --device CORE-SW
```
產出在 `reports/switch-raw/`（每台每指令一個 `.txt`，已 gitignored）。

### 步驟四（選用）：在 Mac 端蒐集本機網路足跡
在受管 Mac 上跑（只讀、不掃描他人、不改設定）：
```bash
tools/mac-fleet/school-ssh --group all -- "$(cat tools/network-discovery/mac-probe-report)"
```
可得每台的網卡、ARP 鄰居、預設路由、Wi-Fi 狀態，協助比對端點位置。

---

## 2. 地雷與避法
- **CLI prompt 不符**：`switch-collect` 預設用 `>`(user)/`#`(enable) 偵測。某些設備 prompt 特殊，需調整 expect 規則。
- **多網卡廣播失效**：見 [`pitfalls.md`](pitfalls.md) E1，採集機若有 VPN/bridge 介面，相關探測要綁實體網卡。
- **憑證外洩風險**：交換器帳密只放 `config/network_credentials.env`（gitignored）；採集到的 `running-config` 可能含密碼雜湊/SNMP community，**`reports/` 已被 `.gitignore` 全擋**，切勿手動加入版控。

---

## 3. 進階（選配，尚未內含）
原始環境另有兩支較大的彙整工具（report / HTML 站台產生器），因含較多環境專屬假設，
列為後續可選模組。若需要把採集資料自動轉成端點對應表與拓撲網站，可在 issue 提出。

## 4. 相關
- `tools/network-discovery/switch-collect` / `mac-probe-report`
- [`ip-phone-audit.md`](ip-phone-audit.md)

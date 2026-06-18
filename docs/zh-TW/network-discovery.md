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

## 3. 實戰教學：老師說「電腦不能上網」end-to-end

這是最常見的求助，也是「Mac × 交換器雙邊對照」最能發揮的場景。下面用一個**去敏的範例**
（所有 IP 用 `192.0.2.x` 測試網段、MAC 用 `aa:bb:cc:*`、主機名用 `LAB-A-07`）走完整流程：
從「聽到問題」到「鎖定根因」再到「對症處理」。

> 🎯 心法：**先看端點（Mac 那一端發生什麼），再看網路（交換器那一端看到什麼），最後對照兩邊。**
> 不靠猜、不亂重開機，每一步都把可能範圍砍一半。

### 全景圖

```
   老師：「這台不能上網」
            │
            ▼
   ┌─────────────────┐        ┌──────────────────────┐
   │  ① Mac 端自述    │        │  ② 交換器端旁證       │
   │  mac-probe-report│        │  switch-collect       │
   │  ─ 有沒有 link？ │        │  ─ MAC 在不在 table？ │
   │  ─ 有沒有 IP？   │        │  ─ 在哪個 port/VLAN？ │
   │  ─ 閘道通不通？  │        │  ─ port 是 up 嗎？    │
   └────────┬────────┘        └───────────┬──────────┘
            └──────────┬───────────────────┘
                       ▼
              ③ 雙邊對照 → 鎖定根因
        （端點設定 / 線路 / port / VLAN / 上游）
```

---

### 步驟 ①：問 Mac 自己——它看到什麼？

如果這台 Mac 還能 SSH（哪怕只有內網通），直接抓它的網路自述：

```bash
# 對單一台跑（把 LAB-A-07 換成清冊裡的主機代號）
tools/mac-fleet/school-ssh --host LAB-A-07 -- "$(cat tools/network-discovery/mac-probe-report)"
```

> 連 SSH 都連不上？那多半是「**完全沒上線**」（link down / 沒拿到 IP / VLAN 不對），
> 直接跳到步驟 ②，從交換器端看它有沒有「冒出來過」。

`mac-probe-report` 會回報幾個關鍵段落，重點看這幾項：

```
## Interfaces
en0 ether aa:bb:cc:11:22:33        ← 記下這個 MAC，等下到交換器反查
en0 inet 192.0.2.77                ← 有沒有拿到「正確網段」的 IP？

## Default Route
   gateway: 192.0.2.1              ← 閘道是誰
   interface: en0

## ARP Neighbors
? (192.0.2.1) at aa:bb:cc:00:00:01 on en0 ifscope [ethernet]   ← 閘道的 ARP 有解析到嗎？
```

對著這三項做第一輪分流：

| Mac 端徵狀 | 初步判斷 | 下一步 |
|------------|----------|--------|
| `en0` 沒有 `inet`（只有 ether，無 IP）或拿到 `169.254.x.x` | **沒拿到 DHCP**：link down、port 沒通、或 VLAN 沒 DHCP | → 步驟②看 port 狀態 |
| 有 IP，但**網段不對**（例如該班該拿 `192.0.2.x` 卻拿到別段） | **VLAN 跑錯** | → 步驟②看 port 的 VLAN |
| 有正確 IP，但 **ARP 解不到閘道**（沒有閘道那行，或 `(incomplete)`） | 上游 / VLAN 間繞送 / 閘道問題 | → 步驟②看 uplink 與 VLAN |
| 有正確 IP、ARP 也解到閘道，但**還是不能上網** | 比較像 **DNS / 對外路由**，不一定是交換器 | 查 `## DNS` 段、ping 外部 IP vs 域名 |

---

### 步驟 ②：問交換器——它看得到這台機器嗎？

用步驟①記下的 **MAC（`aa:bb:cc:11:22:33`）**，到交換器資料裡反查。先採集（或用既有的）：

```bash
tools/network-discovery/switch-collect            # 全部交換器
# 或只抓某台：tools/network-discovery/switch-collect --device EDGE-SW-01
```

採集結果在 `reports/switch-raw/`，每台每指令一個檔。直接 grep 那個 MAC：

```bash
# 不同廠牌 MAC 格式可能是 aabb.cc11.2233 / aa:bb:cc:11:22:33 / aa-bb-cc-11-22-33
grep -i -rE 'aa.?bb.?cc.?11.?22.?33' reports/switch-raw/
```

**情況 A — MAC 出現在某台交換器的 mac-table：**

```
reports/switch-raw/EDGE-SW-01_mac.txt:
  VLAN  MAC Address       Type     Ports
  10    aabb.cc11.2233    DYNAMIC  Gi1/0/7      ← 它接在 EDGE-SW-01 的 Gi1/0/7，VLAN 10
```

→ 知道實體位置了。再看這個 port 的狀態與 VLAN：

```
reports/switch-raw/EDGE-SW-01_status.txt:
  Port      Name        Status        Vlan    Duplex  Speed
  Gi1/0/7   LAB-A-07    connected     10      full    1000    ← connected = 線路 OK
```

對照判讀：

| 交換器端看到的 | 結論 | 處理 |
|----------------|------|------|
| port `connected`、VLAN 正確、Mac 也有正確 IP | 網路層 OK → 問題在**對外/DNS**或應用層 | 查 DNS、ping `1.1.1.1` vs `ping example.com` |
| port `connected`、但 **VLAN 不是該班該用的** | **VLAN 設錯**（換機/換線後沒改） | 把該 port 改回正確 VLAN |
| port `notconnect` / `disabled` / `err-disabled` | **線路或 port 問題** | 換線、換 port、解除 err-disable |
| port `connected` 但 Mac 仍 `169.254` | 該 VLAN **沒有 DHCP**或 DHCP 耗盡 | 查該 VLAN 的 DHCP 範圍 |

**情況 B — grep 完全找不到這個 MAC：**

代表這台機器的封包**根本沒到任何一台你採集的交換器**。可能性：

- 網路線沒插好 / 線壞 / 插到沒在清冊裡的交換器
- Mac 網卡停用或硬體故障（回步驟①看 `## Hardware Ports` 有沒有那張卡）
- 接在 AP/Wi-Fi（這時要看 `## Wi-Fi Status` 段，不是有線 mac-table）

---

### 步驟 ③：雙邊對照，一句話講出根因

把兩邊兜起來，結論通常落在這張表的某一格——這就是「看得見」的價值：

| Mac 端 | 交換器端 | ⇒ 根因 | 動作 |
|--------|----------|--------|------|
| 無 IP | port `notconnect` | 實體線路斷 | 換線 / 換 port |
| 無 IP | port `connected`、VLAN 有 DHCP | DHCP 耗盡或保留衝突 | 查 DHCP 池 |
| IP 網段錯 | port VLAN 錯 | VLAN 設定跑掉 | 改 port VLAN |
| 有 IP、ARP 解不到閘道 | uplink port 異常 / VLAN 不通上游 | 上游中斷 | 查 uplink / trunk |
| 有正確 IP、port 正常 | 一切正常 | 不是網路層，是 DNS/對外 | 查 DNS、對外路由 |
| MAC 遍尋不著 | 任何交換器都沒有 | 沒上線（線/卡/Wi-Fi） | 回步驟① 查實體 |

> 💡 把每次的「徵狀 → 根因 → 動作」記進你的 [`排錯與踩雷紀錄`](pitfalls.md) 風格筆記，
> 下次同類問題可直接命中，這正是讓網路「可交接」的關鍵。

---

## 4. 進階（選配，尚未內含）
原始環境另有兩支較大的彙整工具（report / HTML 站台產生器），因含較多環境專屬假設，
列為後續可選模組。若需要把採集資料自動轉成端點對應表與拓撲網站，可在 issue 提出。

## 5. 相關
- `tools/network-discovery/switch-collect` / `mac-probe-report`
- [`ip-phone-audit.md`](ip-phone-audit.md)

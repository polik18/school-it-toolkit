# 🏫 School IT Toolkit ｜ 學校資訊系統管理工具包

> 用一位學校系管師的實戰探測、納管與**踩雷經驗**，淬煉成可被任何學校快速套用的開源工具包。
> Battle-tested probing, fleet-management, and **hard-won pitfall** know-how from a school IT admin — packaged so any school can adopt it fast.

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

> 📖 **完整介紹文章 / Full write-up**：[一位學校系管師如何讓校園資訊環境「終於看得見」](https://jamespolik.pixnet.net/blog/posts/908160329453493278)
> — 從設計理念、實戰排查案例到導入步驟的完整敘事，新訪客建議先讀這篇。

---

## ✨ 這是什麼 / What is this

不同學校的網段、交換器廠牌、帳號命名、電腦數量都不同。本工具包**分享的是方法，不是資料**——把可重複使用的腳本、SOP，以及最寶貴的「踩過的雷」整理成別校也能直接執行的有效流程，免費回饋社群。

Every school's subnet, switch vendor, account naming, and fleet size differ. This toolkit **shares methods, not data** — reusable scripts, SOPs, and the pitfalls we already hit, turned into procedures other schools can run directly. It's given back to the community for free, not sold.

真正的目標不只是「跑腳本」，而是把 Mac、交換器、IP 話機、連接埠、VLAN 與拓撲串成**一張看得見的校園網管地圖**——讓原本只存在資深系管腦中的隱形基礎設施，變成**可查、可修、可交接**的透明系統。

The real goal isn't just "running scripts" — it's stitching Macs, switches, IP phones, ports, VLANs, and topology into **one visible map of the campus network**, turning infrastructure that used to live only in a veteran admin's head into a system that is **queryable, fixable, and handover-ready**.

### ⭐ 招牌功能 / Flagship capabilities
1. **避雷 + 透過 ARD 納管 SSH** — 用 Apple Remote Desktop 打通並批量佈署 SSH 金鑰，繞過 TCC、kickstart、AppleScript 逾時等地雷。
   *Onboard SSH across the fleet via Apple Remote Desktop, dodging the TCC / kickstart / AppleScript-timeout landmines.*
2. **Homebrew 批量安裝並保持最新** — 全機房一鍵安裝軟體並維持在最新狀態。
   *Install software fleet-wide with Homebrew and keep it continuously up to date.*
3. **Mac × 交換器 雙邊對照定位故障** — 同時掌握端點（Mac 的網路狀態、MAC、ARP）與網路側（交換器 port、MAC table、VLAN），交叉比對快速縮小「不能上網」這類問題的根因。
   *Pinpoint faults by correlating both sides — the endpoint (Mac network state, MAC, ARP) and the network (switch port, MAC table, VLAN) — to rapidly narrow down "can't get online" type problems.*

---

## 🧩 涵蓋範圍 / Scope

| 模組 Module | 內容 |
|------|------|
| `tools/mac-fleet` | Mac 機房批量納管：SSH、ARD 修復、OS 升級、帳號 bootstrap |
| `tools/network-discovery` | 交換器探測、LLDP 拓撲、連接埠對應 |
| `tools/ip-phones` | 網路電話盤點與稽核 |
| `tools/local-ai` | 本地 AI 工作站（oMLX / aider）部署 |

---

## 🔭 實戰情境：「老師說電腦不能上網」/ In action: "the teacher says it can't get online"

工具的價值在真實排查時最明顯。面對最常見的求助，可用系統化流程逐步縮小範圍，而不是靠猜：

1. **Mac 端** — SSH 進該機，查網路狀態、IP、取得網卡 **MAC address**。
2. **交換器端** — 用 MAC 在交換器 **MAC table** 反查它接在哪台交換器、哪個 **port**，看 interface 是否 up。
3. **雙邊對照** — 比對 **ARP** 與 VLAN 是否一致，判斷是設備設定、線路、port、還是 VLAN 問題。
4. **定位根因** — 範圍縮到單一環節後再動手修，避免亂槍打鳥。

> 這正是招牌功能 ③「Mac × 交換器 雙邊對照」的日常用法。
> 📖 **完整 end-to-end 圖文教學**（含分流決策表與各種故障分支）見 [`docs/zh-TW/network-discovery.md` §3 實戰教學](docs/zh-TW/network-discovery.md#3-實戰教學老師說電腦不能上網end-to-end)。

---

## 🧭 導入建議與維運節奏 / Rollout & operating cadence

**小規模試點再推廣 / Start small, then scale**
建議從 **1 台管理端 Mac ＋ 3 台測試 Mac ＋ 1 台測試交換器** 開始，驗證納管、採集與排查流程順暢後，再逐步擴及全校。
Start with **one management Mac, three test Macs, and one test switch**; validate onboarding, collection, and troubleshooting before rolling out fleet-wide.

**固定維運節奏 / A steady cadence**
別等出事才管。建立固定排程能避免問題累積：

| 頻率 | 建議動作 |
|------|----------|
| 每日 / Daily | 處理求助、看是否有異常設備 |
| 每週 / Weekly | 跑 audit 找未完整納管的機器、檢查更新狀態 |
| 每月 / Monthly | Homebrew 批量更新、重新採集交換器拓撲對照清冊 |
| 學期初 / Term start | 全面盤點、新機納管、清冊校正 |
| 假期 / Breaks | 大型升級、重佈署、交接文件更新 |

---

## 🎯 適合什麼樣的校園環境 / Who is this for

本工具包最初是為**靠人力管理一批 Mac** 的學校打造的，但它做的事——**網路拓撲可視化、Mac × 交換器雙邊對照、現場故障排查**——是端點管理／MDM 通常涵蓋不到的，所以**就算你已經有 MDM，網路盤點這一塊仍然用得上**。若你的環境符合以下多數條件，會非常合用：

This toolkit was originally built for schools managing a fleet of Macs **by hand**, but what it does — **network-topology visibility, Mac × switch correlation, and on-site fault triage** — is generally outside what endpoint/MDM tools cover, so the network-discovery side **stays useful even if you already run an MDM**. It fits best if most of the following are true:

**✅ 適合 / A good fit**
- 機房／教室有一批 **macOS 電腦**（Mac mini、iMac 等），尤以 **Apple Silicon** 為主（部分功能假設 `/opt/homebrew` 路徑）。
- **沒有導入 Jamf／Mosyle／Intune 等 MDM**，目前靠 Apple Remote Desktop (ARD) 一台台點。
- 手邊有 **ARD** 可當第一次納管的跳板，且管理機與這些 Mac 在**同一可連通的區域網路**。
- 系管師願意用 **SSH／命令列**管理（具備基本 Python 3 環境）。
- 規模約**數十台**（以教室／電腦教室機房為設計情境）。
- （選配）有 CLI 可登入的**交換器**、可網頁管理的**網路電話**、或一台可跑**本地 LLM** 的 Mac。
- 你對這些機器有**合法管理權限**（本工具會進行 SSH／sudo／改密碼等操作）。

**⚠️ 不太適合 / Probably not for you**
- 管理的是 **Windows／ChromeOS** 機器：本工具的 Mac 納管部分**僅限 macOS**（網路盤點部分仍可用）。
- 你對目標機器**沒有管理授權**：請勿使用。

---

## 🚀 快速開始 / Quickstart

> ⚠️ **請用 `git clone` 取得本工具，不要直接複製整個資料夾。**
> `.gitignore` 只能防止機密進入 Git，**無法防止資料夾被 `cp`／壓縮／AirDrop 整包複製**。
> 一旦你跑過設定精靈，本機資料夾就會含有私鑰與密碼；那份資料夾**不可**再轉交他人。
> **Use `git clone` — do NOT hand someone a copy of your folder.** `.gitignore` keeps
> secrets out of Git, but it does **not** stop a folder copy. After you run the wizard,
> your local folder contains private keys and passwords and must never be shared.

```bash
git clone <your-fork-url> school-it-toolkit
cd school-it-toolkit

# 執行設定精靈：詢問你的網段、帳號、金鑰路徑，
# 自動在「本機」生成 config 與 SSH 金鑰（不會進入 Git）
python3 setup/init-wizard.py
```

> 📖 詳細文件見 [`docs/zh-TW/`](docs/zh-TW/)（繁中完整）與 [`docs/en/`](docs/en/)（English）。

---

## 🔐 安全第一 / Security first

本專案的所有真實資料**只存在你的本機**，並由 `.gitignore` 從第一個 commit 起硬性阻擋：

- 🔑 SSH 私鑰一律由設定精靈**在你本機生成**，repo 永遠零私鑰。
- 🚫 憑證 (`*.env`)、真實清冊 (`inventory/*.csv`)、探測產出 (`reports/`)、交換器設定 (`*_running-config.txt`)、產生的網站 (`index.html`) 全部被忽略。
- ✅ 版本庫只追蹤 `*.example` 範本。

**推送前請務必自行確認沒有機密外洩**。
This repo is designed so **no real credentials, keys, inventories, or scan outputs ever reach Git** — only `*.example` templates are tracked.

### ⛔ 分享時：給網址，不要給資料夾 / Sharing: share the link, not the folder

- ✅ **要分享給其他學校** → 給他們 **GitHub 網址**，請對方 `git clone`。
- ⛔ **不要**把你本機的資料夾整包（`cp`／壓縮／AirDrop）給人——它可能含有你跑精靈後產生的私鑰與密碼，且 `.gitignore` 對複製資料夾**完全無效**。
- 📦 真的需要離線給檔案時，請匯出**只含已提交檔案**的乾淨壓縮包（不含 `.git`、不含任何被忽略的機密）：
  ```bash
  git archive --format=zip -o school-it-toolkit-clean.zip HEAD
  ```

---

## ⚖️ 授權 / License

[MIT](LICENSE) — 歡迎其他學校自由使用、修改、散播。

---

## 🙏 致謝 / Acknowledgements

源自台灣某國小的實際系統管理工作，將踩雷經驗回饋給社群。
Born from real-world IT operations at a Taiwanese elementary school, giving pitfall experience back to the community.

---

<sub>

**關鍵字 / Keywords**：學校 IT 管理、校園資訊組長工具、Mac 機房批量管理、電腦教室管理、Apple Remote Desktop (ARD) 批次納管、SSH 批量管理 macOS、Homebrew 大量佈署、交換器盤點、LLDP 網路拓撲、VLAN／連接埠對應、網路電話盤點、本地 AI 工作站、免 MDM 管理 Mac、無 MDM 校園、IT 交接文件。
School IT management · manage a fleet of Macs without an MDM · macOS fleet management · Apple Remote Desktop SSH onboarding · bulk Homebrew deployment · network discovery · switch / LLDP topology mapping · VLAN & port mapping · IP phone audit · classroom / lab Mac administration · sysadmin toolkit for schools · K-12 IT.

</sub>

# 🏫 School IT Toolkit ｜ 學校資訊系統管理工具包

> 用一位學校系管師的實戰探測、納管與**踩雷經驗**，淬煉成可被任何學校快速套用的開源工具包。
> Battle-tested probing, fleet-management, and **hard-won pitfall** know-how from a school IT admin — packaged so any school can adopt it fast.

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

---

## ✨ 這是什麼 / What is this

不同學校的網段、交換器廠牌、帳號命名、電腦數量都不同。本工具包**不賣資料、只賣方法**——把可重複使用的腳本、SOP，以及最寶貴的「踩過的雷」變成別校也能直接執行的有效流程。

Every school's subnet, switch vendor, account naming, and fleet size differ. This toolkit ships **methods, not data** — reusable scripts, SOPs, and the pitfalls we already hit, turned into procedures other schools can run directly.

### ⭐ 招牌功能 / Flagship capabilities
1. **避雷 + 透過 ARD 納管 SSH** — 用 Apple Remote Desktop 打通並批量佈署 SSH 金鑰，繞過 TCC、kickstart、AppleScript 逾時等地雷。
   *Onboard SSH across the fleet via Apple Remote Desktop, dodging the TCC / kickstart / AppleScript-timeout landmines.*
2. **Homebrew 批量安裝並保持最新** — 全機房一鍵安裝軟體並維持在最新狀態。
   *Install software fleet-wide with Homebrew and keep it continuously up to date.*

---

## 🧩 涵蓋範圍 / Scope

| 模組 Module | 內容 |
|------|------|
| `tools/mac-fleet` | Mac 機房批量納管：SSH、ARD 修復、OS 升級、帳號 bootstrap |
| `tools/network-discovery` | 交換器探測、LLDP 拓撲、連接埠對應 |
| `tools/ip-phones` | 網路電話盤點與稽核 |
| `tools/local-ai` | 本地 AI 工作站（oMLX / aider）部署 |

---

## 🚀 快速開始 / Quickstart

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

**推送前請務必自行確認沒有機密外洩**（後續會提供機密掃描腳本）。
This repo is designed so **no real credentials, keys, inventories, or scan outputs ever reach Git** — only `*.example` templates are tracked.

---

## ⚖️ 授權 / License

[MIT](LICENSE) — 歡迎其他學校自由使用、修改、散播。

---

## 🙏 致謝 / Acknowledgements

源自台灣某國小的實際系統管理工作，將踩雷經驗回饋給社群。
Born from real-world IT operations at a Taiwanese elementary school, giving pitfall experience back to the community.

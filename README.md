# 🏫 School IT Toolkit v2 ｜ AI 系管師工具包

<p align="center">
  <img src="docs/assets/banner.png" alt="校園系管術 — 臺灣學校 IT 管理工具箱：SSH 連線管理、Mac 設備清單、Homebrew 套件管理、網路拓撲、交換器埠口狀態、Apple Remote Desktop 遠端管理與自動化任務" width="100%">
</p>

> 讓 AI（包含可以在學校本機跑的小模型）安全地當你的「系管助手」：查設備在哪、找電腦接在哪個埠、看哪台 AP 離線、批次維護教室電腦、停電後分階段驗收——**先唯讀、後變更，危險動作一定要人點頭**。
> Let an AI assistant — even a small local model — safely help run a school network: read-only first, changes only with explicit human approval.

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

> 🌐 **網站：[polik18.github.io/school-it-toolkit](https://polik18.github.io/school-it-toolkit/)**　｜　📖 **[教學文章：功能介紹與一步一步上手](https://polik18.github.io/school-it-toolkit/blog/ai-sysadmin-tutorial.html)**

---

## ✨ v2 有什麼新東西 / What's new in v2

v1 是一組「Mac 機房 × 交換器盤點」腳本；v2 把「讓 AI 安全參與校園維運」的方法，整理成**任何學校都能套用的框架**：

| v2 能力 | 說明 |
| :--- | :--- |
| 🧭 **單一 CLI 門面 `sitk`** | AI 只需呼叫 `sitk <領域> <動詞> --json`、讀 `status` 欄位，不必拼裝 shell 指令 |
| 📒 **白名單台帳** | 設備與空間只來自你的 CSV 台帳；查不到就回 `UNKNOWN_ASSET`，AI 不能自己猜名稱、網域或 IP |
| 🛡️ **Fail-Closed 安全網** | 預設只預覽（`DRY_RUN`）；變更要 `--apply`；防火牆等高風險還要 `--confirm <目標>`；網段外一律拒絕 |
| 🔁 **狀態機長任務** | 批次維護、停電／復電驗收都能中斷續跑，沒有實測回讀就不能標記完成 |
| 🔌 **轉接器** | 同一組動詞對應不同廠牌：通用 SSH CLI 交換器（Dell / Cisco / Aruba / HPE 指令設定檔）、FortiGate 無線、Linux iptables、BIND9 + ISC DHCP、macOS、Grandstream，另有 mock 供演練；缺的廠牌可自行擴充 |
| 🧠 **AI 技能產生器** | `setup/init.py` 依你的 `site.toml` 產生 Claude Code／Codex 等可用的 SKILL.md（內含通用維運天條） |
| 🔐 **AI 看不到密碼** | 工具自己從 macOS Keychain 或 0600 憑證檔取用；設備回傳內容標示為不可信資料 |

v1 的 Mac 機房與網路盤點工具（`tools/`、`setup/init-wizard.py`）**全部保留**，可繼續使用；見 [v1 → v2 遷移指南](docs/zh-TW/migrate-v1-to-v2.md)。

---

## 🚀 五分鐘試玩（完全不連任何設備）

```bash
git clone https://github.com/polik18/school-it-toolkit.git
cd school-it-toolkit
python3 setup/init.py --example          # 建立「示範國小」站點（全部 mock 轉接器）

bin/sitk doctor
bin/sitk room 三年六班                    # 查空間與裡面的設備
bin/sitk --json wifi aps --offline        # 哪台 AP 離線
bin/sitk wifi reboot 306班                # 只會回 DRY_RUN 預覽
bin/sitk firewall apply --apply           # 被擋：高風險變更需 --confirm
bin/sitk info 火星教室                    # UNKNOWN_ASSET：白名單外不猜測
```

需要 **Python 3.11 以上**，只用標準庫，不需要 `pip install`。

正式導入請看 [快速開始](docs/zh-TW/quickstart.md)；**想先規劃要建立哪些可管理的資源，看 [建議建立的可管理資源](docs/zh-TW/recommendations.md)**；架構說明見 [architecture.md](docs/zh-TW/architecture.md)。

---

## 🧩 組成 / Layout

```
sitk/                核心（站點設定、白名單、守門、憑證、狀態機、稽核日誌）與轉接器
bin/sitk             CLI 門面
skills/templates/    AI 技能模板（sitk-sysadmin / network / endpoints / voip / power）
setup/init.py        v2 初始化精靈：產生 site/ 與本校技能
examples/demo-school 虛構的示範國小（文件專用網段）
schemas/             台帳欄位與輸出格式
tools/  lib/  setup/init-wizard.py   v1 工具（保留）
docs/zh-TW  docs/en  文件
```

你的真實資料全部放在 `site/`（已被 `.gitignore` 排除）：`site.toml`、台帳、憑證檔、產生的技能、備份與日誌。

---

## 🔭 實戰情境：「老師說電腦不能上網」

```bash
bin/sitk --json info 三年六班電腦            # 1. 從台帳找到這台電腦（IP、MAC、所在空間）
bin/sitk --json endpoint status pc-a306      # 2. ping / SSH 是否可達
bin/sitk --json switch find-mac <MAC>        # 3. 接在哪台交換器、哪個埠、哪個 VLAN
bin/sitk --json dhcp search <MAC>            # 4. 有沒有拿到 IP
```

範圍縮到單一環節後再動手修。同一間教室**連續座號**集體斷線，先查排插與電源，而不是改交換器。完整圖文教學見 [`docs/zh-TW/network-discovery.md`](docs/zh-TW/network-discovery.md#3-實戰教學老師說電腦不能上網end-to-end)。

---

## 🎯 適合誰 / Who is this for

- 學校資訊組長／系管師，想讓 AI 協助日常維運，但**不能接受 AI 亂改設定**。
- 想用**本地模型**（不把校內資料送上雲）處理維運問題的學校。
- 設備廠牌不同也沒關係：沒有你的廠牌時，照 [轉接器指南](docs/zh-TW/adapters.md) 補一個類別即可。
- 你對這些設備有**合法管理權限**。

---

## 🔐 安全第一 / Security first

- **真實資料永不進 Git**：`site/`、`*.env`、金鑰、台帳、備份、日誌全被 `.gitignore` 擋下；版本庫只有範本與虛構範例。
- **預設安全**：唯讀優先、`--apply` 才變更、高風險要 `--confirm`、網段外拒絕、死人開關自動回滾、所有變更寫入稽核日誌。
- **雲端模型注意**：不要把台帳、設定備份、日誌貼給雲端服務。
- **分享時給網址，不要給資料夾**：跑過精靈的本機資料夾含有憑證；需要離線檔案請用 `git archive --format=zip -o clean.zip HEAD`。

完整威脅模型與建議見 [docs/zh-TW/security.md](docs/zh-TW/security.md)；回報弱點請看 [SECURITY.md](SECURITY.md)。

---

## ⚖️ 授權 / License

[MIT](LICENSE) — 歡迎其他學校自由使用、修改、散播。

## 🙏 致謝 / Acknowledgements

由**小黃老師**依實際校園系統管理工作整理，將踩雷經驗與 AI 維運方法回饋給社群。
Shared by a Taiwanese elementary-school IT teacher, giving real-world lessons and AI-assisted operations practice back to the community.

---

<sub>

**關鍵字 / Keywords**：AI 系管師、AI 校園網管、學校 IT 管理、校園資訊組長工具、小模型維運、本地 LLM 網管、Mac 機房批量管理、電腦教室管理、Apple Remote Desktop 批次納管、交換器 MAC 找埠、FortiAP 離線查詢、防火牆死人開關、停電復電驗收、網路電話盤點、IT 交接文件。
AI sysadmin for schools · SLM-friendly CLI facade · fail-closed network automation · school network management · macOS fleet management without MDM · switch MAC lookup · FortiAP monitoring · firewall deadman switch · power outage recovery checklist · K-12 IT.

</sub>

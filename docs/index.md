---
title: School IT Toolkit｜AI 系管師工具包
description: 讓 AI（含本地小模型）安全協助校園網路與電腦維運——單一 CLI 門面、白名單台帳、Fail-Closed 安全網、狀態機長任務。
---

![School IT Toolkit](assets/banner.png)

## 讓 AI 當你的校園系管助手，但危險動作一定要人點頭

**School IT Toolkit v2** 把「讓 AI 安全參與校園維運」的方法整理成任何學校都能套用的開源框架：查設備在哪、找電腦接在哪個埠、看哪台 AP 離線、批次維護教室電腦、停電後分階段驗收——**先唯讀、後變更，查不到就停，不讓 AI 猜**。

### 📖 從這裡開始

| | |
| :--- | :--- |
| 🧭 **[教學文章：用 AI 系管師工具包管好校園網路](blog/ai-sysadmin-tutorial.md)** | 功能介紹＋一步一步上手（推薦先讀） |
| 🏗️ [建議建立的可管理資源](zh-TW/recommendations.md) | 導入前該先準備什麼 |
| 🚀 [快速開始](zh-TW/quickstart.md) | 正式導入步驟 |
| 🧱 [架構：讓小模型也能安全維運](zh-TW/architecture.md) | 設計原理與輸出契約 |
| 🔌 [轉接器設定與擴充](zh-TW/adapters.md) | 各廠牌設定、自己寫轉接器 |
| 🔐 [資安說明與威脅模型](zh-TW/security.md) | 哪些資料不能外流、工具內建哪些防護 |
| 🔁 [v1 → v2 遷移](zh-TW/migrate-v1-to-v2.md) | 舊版使用者看這裡 |
| 🌏 [English guide](en/README.md) | Overview in English |

### ✨ 核心能力

- **單一 CLI 門面 `sitk`**：AI 只需呼叫 `sitk <領域> <動詞> --json`，讀 `status` 欄位。
- **白名單台帳**：設備與空間只來自你的 CSV；查不到就回 `UNKNOWN_ASSET`。
- **Fail-Closed 安全網**：預設只預覽；變更要 `--apply`；高風險還要 `--confirm`；網段外一律拒絕；防火牆死人開關自動回滾。
- **狀態機長任務**：批次維護、停電復電可中斷續跑，沒有實測確認不算完成。
- **多廠牌轉接器**：交換器（Dell / Cisco / Aruba / HPE 指令設定檔）、無線控制器、Linux 防火牆、DNS/DHCP、macOS、IP 話機，另有模擬版可演練。
- **AI 技能產生器**：依你的站點設定產生 Claude Code、Codex 或本地模型可用的技能檔。

### 💻 五分鐘試玩（不連任何設備）

```bash
git clone https://github.com/polik18/school-it-toolkit.git
cd school-it-toolkit
python3 setup/init.py --example
bin/sitk room 三年六班
```

原始碼與完整說明：**[GitHub：polik18/school-it-toolkit](https://github.com/polik18/school-it-toolkit)**　｜　授權：MIT　｜　作者：小黃老師

更多作者的教學與系統工具：**[Polik Projects](https://polik18.github.io/)**

# ⭐ Homebrew 批量安裝並保持最新

> 納管完成（SSH 已通）後的第一件大事：讓全機房**裝得到軟體、且永遠是最新版**。
> 用 `tools/mac-fleet/school-brew` 一行指令搞定安裝、佈署、更新。

---

## 0. 為什麼重要

學校機房軟體版本散亂是常態：有的機器有 git、有的沒有；有的卡在舊版有資安風險。
Homebrew 是 macOS 上最乾淨的套件管理方式（裝在使用者空間、好維護）。本工具把
「安裝 Homebrew → 批量裝軟體 → 定期更新」變成可重複、可排程的標準動作。

---

## 1. 標準流程（SOP）

### 步驟一：在缺少 Homebrew 的機器上安裝
```bash
tools/mac-fleet/school-brew --group all setup
```
- 自動偵測 `/opt/homebrew/bin/brew` 是否存在；缺少才安裝。
- 非互動安裝（`NONINTERACTIVE=1`），並**預先快取 sudo**（安裝 Command Line Tools 需要）。
- sudo 密碼來自 `config/credentials.env` 的 `ADMIN_SUDO_PASS`。

### 步驟二：批量安裝你要的軟體
```bash
tools/mac-fleet/school-brew --group all install git wget coreutils
```

### 步驟三：保持最新（可排程）
```bash
tools/mac-fleet/school-brew --group all upgrade
```
等同於每台機器跑 `brew update && brew upgrade && brew cleanup`。

### 步驟四：先看誰過期（不動手）
```bash
tools/mac-fleet/school-brew --group all outdated
```

> 💡 **排程化**：把步驟三包進 cron / launchd，在每週非上課時段自動跑，全校軟體就能長期保持最新。

---

## 2. 地雷與避法（實戰淬煉）

### 🩹 Homebrew 初次安裝需要 sudo（裝 CLT）
* **避法**：`setup` 會用 `echo "$PASS" | sudo -S -v` 預先快取 sudo，再跑 `NONINTERACTIVE=1` 安裝。沒有 `ADMIN_SUDO_PASS` 就會明確報錯，不會卡在互動提示。

### 🩹 安裝很慢、容易逾時
* **原因**：第一次要裝 Command Line Tools + Homebrew core，可能數分鐘。
* **避法**：`--install-timeout` 預設 900 秒（15 分鐘）。網路慢可再加大。

### 🩹 併發太高造成網路壅塞 / 出口頻寬被打爆
* **避法**：`--workers` 預設只開 4。整校同時抓 CLT 會塞爆對外頻寬，**寧可慢一點分批**。

### 🩹 `brew` 不該用 sudo 跑
* **重點**：除了「初次安裝 Homebrew 本體」需要 sudo，之後 `brew install/upgrade` **一律以管理帳號身分跑、不要 sudo**，否則會把權限搞壞。本工具已遵守此原則。

### 🩹 PATH 沒設好，使用者開終端機找不到 brew
* **避法**：搭配 pip wrapper 佈署時會把 `/opt/homebrew/bin` 與使用者 Python bin 寫進 `/etc/zshrc`（若尚未存在）。也可手動確認 `/etc/zshrc` 內含：
  ```bash
  export PATH="/opt/homebrew/bin:$PATH"
  ```

### 🩹（選用）pip 在 macOS 權限錯誤
* **背景**：系統 Python 直接 `pip install` 常因權限失敗。
* **避法**：本包附 `tools/mac-fleet/remote/pip_wrapper.sh`，自動補 `--user`；可佈署成 `/usr/local/bin/pip`。

---

## 3. 驗收清單
- [ ] `school-brew --group all setup` 全部回 OK 或 already installed
- [ ] `school-brew --group all outdated` 確認更新狀態
- [ ] 已將 `upgrade` 排程於非上課時段

---

## 4. 相關工具與文件
- `tools/mac-fleet/school-brew` — 安裝 / install / upgrade / outdated
- `tools/mac-fleet/remote/pip_wrapper.sh` — pip 權限修正
- [`ssh-onboarding-via-ard.md`](ssh-onboarding-via-ard.md) — 前置：先用 ARD 納管 SSH
- [`pitfalls.md`](pitfalls.md) — 完整踩雷大全

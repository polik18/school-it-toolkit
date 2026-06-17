# ⭐ 避雷 + 透過 ARD 納管 SSH

> 在沒有 MDM、機器分散在各教室的環境，如何用 **Apple Remote Desktop (ARD)** 當跳板，
> 把全機房一次打通成「以 SSH 金鑰免密碼管理」，並繞過一路上的所有地雷。

這是整個工具包最核心的能力：**從「只能用 ARD 點來點去」進化到「一行指令管全校」**。

---

## 0. 為什麼用 ARD 當跳板？

第一次納管時，你手上通常只有：
- ARD 看得到機器（但 GUI 操作慢、無法批量腳本化）
- 機器上某個既有帳號（導師帳號、廠商帳號…）的密碼

目標是把它變成：
- 每台機器都有**統一管理員帳號** + 你的 **SSH 公鑰**
- 之後所有管理都走 `ssh -i 金鑰`，快速、可腳本化、可稽核

ARD 的價值在於：當 SSH 還沒通時，它是唯一能「對全部機器同時下指令」的管道。我們用它執行一段
bootstrap 指令，把 SSH 與金鑰佈署好，**之後就不再需要 ARD**。

---

## 1. 標準流程（SOP）

### 步驟一：準備本機設定與金鑰
```bash
python3 setup/init-wizard.py
```
精靈會在本機生成管理金鑰（`keys/admin_ed25519`，**永不入庫**）並寫好 `config/`。

### 步驟二：用 ARD 的「傳送 UNIX 指令 / Send UNIX Command」對全部機器執行 bootstrap
在 ARD 選取所有目標機器 → **管理 > 傳送 UNIX 指令**，以 **root** 身分執行下列（把
`PUBKEY` 換成你 `keys/admin_ed25519.pub` 的內容、`ADMINUSER` 換成你的管理帳號）：

```bash
#!/bin/bash
set -e
ADMINUSER="schooladmin"
PUBKEY="ssh-ed25519 AAAA....your-public-key.... school-it-toolkit"

# 1) 建立統一管理員帳號（若不存在）— 用 sysadminctl，不要手刻 dscl
if ! id "$ADMINUSER" >/dev/null 2>&1; then
  sysadminctl -addUser "$ADMINUSER" -fullName "School Admin" -admin -password - <<<"CHANGE_ME_TEMP_PASS"
fi

# 2) 開啟 Remote Login（SSH）
systemsetup -setremotelogin on

# 3) 佈署公鑰
HOME_DIR=$(dscl . -read /Users/$ADMINUSER NFSHomeDirectory | awk '{print $2}')
mkdir -p "$HOME_DIR/.ssh"
echo "$PUBKEY" >> "$HOME_DIR/.ssh/authorized_keys"
sort -u "$HOME_DIR/.ssh/authorized_keys" -o "$HOME_DIR/.ssh/authorized_keys"
chmod 700 "$HOME_DIR/.ssh"; chmod 600 "$HOME_DIR/.ssh/authorized_keys"
chown -R "$ADMINUSER" "$HOME_DIR/.ssh"

# 4) 讓該帳號可免密碼 sudo（選用；若要保留密碼則略過）
# echo "$ADMINUSER ALL=(ALL) NOPASSWD: ALL" > /etc/sudoers.d/$ADMINUSER
```

### 步驟三：以 SSH 驗證（這一步才是「成功」的真正判準）
```bash
tools/mac-fleet/school-ssh --group all -- "whoami; sw_vers -productVersion"
```
> **ARD 回報「已送出 / submitted」不代表成功**（見地雷 #5）。一律以 SSH 能否登入為準。

### 步驟四：之後全部走 SSH
納管完成後，就用 `school-ssh`、`school-brew` 等工具，不再依賴 ARD GUI。

---

## 2. 一路上的地雷與避法（實戰淬煉）

> 以下每一條都是真的踩過、流血換來的。照做可省下大量時間。

### 🩹 地雷 #1：TCC 保護讓 root 都無法存取使用者目錄
* **症狀**：即使用 root，`ls`/`rm` 使用者的 `Desktop`/`Documents`/`Downloads` 出現 `Operation not permitted`。
* **原因**：macOS TCC 機制保護這些目錄，SSH session 沒有 Full Disk Access。
* **避法**：需要動到這些目錄時，透過該使用者的 GUI session 跑 Finder AppleScript（Finder 原生有完整磁碟權限），並設較長 timeout 防大檔逾時。**佈署 `.ssh/` 不受影響**（那是帳號家目錄根層、非受保護子目錄）。

### 🩹 地雷 #2：ARD AppleScript 執行逾時 (-1712)
* **症狀**：透過 ARD 跑較久的 AppleScript 回 `-1712` 逾時。
* **避法**：把長動作改成「ARD 只負責觸發、實際工作丟背景」，或拆小批次；能用 UNIX 指令就別用 AppleScript。

### 🩹 地雷 #3：Remote Management「拒絕存取」與 kickstart 錯誤
* **症狀**：ARD 顯示機器在清單，但實際下指令「拒絕存取」；用 `kickstart` 重設時報 Perl 錯誤。
* **原因**：Remote Management 服務狀態不一致 / kickstart 參數順序不對。
* **避法**：用 SSH（已通的話）重設 Remote Management；`kickstart` 參數順序要正確（先 `-configure` 相關旗標，最後 `-restart -agent`），並確保帶上 `-privs -all`（見 #5）。

### 🩹 地雷 #4：清單裡看得到 ≠ 管得動
* **症狀**：機器在 ARD 清單，但命令送不進去。
* **避法**：清單存在只代表曾被探測到。真正可管的判準是「SSH 能登入」或「ARD 觀察畫面成功」。納管腳本要以實際登入結果為準，別信清單。

### 🩹 地雷 #5：kickstart 參數順序 / privileges 遺失（ARD 無法觀察或控制螢幕）
* **症狀**：重設後可連線但無法觀察/控制畫面。
* **避法**：`kickstart` 設定權限時務必 `-privs -all`，且 `-restart -agent` 放最後。重設後用 ARD 觀察驗證。

### 🩹 地雷 #6：SSH 通了但 sudo 密碼錯
* **症狀**：金鑰登入成功，但 `sudo` 密碼不對。
* **原因**：班級老師可能改過該帳號密碼；或既有帳號與你以為的不同。
* **避法**：把 sudo 密碼放 `config/credentials.env`（gitignored）集中管理；遇到密碼被改，**不要強制改回**（見 #8），改用其他有效的管理帳號。

### 🩹 地雷 #7：統一帳號 Permission denied，但既有帳號可登入
* **症狀**：新佈的 `schooladmin` SSH 被拒，但舊的導師/科任帳號可登入。
* **避法**：先用「可登入的既有帳號」當跳板，重跑 bootstrap 把金鑰補到統一帳號；確認 `~/.ssh` 權限（700 / 600）與擁有者正確。

### 🩹 地雷 #8：teacher 密碼被班級老師改掉
* **避法**：不要為了統一而強制改回老師密碼（會引發現場糾紛）。改走「另建專用管理帳號」路線，把管理權與老師日常帳號分離。

### 🩹 地雷 #9：升級/重啟導致 SSH 中斷無法追蹤
* **避法**：批量操作放在非上課時段；長任務（如 OS 升級）丟背景並自動重啟，事後用 `school-ssh` 重新驗證版本，而不是盯著連線。

### 🩹 地雷 #10：WiFi 機器 SSH 預設逾時不夠
* **症狀**：WiFi 機器握手 >10s，預設逾時連不上。
* **避法**：對 WiFi 機器用 `--timeout 30`（或在 `admin.conf` 調高 `SSH_TIMEOUT`）。

---

## 3. 驗收清單

- [ ] `school-ssh --group all -- whoami` 全部回傳你的管理帳號
- [ ] `school-ssh --group all -- "sudo -n true || echo NEED_PASS"` 確認 sudo 策略一致
- [ ] 失敗的機器另記，逐台用既有帳號跳板補做（#7）

---

## 4. 相關工具與文件
- `setup/init-wizard.py` — 生成設定與金鑰
- `tools/mac-fleet/school-ssh` — 批量 SSH
- [`homebrew-fleet.md`](homebrew-fleet.md) — 納管後第一件事：佈署/更新軟體
- [`pitfalls.md`](pitfalls.md) — 完整踩雷大全

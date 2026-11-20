# 🩹 踩雷大全 / Pitfalls

> 這些都是在真實學校機房管理中流血換來的經驗。每一條都是「症狀 → 原因 → 避法」。
> 所有範例已移除真實 IP、主機名與密碼，請代換成你環境的值。

分類：
- [A. SSH 與批量連線](#a-ssh-與批量連線)
- [B. Apple Remote Desktop（ARD）](#b-apple-remote-desktopard)
- [C. 帳號與權限](#c-帳號與權限)
- [D. macOS 升級](#d-macos-升級)
- [E. 網路與喚醒](#e-網路與喚醒)
- [F. 工程慣例](#f-工程慣例)

---

## A. SSH 與批量連線

### A1. SSH 在 `while read` 迴圈中只跑前幾台就停 ★★★
* **症狀**：用 `while read` 迴圈批量 SSH，跑完前約 10 台就莫名停止。
* **原因**：SSH 預設會讀 stdin，把 pipe 內容整個吞掉。
* **避法**：迴圈內的 ssh 一律加 `-n`：
  ```bash
  while IFS=: read -r name ip; do
    ssh -n -i "$KEY" "$USER@$ip" "hostname" &
  done < <(some_command)
  ```

### A2. 背景 SSH 卡死（狀態 T / SIGTTIN）★★★
* **症狀**：並行背景 SSH 偵測時整個程序卡死。
* **原因**：某些機器未佈金鑰，SSH 改試密碼並開 `/dev/tty`，背景程序讀寫 TTY 被 `SIGTTIN`/`SIGTTOU` 暫停（狀態 `T`）。
* **避法**：背景/非互動 SSH 一律加 `-o BatchMode=yes`，連線失敗立即返回不卡住。本工具包所有腳本已內建。

### A3. 受限沙盒環境執行 SSH 出現 `Operation not permitted` 誤判 ★★
* **症狀**：在受限沙盒（部分 AI agent 執行環境）直接 `ssh` 立即回 `Operation not permitted`。
* **原因**：本機沙盒攔截，**不代表**遠端沒開 SSH 或網路不通。
* **判讀**：`Operation not permitted` 先當本機環境問題；只有解除沙盒後仍出現 `Connection refused` / `Operation timed out` / `Permission denied (publickey)` 才歸類為遠端狀態。

---

## B. Apple Remote Desktop（ARD）

### B1. AppleScript 執行 ARD 指令逾時（-1712）★★★
* **症狀**：用 `osascript` 叫 ARD 送 Unix 指令時拋 `AppleEvent 逾時 (-1712)`。
* **原因**：AppleEvent 預設只等 60 秒；大批離線機器會拖長等待。
* **避法**：把迴圈包進 `with timeout of 3600 seconds` 區塊。

### B2. ARD 送出逾時 ≠ 失敗，要以 SSH 為準 ★★★
* **症狀**：AppleScript 回 `submitted timeout`，看似失敗。
* **真相**：那只代表 AppleScript 沒等到乾淨回覆。實際結果要看後續 SSH：
  - 送出逾時 + SSH 可登入 → **已成功**。
  - 送出逾時 + `Connection refused` → SSH 當下未開，**等 3~10 分鐘再複查**，仍 refused 才算失敗。
  - 送出逾時 + `Permission denied` → SSH 開了但金鑰/帳號未完成，重跑 bootstrap。

### B3. 清單看得到 ≠ 管得動 ★★★
* **症狀**：機器在 ARD 清單、甚至有 last_contacted，但指令送不進去。
* **避法**：清單只代表曾被探測。真正判準是「SSH 可登入」或「ARD 連接埠 3283+5900 可達」。用 `tools/mac-fleet/school-audit` 取得實際證據。

### B4. Remote Management「拒絕存取」與 kickstart Perl 錯誤 ★★★
* **症狀**：bootstrap 後用舊帳號連 ARD 顯示「拒絕存取」；背景 SSH 跑 `kickstart -activate` 報 Perl `Can't call method "print" on an undefined value`。
* **原因**：(1) 存取被限縮成單一帳號；(2) TCC 禁止背景寫入 `RemoteManagement.launchd`。
* **避法**：
  1. kickstart 的 `-users` 要同時保留管理帳號與既有教學帳號。
  2. 已納管機器臨時修權限時**不要**帶 `-activate` / `-access -on`（避免觸發寫 launchd），改用純設定：
     ```bash
     sudo .../kickstart -configure -allowAccessFor -specifiedUsers \
       -users ADMINUSER,teacher -privs -all -restart -agent -menu
     ```

### B5. kickstart 參數順序錯 → 可連線但無法觀察/控制螢幕 ★★★
* **症狀**：ARD 能連但看不到/控不了畫面；`dscl . -read /Users/USER naprivs` 顯示 `-2147483648`（已啟用但權限全 0）。
* **避法**：把「全域存取原則」與「使用者權限」**拆成兩步**，且 `-privs -all` 要放在 `-users` **之前**：
  ```bash
  # 1) 全域：僅允許指定使用者
  kickstart -configure -allowAccessFor -specifiedUsers
  # 2) 使用者權限：privs 在 users 之前
  kickstart -configure -access -on -privs -all -users ADMINUSER,teacher -restart -agent -menu
  ```
  正確寫入後 `naprivs` 應為 `-1073741569`（全功能）。

### B6. ARD GUI 批量改密碼存成「無帳號密碼」/ 視窗更名錯誤(-10006) ★★★
* **症狀**：用 AppleScript 直接 `set value` 填欄位，按完成卻沒存進去；切換群組後視窗更名導致快取的視窗物件失效。
* **避法**：
  1. 先 `click` 欄位取得焦點，設剪貼簿後用鍵盤模擬 `Cmd+A`、`Cmd+V` 貼上，強制 Cocoa 接收變動才會存檔。
  2. 視窗一律用動態的 `window 1`，不要快取以名稱命名的視窗變數。
  3. 動作前遍歷關閉殘留設定彈窗，完成後若停在摘要模式主動關閉。

---

## C. 帳號與權限

### C1. TCC 保護讓 root 都無法存取使用者目錄 ★★★
* **症狀**：即使 root，存取使用者 `Desktop`/`Documents`/`Downloads` 出現 `Operation not permitted`。
* **原因**：macOS TCC 保護這些目錄，SSH session 沒有 Full Disk Access。
* **避法**：透過該使用者 GUI session 跑 Finder AppleScript（Finder 原生有完整磁碟權限），並設較長 timeout 防大檔逾時。

### C2. SSH 可登入但 sudo 密碼錯 ★★★
* **症狀**：金鑰登入成功，`sudo` 卻 `incorrect password attempts`。
* **原因**：該帳號密碼被現場老師改過，或與設定檔不符。
* **避法**：sudo 密碼集中放 `config/credentials.env`（gitignored）；遇錯**立刻停止批量**避免連續打錯鎖帳號，先單台修正驗證再小批量。

### C3. 統一帳號被拒但既有帳號可登入 ★★★
* **症狀**：新管理帳號 SSH 被拒，舊教學帳號可登入。
* **避法**：先用可登入的既有帳號當跳板重跑 bootstrap 補金鑰；確認 `~/.ssh` 權限 700、`authorized_keys` 600、擁有者正確。

### C4. 教學帳號密碼被改：不要強制改回 ★★★
* **原因**：硬改回共用密碼會破壞現場老師既有使用方式、引發糾紛。
* **避法**：盤點各帳號狀態，改用另一個可用的管理/科任帳號；無法確認者列入現場確認，**不要猜或覆蓋密碼**。

### C5. SSH 通但 ARD 3283/5900 不通：用 SSH 重配即可 ★★★
* **症狀**：管理帳號 SSH 已通，但稽核顯示 ARD 連接埠不通。
* **避法**：這不是金鑰問題，**不要重走 ARD bootstrap**。直接用 `school-ssh` 以管理帳號跑 `kickstart -configure`（見 B5）把各帳號寫入完整 ARD 權限。

---

## D. macOS 升級

### D1. 升級到「最新版」而非指定版本
* **注意**：`softwareupdate -ia --restart` 會升到偵測到的最新版。要精準控制版本需部署 installer 並用 `startosinstall`。

### D2. Apple Silicon 背景升級報 `SACLOStartLogoutWithOptions() failed: 22` ★★★
* **原因**：當 console 有使用者登入時，macOS 禁止非互動 SSH 背景登出/中斷 GUI 會話。
* **避法**：
  1. 暫時關自動登入（備份 `/etc/kcpassword`、清空 `com.apple.loginwindow autoLoginUser`）。
  2. `sudo killall -HUP loginwindow` 強制登出 console（回到 0 活躍使用者）。
  3. 重跑升級與重啟；完成後復原自動登入設定。

### D3. APFS Volume Owner 認證失敗（`Failed to authorize` / `BootPolicy Code 7`）★★★
* **原因**：Apple Silicon 升級前需由合法 **APFS Volume Owner** 安全認證。若指定帳號的 APFS 密碼與登入密碼不同步、或不是 Volume Owner，認證就失敗。
* **避法**：
  ```bash
  diskutil apfs listUsers /          # 找出有效的 Volume Owner
  printf 'PASS' | softwareupdate -ia --restart --user VALID_OWNER --stdinpass
  ```

### D4. 升級/重啟造成 SSH 中斷無法追蹤
* **避法**：放非上課時段；長任務丟背景並自動重啟，事後用 `school-ssh` 重查版本，不要盯著連線。

---

## E. 網路與喚醒

### E1. 多網卡主機 UDP 廣播 `No route to host`（Errno 65）★★
* **症狀**：管理機有 VPN `utun`/`bridge` 等虛擬介面時，廣播 WoL 報 `[Errno 65] No route to host`。
* **原因**：系統選錯輸出介面。
* **避法**：建立 socket 後 `bind` 到實體有線網卡 IP，強制由它送出，並同時對目標 IP 送 unicast。`tools/mac-fleet/school-wake --bind-ip <實體網卡IP>` 已支援。

### E2. WiFi 機器 SSH 預設逾時不夠
* **症狀**：WiFi 機器握手 >10s，預設逾時連不上。
* **避法**：WiFi 機器用 `--timeout 30`，或在 `admin.conf` 調高 `SSH_TIMEOUT`。

---

## F. 工程慣例

### F1. 不要寫死絕對路徑（可攜化）★★★
* **問題**：腳本/手冊寫死家目錄或某機特定路徑，搬到別機/隨身碟就失效。
* **慣例**：
  1. 用相對法定位根目錄（本工具包靠 `lib/schooltk.py` 往上找 `config/admin.conf.example`）。
  2. 所有學校專屬值放 `config/`（gitignored），腳本本身零機密。
  3. 依賴的檔案自包含在 repo 內，不指向外部臨時目錄。
  4. 改完用 `grep` 確認無寫死的真實 IP/密碼/路徑，再提交。

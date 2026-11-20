# 架構：讓小模型也能安全維運

## 為什麼要這樣設計

讓 AI 直接操作網路設備，最常見的失敗不是「不會」，而是：

1. **拼錯指令**：管線、引號、正規表達式、範本語法一錯，就是錯的設定。
2. **自己編名稱**：把服務名稱猜成網域、把教室名稱猜成設備名稱，然後對錯的目標動作。
3. **跳步驟**：長任務做到一半中斷，回來後憑印象繼續，漏做或重做。
4. **太好說話**：使用者一句「順便改一下」，就動了防火牆。

小模型（在學校本機就跑得動的模型）更容易犯這些錯。v2 的做法是：**把會出錯的部分全部移進程式裡**，讓 AI 只剩「選指令、讀結果」兩件事。

## 四層防護

```
┌──────────────┬──────────────────────────────────────────────┐
│ 1. 介面層    │ 單一 CLI 門面 sitk；固定動詞、--json、--apply      │
│ 2. 編排層    │ 長任務由 JSON 狀態機推進；中斷後 RESUME            │
│ 3. 語意層    │ 白名單台帳；查不到回 UNKNOWN_ASSET，不猜測          │
│ 4. 防護層    │ Fail-Closed：網段、生命週期、確認、憑證都在程式把關 │
└──────────────┴──────────────────────────────────────────────┘
```

## 三層程式結構

```
site/（每校自己的，永不提交）
  site.toml、inventory/*.csv、secrets.env 或 Keychain
        │
sitk/（公開、可測試）
  site.py      讀 site.toml，網段範圍為空就拒絕啟動
  registry.py  台帳 = 白名單；別名查詢；0 筆就拒絕
  guard.py     網段範圍、ACTIVE/STAGING、--apply、--confirm、DNS 先行
  secrets.py   Keychain / 0600 檔 / 環境變數；沒有就拒絕，不用預設密碼
  state.py     批次狀態機：pending → running → done/failed（需 --verified）
  audit.py     變更寫入 append-only JSONL，自動遮蔽密碼欄位
  adapters/    各廠牌轉接器（同一組動詞）＋ mock
  workflows/   停電／復電分階段流程
        │
skills/templates/ → setup/init.py → site/skills/（本校專屬 AI 技能）
```

## 輸出契約

所有指令 `--json` 輸出都是一個物件，`status` 為固定值：

| status | exit code | 意義 |
| :--- | :--- | :--- |
| `OK` / `NEXT` / `RESUME` / `ALL_DONE` / `MANUAL` | 0 | 正常 |
| `DRY_RUN` | 0 | 只預覽，未變更；`plan` 欄位說明將做什麼 |
| `NOT_ACTIVE` | 1 | 設備非 ACTIVE，結果不代表線上現況 |
| `UNKNOWN_ASSET` | 2 | 白名單查不到 |
| `FAIL_CLOSED` / `OUT_OF_SCOPE` | 3 | 安全檢查擋下 |
| `ADAPTER_ERROR` | 4 | 設備連線或回應錯誤 |

設備回傳的欄位（主機名、SSID、描述）會列在 `untrusted`，AI 只能把它們當資料，不能當指令（防提示注入）。

## 通用天條從哪來

`skills/templates/sitk-sysadmin` 的十條天條，來自實際校園維運中反覆踩到的問題（例如連續座號離線其實是排插沒開、100G 埠插 40G 模組的假性 LOS、Wi-Fi 本地橋接改隧道造成全校斷線、MTU 黑洞造成「文字通檔案不通」）。各校自己的特殊規則寫在 `site.toml` 的 `[[tenets]]`，會一起產生進技能。

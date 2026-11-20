# 快速開始（正式導入）

> 建議順序：示範站點演練 → 建立自己的台帳 → 只開唯讀轉接器 → 試點一個空間 → 再開放變更動作。

## 0. 需求

- Python 3.11 以上（只用標準庫）。
- 管理電腦能連到各設備的管理網段。
- 你對這些設備有合法管理權限。

## 1. 用示範站點熟悉指令

```bash
python3 setup/init.py --example --site-dir /tmp/demo-site
bin/sitk --site /tmp/demo-site/site.toml doctor
```

## 2. 建立自己的站點

```bash
python3 setup/init.py            # 互動式：學校名稱、管理網段、各類轉接器、憑證來源
```

產生：

| 檔案 | 用途 |
| :--- | :--- |
| `site/site.toml` | 站點設定（網段範圍、轉接器、政策、停電階段） |
| `site/inventory/devices.csv` | 設備台帳（欄位見 `schemas/inventory.md`） |
| `site/inventory/spaces.csv` | 空間台帳（班級、專科教室、別名） |
| `site/secrets.env` | 只在 `backend = "env-file"` 時使用，權限 0600 |
| `site/skills/*/SKILL.md` | 本校專屬 AI 技能 |

**網段範圍（`scope.allowed_networks`）請只填管理網段**，工具不會對範圍外的位址動作。

## 3. 填台帳

- 一行一台設備；`status` 用 `ACTIVE` / `STAGING` / `RETIRED` / `SPARE`。
- `aliases` 用 `|` 分隔，填老師平常的叫法（例如 `306班|三年六班`），AI 才查得到。
- 台帳就是白名單：沒列的設備，工具一律回 `UNKNOWN_ASSET`。

## 4. 設定憑證（AI 永遠看不到）

macOS 建議用 Keychain：

```bash
security add-generic-password -s sitk -a switch_user -w      # 互動輸入，不留在 shell 歷史
security add-generic-password -s sitk -a switch_password -w
```

並在 `site.toml` 設 `[secrets] backend = "keychain"`。各轉接器需要哪些憑證參照，見 [adapters.md](adapters.md)。

**建議**：為巡檢建立**唯讀帳號**；變更用的帳號另外建立，並只在需要時使用。

## 5. 逐類開啟轉接器

先把 `[adapters.*] driver` 一類一類從 `mock` 改成真實轉接器，每改一類就跑：

```bash
bin/sitk doctor
bin/sitk --json switch status <一台交換器>
```

## 6. 接上 AI 工具

```bash
python3 setup/init.py --render-only
ln -s "$PWD/site/skills/sitk-sysadmin" ~/.claude/skills/sitk-sysadmin   # Claude Code 範例
```

其他技能（`sitk-network`、`sitk-endpoints`、`sitk-voip`、`sitk-power`）視需要一併連結。使用本地模型（Ollama、oMLX 等）時，把 `SKILL.md` 內容放進系統提示即可。

## 7. 試點與節奏

- 先在一個空間試點一週，確認查詢正確、沒有誤動作，再擴大。
- 變更動作開放前，先確認稽核日誌（`site/logs/audit.jsonl`）有正確記錄。
- 學期初重新校正台帳；設備調撥時記得改 `status`。

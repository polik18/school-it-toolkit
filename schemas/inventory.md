# 台帳格式

## devices.csv

| 欄位 | 必填 | 說明 |
| :--- | :--- | :--- |
| `name` | ✓ | 唯一名稱，例如 `sw-core-01`、`pc-a306` |
| `kind` | ✓ | `switch` / `ap` / `wifi_controller` / `firewall` / `dnsdhcp` / `endpoint` / `phone`（可自訂，轉接器依此篩選） |
| `ip` | ✓ | 管理 IP，必須落在 `scope.allowed_networks` 內才會被操作 |
| `mac` |  | 小寫冒號格式；喚醒與找埠需要 |
| `model` |  | 型號 |
| `space` |  | 對應 `spaces.csv` 的 `code` |
| `status` | ✓ | `ACTIVE` / `STAGING` / `RETIRED` / `SPARE` |
| `aliases` |  | `|` 分隔的別名（老師的叫法、AP 序號等） |
| `tags` |  | `|` 分隔標籤，例如 `core`；停電流程可依標籤分組 |

## spaces.csv

| 欄位 | 必填 | 說明 |
| :--- | :--- | :--- |
| `code` | ✓ | 空間代碼，例如 `A306` |
| `name` | ✓ | 顯示名稱，例如 `三年六班` |
| `building` |  | 大樓 |
| `floor` |  | 樓層 |
| `aliases` |  | `|` 分隔，例如 `306班|306|三年六班` |

## 規則

- 台帳就是白名單：讀到 0 筆、缺欄位、`status` 不合法都會 Fail-Closed。
- 真實台帳放在 `site/inventory/`，永不提交。

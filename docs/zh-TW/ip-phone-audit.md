# ☎️ 網路電話盤點與稽核

> 盤點全校 IP 話機，並稽核「是否還在用預設帳密」這個常見資安破口。

---

## 0. 概念

學校 IP 話機常見問題：分機/位置沒文件、網頁管理仍是出廠預設 `admin/admin`。
本模組讓你：
1. 用清冊管理話機（分機、位置、接的交換器埠、VLAN）
2. 自動稽核每台話機網頁登入，標記「預設帳密仍可登入」的高風險機。

> ⚠️ **廠牌差異**：話機網頁登入路徑、編碼、成功判斷字串依型號不同。
> 預設假設常見的 `default.htm` 表單登入 + `big5` 編碼，請依你的型號調整
> `audit-phones` 內的 `LOGIN_PATH` / `SUCCESS_MARKERS` / `PAGE_ENCODING`。

---

## 1. 標準流程

### 步驟一：填寫話機清冊
```bash
cd tools/network-discovery/inventory
cp ip_phones.example.csv ip_phones.csv   # 填入你的話機（gitignored）
```

### 步驟二：設定話機網頁帳密
於 `config/network_credentials.env`：
```bash
PHONE_USERNAME="admin"
PHONE_PASSWORD="admin"
```

### 步驟三：執行稽核
```bash
tools/network-discovery/audit-phones
```
輸出每台狀態並回寫清冊的 `note` / `pbx_status` 欄：
- 🟢 **預設帳密仍可登入** → 高風險，建議盡快改密碼
- ✅ 預設帳密被拒 → 較安全
- 離線 / 無法連線

---

## 2. 地雷與避法
- **誤判成功/失敗**：成功判斷靠頁面字串，換型號要重新確認 `SUCCESS_MARKERS`。
- **編碼亂碼**：舊話機網頁多為 `big5`；新型可能 `utf-8`。
- **隱私**：`ip_phones.csv` 含分機與位置對應，屬內部資料，已被 `.gitignore` 忽略。

## 3. 相關
- `tools/network-discovery/audit-phones`
- [`network-discovery.md`](network-discovery.md)

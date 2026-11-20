# v1 → v2 遷移指南

v1 的工具全部保留，**不遷移也能照常使用**。v2 是在旁邊新增 `sitk` 框架與 AI 技能。

## 對照

| v1 | v2 |
| :--- | :--- |
| `setup/init-wizard.py`（Mac 機房設定、金鑰） | 保留；v2 另用 `setup/init.py` 建立 `site/` |
| `config/admin.conf` 的 `ADMIN_USER` | `site.toml` `[adapters.endpoint] user` |
| `config/network_credentials.env` | Keychain 或 `site/secrets.env`（0600），以 `*_ref` 參照 |
| `inventory/inventory.csv`（Mac 清冊） | `site/inventory/devices.csv`（`kind = endpoint`） |
| `tools/network-discovery/inventory/switches.csv` | `devices.csv`（`kind = switch`） |
| `tools/network-discovery/inventory/ip_phones.csv` | `devices.csv`（`kind = phone`） |
| `tools/network-discovery/inventory/locations.csv` | `site/inventory/spaces.csv` |
| `tools/mac-fleet/school-wake` | `sitk endpoint wake`（含網段範圍與預覽） |
| `tools/network-discovery/switch-collect` | `sitk switch backup` / `mac-table` / `lldp` |
| `tools/network-discovery/audit-phones` | `sitk voip status`（會提醒出廠密碼） |

## 步驟

1. `python3 setup/init.py`，管理網段填你 v1 清冊實際使用的網段。
2. 把 v1 清冊整併到 `devices.csv`，補上 `kind`、`space`、`status`、`aliases`。
3. 憑證改存 Keychain（或 `site/secrets.env`，權限 0600）。
4. 逐類開啟轉接器並跑 `bin/sitk doctor`。
5. `python3 setup/init.py --render-only` 產生技能，接上你的 AI 工具。

## 變更提醒

- v2 範例與預設的管理帳號名稱改為 `itadmin`（只是範例，請用你自己的）。
- v2 不會使用任何出廠預設密碼；找不到憑證就拒絕執行。

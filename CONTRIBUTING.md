# 貢獻指南

歡迎各校老師分享轉接器、天條與踩雷經驗！

## 送 PR 前必讀（資安）

1. **不要提交任何真實資料**：IP、網段、網域、校名、人名、帳號、密碼、MAC、序號、設定檔、截圖。
2. 範例一律使用文件專用位址：IPv4 `192.0.2.0/24`、`198.51.100.0/24`、`203.0.113.0/24`；MAC `00:00:5e:00:53:xx`；網域 `example.edu`、`school.example`。
3. 圖片請先清除 EXIF／metadata。
4. 踩雷經驗請寫成「症狀 → 判讀 → 解法」，不要寫是哪所學校、哪台設備、還沒修好的弱點。
5. Commit 信箱請用 GitHub 的 noreply 信箱。

## 程式守則

- 只用 Python 標準庫（3.11+）。
- 新動作預設唯讀；會變更設定的動作必須支援 dry-run（`require_apply`）。
- 連線前檢查網段範圍（`require_in_scope`）；憑證只用 `get_secret`。
- 遠端回傳的自由文字欄位列入 `untrusted_fields`。
- 補測試：`python3 -m unittest discover -s tests`。

## 審核

修改守門檢查（`sitk/guard.py`、`sitk/secrets.py`、`sitk/site.py`、`sitk/registry.py`）或任何轉接器寫入路徑的 PR，需維護者親自審核後才會合併。

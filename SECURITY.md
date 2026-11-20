# 安全政策 / Security Policy

## 回報弱點

請**不要**在公開 issue 回報弱點。請使用 GitHub 的 **Report a vulnerability**（Security → Advisories → Private vulnerability reporting）私下回報。

回報時請提供：受影響的檔案／版本、重現步驟、可能影響。請**不要**附上任何學校的真實 IP、帳號、密碼或設定檔。

## 範圍

- `sitk/` 核心與轉接器的安全檢查可被繞過（例如網段範圍、`--apply`、`--confirm`、生命週期檢查）。
- 憑證可能出現在命令列、日誌、輸出或例外訊息中。
- 注入（指令、路徑、提示注入）。
- 範例或文件中意外包含真實學校資訊。

## 支援版本

| 版本 | 狀態 |
| :--- | :--- |
| 2.x | 支援 |
| 1.x | 僅修正安全問題 |

Please report vulnerabilities privately via GitHub's "Report a vulnerability". Never include real school IPs, credentials, or configs.

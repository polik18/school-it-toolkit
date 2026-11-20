"""sitk — School IT Toolkit v2 核心（AI 系管師框架）.

設計原則（SLM-First）：
  1. CLI 門面：小模型只呼叫 `sitk <領域> <動詞>`，不拼裝 shell。
  2. 狀態機：多設備長任務由 JSON 狀態檔推進。
  3. 封閉白名單：資產只來自站點台帳，未知一律 UNKNOWN_ASSET。
  4. Fail-Closed：安全檢查寫在程式裡，未通過就拒絕執行。

只使用 Python 3.11+ 標準庫。
"""

__version__ = "2.0.0"

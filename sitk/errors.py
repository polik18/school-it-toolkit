"""統一錯誤型別。每個錯誤都帶有給小模型讀的固定狀態碼。"""


class SitkError(Exception):
    status = "ERROR"
    exit_code = 1

    def __init__(self, message: str, **details):
        super().__init__(message)
        self.message = message
        self.details = details

    def to_dict(self) -> dict:
        return {"status": self.status, "message": self.message, **self.details}


class UnknownAsset(SitkError):
    """查詢目標不在站點白名單（台帳）中。"""
    status = "UNKNOWN_ASSET"
    exit_code = 2


class FailClosed(SitkError):
    """前置安全檢查未通過，拒絕執行。"""
    status = "FAIL_CLOSED"
    exit_code = 3


class OutOfScope(FailClosed):
    """目標位址不在 site.toml 允許的網段內。"""
    status = "OUT_OF_SCOPE"


class ConfirmationRequired(SitkError):
    """變更類動作缺少 --apply 或明確確認。"""
    status = "DRY_RUN"
    exit_code = 0


class AdapterError(SitkError):
    status = "ADAPTER_ERROR"
    exit_code = 4

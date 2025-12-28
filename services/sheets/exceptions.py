"""Django ATS - Google Sheets例外クラス

Sheets操作に関連する例外を定義。
"""


class SheetsError(Exception):
    """Sheets操作の基底例外クラス"""

    def __init__(self, message: str, original_error: Exception = None):
        super().__init__(message)
        self.message = message
        self.original_error = original_error

    def __str__(self):
        if self.original_error:
            return f"{self.message} (原因: {self.original_error})"
        return self.message


class SheetsAuthError(SheetsError):
    """認証エラー

    サービスアカウントの認証に失敗した場合。
    - 認証情報が無効
    - 認証情報が期限切れ
    - 認証情報が未設定
    """
    pass


class SheetsNotFoundError(SheetsError):
    """スプレッドシート未発見エラー

    指定されたスプレッドシートが存在しない場合。
    - スプレッドシートIDが無効
    - スプレッドシートが削除された
    - シート名が存在しない
    """
    pass


class SheetsPermissionError(SheetsError):
    """権限エラー

    スプレッドシートへのアクセス権限がない場合。
    - サービスアカウントに共有されていない
    - 読み取り/書き込み権限が不足
    """
    pass


class SheetsRateLimitError(SheetsError):
    """レート制限エラー

    Google Sheets APIのレート制限に達した場合。
    - 300リクエスト/分/プロジェクト
    - 60リクエスト/分/ユーザー
    """

    def __init__(self, message: str, retry_after: int = None, original_error: Exception = None):
        super().__init__(message, original_error)
        self.retry_after = retry_after  # 秒


class SheetsValidationError(SheetsError):
    """データ検証エラー

    スプレッドシートのデータが期待する形式と異なる場合。
    - 必須カラムが存在しない
    - データ型が不正
    - 値が範囲外
    """

    def __init__(self, message: str, field: str = None, original_error: Exception = None):
        super().__init__(message, original_error)
        self.field = field

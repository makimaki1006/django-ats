"""Django ATS - カスタム例外クラス

アプリケーション固有の例外を定義。
適切なHTTPステータスコードとユーザーフレンドリーなメッセージを提供。
"""

from django.core.exceptions import PermissionDenied, ValidationError


class ATSBaseException(Exception):
    """ATS例外の基底クラス"""
    default_message = "エラーが発生しました。"

    def __init__(self, message=None, detail=None):
        self.message = message or self.default_message
        self.detail = detail
        super().__init__(self.message)


class TenantAccessError(PermissionDenied):
    """テナントアクセス権限エラー

    他テナントのデータにアクセスしようとした場合に発生。
    HTTP 403 Forbidden を返す。
    """
    def __init__(self, message=None):
        if message is None:
            message = "他のテナントのデータにはアクセスできません。"
        super().__init__(message)


class RolePermissionError(PermissionDenied):
    """ロール権限エラー

    必要なロールを持っていない場合に発生。
    HTTP 403 Forbidden を返す。
    """
    def __init__(self, required_roles=None, message=None):
        self.required_roles = required_roles or []
        if message is None:
            if required_roles:
                roles_str = ', '.join(required_roles)
                message = f"この操作には以下のロールが必要です: {roles_str}"
            else:
                message = "この操作を実行する権限がありません。"
        super().__init__(message)


class OptimisticLockError(ValidationError):
    """楽観的ロック競合エラー

    他のユーザーが同じレコードを先に更新した場合に発生。
    フォームでのバリデーションエラーとして扱う。
    """
    def __init__(self, message=None, code='optimistic_lock'):
        if message is None:
            message = "このレコードは他のユーザーによって更新されました。再読み込みしてください。"
        super().__init__(message, code=code)


class ResourceNotFoundError(ATSBaseException):
    """リソース未検出エラー

    指定されたリソースが見つからない場合に発生。
    HTTP 404 Not Found を返すべき。
    """
    default_message = "指定されたリソースが見つかりません。"

    def __init__(self, resource_type=None, resource_id=None, message=None):
        self.resource_type = resource_type
        self.resource_id = resource_id
        if message is None and resource_type:
            message = f"{resource_type}が見つかりません。"
        super().__init__(message)


class DuplicateResourceError(ValidationError):
    """重複リソースエラー

    一意制約に違反する場合に発生。
    """
    def __init__(self, field=None, value=None, message=None, code='duplicate'):
        self.field = field
        self.value = value
        if message is None and field:
            message = f"{field}は既に使用されています。"
        super().__init__(message, code=code)


class CSVImportError(ATSBaseException):
    """CSVインポートエラー

    CSVファイルのインポート処理で発生するエラー。
    行番号とエラー詳細を含む。
    """
    default_message = "CSVインポート中にエラーが発生しました。"

    def __init__(self, message=None, row_number=None, errors=None):
        self.row_number = row_number
        self.errors = errors or []
        if message is None and row_number:
            message = f"行 {row_number} でエラーが発生しました。"
        super().__init__(message, detail={'row_number': row_number, 'errors': errors})


class CSVSchemaError(CSVImportError):
    """CSVスキーマエラー

    CSVファイルのカラム構成が不正な場合に発生。
    """
    default_message = "CSVファイルの形式が不正です。"

    def __init__(self, missing_columns=None, extra_columns=None, message=None):
        self.missing_columns = missing_columns or []
        self.extra_columns = extra_columns or []
        if message is None and missing_columns:
            cols_str = ', '.join(missing_columns)
            message = f"必須カラムがありません: {cols_str}"
        super().__init__(message, errors={'missing': missing_columns, 'extra': extra_columns})


class BusinessRuleError(ValidationError):
    """ビジネスルール違反エラー

    アプリケーション固有のビジネスルールに違反した場合に発生。
    """
    def __init__(self, rule=None, message=None, code='business_rule'):
        self.rule = rule
        super().__init__(message or f"ビジネスルール違反: {rule}", code=code)


class ApplicationStatusError(BusinessRuleError):
    """応募ステータス遷移エラー

    無効なステータス遷移を試みた場合に発生。
    """
    def __init__(self, current_status=None, target_status=None, message=None):
        self.current_status = current_status
        self.target_status = target_status
        if message is None and current_status and target_status:
            message = f"ステータス '{current_status}' から '{target_status}' への変更はできません。"
        super().__init__(
            rule='application_status_transition',
            message=message,
            code='invalid_status_transition'
        )


class QuotaExceededError(ATSBaseException):
    """クォータ超過エラー

    テナントの制限値を超えた場合に発生。
    将来的な課金機能やリソース制限に使用。
    """
    default_message = "利用上限に達しました。"

    def __init__(self, resource_type=None, limit=None, current=None, message=None):
        self.resource_type = resource_type
        self.limit = limit
        self.current = current
        if message is None and resource_type and limit:
            message = f"{resource_type}の上限（{limit}）に達しました。"
        super().__init__(message, detail={
            'resource_type': resource_type,
            'limit': limit,
            'current': current
        })

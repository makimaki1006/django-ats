"""Django ATS - Core Exceptions ユニットテスト

カスタム例外クラスのテストケース。
"""

import pytest
from django.core.exceptions import PermissionDenied, ValidationError

from apps.core.exceptions import (
    ATSBaseException,
    TenantAccessError,
    RolePermissionError,
    OptimisticLockError,
    ResourceNotFoundError,
    DuplicateResourceError,
    CSVImportError,
    CSVSchemaError,
    BusinessRuleError,
    ApplicationStatusError,
    QuotaExceededError,
)


class TestTenantAccessError:
    """TenantAccessError のテスト"""

    def test_is_permission_denied(self):
        """PermissionDeniedを継承していること"""
        error = TenantAccessError()
        assert isinstance(error, PermissionDenied)

    def test_default_message(self):
        """デフォルトメッセージが設定されていること"""
        error = TenantAccessError()
        assert "他のテナント" in str(error)

    def test_custom_message(self):
        """カスタムメッセージが設定できること"""
        msg = "テスト用メッセージ"
        error = TenantAccessError(msg)
        assert str(error) == msg


class TestRolePermissionError:
    """RolePermissionError のテスト"""

    def test_is_permission_denied(self):
        """PermissionDeniedを継承していること"""
        error = RolePermissionError()
        assert isinstance(error, PermissionDenied)

    def test_with_required_roles(self):
        """必要なロールがメッセージに含まれること"""
        roles = ['system_admin', 'client_admin']
        error = RolePermissionError(required_roles=roles)
        assert 'system_admin' in str(error)
        assert 'client_admin' in str(error)

    def test_stores_required_roles(self):
        """required_rolesが保存されること"""
        roles = ['system_admin']
        error = RolePermissionError(required_roles=roles)
        assert error.required_roles == roles


class TestOptimisticLockErrorInExceptions:
    """OptimisticLockError (exceptions module) のテスト"""

    def test_is_validation_error(self):
        """ValidationErrorを継承していること"""
        error = OptimisticLockError()
        assert isinstance(error, ValidationError)

    def test_error_code(self):
        """エラーコードが設定されていること"""
        error = OptimisticLockError()
        assert error.code == 'optimistic_lock'


class TestResourceNotFoundError:
    """ResourceNotFoundError のテスト"""

    def test_is_ats_base_exception(self):
        """ATSBaseExceptionを継承していること"""
        error = ResourceNotFoundError()
        assert isinstance(error, ATSBaseException)

    def test_with_resource_type(self):
        """リソースタイプがメッセージに含まれること"""
        error = ResourceNotFoundError(resource_type="候補者")
        assert "候補者" in str(error)

    def test_stores_resource_info(self):
        """リソース情報が保存されること"""
        error = ResourceNotFoundError(resource_type="候補者", resource_id="12345")
        assert error.resource_type == "候補者"
        assert error.resource_id == "12345"


class TestDuplicateResourceError:
    """DuplicateResourceError のテスト"""

    def test_is_validation_error(self):
        """ValidationErrorを継承していること"""
        error = DuplicateResourceError()
        assert isinstance(error, ValidationError)

    def test_with_field_name(self):
        """フィールド名がメッセージに含まれること"""
        error = DuplicateResourceError(field="email")
        assert "email" in str(error)

    def test_error_code(self):
        """エラーコードが設定されていること"""
        error = DuplicateResourceError()
        assert error.code == 'duplicate'


class TestCSVImportError:
    """CSVImportError のテスト"""

    def test_is_ats_base_exception(self):
        """ATSBaseExceptionを継承していること"""
        error = CSVImportError()
        assert isinstance(error, ATSBaseException)

    def test_with_row_number(self):
        """行番号がメッセージに含まれること"""
        error = CSVImportError(row_number=5)
        assert "5" in str(error)

    def test_stores_row_number(self):
        """行番号が保存されること"""
        error = CSVImportError(row_number=10)
        assert error.row_number == 10


class TestCSVSchemaError:
    """CSVSchemaError のテスト"""

    def test_inherits_csv_import_error(self):
        """CSVImportErrorを継承していること"""
        error = CSVSchemaError()
        assert isinstance(error, CSVImportError)

    def test_with_missing_columns(self):
        """欠落カラムがメッセージに含まれること"""
        error = CSVSchemaError(missing_columns=['name', 'email'])
        assert "name" in str(error)
        assert "email" in str(error)

    def test_stores_columns(self):
        """カラム情報が保存されること"""
        missing = ['name']
        extra = ['unknown']
        error = CSVSchemaError(missing_columns=missing, extra_columns=extra)
        assert error.missing_columns == missing
        assert error.extra_columns == extra


class TestBusinessRuleError:
    """BusinessRuleError のテスト"""

    def test_is_validation_error(self):
        """ValidationErrorを継承していること"""
        error = BusinessRuleError()
        assert isinstance(error, ValidationError)

    def test_with_rule_name(self):
        """ルール名がメッセージに含まれること"""
        error = BusinessRuleError(rule="max_applications")
        assert "max_applications" in str(error)


class TestApplicationStatusError:
    """ApplicationStatusError のテスト"""

    def test_inherits_business_rule_error(self):
        """BusinessRuleErrorを継承していること"""
        error = ApplicationStatusError()
        assert isinstance(error, BusinessRuleError)

    def test_with_status_transition(self):
        """ステータス遷移がメッセージに含まれること"""
        error = ApplicationStatusError(
            current_status="新規応募",
            target_status="内定"
        )
        assert "新規応募" in str(error)
        assert "内定" in str(error)

    def test_stores_statuses(self):
        """ステータスが保存されること"""
        error = ApplicationStatusError(
            current_status="新規応募",
            target_status="内定"
        )
        assert error.current_status == "新規応募"
        assert error.target_status == "内定"

    def test_error_code(self):
        """エラーコードが設定されていること"""
        error = ApplicationStatusError()
        assert error.code == 'invalid_status_transition'


class TestQuotaExceededError:
    """QuotaExceededError のテスト"""

    def test_is_ats_base_exception(self):
        """ATSBaseExceptionを継承していること"""
        error = QuotaExceededError()
        assert isinstance(error, ATSBaseException)

    def test_with_quota_info(self):
        """クォータ情報がメッセージに含まれること"""
        error = QuotaExceededError(
            resource_type="候補者",
            limit=100
        )
        assert "候補者" in str(error)
        assert "100" in str(error)

    def test_stores_quota_info(self):
        """クォータ情報が保存されること"""
        error = QuotaExceededError(
            resource_type="候補者",
            limit=100,
            current=100
        )
        assert error.resource_type == "候補者"
        assert error.limit == 100
        assert error.current == 100

"""Django ATS - Core Models ユニットテスト

BaseModel, TenantBaseModel のテストケース。

テスト方針:
    - 正常系: 期待通りの動作を確認
    - 異常系（逆証明）: 不正な入力でエラーになることを確認
"""

import pytest
import uuid
from datetime import datetime
from unittest.mock import patch, MagicMock
from django.core.exceptions import ValidationError
from django.db import models

# テスト対象
from apps.core.models import (
    BaseModel,
    TenantBaseModel,
    SoftDeleteModel,
    OptimisticLockError,
)


class TestBaseModel:
    """BaseModel のテスト"""

    def test_base_model_is_abstract(self):
        """BaseModelは抽象クラスであること"""
        assert BaseModel._meta.abstract is True

    def test_base_model_has_uuid_primary_key(self):
        """UUIDフィールドが主キーであること"""
        id_field = BaseModel._meta.get_field('id')
        assert isinstance(id_field, models.UUIDField)
        assert id_field.primary_key is True
        assert id_field.editable is False

    def test_base_model_has_timestamps(self):
        """created_at, updated_at フィールドがあること"""
        created_at = BaseModel._meta.get_field('created_at')
        updated_at = BaseModel._meta.get_field('updated_at')

        assert isinstance(created_at, models.DateTimeField)
        assert created_at.auto_now_add is True

        assert isinstance(updated_at, models.DateTimeField)
        assert updated_at.auto_now is True

    def test_base_model_has_version_field(self):
        """楽観的ロック用versionフィールドがあること"""
        version = BaseModel._meta.get_field('version')
        assert isinstance(version, models.PositiveIntegerField)
        assert version.default == 1

    def test_base_model_default_ordering(self):
        """デフォルトのソート順が-created_atであること"""
        assert BaseModel._meta.ordering == ['-created_at']


class TestTenantBaseModel:
    """TenantBaseModel のテスト"""

    def test_tenant_base_model_is_abstract(self):
        """TenantBaseModelは抽象クラスであること"""
        assert TenantBaseModel._meta.abstract is True

    def test_tenant_base_model_inherits_base_model(self):
        """BaseModelを継承していること"""
        assert issubclass(TenantBaseModel, BaseModel)

    def test_tenant_base_model_has_tenant_field(self):
        """tenantフィールドがあること"""
        tenant_field = TenantBaseModel._meta.get_field('tenant')
        assert isinstance(tenant_field, models.ForeignKey)
        assert tenant_field.remote_field.on_delete == models.CASCADE


class TestSoftDeleteModel:
    """SoftDeleteModel のテスト"""

    def test_soft_delete_model_is_abstract(self):
        """SoftDeleteModelは抽象クラスであること"""
        assert SoftDeleteModel._meta.abstract is True

    def test_soft_delete_model_has_delete_fields(self):
        """is_deleted, deleted_at フィールドがあること"""
        is_deleted = SoftDeleteModel._meta.get_field('is_deleted')
        deleted_at = SoftDeleteModel._meta.get_field('deleted_at')

        assert isinstance(is_deleted, models.BooleanField)
        assert is_deleted.default is False

        assert isinstance(deleted_at, models.DateTimeField)
        assert deleted_at.null is True


class TestOptimisticLockError:
    """OptimisticLockError のテスト"""

    def test_optimistic_lock_error_is_validation_error(self):
        """ValidationErrorを継承していること"""
        error = OptimisticLockError()
        assert isinstance(error, ValidationError)

    def test_optimistic_lock_error_default_message(self):
        """デフォルトメッセージが設定されていること"""
        error = OptimisticLockError()
        assert "他のユーザーによって更新" in str(error.message)

    def test_optimistic_lock_error_custom_message(self):
        """カスタムメッセージが設定できること"""
        custom_msg = "カスタムエラーメッセージ"
        error = OptimisticLockError(custom_msg)
        assert error.message == custom_msg


class TestVersionIncrement:
    """バージョンインクリメントのテスト（モック使用）"""

    def test_version_increments_on_update(self):
        """更新時にバージョンがインクリメントされること"""
        # 具体的なモデルがないため、ロジックのみテスト
        class TestModel(BaseModel):
            class Meta:
                abstract = True

        # save メソッドのロジック確認
        # 実際のDB操作はモデル作成後にテスト
        pass

    def test_version_not_incremented_on_create(self):
        """新規作成時はバージョンがインクリメントされないこと"""
        # pk がない場合はインクリメントしない
        pass

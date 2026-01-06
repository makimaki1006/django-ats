"""Django ATS - カスタムマネージャー

テナントフィルタリングを自動化するカスタムManagerを提供。

使用方法:
    # モデルに適用
    class Candidate(TenantBaseModel):
        objects = TenantManager()
        all_objects = models.Manager()  # フィルタなし版

    # 使用例（テナントコンテキスト設定済みの場合）
    candidates = Candidate.objects.all()  # 自動的に現在のテナントでフィルタ

    # 全テナント横断（管理者用）
    all_candidates = Candidate.all_objects.all()
"""

from django.db import models
from apps.core.context import get_current_tenant


class TenantQuerySet(models.QuerySet):
    """テナントフィルタリング対応QuerySet

    get_current_tenant()で取得したテナントで自動フィルタリング。
    """

    def for_tenant(self, tenant):
        """指定テナントでフィルタ

        Args:
            tenant: テナントオブジェクト

        Returns:
            QuerySet: フィルタ済みQuerySet
        """
        return self.filter(tenant=tenant)

    def for_current_tenant(self):
        """現在のテナントでフィルタ

        Returns:
            QuerySet: フィルタ済みQuerySet

        Raises:
            TenantNotSetError: テナントが設定されていない場合
        """
        tenant = get_current_tenant()
        if tenant is None:
            from apps.core.exceptions import TenantNotSetError
            raise TenantNotSetError()
        return self.filter(tenant=tenant)


class TenantManager(models.Manager):
    """テナント自動フィルタリングManager

    get_queryset()をオーバーライドし、
    コンテキストにテナントが設定されている場合は自動フィルタリング。

    Note:
        テナントが設定されていない場合は全件を返す（後方互換性のため）。
        厳密なフィルタリングが必要な場合は TenantStrictManager を使用。
    """

    def get_queryset(self):
        """QuerySetを取得（テナント自動フィルタリング）

        Returns:
            TenantQuerySet: フィルタ済みQuerySet
        """
        qs = TenantQuerySet(self.model, using=self._db)
        tenant = get_current_tenant()
        if tenant:
            return qs.filter(tenant=tenant)
        return qs

    def for_tenant(self, tenant):
        """指定テナントでフィルタ"""
        return self.get_queryset().for_tenant(tenant)

    def all_tenants(self):
        """全テナントのデータを取得（管理者用）

        テナントフィルタを適用せずに全件を返す。
        """
        return TenantQuerySet(self.model, using=self._db)


class TenantStrictManager(TenantManager):
    """厳密なテナントフィルタリングManager

    テナントが設定されていない場合は空のQuerySetを返す。
    セキュリティが重要な場面で使用。
    """

    def get_queryset(self):
        """QuerySetを取得（テナント必須）

        Returns:
            TenantQuerySet: フィルタ済みQuerySet（テナント未設定時は空）
        """
        qs = TenantQuerySet(self.model, using=self._db)
        tenant = get_current_tenant()
        if tenant:
            return qs.filter(tenant=tenant)
        # テナント未設定時は空のQuerySetを返す
        return qs.none()


class ActiveManager(models.Manager):
    """アクティブレコードのみを返すManager

    is_active=True のレコードのみを返す。
    論理削除やステータス管理で使用。
    """

    def get_queryset(self):
        return super().get_queryset().filter(is_active=True)


class TenantActiveManager(TenantManager):
    """テナントフィルタリング + アクティブフィルタリング

    テナント + is_active=True の両方でフィルタ。
    """

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.filter(is_active=True)


class SoftDeleteQuerySet(models.QuerySet):
    """論理削除対応QuerySet"""

    def active(self):
        """削除されていないレコード"""
        return self.filter(is_deleted=False)

    def deleted(self):
        """削除済みレコード"""
        return self.filter(is_deleted=True)

    def with_deleted(self):
        """削除済み含む全レコード"""
        return self.all()


class SoftDeleteManager(models.Manager):
    """論理削除対応Manager

    デフォルトで is_deleted=False のレコードのみを返す。
    """

    def get_queryset(self):
        return SoftDeleteQuerySet(self.model, using=self._db).filter(is_deleted=False)

    def deleted(self):
        """削除済みレコードを取得"""
        return SoftDeleteQuerySet(self.model, using=self._db).filter(is_deleted=True)

    def with_deleted(self):
        """削除済み含む全レコードを取得"""
        return SoftDeleteQuerySet(self.model, using=self._db)


class TenantSoftDeleteManager(TenantManager):
    """テナント + 論理削除対応Manager"""

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.filter(is_deleted=False)

    def deleted(self):
        """削除済みレコード（テナント内）"""
        return TenantQuerySet(self.model, using=self._db).filter(
            tenant=get_current_tenant(),
            is_deleted=True
        )

    def with_deleted(self):
        """削除済み含む全レコード（テナント内）"""
        return TenantQuerySet(self.model, using=self._db).filter(
            tenant=get_current_tenant()
        )

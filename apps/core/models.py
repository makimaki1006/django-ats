"""Django ATS - Core Models

BaseModel と TenantBaseModel を提供する。
全てのモデルはこれらを継承する。

設計方針:
- UUID主キー: 分散システム対応、URL予測困難
- 楽観的ロック: version フィールドで同時編集を検出
- 監査フィールド: created_at, updated_at を自動管理
- テナント分離: TenantBaseModel で多テナント対応
"""

import uuid
from django.db import models
from django.core.exceptions import ValidationError


class OptimisticLockError(ValidationError):
    """楽観的ロック競合エラー

    他のユーザーが同じレコードを先に更新した場合に発生。
    """
    def __init__(self, message=None):
        if message is None:
            message = "このレコードは他のユーザーによって更新されました。再読み込みしてください。"
        super().__init__(message)


class BaseModel(models.Model):
    """全モデルの基底クラス

    Attributes:
        id: UUID主キー（自動生成）
        created_at: 作成日時（自動設定）
        updated_at: 更新日時（自動更新）
        version: 楽観的ロック用バージョン番号
    """
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name='ID'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='作成日時'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='更新日時'
    )
    version = models.PositiveIntegerField(
        default=1,
        verbose_name='バージョン',
        help_text='楽観的ロック用。更新ごとにインクリメントされる。'
    )

    class Meta:
        abstract = True
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        """保存時にバージョンをインクリメント

        新規作成時: version = 1
        更新時: version += 1

        Note:
            楽観的ロックの検証は OptimisticLockMixin で行う。
            ここではバージョンのインクリメントのみ。
        """
        if self.pk:
            # 更新時のみバージョンをインクリメント
            # skip_version_increment フラグで制御可能
            if not kwargs.pop('skip_version_increment', False):
                self.version += 1
        super().save(*args, **kwargs)

    def save_without_version_increment(self, *args, **kwargs):
        """バージョンを更新せずに保存

        管理操作やバッチ処理で使用。
        通常のユーザー操作では使用しないこと。
        """
        kwargs['skip_version_increment'] = True
        self.save(*args, **kwargs)


class TenantBaseModel(BaseModel):
    """テナント所属モデルの基底クラス

    マルチテナント対応が必要なモデルはこれを継承する。

    Attributes:
        tenant: 所属テナント（必須）

    設計ポイント:
        - related_name は '%(class)ss' で自動生成
          例: Candidate → tenant.candidates
        - db_index=True でテナントフィルタを高速化
        - CASCADE: テナント削除時に関連データも削除
    """
    tenant = models.ForeignKey(
        'tenants.Tenant',
        on_delete=models.CASCADE,
        related_name='%(class)ss',
        db_index=True,
        verbose_name='テナント'
    )

    class Meta:
        abstract = True

    def clean(self):
        """テナントの整合性チェック

        関連オブジェクトが同一テナントに属することを検証。
        サブクラスでオーバーライドして具体的なチェックを追加。
        """
        super().clean()

    def save(self, *args, **kwargs):
        """保存前にテナント検証"""
        self.full_clean()
        super().save(*args, **kwargs)


class SoftDeleteModel(BaseModel):
    """論理削除対応モデルの基底クラス

    物理削除ではなく論理削除（is_deleted=True）を行う。
    削除履歴の保持や復元が必要な場合に使用。

    Attributes:
        is_deleted: 削除フラグ
        deleted_at: 削除日時

    Note:
        現時点では使用していないが、将来的な拡張に備えて定義。
    """
    is_deleted = models.BooleanField(
        default=False,
        db_index=True,
        verbose_name='削除済み'
    )
    deleted_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='削除日時'
    )

    class Meta:
        abstract = True

    def delete(self, using=None, keep_parents=False):
        """論理削除を実行"""
        from django.utils import timezone
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save(update_fields=['is_deleted', 'deleted_at'])

    def hard_delete(self, using=None, keep_parents=False):
        """物理削除を実行（管理操作用）"""
        super().delete(using=using, keep_parents=keep_parents)

    def restore(self):
        """削除を取り消して復元"""
        self.is_deleted = False
        self.deleted_at = None
        self.save(update_fields=['is_deleted', 'deleted_at'])


class SoftDeleteTenantModel(TenantBaseModel, SoftDeleteModel):
    """テナント所属 + 論理削除対応モデル

    テナント分離と論理削除の両方が必要な場合に使用。
    """
    class Meta:
        abstract = True

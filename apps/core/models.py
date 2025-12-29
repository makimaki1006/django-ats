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


class AuditActionChoices(models.TextChoices):
    """監査アクションの種類"""
    CREATE = 'create', '作成'
    UPDATE = 'update', '更新'
    DELETE = 'delete', '削除'
    LOGIN = 'login', 'ログイン'
    LOGOUT = 'logout', 'ログアウト'
    VIEW = 'view', '閲覧'
    EXPORT = 'export', 'エクスポート'
    IMPORT = 'import', 'インポート'
    OTHER = 'other', 'その他'


class AuditLog(models.Model):
    """監査ログモデル

    システム内の重要な操作を記録。
    セキュリティ監査、コンプライアンス対応に使用。

    Attributes:
        timestamp: 操作日時
        user: 操作ユーザー（null=匿名）
        tenant: テナント
        action: 操作種類
        resource_type: リソース種別（モデル名）
        resource_id: リソースID
        resource_repr: リソースの表示名
        ip_address: クライアントIPアドレス
        user_agent: ユーザーエージェント
        path: リクエストパス
        method: HTTPメソッド
        status_code: レスポンスステータスコード
        changes: 変更内容（JSON）
        extra_data: 追加データ（JSON）
    """
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name='ID'
    )
    timestamp = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        verbose_name='操作日時'
    )
    user = models.ForeignKey(
        'accounts.CustomUser',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_logs',
        verbose_name='ユーザー'
    )
    tenant = models.ForeignKey(
        'tenants.Tenant',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_logs',
        verbose_name='テナント'
    )
    action = models.CharField(
        max_length=20,
        choices=AuditActionChoices.choices,
        db_index=True,
        verbose_name='アクション'
    )
    resource_type = models.CharField(
        max_length=100,
        db_index=True,
        verbose_name='リソース種別'
    )
    resource_id = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='リソースID'
    )
    resource_repr = models.CharField(
        max_length=255,
        blank=True,
        verbose_name='リソース表示名'
    )
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        verbose_name='IPアドレス'
    )
    user_agent = models.TextField(
        blank=True,
        verbose_name='ユーザーエージェント'
    )
    path = models.CharField(
        max_length=500,
        blank=True,
        verbose_name='パス'
    )
    method = models.CharField(
        max_length=10,
        blank=True,
        verbose_name='メソッド'
    )
    status_code = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        verbose_name='ステータスコード'
    )
    changes = models.JSONField(
        default=dict,
        blank=True,
        verbose_name='変更内容'
    )
    extra_data = models.JSONField(
        default=dict,
        blank=True,
        verbose_name='追加データ'
    )

    class Meta:
        verbose_name = '監査ログ'
        verbose_name_plural = '監査ログ'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['tenant', 'timestamp']),
            models.Index(fields=['user', 'timestamp']),
            models.Index(fields=['resource_type', 'resource_id']),
        ]

    def __str__(self):
        user_str = self.user.email if self.user else 'anonymous'
        return f"{self.timestamp} | {user_str} | {self.action} | {self.resource_type}"

    @classmethod
    def log(cls, action, resource_type, request=None, user=None, tenant=None,
            resource_id='', resource_repr='', changes=None, extra_data=None,
            status_code=None):
        """監査ログを作成するユーティリティメソッド

        Args:
            action: AuditActionChoices の値
            resource_type: リソース種別（モデル名など）
            request: HttpRequest オブジェクト（オプション）
            user: ユーザー（requestから取得可能）
            tenant: テナント（requestから取得可能）
            resource_id: リソースID
            resource_repr: リソースの表示名
            changes: 変更内容辞書
            extra_data: 追加データ辞書
            status_code: レスポンスステータスコード

        Returns:
            AuditLog: 作成されたログオブジェクト
        """
        if request:
            user = user or (request.user if request.user.is_authenticated else None)
            tenant = tenant or getattr(request, 'tenant', None)
            ip_address = cls._get_client_ip(request)
            user_agent = request.META.get('HTTP_USER_AGENT', '')[:500]
            path = request.path
            method = request.method
        else:
            ip_address = None
            user_agent = ''
            path = ''
            method = ''

        return cls.objects.create(
            user=user,
            tenant=tenant,
            action=action,
            resource_type=resource_type,
            resource_id=str(resource_id) if resource_id else '',
            resource_repr=str(resource_repr)[:255] if resource_repr else '',
            ip_address=ip_address,
            user_agent=user_agent,
            path=path,
            method=method,
            status_code=status_code,
            changes=changes or {},
            extra_data=extra_data or {},
        )

    @staticmethod
    def _get_client_ip(request):
        """クライアントIPアドレスを取得"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip

"""Django ATS - Tenant モデル

マルチテナント対応のためのテナントモデル。
全てのテナント所属データはこのテナントに紐付く。

設計ポイント:
- BaseModelを継承（UUID主キー、監査フィールド）
- テナント固有の設定はsettingsフィールド（JSON）で管理
- 論理削除は使用しない（テナント削除時は関連データもCASCADE削除）
"""

from django.db import models

from apps.core.models import BaseModel


class Tenant(BaseModel):
    """テナントモデル

    企業・組織単位でデータを分離するための基本モデル。

    Attributes:
        name: テナント名（企業名）
        code: テナントコード（URLスラッグとして使用可能）
        logo_url: ロゴ画像URL
        is_active: 有効フラグ
        settings: テナント固有設定（JSON）
        plan: 契約プラン
        max_users: 最大ユーザー数
        trial_ends_at: トライアル終了日
    """

    # 基本情報
    name = models.CharField(
        max_length=255,
        verbose_name='テナント名'
    )
    code = models.SlugField(
        max_length=50,
        unique=True,
        verbose_name='テナントコード',
        help_text='URLやサブドメインで使用可能な識別子'
    )
    logo_url = models.URLField(
        blank=True,
        null=True,
        verbose_name='ロゴURL'
    )

    # 状態管理
    is_active = models.BooleanField(
        default=True,
        verbose_name='有効',
        help_text='無効にするとテナントのユーザーはログイン不可'
    )

    # 契約情報
    class PlanChoices(models.TextChoices):
        FREE = 'free', '無料プラン'
        STARTER = 'starter', 'スタータープラン'
        PROFESSIONAL = 'professional', 'プロフェッショナルプラン'
        ENTERPRISE = 'enterprise', 'エンタープライズプラン'

    plan = models.CharField(
        max_length=20,
        choices=PlanChoices.choices,
        default=PlanChoices.FREE,
        verbose_name='契約プラン'
    )
    max_users = models.PositiveIntegerField(
        default=5,
        verbose_name='最大ユーザー数',
        help_text='このテナントで作成可能なユーザー数の上限'
    )
    trial_ends_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='トライアル終了日'
    )

    # テナント固有設定（JSON）
    settings = models.JSONField(
        default=dict,
        blank=True,
        verbose_name='設定',
        help_text='テナント固有の設定をJSON形式で保存'
    )

    class Meta:
        verbose_name = 'テナント'
        verbose_name_plural = 'テナント'
        ordering = ['name']

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('tenants:detail', kwargs={'pk': self.pk})

    @property
    def is_trial(self):
        """トライアル中かどうか"""
        if not self.trial_ends_at:
            return False
        from django.utils import timezone
        return self.trial_ends_at > timezone.now()

    @property
    def is_trial_expired(self):
        """トライアルが終了しているかどうか"""
        if not self.trial_ends_at:
            return False
        from django.utils import timezone
        return self.trial_ends_at <= timezone.now()

    def get_setting(self, key, default=None):
        """設定値を取得"""
        return self.settings.get(key, default)

    def set_setting(self, key, value):
        """設定値を保存"""
        self.settings[key] = value
        self.save(update_fields=['settings', 'updated_at'])

    def user_count(self):
        """テナントのユーザー数"""
        return self.users.count() if hasattr(self, 'users') else 0

    def can_add_user(self):
        """ユーザーを追加可能かどうか"""
        return self.user_count() < self.max_users


class TenantSpreadsheet(BaseModel):
    """テナント-スプレッドシート紐付けモデル

    テナントごとのGoogle Spreadsheet接続情報を管理。
    1テナント = 1スプレッドシートの関係。

    Attributes:
        tenant: 紐付けるテナント
        spreadsheet_id: Google SpreadsheetのID
        spreadsheet_url: スプレッドシートのURL（自動生成）
        spreadsheet_name: スプレッドシート名（参照用）
        is_active: 接続が有効かどうか
        last_synced_at: 最終同期日時
        sync_errors: 同期エラーログ（JSON）
    """

    tenant = models.OneToOneField(
        Tenant,
        on_delete=models.CASCADE,
        related_name='spreadsheet',
        verbose_name='テナント'
    )

    spreadsheet_id = models.CharField(
        max_length=255,
        verbose_name='スプレッドシートID',
        help_text='Google SpreadsheetのID（URLの/d/以降の部分）'
    )

    spreadsheet_name = models.CharField(
        max_length=255,
        blank=True,
        verbose_name='業務用スプレッドシート名',
        help_text='管理用の表示名'
    )

    admin_spreadsheet_id = models.CharField(
        max_length=255,
        blank=True,
        default='',
        verbose_name='管理用スプレッドシートID',
        help_text='ユーザー・パスワード管理用（コンサルタントのみ閲覧可）'
    )

    admin_spreadsheet_name = models.CharField(
        max_length=255,
        blank=True,
        default='',
        verbose_name='管理用スプレッドシート名',
        help_text='管理用の表示名'
    )

    is_active = models.BooleanField(
        default=True,
        verbose_name='有効',
        help_text='無効にするとシートへの読み書きを停止'
    )

    last_synced_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='最終同期日時'
    )

    sync_errors = models.JSONField(
        default=list,
        blank=True,
        verbose_name='同期エラーログ',
        help_text='直近のエラー情報をJSON形式で保存'
    )

    class Meta:
        verbose_name = 'テナントスプレッドシート'
        verbose_name_plural = 'テナントスプレッドシート'

    def __str__(self):
        return f"{self.tenant.name} - {self.spreadsheet_name or self.spreadsheet_id}"

    @property
    def spreadsheet_url(self):
        """スプレッドシートのURLを生成"""
        return f"https://docs.google.com/spreadsheets/d/{self.spreadsheet_id}"

    def record_sync_error(self, error_message: str):
        """同期エラーを記録"""
        from django.utils import timezone
        error_entry = {
            'timestamp': timezone.now().isoformat(),
            'message': str(error_message)
        }
        # 直近10件のエラーのみ保持
        self.sync_errors = [error_entry] + self.sync_errors[:9]
        self.save(update_fields=['sync_errors', 'updated_at'])

    def update_sync_time(self):
        """同期日時を更新"""
        from django.utils import timezone
        self.last_synced_at = timezone.now()
        self.save(update_fields=['last_synced_at', 'updated_at'])

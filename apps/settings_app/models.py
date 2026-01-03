"""Django ATS - 設定モデル

アプリケーション設定の管理用モデル。

設計ポイント:
- StatusSetting: テナント固有のステータス設定
- ApplicationSource: 応募経路マスター
- SpreadsheetConnection: スプレッドシート連携設定
- 表示順序（display_order）で並び替え可能
"""

from django.db import models
from django.utils import timezone

from apps.core.models import BaseModel, TenantBaseModel


class StatusCategoryChoices(models.TextChoices):
    """ステータスカテゴリ"""
    APPLICATION = 'application', '応募ステータス'
    INTERVIEW = 'interview', '面接ステータス'
    JOB = 'job', '求人ステータス'


class StatusSetting(TenantBaseModel):
    """ステータス設定モデル

    テナントごとのカスタムステータスを管理。

    Attributes:
        category: ステータスカテゴリ
        name: ステータス名
        code: ステータスコード
        display_order: 表示順序
        color: 表示色
        is_active: 有効フラグ
        is_terminal: 終了ステータスかどうか
    """

    category = models.CharField(
        max_length=20,
        choices=StatusCategoryChoices.choices,
        verbose_name='カテゴリ'
    )

    name = models.CharField(
        max_length=50,
        verbose_name='ステータス名'
    )

    code = models.CharField(
        max_length=30,
        verbose_name='ステータスコード',
        help_text='システム内部で使用するコード'
    )

    display_order = models.PositiveIntegerField(
        default=0,
        verbose_name='表示順序'
    )

    color = models.CharField(
        max_length=20,
        default='gray',
        verbose_name='表示色',
        help_text='Tailwind CSSのカラー名（例: blue, green, red）'
    )

    is_active = models.BooleanField(
        default=True,
        verbose_name='有効'
    )

    is_terminal = models.BooleanField(
        default=False,
        verbose_name='終了ステータス',
        help_text='このステータスで処理が終了するかどうか'
    )

    description = models.TextField(
        blank=True,
        verbose_name='説明'
    )

    class Meta:
        verbose_name = 'ステータス設定'
        verbose_name_plural = 'ステータス設定'
        ordering = ['category', 'display_order']
        constraints = [
            models.UniqueConstraint(
                fields=['tenant', 'category', 'code'],
                name='unique_status_code_per_tenant_category'
            )
        ]

    def __str__(self):
        return f"{self.get_category_display()}: {self.name}"


class SourceTypeChoices(models.TextChoices):
    """応募経路タイプ"""
    DIRECT = 'direct', '直接応募'
    AGENT = 'agent', 'エージェント'
    JOB_BOARD = 'job_board', '求人サイト'
    REFERRAL = 'referral', 'リファラル'
    SNS = 'sns', 'SNS'
    OTHER = 'other', 'その他'


class ApplicationSource(BaseModel):
    """応募経路モデル

    候補者の流入経路を管理。
    テナント固有または全テナント共通。

    Attributes:
        tenant: テナント（nullなら共通）
        name: 経路名
        source_type: 経路タイプ
        is_active: 有効フラグ
    """

    tenant = models.ForeignKey(
        'tenants.Tenant',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='application_sources',
        verbose_name='テナント',
        help_text='空欄の場合は全テナント共通'
    )

    name = models.CharField(
        max_length=100,
        verbose_name='経路名'
    )

    source_type = models.CharField(
        max_length=20,
        choices=SourceTypeChoices.choices,
        default=SourceTypeChoices.OTHER,
        verbose_name='経路タイプ'
    )

    url = models.URLField(
        blank=True,
        null=True,
        verbose_name='URL',
        help_text='求人サイトやSNSの場合のURL'
    )

    display_order = models.PositiveIntegerField(
        default=0,
        verbose_name='表示順序'
    )

    is_active = models.BooleanField(
        default=True,
        verbose_name='有効'
    )

    notes = models.TextField(
        blank=True,
        verbose_name='備考'
    )

    class Meta:
        verbose_name = '応募経路'
        verbose_name_plural = '応募経路'
        ordering = ['display_order', 'name']

    def __str__(self):
        return self.name

    @property
    def is_global(self):
        """全テナント共通かどうか"""
        return self.tenant is None


class EmailTemplate(TenantBaseModel):
    """メールテンプレートモデル

    通知メールのテンプレートを管理。

    Attributes:
        name: テンプレート名
        subject: 件名テンプレート
        body: 本文テンプレート
        template_type: テンプレートタイプ
        is_active: 有効フラグ
    """

    class TemplateTypeChoices(models.TextChoices):
        INTERVIEW_INVITATION = 'interview_invitation', '面接案内'
        INTERVIEW_REMINDER = 'interview_reminder', '面接リマインダー'
        INTERVIEW_FEEDBACK = 'interview_feedback', '面接結果'
        OFFER_LETTER = 'offer_letter', '内定通知'
        REJECTION = 'rejection', '不採用通知'
        WELCOME = 'welcome', 'ウェルカムメール'
        CUSTOM = 'custom', 'カスタム'

    name = models.CharField(
        max_length=100,
        verbose_name='テンプレート名'
    )

    template_type = models.CharField(
        max_length=30,
        choices=TemplateTypeChoices.choices,
        default=TemplateTypeChoices.CUSTOM,
        verbose_name='テンプレートタイプ'
    )

    subject = models.CharField(
        max_length=255,
        verbose_name='件名',
        help_text='変数: {{candidate_name}}, {{job_title}} など'
    )

    body = models.TextField(
        verbose_name='本文',
        help_text='変数: {{candidate_name}}, {{job_title}}, {{interview_date}} など'
    )

    is_active = models.BooleanField(
        default=True,
        verbose_name='有効'
    )

    is_default = models.BooleanField(
        default=False,
        verbose_name='デフォルト',
        help_text='同じタイプのデフォルトテンプレート'
    )

    class Meta:
        verbose_name = 'メールテンプレート'
        verbose_name_plural = 'メールテンプレート'
        ordering = ['template_type', 'name']

    def __str__(self):
        return f"{self.get_template_type_display()}: {self.name}"

    def render(self, context):
        """テンプレートをレンダリング"""
        from django.template import Template, Context
        subject_template = Template(self.subject)
        body_template = Template(self.body)
        ctx = Context(context)
        return {
            'subject': subject_template.render(ctx),
            'body': body_template.render(ctx),
        }


class SyncStatusChoices(models.TextChoices):
    """同期ステータス"""
    PENDING = 'pending', '未接続'
    CONNECTED = 'connected', '接続済み'
    SYNCING = 'syncing', '同期中'
    ERROR = 'error', 'エラー'


class SpreadsheetConnection(TenantBaseModel):
    """スプレッドシート連携設定モデル

    Google Spreadsheetとの双方向同期設定を管理。

    Attributes:
        spreadsheet_id: Google SpreadsheetのID
        spreadsheet_url: スプレッドシートのURL
        spreadsheet_name: スプレッドシート名（表示用）
        credentials_json: サービスアカウント認証情報（暗号化推奨）
        is_active: 連携有効フラグ
        sync_status: 同期ステータス
        last_synced_at: 最終同期日時
        last_sync_error: 最終エラーメッセージ
        sync_candidates: 候補者データを同期するか
        sync_jobs: 求人データを同期するか
        sync_applications: 応募データを同期するか
        sync_interviews: 面接データを同期するか
    """

    spreadsheet_id = models.CharField(
        max_length=255,
        verbose_name='スプレッドシートID',
        help_text='GoogleスプレッドシートのID（URLから取得）'
    )

    spreadsheet_url = models.URLField(
        blank=True,
        verbose_name='スプレッドシートURL',
        help_text='https://docs.google.com/spreadsheets/d/xxxxx/edit'
    )

    spreadsheet_name = models.CharField(
        max_length=255,
        blank=True,
        verbose_name='スプレッドシート名',
        help_text='識別用の名前'
    )

    credentials_json = models.TextField(
        blank=True,
        verbose_name='認証情報（JSON）',
        help_text='Google Cloud サービスアカウントのJSONキー'
    )

    is_active = models.BooleanField(
        default=True,
        verbose_name='連携有効'
    )

    sync_status = models.CharField(
        max_length=20,
        choices=SyncStatusChoices.choices,
        default=SyncStatusChoices.PENDING,
        verbose_name='同期ステータス'
    )

    last_synced_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='最終同期日時'
    )

    last_sync_error = models.TextField(
        blank=True,
        verbose_name='最終エラー'
    )

    # 同期対象設定
    sync_candidates = models.BooleanField(
        default=True,
        verbose_name='候補者を同期'
    )

    sync_jobs = models.BooleanField(
        default=True,
        verbose_name='求人を同期'
    )

    sync_applications = models.BooleanField(
        default=True,
        verbose_name='応募を同期'
    )

    sync_interviews = models.BooleanField(
        default=True,
        verbose_name='面接を同期'
    )

    # 同期設定
    auto_sync_enabled = models.BooleanField(
        default=True,
        verbose_name='自動同期有効',
        help_text='アプリ側の変更を自動的にスプレッドシートに反映'
    )

    sync_interval_minutes = models.PositiveIntegerField(
        default=5,
        verbose_name='同期間隔（分）',
        help_text='スプレッドシートからの変更を取り込む間隔'
    )

    class Meta:
        verbose_name = 'スプレッドシート連携'
        verbose_name_plural = 'スプレッドシート連携'
        constraints = [
            models.UniqueConstraint(
                fields=['tenant', 'spreadsheet_id'],
                name='unique_spreadsheet_per_tenant'
            )
        ]

    def __str__(self):
        return f"{self.spreadsheet_name or self.spreadsheet_id}"

    @property
    def is_connected(self):
        """接続済みかどうか"""
        return self.sync_status == SyncStatusChoices.CONNECTED

    @property
    def has_error(self):
        """エラー状態かどうか"""
        return self.sync_status == SyncStatusChoices.ERROR

    def mark_synced(self):
        """同期完了をマーク"""
        self.sync_status = SyncStatusChoices.CONNECTED
        self.last_synced_at = timezone.now()
        self.last_sync_error = ''
        self.save(update_fields=['sync_status', 'last_synced_at', 'last_sync_error'])

    def mark_error(self, error_message):
        """エラーをマーク"""
        self.sync_status = SyncStatusChoices.ERROR
        self.last_sync_error = str(error_message)
        self.save(update_fields=['sync_status', 'last_sync_error'])

    def mark_syncing(self):
        """同期中をマーク"""
        self.sync_status = SyncStatusChoices.SYNCING
        self.save(update_fields=['sync_status'])

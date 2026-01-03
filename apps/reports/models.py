"""Django ATS - レポートモデル

定期レポート配信のための設定モデル。
"""

from django.db import models
from django.conf import settings

from apps.core.models import TenantBaseModel


class ReportTypeChoices(models.TextChoices):
    """レポートタイプ"""
    MONTHLY_SUMMARY = 'monthly_summary', '月次サマリー'
    WEEKLY_PROGRESS = 'weekly_progress', '週次進捗'
    BIMONTHLY_COMPARISON = 'bimonthly_comparison', '過去2ヶ月比較'
    SEMI_ANNUAL = 'semi_annual', '半期レビュー'
    CUSTOM = 'custom', 'カスタム'


class ReportFormatChoices(models.TextChoices):
    """レポート形式"""
    PDF = 'pdf', 'PDF'
    CSV = 'csv', 'CSV'
    EXCEL = 'excel', 'Excel'
    HTML = 'html', 'HTML（メール本文）'


class ReportSchedule(TenantBaseModel):
    """定期レポート設定

    各テナントごとに定期レポートの配信設定を管理。

    使用例:
        # 月次レポート設定
        schedule = ReportSchedule.objects.create(
            tenant=tenant,
            name='月次採用サマリー',
            report_type='monthly_summary',
            format='pdf',
            recipients=['hr@example.com'],
            is_active=True,
        )
    """

    name = models.CharField(
        '設定名',
        max_length=100,
    )
    report_type = models.CharField(
        'レポートタイプ',
        max_length=30,
        choices=ReportTypeChoices.choices,
    )
    format = models.CharField(
        '形式',
        max_length=10,
        choices=ReportFormatChoices.choices,
        default=ReportFormatChoices.PDF,
    )
    recipients = models.JSONField(
        '配信先メールアドレス',
        default=list,
        help_text='配信先メールアドレスのリスト',
    )
    cc_recipients = models.JSONField(
        'CC配信先',
        default=list,
        blank=True,
    )
    is_active = models.BooleanField(
        '有効',
        default=True,
    )
    include_charts = models.BooleanField(
        'グラフを含む',
        default=True,
    )
    include_details = models.BooleanField(
        '詳細データを含む',
        default=False,
    )

    # スケジュール設定（Celery Beat用）
    cron_expression = models.CharField(
        'Cron式',
        max_length=100,
        blank=True,
        help_text='カスタムスケジュール用（例: 0 9 1 * *）',
    )

    # 実行履歴
    last_run_at = models.DateTimeField(
        '最終実行日時',
        null=True,
        blank=True,
    )
    last_run_status = models.CharField(
        '最終実行結果',
        max_length=20,
        blank=True,
    )
    last_run_error = models.TextField(
        '最終実行エラー',
        blank=True,
    )

    # 作成者
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_report_schedules',
        verbose_name='作成者',
    )

    class Meta:
        verbose_name = '定期レポート設定'
        verbose_name_plural = '定期レポート設定'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.get_report_type_display()})"

    def get_default_cron(self):
        """レポートタイプに応じたデフォルトCron式を取得"""
        cron_defaults = {
            ReportTypeChoices.MONTHLY_SUMMARY: '0 9 1 * *',      # 毎月1日 9:00
            ReportTypeChoices.WEEKLY_PROGRESS: '0 9 * * 1',      # 毎週月曜 9:00
            ReportTypeChoices.BIMONTHLY_COMPARISON: '0 9 15 * *', # 毎月15日 9:00
            ReportTypeChoices.SEMI_ANNUAL: '0 9 1 6,12 *',       # 6月と12月の1日 9:00
        }
        return cron_defaults.get(self.report_type, '')


class ReportExecution(TenantBaseModel):
    """レポート実行履歴

    各レポート実行の詳細ログを保存。
    """

    schedule = models.ForeignKey(
        ReportSchedule,
        on_delete=models.CASCADE,
        related_name='executions',
        verbose_name='スケジュール',
    )
    status = models.CharField(
        'ステータス',
        max_length=20,
        choices=[
            ('pending', '待機中'),
            ('running', '実行中'),
            ('completed', '完了'),
            ('failed', '失敗'),
        ],
        default='pending',
    )
    started_at = models.DateTimeField(
        '開始日時',
        null=True,
        blank=True,
    )
    completed_at = models.DateTimeField(
        '完了日時',
        null=True,
        blank=True,
    )
    report_file = models.FileField(
        'レポートファイル',
        upload_to='reports/%Y/%m/',
        null=True,
        blank=True,
    )
    recipients_sent = models.JSONField(
        '送信先',
        default=list,
    )
    error_message = models.TextField(
        'エラーメッセージ',
        blank=True,
    )

    class Meta:
        verbose_name = 'レポート実行履歴'
        verbose_name_plural = 'レポート実行履歴'
        ordering = ['-started_at']

    def __str__(self):
        return f"{self.schedule.name} - {self.started_at}"

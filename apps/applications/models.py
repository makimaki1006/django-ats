"""Django ATS - 応募モデル

応募（候補者×求人）の管理用モデル。

設計ポイント:
- TenantBaseModelを継承（テナント分離）
- ステータス履歴を別テーブルで管理
- 楽観的ロック対応（version フィールド）
"""

from django.db import models

from apps.core.models import TenantBaseModel


class ApplicationStatusChoices(models.TextChoices):
    """応募ステータス"""
    NEW = 'new', '新規応募'
    DOCUMENT_SCREENING = 'document_screening', '書類選考中'
    DOCUMENT_PASSED = 'document_passed', '書類通過'
    DOCUMENT_REJECTED = 'document_rejected', '書類不合格'
    INTERVIEW_SCHEDULED = 'interview_scheduled', '面接調整中'
    INTERVIEWING = 'interviewing', '面接中'
    OFFER_PENDING = 'offer_pending', '内定検討中'
    OFFER_MADE = 'offer_made', '内定'
    OFFER_ACCEPTED = 'offer_accepted', '内定承諾'
    OFFER_DECLINED = 'offer_declined', '内定辞退'
    REJECTED = 'rejected', '不採用'
    WITHDRAWN = 'withdrawn', '辞退'
    ON_HOLD = 'on_hold', '保留'


class Application(TenantBaseModel):
    """応募モデル

    候補者と求人の紐付けを管理。
    選考プロセス全体を追跡。

    Attributes:
        candidate: 候補者
        job: 求人
        status: 現在のステータス
        source: 応募経路
        applied_at: 応募日時
        evaluation_score: 評価スコア
        evaluation_notes: 評価コメント
        offer_salary: 提示年収
        offer_made_at: 内定日
        offer_deadline: 内定回答期限
        joined_at: 入社日
        registered_by: 登録者
    """

    candidate = models.ForeignKey(
        'candidates.Candidate',
        on_delete=models.CASCADE,
        related_name='applications',
        verbose_name='候補者'
    )

    job = models.ForeignKey(
        'jobs.Job',
        on_delete=models.CASCADE,
        related_name='applications',
        verbose_name='求人'
    )

    status = models.CharField(
        max_length=30,
        choices=ApplicationStatusChoices.choices,
        default=ApplicationStatusChoices.NEW,
        verbose_name='ステータス'
    )

    source = models.ForeignKey(
        'settings_app.ApplicationSource',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='applications',
        verbose_name='応募経路'
    )

    applied_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='応募日時'
    )

    # 評価
    evaluation_score = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        verbose_name='評価スコア',
        help_text='1〜5の5段階評価'
    )

    evaluation_notes = models.TextField(
        blank=True,
        verbose_name='評価コメント'
    )

    # 内定情報
    offer_salary = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name='提示年収（万円）'
    )

    offer_made_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='内定日'
    )

    offer_deadline = models.DateField(
        null=True,
        blank=True,
        verbose_name='内定回答期限'
    )

    offer_notes = models.TextField(
        blank=True,
        verbose_name='内定条件メモ'
    )

    # 入社情報
    joined_at = models.DateField(
        null=True,
        blank=True,
        verbose_name='入社日'
    )

    # 登録情報
    registered_by = models.ForeignKey(
        'accounts.CustomUser',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='registered_applications',
        verbose_name='登録者'
    )

    # メモ
    notes = models.TextField(
        blank=True,
        verbose_name='備考'
    )

    class Meta:
        verbose_name = '応募'
        verbose_name_plural = '応募'
        ordering = ['-applied_at']
        constraints = [
            models.UniqueConstraint(
                fields=['candidate', 'job'],
                name='unique_application_per_candidate_job'
            )
        ]

    def __str__(self):
        return f"{self.candidate.name} → {self.job.title}"

    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('applications:application_detail', kwargs={'pk': self.pk})

    @property
    def is_active(self):
        """進行中かどうか"""
        inactive_statuses = [
            ApplicationStatusChoices.REJECTED,
            ApplicationStatusChoices.WITHDRAWN,
            ApplicationStatusChoices.OFFER_DECLINED,
            ApplicationStatusChoices.OFFER_ACCEPTED,
        ]
        return self.status not in inactive_statuses

    @property
    def days_since_applied(self):
        """応募からの経過日数"""
        from django.utils import timezone
        return (timezone.now() - self.applied_at).days

    @property
    def is_pending_action(self):
        """アクションが必要かどうか（3日以上放置）"""
        return self.is_active and self.days_since_applied >= 3

    def change_status(self, new_status, user=None, notes=''):
        """ステータスを変更し、履歴を記録"""
        old_status = self.status
        self.status = new_status
        self.save()

        # 履歴を記録
        ApplicationStatusHistory.objects.create(
            tenant=self.tenant,
            application=self,
            from_status=old_status,
            to_status=new_status,
            changed_by=user,
            notes=notes
        )

        return self


class ApplicationStatusHistory(TenantBaseModel):
    """応募ステータス履歴モデル

    ステータス変更の履歴を記録。
    監査とトラッキングのため。

    Attributes:
        application: 対象応募
        from_status: 変更前ステータス
        to_status: 変更後ステータス
        changed_by: 変更者
        notes: 変更理由・メモ
    """

    application = models.ForeignKey(
        Application,
        on_delete=models.CASCADE,
        related_name='status_history',
        verbose_name='応募'
    )

    from_status = models.CharField(
        max_length=30,
        choices=ApplicationStatusChoices.choices,
        verbose_name='変更前ステータス'
    )

    to_status = models.CharField(
        max_length=30,
        choices=ApplicationStatusChoices.choices,
        verbose_name='変更後ステータス'
    )

    changed_by = models.ForeignKey(
        'accounts.CustomUser',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='status_changes',
        verbose_name='変更者'
    )

    notes = models.TextField(
        blank=True,
        verbose_name='変更理由・メモ'
    )

    class Meta:
        verbose_name = 'ステータス履歴'
        verbose_name_plural = 'ステータス履歴'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.application}: {self.from_status} → {self.to_status}"

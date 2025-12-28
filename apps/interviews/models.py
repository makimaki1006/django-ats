"""Django ATS - 面接モデル

面接スケジュール・記録の管理用モデル。

設計ポイント:
- TenantBaseModelを継承（テナント分離）
- 応募（Application）と1:N関係
- 面接記録（評価・フィードバック）を保存
"""

from django.db import models

from apps.core.models import TenantBaseModel


class InterviewTypeChoices(models.TextChoices):
    """面接タイプ"""
    PHONE = 'phone', '電話面接'
    VIDEO = 'video', 'Web面接'
    IN_PERSON = 'in_person', '対面面接'
    TECHNICAL = 'technical', '技術面接'
    FINAL = 'final', '最終面接'


class InterviewStatusChoices(models.TextChoices):
    """面接ステータス"""
    SCHEDULED = 'scheduled', '予定'
    CONFIRMED = 'confirmed', '確定'
    IN_PROGRESS = 'in_progress', '実施中'
    COMPLETED = 'completed', '完了'
    CANCELLED = 'cancelled', 'キャンセル'
    NO_SHOW = 'no_show', '欠席'
    RESCHEDULED = 'rescheduled', '再調整'


class InterviewResultChoices(models.TextChoices):
    """面接結果"""
    PENDING = 'pending', '評価待ち'
    PASSED = 'passed', '合格'
    FAILED = 'failed', '不合格'
    HOLD = 'hold', '保留'


class Interview(TenantBaseModel):
    """面接モデル

    面接スケジュールと結果を管理。

    Attributes:
        application: 対象応募
        interview_type: 面接タイプ
        interview_round: 面接回数（1次、2次...）
        scheduled_at: 面接予定日時
        duration_minutes: 予定時間（分）
        location: 場所（対面の場合）/URL（Webの場合）
        interviewer: 面接官
        status: ステータス
        result: 結果
        evaluation_score: 評価スコア
        feedback: フィードバック
        notes: 社内メモ
    """

    application = models.ForeignKey(
        'applications.Application',
        on_delete=models.CASCADE,
        related_name='interviews',
        verbose_name='応募'
    )

    interview_type = models.CharField(
        max_length=20,
        choices=InterviewTypeChoices.choices,
        default=InterviewTypeChoices.VIDEO,
        verbose_name='面接タイプ'
    )

    interview_round = models.PositiveSmallIntegerField(
        default=1,
        verbose_name='面接回数',
        help_text='何次面接か（1次、2次...）'
    )

    # スケジュール
    scheduled_at = models.DateTimeField(
        verbose_name='面接予定日時'
    )

    duration_minutes = models.PositiveIntegerField(
        default=60,
        verbose_name='予定時間（分）'
    )

    location = models.CharField(
        max_length=500,
        blank=True,
        verbose_name='場所/URL',
        help_text='対面の場合は住所、Webの場合はURL'
    )

    # 面接官
    interviewer = models.ForeignKey(
        'accounts.CustomUser',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='conducted_interviews',
        verbose_name='面接官'
    )

    additional_interviewers = models.ManyToManyField(
        'accounts.CustomUser',
        blank=True,
        related_name='additional_interviews',
        verbose_name='同席者'
    )

    # ステータス・結果
    status = models.CharField(
        max_length=20,
        choices=InterviewStatusChoices.choices,
        default=InterviewStatusChoices.SCHEDULED,
        verbose_name='ステータス'
    )

    result = models.CharField(
        max_length=20,
        choices=InterviewResultChoices.choices,
        default=InterviewResultChoices.PENDING,
        verbose_name='結果'
    )

    # 評価
    evaluation_score = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        verbose_name='評価スコア',
        help_text='1〜5の5段階評価'
    )

    # 評価項目（構造化）
    evaluation_criteria = models.JSONField(
        default=dict,
        blank=True,
        verbose_name='評価項目',
        help_text='項目別評価をJSON形式で保存'
    )

    feedback = models.TextField(
        blank=True,
        verbose_name='フィードバック',
        help_text='候補者への伝達事項'
    )

    internal_notes = models.TextField(
        blank=True,
        verbose_name='社内メモ',
        help_text='社内のみで共有する情報'
    )

    # 実施情報
    started_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='実際の開始時刻'
    )

    ended_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='実際の終了時刻'
    )

    # リマインダー
    reminder_sent = models.BooleanField(
        default=False,
        verbose_name='リマインダー送信済み'
    )

    class Meta:
        verbose_name = '面接'
        verbose_name_plural = '面接'
        ordering = ['-scheduled_at']

    def __str__(self):
        return f"{self.application.candidate.name} - {self.get_interview_round_display()}"

    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('interviews:interview_detail', kwargs={'pk': self.pk})

    def get_interview_round_display(self):
        """面接回数の表示"""
        if self.interview_type == InterviewTypeChoices.FINAL:
            return '最終面接'
        return f"{self.interview_round}次面接"

    @property
    def is_upcoming(self):
        """これから行われる面接かどうか"""
        from django.utils import timezone
        return (
            self.status in [InterviewStatusChoices.SCHEDULED, InterviewStatusChoices.CONFIRMED]
            and self.scheduled_at > timezone.now()
        )

    @property
    def is_today(self):
        """今日の面接かどうか"""
        from django.utils import timezone
        return self.scheduled_at.date() == timezone.now().date()

    @property
    def candidate(self):
        """候補者へのショートカット"""
        return self.application.candidate

    @property
    def job(self):
        """求人へのショートカット"""
        return self.application.job

    @property
    def actual_duration_minutes(self):
        """実際の面接時間（分）"""
        if self.started_at and self.ended_at:
            return int((self.ended_at - self.started_at).total_seconds() / 60)
        return None

    def complete(self, result, score=None, feedback='', internal_notes=''):
        """面接を完了にする"""
        from django.utils import timezone
        self.status = InterviewStatusChoices.COMPLETED
        self.result = result
        self.evaluation_score = score
        self.feedback = feedback
        self.internal_notes = internal_notes
        if not self.ended_at:
            self.ended_at = timezone.now()
        self.save()

    def cancel(self, reason=''):
        """面接をキャンセル"""
        self.status = InterviewStatusChoices.CANCELLED
        self.internal_notes = reason
        self.save()


class InterviewFeedbackRequest(TenantBaseModel):
    """面接フィードバック依頼モデル

    面接官にフィードバック入力を依頼。
    複数の面接官がいる場合に使用。
    """

    interview = models.ForeignKey(
        Interview,
        on_delete=models.CASCADE,
        related_name='feedback_requests',
        verbose_name='面接'
    )

    requested_to = models.ForeignKey(
        'accounts.CustomUser',
        on_delete=models.CASCADE,
        related_name='feedback_requests',
        verbose_name='依頼先'
    )

    is_completed = models.BooleanField(
        default=False,
        verbose_name='入力完了'
    )

    evaluation_score = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        verbose_name='評価スコア'
    )

    feedback = models.TextField(
        blank=True,
        verbose_name='フィードバック'
    )

    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='入力完了日時'
    )

    class Meta:
        verbose_name = 'フィードバック依頼'
        verbose_name_plural = 'フィードバック依頼'
        ordering = ['-created_at']
        unique_together = ['interview', 'requested_to']

    def __str__(self):
        return f"{self.interview} - {self.requested_to}"

    def submit(self, score, feedback):
        """フィードバックを提出"""
        from django.utils import timezone
        self.evaluation_score = score
        self.feedback = feedback
        self.is_completed = True
        self.completed_at = timezone.now()
        self.save()

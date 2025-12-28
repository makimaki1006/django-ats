"""Django ATS - 通知モデル

アプリ内通知の管理用モデル。

設計ポイント:
- TenantBaseModelを継承（テナント分離）
- 通知タイプごとに異なるアクションを定義
- 既読/未読管理
- Signalで自動生成
"""

from django.db import models

from apps.core.models import TenantBaseModel


class NotificationTypeChoices(models.TextChoices):
    """通知タイプ"""
    NEW_APPLICATION = 'new_application', '新規応募'
    STATUS_CHANGE = 'status_change', 'ステータス変更'
    INTERVIEW_REMINDER = 'interview_reminder', '面接リマインド'
    INTERVIEW_SCHEDULED = 'interview_scheduled', '面接スケジュール確定'
    INTERVIEW_COMPLETED = 'interview_completed', '面接完了'
    FEEDBACK_REQUEST = 'feedback_request', 'フィードバック依頼'
    PENDING_DEADLINE = 'pending_deadline', '対応期限'
    OFFER_MADE = 'offer_made', '内定通知'
    OFFER_RESPONSE = 'offer_response', '内定回答'
    SYSTEM = 'system', 'システム通知'


class NotificationPriorityChoices(models.TextChoices):
    """通知優先度"""
    LOW = 'low', '低'
    NORMAL = 'normal', '通常'
    HIGH = 'high', '高'
    URGENT = 'urgent', '緊急'


class Notification(TenantBaseModel):
    """通知モデル

    ユーザーへのアプリ内通知を管理。

    Attributes:
        user: 通知先ユーザー
        notification_type: 通知タイプ
        priority: 優先度
        title: タイトル
        message: 本文
        link: リンク先URL
        is_read: 既読フラグ
        read_at: 既読日時
        metadata: 追加データ（JSON）
    """

    user = models.ForeignKey(
        'accounts.CustomUser',
        on_delete=models.CASCADE,
        related_name='notifications',
        verbose_name='通知先ユーザー'
    )

    notification_type = models.CharField(
        max_length=30,
        choices=NotificationTypeChoices.choices,
        default=NotificationTypeChoices.SYSTEM,
        verbose_name='通知タイプ'
    )

    priority = models.CharField(
        max_length=10,
        choices=NotificationPriorityChoices.choices,
        default=NotificationPriorityChoices.NORMAL,
        verbose_name='優先度'
    )

    title = models.CharField(
        max_length=255,
        verbose_name='タイトル'
    )

    message = models.TextField(
        blank=True,
        verbose_name='本文'
    )

    link = models.CharField(
        max_length=500,
        blank=True,
        verbose_name='リンク先',
        help_text='クリック時の遷移先URL'
    )

    # 既読管理
    is_read = models.BooleanField(
        default=False,
        verbose_name='既読'
    )

    read_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='既読日時'
    )

    # 追加データ
    metadata = models.JSONField(
        default=dict,
        blank=True,
        verbose_name='追加データ',
        help_text='通知に関連する追加情報'
    )

    # 関連オブジェクト（ジェネリック）
    related_object_type = models.CharField(
        max_length=50,
        blank=True,
        verbose_name='関連オブジェクトタイプ'
    )

    related_object_id = models.CharField(
        max_length=36,
        blank=True,
        verbose_name='関連オブジェクトID'
    )

    class Meta:
        verbose_name = '通知'
        verbose_name_plural = '通知'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'is_read', '-created_at']),
        ]

    def __str__(self):
        return f"{self.user.email}: {self.title}"

    @property
    def icon(self):
        """通知タイプに応じたアイコン"""
        icons = {
            NotificationTypeChoices.NEW_APPLICATION: 'user-plus',
            NotificationTypeChoices.STATUS_CHANGE: 'refresh-cw',
            NotificationTypeChoices.INTERVIEW_REMINDER: 'bell',
            NotificationTypeChoices.INTERVIEW_SCHEDULED: 'calendar',
            NotificationTypeChoices.INTERVIEW_COMPLETED: 'check-circle',
            NotificationTypeChoices.FEEDBACK_REQUEST: 'message-square',
            NotificationTypeChoices.PENDING_DEADLINE: 'clock',
            NotificationTypeChoices.OFFER_MADE: 'gift',
            NotificationTypeChoices.OFFER_RESPONSE: 'mail',
            NotificationTypeChoices.SYSTEM: 'info',
        }
        return icons.get(self.notification_type, 'bell')

    def mark_as_read(self):
        """既読にする"""
        if not self.is_read:
            from django.utils import timezone
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=['is_read', 'read_at'])

    @classmethod
    def create_notification(
        cls,
        tenant,
        user,
        notification_type,
        title,
        message='',
        link='',
        priority='normal',
        metadata=None,
        related_object=None
    ):
        """通知を作成するヘルパーメソッド"""
        notification = cls(
            tenant=tenant,
            user=user,
            notification_type=notification_type,
            title=title,
            message=message,
            link=link,
            priority=priority,
            metadata=metadata or {}
        )

        if related_object:
            notification.related_object_type = related_object.__class__.__name__
            notification.related_object_id = str(related_object.pk)

        notification.save()
        return notification

    @classmethod
    def get_unread_count(cls, user):
        """未読通知数を取得"""
        return cls.objects.filter(user=user, is_read=False).count()

    @classmethod
    def mark_all_as_read(cls, user):
        """全て既読にする"""
        from django.utils import timezone
        cls.objects.filter(user=user, is_read=False).update(
            is_read=True,
            read_at=timezone.now()
        )

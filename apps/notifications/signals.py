"""
Django ATS - 通知シグナル

モデルのイベントに応じて自動的に通知を生成するシグナルハンドラ。

対応イベント:
1. 新規応募 - Application作成時
2. 応募ステータス変更 - Applicationステータス変更時
3. 面接スケジュール確定 - Interview作成時
4. 面接完了 - Interview完了時
5. 内定通知 - Application内定時
"""

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.urls import reverse

from apps.applications.models import Application, ApplicationStatusChoices
from apps.interviews.models import Interview, InterviewStatusChoices
from apps.notifications.models import (
    Notification,
    NotificationTypeChoices,
    NotificationPriorityChoices,
)


@receiver(post_save, sender=Application)
def notify_new_application(sender, instance, created, **kwargs):
    """新規応募時に通知を作成

    通知先:
    - 求人の採用担当者
    - 求人の作成者
    """
    if not created:
        return

    application = instance
    job = application.job
    candidate = application.candidate

    # 通知先ユーザーを収集
    recipients = set()
    if job.hiring_manager:
        recipients.add(job.hiring_manager)
    if job.created_by:
        recipients.add(job.created_by)

    for user in recipients:
        Notification.create_notification(
            tenant=application.tenant,
            user=user,
            notification_type=NotificationTypeChoices.NEW_APPLICATION,
            title=f'新規応募: {candidate.name}',
            message=f'{candidate.name}さんが「{job.title}」に応募しました。',
            link=reverse('applications:application_detail', kwargs={'pk': application.pk}),
            priority=NotificationPriorityChoices.NORMAL,
            related_object=application,
        )


@receiver(pre_save, sender=Application)
def track_application_status_change(sender, instance, **kwargs):
    """ステータス変更を追跡（pre_save）"""
    if instance.pk:
        try:
            old_instance = Application.objects.get(pk=instance.pk)
            instance._old_status = old_instance.status
        except Application.DoesNotExist:
            instance._old_status = None
    else:
        instance._old_status = None


@receiver(post_save, sender=Application)
def notify_application_status_change(sender, instance, created, **kwargs):
    """応募ステータス変更時に通知を作成

    通知先:
    - 応募を更新したユーザー以外の関係者
    - 担当者がいる場合は担当者
    """
    if created:
        return

    old_status = getattr(instance, '_old_status', None)
    if old_status is None or old_status == instance.status:
        return

    application = instance
    job = application.job
    candidate = application.candidate

    # ステータス表示名を取得
    new_status_display = application.get_status_display()

    # 通知先ユーザーを収集
    recipients = set()
    if job.hiring_manager:
        recipients.add(job.hiring_manager)
    if job.created_by:
        recipients.add(job.created_by)

    # 優先度の決定
    priority = NotificationPriorityChoices.NORMAL
    notification_type = NotificationTypeChoices.STATUS_CHANGE

    # 内定の場合は優先度を上げる
    if instance.status in [
        ApplicationStatusChoices.OFFER_MADE,
        ApplicationStatusChoices.OFFER_ACCEPTED,
    ]:
        priority = NotificationPriorityChoices.HIGH
        notification_type = NotificationTypeChoices.OFFER_MADE

    for user in recipients:
        Notification.create_notification(
            tenant=application.tenant,
            user=user,
            notification_type=notification_type,
            title=f'ステータス変更: {candidate.name}',
            message=f'{candidate.name}さんの応募ステータスが「{new_status_display}」に変更されました。',
            link=reverse('applications:application_detail', kwargs={'pk': application.pk}),
            priority=priority,
            related_object=application,
        )


@receiver(post_save, sender=Interview)
def notify_interview_scheduled(sender, instance, created, **kwargs):
    """面接スケジュール確定時に通知を作成

    通知先:
    - 面接官
    - 求人の採用担当者
    """
    if not created:
        return

    interview = instance
    application = interview.application
    candidate = interview.candidate
    job = application.job

    # 通知先ユーザーを収集
    recipients = set()
    if interview.interviewer:
        recipients.add(interview.interviewer)
    if job.hiring_manager:
        recipients.add(job.hiring_manager)

    for user in recipients:
        scheduled_at = interview.scheduled_at.strftime('%Y/%m/%d %H:%M') if interview.scheduled_at else '未定'

        Notification.create_notification(
            tenant=interview.tenant,
            user=user,
            notification_type=NotificationTypeChoices.INTERVIEW_SCHEDULED,
            title=f'面接スケジュール確定: {candidate.name}',
            message=f'{candidate.name}さんの面接が{scheduled_at}に予定されています。',
            link=reverse('interviews:interview_detail', kwargs={'pk': interview.pk}),
            priority=NotificationPriorityChoices.NORMAL,
            related_object=interview,
        )


@receiver(pre_save, sender=Interview)
def track_interview_status_change(sender, instance, **kwargs):
    """面接ステータス変更を追跡（pre_save）"""
    if instance.pk:
        try:
            old_instance = Interview.objects.get(pk=instance.pk)
            instance._old_status = old_instance.status
        except Interview.DoesNotExist:
            instance._old_status = None
    else:
        instance._old_status = None


@receiver(post_save, sender=Interview)
def notify_interview_completed(sender, instance, created, **kwargs):
    """面接完了時に通知を作成

    通知先:
    - 求人の採用担当者
    - 応募の担当者
    """
    if created:
        return

    old_status = getattr(instance, '_old_status', None)
    if old_status is None:
        return

    # 完了ステータスに変更された場合のみ
    if instance.status != InterviewStatusChoices.COMPLETED:
        return
    if old_status == InterviewStatusChoices.COMPLETED:
        return

    interview = instance
    application = interview.application
    candidate = interview.candidate
    job = application.job

    # 通知先ユーザーを収集
    recipients = set()
    if job.hiring_manager:
        recipients.add(job.hiring_manager)

    # 面接結果の表示
    result_display = interview.get_result_display() if interview.result else '評価待ち'

    for user in recipients:
        Notification.create_notification(
            tenant=interview.tenant,
            user=user,
            notification_type=NotificationTypeChoices.INTERVIEW_COMPLETED,
            title=f'面接完了: {candidate.name}',
            message=f'{candidate.name}さんの面接が完了しました。結果: {result_display}',
            link=reverse('interviews:interview_detail', kwargs={'pk': interview.pk}),
            priority=NotificationPriorityChoices.NORMAL,
            related_object=interview,
        )


def create_interview_reminder_notifications():
    """面接リマインド通知を作成（定期タスク用）

    翌日の面接に対してリマインド通知を送信。
    Celery等のタスクスケジューラから呼び出す。
    """
    from datetime import timedelta
    from django.utils import timezone

    tomorrow_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
    tomorrow_end = tomorrow_start + timedelta(days=1)

    interviews = Interview.objects.filter(
        status=InterviewStatusChoices.SCHEDULED,
        scheduled_at__gte=tomorrow_start,
        scheduled_at__lt=tomorrow_end,
    ).select_related('application__job', 'interviewer', 'application__candidate')

    for interview in interviews:
        candidate = interview.candidate
        scheduled_at = interview.scheduled_at.strftime('%H:%M')

        # 面接官にリマインド
        if interview.interviewer:
            Notification.create_notification(
                tenant=interview.tenant,
                user=interview.interviewer,
                notification_type=NotificationTypeChoices.INTERVIEW_REMINDER,
                title=f'明日の面接: {candidate.name}',
                message=f'{candidate.name}さんとの面接が明日{scheduled_at}に予定されています。',
                link=reverse('interviews:interview_detail', kwargs={'pk': interview.pk}),
                priority=NotificationPriorityChoices.HIGH,
                related_object=interview,
            )

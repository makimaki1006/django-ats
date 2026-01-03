"""
Notifications シグナルテスト

自動通知生成が正しく動作することを検証。
"""

from django.test import TestCase
from django.contrib.auth import get_user_model

from apps.tenants.models import Tenant
from apps.jobs.models import Job
from apps.candidates.models import Candidate
from apps.applications.models import Application, ApplicationStatusChoices
from apps.interviews.models import Interview, InterviewStatusChoices, InterviewResultChoices
from apps.notifications.models import Notification, NotificationTypeChoices

User = get_user_model()


class NewApplicationSignalTest(TestCase):
    """新規応募シグナルテスト"""

    def setUp(self):
        self.tenant = Tenant.objects.create(
            name='テストテナント',
            code='test-tenant',
            is_active=True,
        )
        self.hiring_manager = User.objects.create_user(
            email='manager@example.com',
            password='testpass123',
            tenant=self.tenant,
        )
        self.job = Job.objects.create(
            tenant=self.tenant,
            title='テスト求人',
            unique_code='JOB-001',
            hiring_manager=self.hiring_manager,
        )
        self.candidate = Candidate.objects.create(
            tenant=self.tenant,
            name='テスト候補者',
            email='candidate@example.com',
        )

    def test_notification_created_on_new_application(self):
        """新規応募時に通知が作成される"""
        initial_count = Notification.objects.count()

        Application.objects.create(
            tenant=self.tenant,
            job=self.job,
            candidate=self.candidate,
            status=ApplicationStatusChoices.NEW,
        )

        self.assertEqual(Notification.objects.count(), initial_count + 1)

        notification = Notification.objects.latest('created_at')
        self.assertEqual(notification.notification_type, NotificationTypeChoices.NEW_APPLICATION)
        self.assertEqual(notification.user, self.hiring_manager)
        self.assertIn('テスト候補者', notification.title)

    def test_no_notification_on_update(self):
        """応募更新時には新規応募通知は作成されない"""
        application = Application.objects.create(
            tenant=self.tenant,
            job=self.job,
            candidate=self.candidate,
            status=ApplicationStatusChoices.NEW,
        )

        initial_count = Notification.objects.filter(
            notification_type=NotificationTypeChoices.NEW_APPLICATION
        ).count()

        # 更新
        application.notes = '更新テスト'
        application.save()

        new_count = Notification.objects.filter(
            notification_type=NotificationTypeChoices.NEW_APPLICATION
        ).count()
        self.assertEqual(new_count, initial_count)


class ApplicationStatusChangeSignalTest(TestCase):
    """応募ステータス変更シグナルテスト"""

    def setUp(self):
        self.tenant = Tenant.objects.create(
            name='テストテナント',
            code='test-tenant',
            is_active=True,
        )
        self.hiring_manager = User.objects.create_user(
            email='manager@example.com',
            password='testpass123',
            tenant=self.tenant,
        )
        self.job = Job.objects.create(
            tenant=self.tenant,
            title='テスト求人',
            unique_code='JOB-001',
            hiring_manager=self.hiring_manager,
        )
        self.candidate = Candidate.objects.create(
            tenant=self.tenant,
            name='テスト候補者',
            email='candidate@example.com',
        )
        self.application = Application.objects.create(
            tenant=self.tenant,
            job=self.job,
            candidate=self.candidate,
            status=ApplicationStatusChoices.NEW,
        )
        # 新規応募通知をクリア
        Notification.objects.all().delete()

    def test_notification_on_status_change(self):
        """ステータス変更時に通知が作成される"""
        self.application.status = ApplicationStatusChoices.INTERVIEW_SCHEDULED
        self.application.save()

        notification = Notification.objects.latest('created_at')
        self.assertEqual(notification.notification_type, NotificationTypeChoices.STATUS_CHANGE)
        self.assertIn('ステータス変更', notification.title)

    def test_no_notification_on_same_status(self):
        """同じステータスへの変更では通知は作成されない"""
        initial_count = Notification.objects.count()

        self.application.status = ApplicationStatusChoices.NEW  # 同じ
        self.application.save()

        self.assertEqual(Notification.objects.count(), initial_count)

    def test_offer_notification_has_high_priority(self):
        """内定通知は優先度が高い"""
        self.application.status = ApplicationStatusChoices.OFFER_MADE
        self.application.save()

        notification = Notification.objects.latest('created_at')
        self.assertEqual(notification.notification_type, NotificationTypeChoices.OFFER_MADE)
        self.assertEqual(notification.priority, 'high')


class InterviewScheduledSignalTest(TestCase):
    """面接スケジュールシグナルテスト"""

    def setUp(self):
        self.tenant = Tenant.objects.create(
            name='テストテナント',
            code='test-tenant',
            is_active=True,
        )
        self.interviewer = User.objects.create_user(
            email='interviewer@example.com',
            password='testpass123',
            tenant=self.tenant,
        )
        self.hiring_manager = User.objects.create_user(
            email='manager@example.com',
            password='testpass123',
            tenant=self.tenant,
        )
        self.job = Job.objects.create(
            tenant=self.tenant,
            title='テスト求人',
            unique_code='JOB-001',
            hiring_manager=self.hiring_manager,
        )
        self.candidate = Candidate.objects.create(
            tenant=self.tenant,
            name='テスト候補者',
            email='candidate@example.com',
        )
        self.application = Application.objects.create(
            tenant=self.tenant,
            job=self.job,
            candidate=self.candidate,
            status=ApplicationStatusChoices.INTERVIEW_SCHEDULED,
        )
        # 通知をクリア
        Notification.objects.all().delete()

    def test_notification_on_interview_created(self):
        """面接作成時に通知が作成される"""
        from django.utils import timezone

        Interview.objects.create(
            tenant=self.tenant,
            application=self.application,
            interviewer=self.interviewer,
            scheduled_at=timezone.now(),
            status=InterviewStatusChoices.SCHEDULED,
        )

        # 面接官と採用担当者に通知が送られる
        notifications = Notification.objects.filter(
            notification_type=NotificationTypeChoices.INTERVIEW_SCHEDULED
        )
        self.assertEqual(notifications.count(), 2)

        users = set(n.user for n in notifications)
        self.assertIn(self.interviewer, users)
        self.assertIn(self.hiring_manager, users)


class InterviewCompletedSignalTest(TestCase):
    """面接完了シグナルテスト"""

    def setUp(self):
        self.tenant = Tenant.objects.create(
            name='テストテナント',
            code='test-tenant',
            is_active=True,
        )
        self.interviewer = User.objects.create_user(
            email='interviewer@example.com',
            password='testpass123',
            tenant=self.tenant,
        )
        self.hiring_manager = User.objects.create_user(
            email='manager@example.com',
            password='testpass123',
            tenant=self.tenant,
        )
        self.job = Job.objects.create(
            tenant=self.tenant,
            title='テスト求人',
            unique_code='JOB-001',
            hiring_manager=self.hiring_manager,
        )
        self.candidate = Candidate.objects.create(
            tenant=self.tenant,
            name='テスト候補者',
            email='candidate@example.com',
        )
        self.application = Application.objects.create(
            tenant=self.tenant,
            job=self.job,
            candidate=self.candidate,
            status=ApplicationStatusChoices.INTERVIEW_SCHEDULED,
        )
        from django.utils import timezone
        self.interview = Interview.objects.create(
            tenant=self.tenant,
            application=self.application,
            interviewer=self.interviewer,
            scheduled_at=timezone.now(),
            status=InterviewStatusChoices.SCHEDULED,
        )
        # 通知をクリア
        Notification.objects.all().delete()

    def test_notification_on_interview_completed(self):
        """面接完了時に通知が作成される"""
        self.interview.status = InterviewStatusChoices.COMPLETED
        self.interview.result = InterviewResultChoices.PASSED
        self.interview.save()

        notification = Notification.objects.filter(
            notification_type=NotificationTypeChoices.INTERVIEW_COMPLETED
        ).first()
        self.assertIsNotNone(notification)
        self.assertIn('面接完了', notification.title)

    def test_no_notification_on_status_change_to_non_completed(self):
        """完了以外のステータス変更では通知は作成されない"""
        self.interview.status = InterviewStatusChoices.CANCELLED
        self.interview.save()

        notifications = Notification.objects.filter(
            notification_type=NotificationTypeChoices.INTERVIEW_COMPLETED
        )
        self.assertEqual(notifications.count(), 0)

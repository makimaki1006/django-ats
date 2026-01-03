"""
Notifications アプリモデルテスト
"""

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.tenants.models import Tenant
from apps.notifications.models import (
    Notification,
    NotificationTypeChoices,
    NotificationPriorityChoices,
)

User = get_user_model()


class NotificationModelTest(TestCase):
    """通知モデルテスト"""

    def setUp(self):
        self.tenant = Tenant.objects.create(
            name='テストテナント',
            code='test-tenant',
            is_active=True,
        )
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            tenant=self.tenant,
        )

    def test_create_notification(self):
        """通知を作成できる"""
        notification = Notification.objects.create(
            tenant=self.tenant,
            user=self.user,
            notification_type=NotificationTypeChoices.NEW_APPLICATION,
            title='新規応募がありました',
            message='テスト候補者から応募がありました',
        )
        self.assertEqual(notification.title, '新規応募がありました')
        self.assertEqual(notification.user, self.user)
        self.assertFalse(notification.is_read)

    def test_str_representation(self):
        """文字列表現が正しい"""
        notification = Notification.objects.create(
            tenant=self.tenant,
            user=self.user,
            title='テスト通知',
        )
        self.assertEqual(str(notification), f'{self.user.email}: テスト通知')

    def test_mark_as_read(self):
        """通知を既読にできる"""
        notification = Notification.objects.create(
            tenant=self.tenant,
            user=self.user,
            title='テスト通知',
        )
        self.assertFalse(notification.is_read)
        self.assertIsNone(notification.read_at)

        notification.mark_as_read()

        self.assertTrue(notification.is_read)
        self.assertIsNotNone(notification.read_at)

    def test_mark_as_read_idempotent(self):
        """既読の通知を再度既読にしても問題ない"""
        notification = Notification.objects.create(
            tenant=self.tenant,
            user=self.user,
            title='テスト通知',
            is_read=True,
            read_at=timezone.now(),
        )
        original_read_at = notification.read_at

        notification.mark_as_read()

        self.assertEqual(notification.read_at, original_read_at)

    def test_icon_property(self):
        """通知タイプに応じたアイコンが返される"""
        notification = Notification.objects.create(
            tenant=self.tenant,
            user=self.user,
            notification_type=NotificationTypeChoices.NEW_APPLICATION,
            title='テスト',
        )
        self.assertEqual(notification.icon, 'user-plus')

        notification.notification_type = NotificationTypeChoices.INTERVIEW_REMINDER
        self.assertEqual(notification.icon, 'bell')

    def test_create_notification_classmethod(self):
        """ヘルパーメソッドで通知を作成できる"""
        notification = Notification.create_notification(
            tenant=self.tenant,
            user=self.user,
            notification_type=NotificationTypeChoices.STATUS_CHANGE,
            title='ステータス変更',
            message='応募ステータスが変更されました',
            priority='high',
        )
        self.assertEqual(notification.title, 'ステータス変更')
        self.assertEqual(notification.priority, 'high')

    def test_get_unread_count(self):
        """未読通知数を取得できる"""
        # 未読通知を3件作成
        for i in range(3):
            Notification.objects.create(
                tenant=self.tenant,
                user=self.user,
                title=f'未読通知{i}',
                is_read=False,
            )
        # 既読通知を2件作成
        for i in range(2):
            Notification.objects.create(
                tenant=self.tenant,
                user=self.user,
                title=f'既読通知{i}',
                is_read=True,
            )

        count = Notification.get_unread_count(self.user)
        self.assertEqual(count, 3)

    def test_mark_all_as_read(self):
        """全通知を既読にできる"""
        # 未読通知を3件作成
        for i in range(3):
            Notification.objects.create(
                tenant=self.tenant,
                user=self.user,
                title=f'未読通知{i}',
                is_read=False,
            )

        Notification.mark_all_as_read(self.user)

        unread_count = Notification.get_unread_count(self.user)
        self.assertEqual(unread_count, 0)

    def test_default_values(self):
        """デフォルト値が正しく設定される"""
        notification = Notification.objects.create(
            tenant=self.tenant,
            user=self.user,
            title='テスト',
        )
        self.assertEqual(notification.notification_type, NotificationTypeChoices.SYSTEM)
        self.assertEqual(notification.priority, NotificationPriorityChoices.NORMAL)
        self.assertFalse(notification.is_read)
        self.assertEqual(notification.metadata, {})

    def test_notification_ordering(self):
        """通知は作成日時の降順で並ぶ"""
        n1 = Notification.objects.create(
            tenant=self.tenant,
            user=self.user,
            title='古い通知',
        )
        n2 = Notification.objects.create(
            tenant=self.tenant,
            user=self.user,
            title='新しい通知',
        )

        notifications = list(Notification.objects.filter(user=self.user))
        self.assertEqual(notifications[0], n2)  # 新しい方が先
        self.assertEqual(notifications[1], n1)

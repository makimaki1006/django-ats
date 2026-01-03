"""
Notifications アプリビューテスト
"""

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model

from apps.tenants.models import Tenant
from apps.notifications.models import Notification, NotificationTypeChoices

User = get_user_model()


class NotificationListViewTest(TestCase):
    """通知一覧ビューテスト"""

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
        self.client = Client()
        self.client.login(email='test@example.com', password='testpass123')

        # テスト用通知を作成
        for i in range(5):
            Notification.objects.create(
                tenant=self.tenant,
                user=self.user,
                title=f'通知{i}',
                is_read=(i % 2 == 0),
            )

    def test_notification_list_accessible(self):
        """通知一覧にアクセスできる"""
        response = self.client.get(reverse('notifications:notification_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '通知一覧')

    def test_notification_list_shows_all_notifications(self):
        """一覧に全通知が表示される"""
        response = self.client.get(reverse('notifications:notification_list'))
        self.assertEqual(len(response.context['notifications']), 5)

    def test_notification_list_filter_unread(self):
        """未読フィルターが機能する"""
        response = self.client.get(
            reverse('notifications:notification_list') + '?is_read=unread'
        )
        notifications = response.context['notifications']
        for n in notifications:
            self.assertFalse(n.is_read)

    def test_notification_list_filter_read(self):
        """既読フィルターが機能する"""
        response = self.client.get(
            reverse('notifications:notification_list') + '?is_read=read'
        )
        notifications = response.context['notifications']
        for n in notifications:
            self.assertTrue(n.is_read)

    def test_notification_list_filter_by_type(self):
        """タイプフィルターが機能する"""
        Notification.objects.create(
            tenant=self.tenant,
            user=self.user,
            title='新規応募',
            notification_type=NotificationTypeChoices.NEW_APPLICATION,
        )
        response = self.client.get(
            reverse('notifications:notification_list') + '?type=new_application'
        )
        notifications = response.context['notifications']
        self.assertEqual(len(notifications), 1)
        self.assertEqual(notifications[0].notification_type, NotificationTypeChoices.NEW_APPLICATION)

    def test_unauthenticated_cannot_access(self):
        """未認証ユーザーはアクセスできない"""
        self.client.logout()
        response = self.client.get(reverse('notifications:notification_list'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('login', response.url)


class NotificationMarkReadViewTest(TestCase):
    """既読マークビューテスト"""

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
        self.notification = Notification.objects.create(
            tenant=self.tenant,
            user=self.user,
            title='テスト通知',
            is_read=False,
        )
        self.client = Client()
        self.client.login(email='test@example.com', password='testpass123')

    def test_mark_read(self):
        """通知を既読にできる"""
        response = self.client.post(
            reverse('notifications:mark_read', kwargs={'pk': self.notification.pk})
        )
        self.assertEqual(response.status_code, 204)
        self.notification.refresh_from_db()
        self.assertTrue(self.notification.is_read)

    def test_mark_read_htmx(self):
        """HTMXリクエストでパーシャルが返される"""
        response = self.client.post(
            reverse('notifications:mark_read', kwargs={'pk': self.notification.pk}),
            HTTP_HX_REQUEST='true'
        )
        self.assertEqual(response.status_code, 200)
        self.notification.refresh_from_db()
        self.assertTrue(self.notification.is_read)


class NotificationMarkAllReadViewTest(TestCase):
    """全既読ビューテスト"""

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
        # 未読通知を作成
        for i in range(3):
            Notification.objects.create(
                tenant=self.tenant,
                user=self.user,
                title=f'未読通知{i}',
                is_read=False,
            )
        self.client = Client()
        self.client.login(email='test@example.com', password='testpass123')

    def test_mark_all_read(self):
        """全通知を既読にできる"""
        response = self.client.post(reverse('notifications:mark_all_read'))
        self.assertEqual(response.status_code, 204)

        unread = Notification.objects.filter(user=self.user, is_read=False).count()
        self.assertEqual(unread, 0)


class NotificationDeleteViewTest(TestCase):
    """削除ビューテスト"""

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
        self.notification = Notification.objects.create(
            tenant=self.tenant,
            user=self.user,
            title='削除対象',
        )
        self.client = Client()
        self.client.login(email='test@example.com', password='testpass123')

    def test_delete_notification(self):
        """通知を削除できる"""
        pk = self.notification.pk
        response = self.client.post(
            reverse('notifications:delete', kwargs={'pk': pk})
        )
        self.assertEqual(response.status_code, 204)
        self.assertFalse(Notification.objects.filter(pk=pk).exists())


class NotificationDropdownViewTest(TestCase):
    """ドロップダウンビューテスト"""

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
        self.client = Client()
        self.client.login(email='test@example.com', password='testpass123')

    def test_dropdown_shows_unread(self):
        """ドロップダウンに未読通知が表示される"""
        Notification.objects.create(
            tenant=self.tenant,
            user=self.user,
            title='未読通知',
            is_read=False,
        )
        response = self.client.get(reverse('notifications:dropdown'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '未読通知')

    def test_dropdown_max_5(self):
        """ドロップダウンは最大5件表示"""
        for i in range(10):
            Notification.objects.create(
                tenant=self.tenant,
                user=self.user,
                title=f'通知{i}',
                is_read=False,
            )
        response = self.client.get(reverse('notifications:dropdown'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['notifications']), 5)


class NotificationUnreadCountViewTest(TestCase):
    """未読数ビューテスト"""

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
        self.client = Client()
        self.client.login(email='test@example.com', password='testpass123')

    def test_unread_count_zero(self):
        """未読0件の場合は空を返す"""
        response = self.client.get(reverse('notifications:unread_count'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content.decode(), '')

    def test_unread_count_badge(self):
        """未読がある場合はバッジを返す"""
        for i in range(3):
            Notification.objects.create(
                tenant=self.tenant,
                user=self.user,
                title=f'通知{i}',
                is_read=False,
            )
        response = self.client.get(reverse('notifications:unread_count'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('3', response.content.decode())

    def test_unread_count_max_display(self):
        """100件以上は99+と表示"""
        for i in range(105):
            Notification.objects.create(
                tenant=self.tenant,
                user=self.user,
                title=f'通知{i}',
                is_read=False,
            )
        response = self.client.get(reverse('notifications:unread_count'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('99+', response.content.decode())

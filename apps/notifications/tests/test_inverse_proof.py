"""
Notifications アプリ逆証明テスト

逆証明（Proof by Contradiction）により、
不正な操作が適切に拒否されることを検証します。

テスト観点:
1. 他ユーザーの通知へのアクセス拒否
2. 認証・認可 - 未認証アクセスの拒否
3. 存在しない通知へのアクセス拒否
"""

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model

from apps.tenants.models import Tenant
from apps.notifications.models import Notification

User = get_user_model()


class NotificationAccessControlInverseTest(TestCase):
    """アクセス制御の逆証明テスト

    証明: 他ユーザーの通知にはアクセスできないこと
    """

    def setUp(self):
        # テナントA
        self.tenant_a = Tenant.objects.create(
            name='テナントA',
            code='tenant-a',
            is_active=True,
        )
        self.user_a = User.objects.create_user(
            email='user_a@example.com',
            password='testpass123',
            tenant=self.tenant_a,
        )
        self.notification_a = Notification.objects.create(
            tenant=self.tenant_a,
            user=self.user_a,
            title='ユーザーAの通知',
        )

        # テナントB
        self.tenant_b = Tenant.objects.create(
            name='テナントB',
            code='tenant-b',
            is_active=True,
        )
        self.user_b = User.objects.create_user(
            email='user_b@example.com',
            password='testpass123',
            tenant=self.tenant_b,
        )
        self.notification_b = Notification.objects.create(
            tenant=self.tenant_b,
            user=self.user_b,
            title='ユーザーBの通知',
        )

        self.client = Client()

    def test_cannot_mark_other_user_notification_read(self):
        """他ユーザーの通知を既読にできない"""
        self.client.login(email='user_a@example.com', password='testpass123')
        response = self.client.post(
            reverse('notifications:mark_read', kwargs={'pk': self.notification_b.pk})
        )
        self.assertEqual(response.status_code, 404)
        self.notification_b.refresh_from_db()
        self.assertFalse(self.notification_b.is_read)

    def test_cannot_delete_other_user_notification(self):
        """他ユーザーの通知を削除できない"""
        self.client.login(email='user_a@example.com', password='testpass123')
        response = self.client.post(
            reverse('notifications:delete', kwargs={'pk': self.notification_b.pk})
        )
        self.assertEqual(response.status_code, 404)
        self.assertTrue(Notification.objects.filter(pk=self.notification_b.pk).exists())

    def test_list_shows_only_own_notifications(self):
        """一覧には自分の通知のみ表示される"""
        self.client.login(email='user_a@example.com', password='testpass123')
        response = self.client.get(reverse('notifications:notification_list'))
        self.assertEqual(response.status_code, 200)
        notifications = response.context['notifications']
        for n in notifications:
            self.assertEqual(n.user, self.user_a)

    def test_dropdown_shows_only_own_notifications(self):
        """ドロップダウンには自分の未読通知のみ表示される"""
        # ユーザーAの未読通知
        Notification.objects.create(
            tenant=self.tenant_a,
            user=self.user_a,
            title='Aの未読',
            is_read=False,
        )
        # ユーザーBの未読通知
        Notification.objects.create(
            tenant=self.tenant_b,
            user=self.user_b,
            title='Bの未読',
            is_read=False,
        )

        self.client.login(email='user_a@example.com', password='testpass123')
        response = self.client.get(reverse('notifications:dropdown'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Aの未読')
        self.assertNotContains(response, 'Bの未読')


class NotificationAuthenticationInverseTest(TestCase):
    """認証・認可の逆証明テスト

    証明: 未認証ユーザーはアクセスできないこと
    """

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
        )
        self.client = Client()
        # ログインしない

    def test_unauthenticated_cannot_access_list(self):
        """未認証ユーザーは一覧にアクセスできない"""
        response = self.client.get(reverse('notifications:notification_list'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('login', response.url)

    def test_unauthenticated_cannot_access_dropdown(self):
        """未認証ユーザーはドロップダウンにアクセスできない"""
        response = self.client.get(reverse('notifications:dropdown'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('login', response.url)

    def test_unauthenticated_cannot_mark_read(self):
        """未認証ユーザーは既読にできない"""
        response = self.client.post(
            reverse('notifications:mark_read', kwargs={'pk': self.notification.pk})
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn('login', response.url)
        self.notification.refresh_from_db()
        self.assertFalse(self.notification.is_read)

    def test_unauthenticated_cannot_mark_all_read(self):
        """未認証ユーザーは全既読にできない"""
        response = self.client.post(reverse('notifications:mark_all_read'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('login', response.url)

    def test_unauthenticated_cannot_delete(self):
        """未認証ユーザーは削除できない"""
        response = self.client.post(
            reverse('notifications:delete', kwargs={'pk': self.notification.pk})
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn('login', response.url)
        self.assertTrue(Notification.objects.filter(pk=self.notification.pk).exists())

    def test_unauthenticated_cannot_clear_all(self):
        """未認証ユーザーは全削除できない"""
        response = self.client.post(reverse('notifications:clear_all'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('login', response.url)
        self.assertTrue(Notification.objects.filter(pk=self.notification.pk).exists())


class NotificationNotFoundInverseTest(TestCase):
    """存在しない通知の逆証明テスト

    証明: 存在しない通知へのアクセスは404を返すこと
    """

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
        # 存在しないUUID
        self.fake_pk = '00000000-0000-0000-0000-000000000000'

    def test_mark_read_not_found(self):
        """存在しない通知を既読にしようとすると404"""
        response = self.client.post(
            reverse('notifications:mark_read', kwargs={'pk': self.fake_pk})
        )
        self.assertEqual(response.status_code, 404)

    def test_delete_not_found(self):
        """存在しない通知を削除しようとすると404"""
        response = self.client.post(
            reverse('notifications:delete', kwargs={'pk': self.fake_pk})
        )
        self.assertEqual(response.status_code, 404)


class NotificationMarkAllReadIsolationTest(TestCase):
    """全既読の分離テスト

    証明: 全既読は自分の通知のみに適用されること
    """

    def setUp(self):
        self.tenant_a = Tenant.objects.create(
            name='テナントA',
            code='tenant-a',
            is_active=True,
        )
        self.user_a = User.objects.create_user(
            email='user_a@example.com',
            password='testpass123',
            tenant=self.tenant_a,
        )

        self.tenant_b = Tenant.objects.create(
            name='テナントB',
            code='tenant-b',
            is_active=True,
        )
        self.user_b = User.objects.create_user(
            email='user_b@example.com',
            password='testpass123',
            tenant=self.tenant_b,
        )

        # ユーザーAの未読通知
        for i in range(3):
            Notification.objects.create(
                tenant=self.tenant_a,
                user=self.user_a,
                title=f'A通知{i}',
                is_read=False,
            )

        # ユーザーBの未読通知
        for i in range(3):
            Notification.objects.create(
                tenant=self.tenant_b,
                user=self.user_b,
                title=f'B通知{i}',
                is_read=False,
            )

        self.client = Client()

    def test_mark_all_read_only_affects_own_notifications(self):
        """全既読は自分の通知のみに適用される"""
        self.client.login(email='user_a@example.com', password='testpass123')
        self.client.post(reverse('notifications:mark_all_read'))

        # ユーザーAの通知は全て既読
        a_unread = Notification.objects.filter(user=self.user_a, is_read=False).count()
        self.assertEqual(a_unread, 0)

        # ユーザーBの通知は未読のまま
        b_unread = Notification.objects.filter(user=self.user_b, is_read=False).count()
        self.assertEqual(b_unread, 3)


class NotificationClearAllIsolationTest(TestCase):
    """全削除の分離テスト

    証明: 全削除は自分の通知のみに適用されること
    """

    def setUp(self):
        self.tenant_a = Tenant.objects.create(
            name='テナントA',
            code='tenant-a',
            is_active=True,
        )
        self.user_a = User.objects.create_user(
            email='user_a@example.com',
            password='testpass123',
            tenant=self.tenant_a,
        )

        self.tenant_b = Tenant.objects.create(
            name='テナントB',
            code='tenant-b',
            is_active=True,
        )
        self.user_b = User.objects.create_user(
            email='user_b@example.com',
            password='testpass123',
            tenant=self.tenant_b,
        )

        # ユーザーAの通知
        for i in range(3):
            Notification.objects.create(
                tenant=self.tenant_a,
                user=self.user_a,
                title=f'A通知{i}',
            )

        # ユーザーBの通知
        for i in range(3):
            Notification.objects.create(
                tenant=self.tenant_b,
                user=self.user_b,
                title=f'B通知{i}',
            )

        self.client = Client()

    def test_clear_all_only_affects_own_notifications(self):
        """全削除は自分の通知のみに適用される"""
        self.client.login(email='user_a@example.com', password='testpass123')
        self.client.post(reverse('notifications:clear_all'))

        # ユーザーAの通知は全て削除
        a_count = Notification.objects.filter(user=self.user_a).count()
        self.assertEqual(a_count, 0)

        # ユーザーBの通知は残っている
        b_count = Notification.objects.filter(user=self.user_b).count()
        self.assertEqual(b_count, 3)

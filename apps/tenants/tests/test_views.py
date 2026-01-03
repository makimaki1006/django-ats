"""
Tenants アプリビューテスト
"""

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model

from apps.tenants.models import Tenant, TenantSpreadsheet

User = get_user_model()


class TenantListViewTest(TestCase):
    """テナント一覧ビューテスト"""

    def setUp(self):
        self.tenant = Tenant.objects.create(
            name='テストテナント',
            code='test-tenant',
            is_active=True,
        )
        self.superuser = User.objects.create_superuser(
            email='admin@example.com',
            password='adminpass123',
            tenant=self.tenant,
        )
        self.normal_user = User.objects.create_user(
            email='user@example.com',
            password='userpass123',
            tenant=self.tenant,
        )
        self.client = Client()

    def test_superuser_can_access(self):
        """スーパーユーザー（システム管理者）はアクセスできる"""
        self.client.login(email='admin@example.com', password='adminpass123')
        response = self.client.get(reverse('tenants:tenant_list'))
        self.assertEqual(response.status_code, 200)

    def test_consultant_can_access(self):
        """コンサルタントはアクセスできる"""
        consultant = User.objects.create_user(
            email='consultant@example.com',
            password='consultpass123',
            tenant=self.tenant,
            role='consultant',
        )
        self.client.login(email='consultant@example.com', password='consultpass123')
        response = self.client.get(reverse('tenants:tenant_list'))
        self.assertEqual(response.status_code, 200)

    def test_normal_user_cannot_access(self):
        """一般ユーザーはアクセスできない"""
        self.client.login(email='user@example.com', password='userpass123')
        response = self.client.get(reverse('tenants:tenant_list'))
        self.assertEqual(response.status_code, 403)

    def test_unauthenticated_cannot_access(self):
        """未認証ユーザーはアクセスできない"""
        response = self.client.get(reverse('tenants:tenant_list'))
        self.assertEqual(response.status_code, 302)

    def test_list_shows_tenants(self):
        """一覧にテナントが表示される"""
        Tenant.objects.create(name='テナント2', code='tenant-2')
        Tenant.objects.create(name='テナント3', code='tenant-3')

        self.client.login(email='admin@example.com', password='adminpass123')
        response = self.client.get(reverse('tenants:tenant_list'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['total_tenants'], 3)

    def test_filter_by_is_active(self):
        """有効/無効でフィルターできる"""
        Tenant.objects.create(name='無効テナント', code='inactive', is_active=False)

        self.client.login(email='admin@example.com', password='adminpass123')

        # 有効のみ
        response = self.client.get(reverse('tenants:tenant_list') + '?is_active=true')
        tenants = response.context['tenants']
        for t in tenants:
            self.assertTrue(t.is_active)

        # 無効のみ
        response = self.client.get(reverse('tenants:tenant_list') + '?is_active=false')
        tenants = response.context['tenants']
        for t in tenants:
            self.assertFalse(t.is_active)

    def test_search_by_name(self):
        """テナント名で検索できる"""
        Tenant.objects.create(name='検索テスト', code='search-test')

        self.client.login(email='admin@example.com', password='adminpass123')
        response = self.client.get(reverse('tenants:tenant_list') + '?q=検索')
        tenants = response.context['tenants']
        self.assertTrue(any('検索' in t.name for t in tenants))


class TenantDetailViewTest(TestCase):
    """テナント詳細ビューテスト"""

    def setUp(self):
        self.tenant = Tenant.objects.create(
            name='テストテナント',
            code='test-tenant',
            is_active=True,
        )
        self.superuser = User.objects.create_superuser(
            email='admin@example.com',
            password='adminpass123',
            tenant=self.tenant,
        )
        self.client = Client()
        self.client.login(email='admin@example.com', password='adminpass123')

    def test_detail_accessible(self):
        """詳細ページにアクセスできる"""
        response = self.client.get(
            reverse('tenants:tenant_detail', kwargs={'pk': self.tenant.pk})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'テストテナント')

    def test_detail_shows_stats(self):
        """統計情報が表示される"""
        response = self.client.get(
            reverse('tenants:tenant_detail', kwargs={'pk': self.tenant.pk})
        )
        self.assertIn('stats', response.context)

    def test_detail_shows_users(self):
        """ユーザー一覧が表示される"""
        User.objects.create_user(
            email='user1@example.com',
            password='pass',
            tenant=self.tenant,
        )
        response = self.client.get(
            reverse('tenants:tenant_detail', kwargs={'pk': self.tenant.pk})
        )
        self.assertIn('users', response.context)


class TenantCreateViewTest(TestCase):
    """テナント作成ビューテスト"""

    def setUp(self):
        self.tenant = Tenant.objects.create(
            name='テストテナント',
            code='test-tenant',
        )
        self.superuser = User.objects.create_superuser(
            email='admin@example.com',
            password='adminpass123',
            tenant=self.tenant,
        )
        self.client = Client()
        self.client.login(email='admin@example.com', password='adminpass123')

    def test_create_tenant(self):
        """テナントを作成できる"""
        response = self.client.post(reverse('tenants:tenant_create'), {
            'name': '新規テナント',
            'code': 'new-tenant',
            'plan': 'starter',
            'max_users': 10,
            'is_active': True,
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Tenant.objects.filter(code='new-tenant').exists())

    def test_create_duplicate_code_fails(self):
        """重複コードは作成できない"""
        response = self.client.post(reverse('tenants:tenant_create'), {
            'name': '重複テナント',
            'code': 'test-tenant',  # 既存
            'plan': 'free',
            'max_users': 5,
        })
        self.assertEqual(response.status_code, 200)  # フォームエラーで再表示
        self.assertContains(response, 'このコードは既に使用されています')


class TenantUpdateViewTest(TestCase):
    """テナント編集ビューテスト"""

    def setUp(self):
        self.tenant = Tenant.objects.create(
            name='テストテナント',
            code='test-tenant',
        )
        self.superuser = User.objects.create_superuser(
            email='admin@example.com',
            password='adminpass123',
            tenant=self.tenant,
        )
        self.client = Client()
        self.client.login(email='admin@example.com', password='adminpass123')

    def test_update_tenant(self):
        """テナントを編集できる"""
        response = self.client.post(
            reverse('tenants:tenant_update', kwargs={'pk': self.tenant.pk}),
            {
                'name': '更新テナント',
                'code': 'test-tenant',
                'plan': 'professional',
                'max_users': 20,
                'is_active': True,
            }
        )
        self.assertEqual(response.status_code, 302)
        self.tenant.refresh_from_db()
        self.assertEqual(self.tenant.name, '更新テナント')
        self.assertEqual(self.tenant.plan, 'professional')


class TenantToggleActiveViewTest(TestCase):
    """テナント有効/無効切り替えビューテスト"""

    def setUp(self):
        self.tenant = Tenant.objects.create(
            name='テストテナント',
            code='test-tenant',
            is_active=True,
        )
        self.superuser = User.objects.create_superuser(
            email='admin@example.com',
            password='adminpass123',
            tenant=self.tenant,
        )
        self.client = Client()
        self.client.login(email='admin@example.com', password='adminpass123')

    def test_toggle_active(self):
        """有効/無効を切り替えられる"""
        self.assertTrue(self.tenant.is_active)

        response = self.client.post(
            reverse('tenants:tenant_toggle_active', kwargs={'pk': self.tenant.pk})
        )
        self.assertEqual(response.status_code, 302)

        self.tenant.refresh_from_db()
        self.assertFalse(self.tenant.is_active)

        # もう一度切り替え
        response = self.client.post(
            reverse('tenants:tenant_toggle_active', kwargs={'pk': self.tenant.pk})
        )
        self.tenant.refresh_from_db()
        self.assertTrue(self.tenant.is_active)


class TenantSpreadsheetViewTest(TestCase):
    """スプレッドシート接続ビューテスト"""

    def setUp(self):
        self.tenant = Tenant.objects.create(
            name='テストテナント',
            code='test-tenant',
        )
        self.superuser = User.objects.create_superuser(
            email='admin@example.com',
            password='adminpass123',
            tenant=self.tenant,
        )
        self.client = Client()
        self.client.login(email='admin@example.com', password='adminpass123')

    def test_create_spreadsheet(self):
        """スプレッドシート接続を作成できる"""
        response = self.client.post(
            reverse('tenants:tenant_spreadsheet', kwargs={'pk': self.tenant.pk}),
            {
                'spreadsheet_id': 'abc123',
                'spreadsheet_name': 'テストシート',
                'is_active': True,
            }
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(hasattr(self.tenant, 'spreadsheet'))
        self.assertEqual(self.tenant.spreadsheet.spreadsheet_id, 'abc123')

    def test_update_spreadsheet(self):
        """スプレッドシート接続を更新できる"""
        TenantSpreadsheet.objects.create(
            tenant=self.tenant,
            spreadsheet_id='old123',
        )

        response = self.client.post(
            reverse('tenants:tenant_spreadsheet', kwargs={'pk': self.tenant.pk}),
            {
                'spreadsheet_id': 'new456',
                'spreadsheet_name': '新シート',
                'is_active': True,
            }
        )
        self.assertEqual(response.status_code, 302)
        self.tenant.refresh_from_db()
        self.assertEqual(self.tenant.spreadsheet.spreadsheet_id, 'new456')

    def test_delete_spreadsheet(self):
        """スプレッドシート接続を削除できる"""
        TenantSpreadsheet.objects.create(
            tenant=self.tenant,
            spreadsheet_id='abc123',
        )

        response = self.client.post(
            reverse('tenants:tenant_spreadsheet_delete', kwargs={'pk': self.tenant.pk})
        )
        self.assertEqual(response.status_code, 302)

        self.tenant.refresh_from_db()
        self.assertFalse(hasattr(self.tenant, 'spreadsheet') or
                        TenantSpreadsheet.objects.filter(tenant=self.tenant).exists())

"""
Tenants アプリ逆証明テスト

逆証明（Proof by Contradiction）により、
不正な操作が適切に拒否されることを検証します。

テスト観点:
1. 権限管理 - 非管理者はアクセスできない
2. 未認証アクセスの拒否
3. 存在しないテナントへのアクセス拒否
4. バリデーションエラーの適切な処理
"""

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model

from apps.tenants.models import Tenant, TenantSpreadsheet

User = get_user_model()


class TenantAccessControlInverseTest(TestCase):
    """アクセス制御の逆証明テスト

    証明: 顧客企業ユーザーはテナント管理にアクセスできないこと
    （SYSTEM_ADMIN/CONSULTANT以外はアクセス不可）
    """

    def setUp(self):
        self.tenant = Tenant.objects.create(
            name='テストテナント',
            code='test-tenant',
            is_active=True,
        )
        # 顧客企業の管理者（CLIENT_ADMIN）- アクセス不可
        self.client_admin = User.objects.create_user(
            email='client_admin@example.com',
            password='clientpass123',
            tenant=self.tenant,
            role='client_admin',
        )
        # 一般ユーザー（CLIENT_RECRUITER）
        self.normal_user = User.objects.create_user(
            email='user@example.com',
            password='userpass123',
            tenant=self.tenant,
        )
        self.client = Client()

    def test_client_admin_cannot_access_list(self):
        """顧客企業管理者はテナント一覧にアクセスできない"""
        self.client.login(email='client_admin@example.com', password='clientpass123')
        response = self.client.get(reverse('tenants:tenant_list'))
        self.assertEqual(response.status_code, 403)

    def test_normal_user_cannot_access_list(self):
        """一般ユーザーは一覧にアクセスできない"""
        self.client.login(email='user@example.com', password='userpass123')
        response = self.client.get(reverse('tenants:tenant_list'))
        self.assertEqual(response.status_code, 403)

    def test_normal_user_cannot_access_detail(self):
        """一般ユーザーは詳細にアクセスできない"""
        self.client.login(email='user@example.com', password='userpass123')
        response = self.client.get(
            reverse('tenants:tenant_detail', kwargs={'pk': self.tenant.pk})
        )
        self.assertEqual(response.status_code, 403)

    def test_normal_user_cannot_create(self):
        """一般ユーザーはテナントを作成できない"""
        self.client.login(email='user@example.com', password='userpass123')
        response = self.client.post(reverse('tenants:tenant_create'), {
            'name': '不正テナント',
            'code': 'invalid-tenant',
            'plan': 'free',
            'max_users': 5,
        })
        self.assertEqual(response.status_code, 403)
        self.assertFalse(Tenant.objects.filter(code='invalid-tenant').exists())

    def test_normal_user_cannot_update(self):
        """一般ユーザーはテナントを編集できない"""
        self.client.login(email='user@example.com', password='userpass123')
        response = self.client.post(
            reverse('tenants:tenant_update', kwargs={'pk': self.tenant.pk}),
            {'name': '改ざん', 'code': 'test-tenant', 'plan': 'free', 'max_users': 5}
        )
        self.assertEqual(response.status_code, 403)
        self.tenant.refresh_from_db()
        self.assertNotEqual(self.tenant.name, '改ざん')

    def test_normal_user_cannot_toggle_active(self):
        """一般ユーザーは有効/無効を切り替えできない"""
        self.client.login(email='user@example.com', password='userpass123')
        response = self.client.post(
            reverse('tenants:tenant_toggle_active', kwargs={'pk': self.tenant.pk})
        )
        self.assertEqual(response.status_code, 403)
        self.tenant.refresh_from_db()
        self.assertTrue(self.tenant.is_active)


class TenantAuthenticationInverseTest(TestCase):
    """認証の逆証明テスト

    証明: 未認証ユーザーはアクセスできないこと
    """

    def setUp(self):
        self.tenant = Tenant.objects.create(
            name='テストテナント',
            code='test-tenant',
        )
        self.client = Client()
        # ログインしない

    def test_unauthenticated_cannot_access_list(self):
        """未認証ユーザーは一覧にアクセスできない"""
        response = self.client.get(reverse('tenants:tenant_list'))
        self.assertEqual(response.status_code, 302)

    def test_unauthenticated_cannot_access_detail(self):
        """未認証ユーザーは詳細にアクセスできない"""
        response = self.client.get(
            reverse('tenants:tenant_detail', kwargs={'pk': self.tenant.pk})
        )
        self.assertEqual(response.status_code, 302)

    def test_unauthenticated_cannot_create(self):
        """未認証ユーザーはテナントを作成できない"""
        initial_count = Tenant.objects.count()
        response = self.client.post(reverse('tenants:tenant_create'), {
            'name': '不正テナント',
            'code': 'invalid-tenant',
            'plan': 'free',
            'max_users': 5,
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Tenant.objects.count(), initial_count)

    def test_unauthenticated_cannot_update(self):
        """未認証ユーザーはテナントを編集できない"""
        response = self.client.post(
            reverse('tenants:tenant_update', kwargs={'pk': self.tenant.pk}),
            {'name': '改ざん', 'code': 'test-tenant', 'plan': 'free', 'max_users': 5}
        )
        self.assertEqual(response.status_code, 302)
        self.tenant.refresh_from_db()
        self.assertNotEqual(self.tenant.name, '改ざん')


class TenantNotFoundInverseTest(TestCase):
    """存在しないテナントの逆証明テスト

    証明: 存在しないテナントへのアクセスは404を返すこと
    """

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
        # 存在しないUUID
        self.fake_pk = '00000000-0000-0000-0000-000000000000'

    def test_detail_not_found(self):
        """存在しないテナントの詳細は404"""
        response = self.client.get(
            reverse('tenants:tenant_detail', kwargs={'pk': self.fake_pk})
        )
        self.assertEqual(response.status_code, 404)

    def test_update_not_found(self):
        """存在しないテナントの編集は404"""
        response = self.client.post(
            reverse('tenants:tenant_update', kwargs={'pk': self.fake_pk}),
            {'name': 'Test', 'code': 'test', 'plan': 'free', 'max_users': 5}
        )
        self.assertEqual(response.status_code, 404)

    def test_toggle_active_not_found(self):
        """存在しないテナントの有効/無効切り替えは404"""
        response = self.client.post(
            reverse('tenants:tenant_toggle_active', kwargs={'pk': self.fake_pk})
        )
        self.assertEqual(response.status_code, 404)


class TenantValidationInverseTest(TestCase):
    """バリデーションの逆証明テスト

    証明: 不正な値は拒否されること
    """

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
        # テナントにユーザーを追加
        for i in range(3):
            User.objects.create_user(
                email=f'user{i}@example.com',
                password='pass',
                tenant=self.tenant,
            )

        self.client = Client()
        self.client.login(email='admin@example.com', password='adminpass123')

    def test_duplicate_code_rejected(self):
        """重複コードは拒否される"""
        response = self.client.post(reverse('tenants:tenant_create'), {
            'name': '新テナント',
            'code': 'test-tenant',  # 既存コード
            'plan': 'free',
            'max_users': 5,
        })
        self.assertEqual(response.status_code, 200)  # フォームエラーで再表示
        # 新しいテナントは作成されていない
        self.assertEqual(Tenant.objects.filter(code='test-tenant').count(), 1)

    def test_max_users_below_current_rejected(self):
        """現在のユーザー数より少ない最大ユーザー数は拒否される"""
        # 現在4ユーザー（superuser + 3）
        response = self.client.post(
            reverse('tenants:tenant_update', kwargs={'pk': self.tenant.pk}),
            {
                'name': 'テストテナント',
                'code': 'test-tenant',
                'plan': 'free',
                'max_users': 2,  # 現在4ユーザーなのに2に制限
                'is_active': True,
            }
        )
        self.assertEqual(response.status_code, 200)  # フォームエラーで再表示
        self.tenant.refresh_from_db()
        self.assertNotEqual(self.tenant.max_users, 2)

    def test_empty_name_rejected(self):
        """空のテナント名は拒否される"""
        response = self.client.post(reverse('tenants:tenant_create'), {
            'name': '',
            'code': 'empty-name',
            'plan': 'free',
            'max_users': 5,
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Tenant.objects.filter(code='empty-name').exists())

    def test_empty_code_rejected(self):
        """空のコードは拒否される"""
        response = self.client.post(reverse('tenants:tenant_create'), {
            'name': 'テスト',
            'code': '',
            'plan': 'free',
            'max_users': 5,
        })
        self.assertEqual(response.status_code, 200)
        # テナント数は変わらない
        self.assertEqual(Tenant.objects.count(), 1)


class SpreadsheetAccessControlInverseTest(TestCase):
    """スプレッドシート接続のアクセス制御逆証明テスト"""

    def setUp(self):
        self.tenant = Tenant.objects.create(
            name='テストテナント',
            code='test-tenant',
        )
        self.normal_user = User.objects.create_user(
            email='user@example.com',
            password='userpass123',
            tenant=self.tenant,
        )
        TenantSpreadsheet.objects.create(
            tenant=self.tenant,
            spreadsheet_id='abc123',
        )
        self.client = Client()

    def test_normal_user_cannot_update_spreadsheet(self):
        """一般ユーザーはスプレッドシート設定を変更できない"""
        self.client.login(email='user@example.com', password='userpass123')
        response = self.client.post(
            reverse('tenants:tenant_spreadsheet', kwargs={'pk': self.tenant.pk}),
            {'spreadsheet_id': 'hacked', 'is_active': True}
        )
        self.assertEqual(response.status_code, 403)
        self.tenant.refresh_from_db()
        self.assertEqual(self.tenant.spreadsheet.spreadsheet_id, 'abc123')

    def test_normal_user_cannot_delete_spreadsheet(self):
        """一般ユーザーはスプレッドシート接続を削除できない"""
        self.client.login(email='user@example.com', password='userpass123')
        response = self.client.post(
            reverse('tenants:tenant_spreadsheet_delete', kwargs={'pk': self.tenant.pk})
        )
        self.assertEqual(response.status_code, 403)
        self.assertTrue(TenantSpreadsheet.objects.filter(tenant=self.tenant).exists())

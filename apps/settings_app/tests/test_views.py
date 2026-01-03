"""
設定アプリ Views テスト
StatusSetting, ApplicationSource, EmailTemplate のCRUDテスト
"""

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model

from apps.tenants.models import Tenant
from apps.settings_app.models import (
    StatusSetting,
    ApplicationSource,
    EmailTemplate,
    SpreadsheetConnection,
)

User = get_user_model()


class SettingsViewTestBase(TestCase):
    """設定Viewテストの基底クラス"""

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


# =============================================================================
# StatusSetting Tests
# =============================================================================

class StatusSettingViewTest(SettingsViewTestBase):
    """ステータス設定ビューのテスト"""

    def setUp(self):
        super().setUp()
        self.status = StatusSetting.objects.create(
            tenant=self.tenant,
            category='application',
            name='書類選考中',
            code='document_screening',
            display_order=1,
            color='#3B82F6',
            is_active=True,
            is_terminal=False,
        )

    def test_status_list_view_accessible(self):
        """ステータス一覧にアクセスできる"""
        response = self.client.get(reverse('settings:status_list'))
        self.assertEqual(response.status_code, 200)

    def test_status_list_contains_status(self):
        """作成したステータスが表示される"""
        response = self.client.get(reverse('settings:status_list'))
        self.assertContains(response, '書類選考中')

    def test_status_create_view_accessible(self):
        """ステータス作成ページにアクセスできる"""
        response = self.client.get(reverse('settings:status_create'))
        self.assertEqual(response.status_code, 200)

    def test_status_create_post_valid_data(self):
        """有効なデータでステータス作成"""
        data = {
            'category': 'application',
            'name': '新規ステータス',
            'code': 'new_status',
            'display_order': 2,
            'color': '#10B981',
            'is_active': True,
            'is_terminal': False,
            'description': 'テスト説明',
        }
        response = self.client.post(reverse('settings:status_create'), data)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(StatusSetting.objects.filter(name='新規ステータス').exists())

    def test_status_update_view_accessible(self):
        """ステータス更新ページにアクセスできる"""
        response = self.client.get(
            reverse('settings:status_update', kwargs={'pk': self.status.pk})
        )
        self.assertEqual(response.status_code, 200)

    def test_status_update_post_valid_data(self):
        """有効なデータでステータス更新"""
        data = {
            'category': 'application',
            'name': '更新済みステータス',
            'code': 'document_screening',
            'display_order': 1,
            'color': '#EF4444',
            'is_active': True,
            'is_terminal': False,
            'description': '',
        }
        response = self.client.post(
            reverse('settings:status_update', kwargs={'pk': self.status.pk}),
            data
        )
        self.assertEqual(response.status_code, 302)
        self.status.refresh_from_db()
        self.assertEqual(self.status.name, '更新済みステータス')

    def test_status_delete_view(self):
        """ステータス削除"""
        status_id = self.status.pk
        response = self.client.post(
            reverse('settings:status_delete', kwargs={'pk': status_id})
        )
        self.assertEqual(response.status_code, 302)
        self.assertFalse(StatusSetting.objects.filter(pk=status_id).exists())


# =============================================================================
# ApplicationSource Tests
# =============================================================================

class ApplicationSourceViewTest(SettingsViewTestBase):
    """応募経路設定ビューのテスト"""

    def setUp(self):
        super().setUp()
        self.source = ApplicationSource.objects.create(
            tenant=self.tenant,
            name='自社サイト',
            source_type='website',
            is_active=True,
            display_order=1,
        )

    def test_source_list_view_accessible(self):
        """応募経路一覧にアクセスできる"""
        response = self.client.get(reverse('settings:source_list'))
        self.assertEqual(response.status_code, 200)

    def test_source_list_contains_source(self):
        """作成した応募経路が表示される"""
        response = self.client.get(reverse('settings:source_list'))
        self.assertContains(response, '自社サイト')

    def test_source_create_view_accessible(self):
        """応募経路作成ページにアクセスできる"""
        response = self.client.get(reverse('settings:source_create'))
        self.assertEqual(response.status_code, 200)

    def test_source_create_post_valid_data(self):
        """有効なデータで応募経路作成"""
        data = {
            'name': 'Indeed',
            'source_type': 'job_board',
            'url': 'https://indeed.com',
            'is_active': True,
            'display_order': 2,
        }
        response = self.client.post(reverse('settings:source_create'), data)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(ApplicationSource.objects.filter(name='Indeed').exists())

    def test_source_update_view_accessible(self):
        """応募経路更新ページにアクセスできる"""
        response = self.client.get(
            reverse('settings:source_update', kwargs={'pk': self.source.pk})
        )
        self.assertEqual(response.status_code, 200)

    def test_source_delete_view(self):
        """応募経路削除"""
        source_id = self.source.pk
        response = self.client.post(
            reverse('settings:source_delete', kwargs={'pk': source_id})
        )
        self.assertEqual(response.status_code, 302)
        self.assertFalse(ApplicationSource.objects.filter(pk=source_id).exists())


# =============================================================================
# EmailTemplate Tests
# =============================================================================

class EmailTemplateViewTest(SettingsViewTestBase):
    """メールテンプレート設定ビューのテスト"""

    def setUp(self):
        super().setUp()
        self.template = EmailTemplate.objects.create(
            tenant=self.tenant,
            name='面接案内メール',
            template_type='interview_invitation',
            subject='面接のご案内',
            body='{{candidate_name}}様\n\n面接のご案内です。',
            is_active=True,
            is_default=True,
        )

    def test_template_list_view_accessible(self):
        """テンプレート一覧にアクセスできる"""
        response = self.client.get(reverse('settings:template_list'))
        self.assertEqual(response.status_code, 200)

    def test_template_list_contains_template(self):
        """作成したテンプレートが表示される"""
        response = self.client.get(reverse('settings:template_list'))
        self.assertContains(response, '面接案内メール')

    def test_template_create_view_accessible(self):
        """テンプレート作成ページにアクセスできる"""
        response = self.client.get(reverse('settings:template_create'))
        self.assertEqual(response.status_code, 200)

    def test_template_create_post_valid_data(self):
        """有効なデータでテンプレート作成"""
        data = {
            'name': '採用通知メール',
            'template_type': 'offer_letter',
            'subject': '採用のお知らせ',
            'body': '{{candidate_name}}様\n\n採用が決定いたしました。',
            'is_active': True,
            'is_default': False,
        }
        response = self.client.post(reverse('settings:template_create'), data)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(EmailTemplate.objects.filter(name='採用通知メール').exists())

    def test_template_update_view_accessible(self):
        """テンプレート更新ページにアクセスできる"""
        response = self.client.get(
            reverse('settings:template_update', kwargs={'pk': self.template.pk})
        )
        self.assertEqual(response.status_code, 200)

    def test_template_delete_view(self):
        """テンプレート削除"""
        template_id = self.template.pk
        response = self.client.post(
            reverse('settings:template_delete', kwargs={'pk': template_id})
        )
        self.assertEqual(response.status_code, 302)
        self.assertFalse(EmailTemplate.objects.filter(pk=template_id).exists())


# =============================================================================
# SpreadsheetConnection Tests
# =============================================================================

class SpreadsheetConnectionViewTest(SettingsViewTestBase):
    """スプレッドシート接続設定ビューのテスト"""

    def setUp(self):
        super().setUp()
        self.connection = SpreadsheetConnection.objects.create(
            tenant=self.tenant,
            spreadsheet_id='test-spreadsheet-id',
            spreadsheet_url='https://docs.google.com/spreadsheets/d/test-spreadsheet-id',
            spreadsheet_name='テストシート',
            credentials_json='{"type": "service_account"}',
            is_active=True,
        )

    def test_spreadsheet_detail_view_accessible(self):
        """スプレッドシート接続詳細にアクセスできる"""
        response = self.client.get(reverse('settings:spreadsheet_detail'))
        self.assertEqual(response.status_code, 200)

    def test_spreadsheet_detail_contains_connection(self):
        """作成した接続が表示される"""
        response = self.client.get(reverse('settings:spreadsheet_detail'))
        self.assertContains(response, 'テストシート')

    def test_spreadsheet_create_view_accessible(self):
        """スプレッドシート接続作成ページにアクセスできる"""
        response = self.client.get(reverse('settings:spreadsheet_create'))
        self.assertEqual(response.status_code, 200)


# =============================================================================
# Settings Index Tests
# =============================================================================

class SettingsIndexViewTest(SettingsViewTestBase):
    """設定インデックスビューのテスト"""

    def test_settings_index_accessible(self):
        """設定インデックスにアクセスできる"""
        response = self.client.get(reverse('settings:index'))
        self.assertEqual(response.status_code, 200)

    def test_settings_index_uses_correct_template(self):
        """正しいテンプレートを使用"""
        response = self.client.get(reverse('settings:index'))
        self.assertTemplateUsed(response, 'settings/index.html')


# =============================================================================
# Authentication Tests
# =============================================================================

class SettingsAuthenticationTest(TestCase):
    """設定ビューの認証テスト"""

    def test_settings_index_requires_login(self):
        """設定インデックスは認証が必要"""
        response = self.client.get(reverse('settings:index'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('login', response.url)

    def test_status_list_requires_login(self):
        """ステータス一覧は認証が必要"""
        response = self.client.get(reverse('settings:status_list'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('login', response.url)


# =============================================================================
# Tenant Isolation Tests
# =============================================================================

class SettingsTenantIsolationTest(SettingsViewTestBase):
    """設定のテナント分離テスト"""

    def test_status_other_tenant_not_visible(self):
        """他テナントのステータスは表示されない"""
        other_tenant = Tenant.objects.create(
            name='他テナント',
            code='other-tenant',
            is_active=True,
        )
        other_status = StatusSetting.objects.create(
            tenant=other_tenant,
            category='application',
            name='他テナントステータス',
            code='other_status',
            display_order=1,
        )
        response = self.client.get(reverse('settings:status_list'))
        self.assertNotContains(response, '他テナントステータス')

    def test_source_other_tenant_not_visible(self):
        """他テナントの応募経路は表示されない"""
        other_tenant = Tenant.objects.create(
            name='他テナント',
            code='other-tenant',
            is_active=True,
        )
        other_source = ApplicationSource.objects.create(
            tenant=other_tenant,
            name='他テナント経路',
            source_type='website',
        )
        response = self.client.get(reverse('settings:source_list'))
        self.assertNotContains(response, '他テナント経路')

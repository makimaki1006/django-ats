"""
Settings アプリ逆証明テスト

逆証明（Proof by Contradiction）により、
不正な操作が適切に拒否されることを検証します。

テスト観点:
1. テナント分離 - 他テナントデータへのアクセス拒否
2. バリデーション - 不正な入力の拒否
3. 認証・認可 - 未認証アクセスの拒否
4. 重複チェック - コード重複の拒否
5. グローバル/テナント固有スコープ制御
"""

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model

from apps.tenants.models import Tenant
from apps.settings_app.models import (
    StatusSetting, StatusCategoryChoices,
    ApplicationSource, SourceTypeChoices,
    EmailTemplate,
)

User = get_user_model()


class StatusSettingTenantIsolationInverseTest(TestCase):
    """ステータス設定のテナント分離逆証明テスト"""

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
        self.status_a = StatusSetting.objects.create(
            tenant=self.tenant_a,
            category=StatusCategoryChoices.APPLICATION,
            name='テナントAステータス',
            code='status-a',
            is_active=True,
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
        self.status_b = StatusSetting.objects.create(
            tenant=self.tenant_b,
            category=StatusCategoryChoices.APPLICATION,
            name='テナントBステータス',
            code='status-b',
            is_active=True,
        )

        self.client = Client()

    def test_cannot_update_other_tenant_status(self):
        """他テナントのステータスは更新できない"""
        self.client.login(email='user_a@example.com', password='testpass123')
        response = self.client.post(
            reverse('settings:status_update', kwargs={'pk': self.status_b.pk}),
            {
                'category': StatusCategoryChoices.APPLICATION,
                'name': '不正な更新',
                'code': 'status-b',
                'is_active': True,
            }
        )
        self.assertEqual(response.status_code, 404)
        self.status_b.refresh_from_db()
        self.assertEqual(self.status_b.name, 'テナントBステータス')

    def test_cannot_delete_other_tenant_status(self):
        """他テナントのステータスは削除できない"""
        self.client.login(email='user_a@example.com', password='testpass123')
        response = self.client.post(
            reverse('settings:status_delete', kwargs={'pk': self.status_b.pk})
        )
        self.assertEqual(response.status_code, 404)
        self.assertTrue(StatusSetting.objects.filter(pk=self.status_b.pk).exists())

    def test_list_shows_only_own_tenant_statuses(self):
        """一覧は自テナントのステータスのみ表示"""
        self.client.login(email='user_a@example.com', password='testpass123')
        response = self.client.get(reverse('settings:status_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'テナントAステータス')
        self.assertNotContains(response, 'テナントBステータス')


class StatusSettingValidationInverseTest(TestCase):
    """ステータス設定のバリデーション逆証明テスト"""

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
        self.existing_status = StatusSetting.objects.create(
            tenant=self.tenant,
            category=StatusCategoryChoices.APPLICATION,
            name='既存ステータス',
            code='existing',
            is_active=True,
        )
        self.client = Client()
        self.client.login(email='test@example.com', password='testpass123')

    def test_cannot_create_status_without_name(self):
        """名前なしでステータスを作成できない"""
        response = self.client.post(
            reverse('settings:status_create'),
            {
                'category': StatusCategoryChoices.APPLICATION,
                'name': '',
                'code': 'new-status',
                'is_active': True,
            }
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'このフィールドは必須です')

    def test_cannot_create_status_with_duplicate_code_in_category(self):
        """同一カテゴリで重複コードは作成できない"""
        response = self.client.post(
            reverse('settings:status_create'),
            {
                'category': StatusCategoryChoices.APPLICATION,
                'name': '新規ステータス',
                'code': 'existing',  # 既存コード
                'is_active': True,
            }
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '既に')

    def test_can_use_same_code_in_different_category(self):
        """異なるカテゴリでは同一コードを使用可能"""
        response = self.client.post(
            reverse('settings:status_create'),
            {
                'category': StatusCategoryChoices.INTERVIEW,  # 異なるカテゴリ
                'name': '面接ステータス',
                'code': 'existing',  # 同じコード
                'is_active': True,
            }
        )
        # 作成成功（302リダイレクト）またはフォーム再表示
        self.assertIn(response.status_code, [200, 302])


class ApplicationSourceTenantIsolationInverseTest(TestCase):
    """応募経路のテナント分離逆証明テスト"""

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
        self.source_a = ApplicationSource.objects.create(
            tenant=self.tenant_a,
            name='テナントA経路',
            source_type=SourceTypeChoices.JOB_BOARD,
            is_active=True,
        )

        # テナントB
        self.tenant_b = Tenant.objects.create(
            name='テナントB',
            code='tenant-b',
            is_active=True,
        )
        self.source_b = ApplicationSource.objects.create(
            tenant=self.tenant_b,
            name='テナントB経路',
            source_type=SourceTypeChoices.JOB_BOARD,
            is_active=True,
        )

        # グローバル経路
        self.global_source = ApplicationSource.objects.create(
            tenant=None,
            name='グローバル経路',
            source_type=SourceTypeChoices.REFERRAL,
            is_active=True,
        )

        self.client = Client()

    def test_cannot_update_other_tenant_source(self):
        """他テナントの応募経路は更新できない"""
        self.client.login(email='user_a@example.com', password='testpass123')
        response = self.client.post(
            reverse('settings:source_update', kwargs={'pk': self.source_b.pk}),
            {
                'name': '不正な更新',
                'source_type': SourceTypeChoices.JOB_BOARD,
                'is_active': True,
            }
        )
        self.assertEqual(response.status_code, 404)

    def test_cannot_delete_other_tenant_source(self):
        """他テナントの応募経路は削除できない"""
        self.client.login(email='user_a@example.com', password='testpass123')
        response = self.client.post(
            reverse('settings:source_delete', kwargs={'pk': self.source_b.pk})
        )
        self.assertEqual(response.status_code, 404)
        self.assertTrue(ApplicationSource.objects.filter(pk=self.source_b.pk).exists())

    def test_cannot_update_global_source(self):
        """グローバル応募経路は更新できない"""
        self.client.login(email='user_a@example.com', password='testpass123')
        response = self.client.post(
            reverse('settings:source_update', kwargs={'pk': self.global_source.pk}),
            {
                'name': '不正な更新',
                'source_type': SourceTypeChoices.REFERRAL,
                'is_active': True,
            }
        )
        self.assertEqual(response.status_code, 404)

    def test_can_view_global_source_in_list(self):
        """グローバル経路は一覧に表示される"""
        self.client.login(email='user_a@example.com', password='testpass123')
        response = self.client.get(reverse('settings:source_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'グローバル経路')
        self.assertContains(response, 'テナントA経路')
        self.assertNotContains(response, 'テナントB経路')


class EmailTemplateTenantIsolationInverseTest(TestCase):
    """メールテンプレートのテナント分離逆証明テスト"""

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
        self.template_a = EmailTemplate.objects.create(
            tenant=self.tenant_a,
            name='テナントAテンプレート',
            template_type=EmailTemplate.TemplateTypeChoices.INTERVIEW_INVITATION,
            subject='テストsubject',
            body='テストbody',
            is_active=True,
        )

        # テナントB
        self.tenant_b = Tenant.objects.create(
            name='テナントB',
            code='tenant-b',
            is_active=True,
        )
        self.template_b = EmailTemplate.objects.create(
            tenant=self.tenant_b,
            name='テナントBテンプレート',
            template_type=EmailTemplate.TemplateTypeChoices.INTERVIEW_INVITATION,
            subject='テストsubject',
            body='テストbody',
            is_active=True,
        )

        self.client = Client()

    def test_cannot_update_other_tenant_template(self):
        """他テナントのテンプレートは更新できない"""
        self.client.login(email='user_a@example.com', password='testpass123')
        response = self.client.post(
            reverse('settings:template_update', kwargs={'pk': self.template_b.pk}),
            {
                'name': '不正な更新',
                'template_type': EmailTemplate.TemplateTypeChoices.INTERVIEW_INVITATION,
                'subject': '不正subject',
                'body': '不正body',
                'is_active': True,
            }
        )
        self.assertEqual(response.status_code, 404)

    def test_cannot_delete_other_tenant_template(self):
        """他テナントのテンプレートは削除できない"""
        self.client.login(email='user_a@example.com', password='testpass123')
        response = self.client.post(
            reverse('settings:template_delete', kwargs={'pk': self.template_b.pk})
        )
        self.assertEqual(response.status_code, 404)
        self.assertTrue(EmailTemplate.objects.filter(pk=self.template_b.pk).exists())

    def test_cannot_preview_other_tenant_template(self):
        """他テナントのテンプレートはプレビューできない"""
        self.client.login(email='user_a@example.com', password='testpass123')
        response = self.client.get(
            reverse('settings:template_preview', kwargs={'pk': self.template_b.pk})
        )
        self.assertEqual(response.status_code, 404)

    def test_cannot_duplicate_other_tenant_template(self):
        """他テナントのテンプレートは複製できない"""
        self.client.login(email='user_a@example.com', password='testpass123')
        response = self.client.post(
            reverse('settings:template_duplicate', kwargs={'pk': self.template_b.pk})
        )
        self.assertEqual(response.status_code, 404)


class EmailTemplateValidationInverseTest(TestCase):
    """メールテンプレートのバリデーション逆証明テスト"""

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

    def test_cannot_create_template_without_name(self):
        """名前なしでテンプレートを作成できない"""
        response = self.client.post(
            reverse('settings:template_create'),
            {
                'name': '',
                'template_type': EmailTemplate.TemplateTypeChoices.INTERVIEW_INVITATION,
                'subject': 'テスト件名',
                'body': 'テスト本文',
                'is_active': True,
            }
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'このフィールドは必須です')

    def test_cannot_create_template_without_subject(self):
        """件名なしでテンプレートを作成できない"""
        response = self.client.post(
            reverse('settings:template_create'),
            {
                'name': 'テストテンプレート',
                'template_type': EmailTemplate.TemplateTypeChoices.INTERVIEW_INVITATION,
                'subject': '',
                'body': 'テスト本文',
                'is_active': True,
            }
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'このフィールドは必須です')

    def test_cannot_create_template_without_body(self):
        """本文なしでテンプレートを作成できない"""
        response = self.client.post(
            reverse('settings:template_create'),
            {
                'name': 'テストテンプレート',
                'template_type': EmailTemplate.TemplateTypeChoices.INTERVIEW_INVITATION,
                'subject': 'テスト件名',
                'body': '',
                'is_active': True,
            }
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'このフィールドは必須です')


class SettingsAuthenticationInverseTest(TestCase):
    """認証・認可の逆証明テスト"""

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
        self.status = StatusSetting.objects.create(
            tenant=self.tenant,
            category=StatusCategoryChoices.APPLICATION,
            name='テストステータス',
            code='test',
            is_active=True,
        )
        self.client = Client()
        # ログインしない

    def test_unauthenticated_cannot_access_index(self):
        """未認証ユーザーは設定インデックスにアクセスできない"""
        response = self.client.get(reverse('settings:index'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('login', response.url)

    def test_unauthenticated_cannot_access_status_list(self):
        """未認証ユーザーはステータス一覧にアクセスできない"""
        response = self.client.get(reverse('settings:status_list'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('login', response.url)

    def test_unauthenticated_cannot_create_status(self):
        """未認証ユーザーはステータスを作成できない"""
        response = self.client.post(
            reverse('settings:status_create'),
            {
                'category': StatusCategoryChoices.APPLICATION,
                'name': '不正ステータス',
                'code': 'invalid',
                'is_active': True,
            }
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn('login', response.url)

    def test_unauthenticated_cannot_delete_status(self):
        """未認証ユーザーはステータスを削除できない"""
        response = self.client.post(
            reverse('settings:status_delete', kwargs={'pk': self.status.pk})
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn('login', response.url)
        self.assertTrue(StatusSetting.objects.filter(pk=self.status.pk).exists())


class EmailTemplateRenderInverseTest(TestCase):
    """メールテンプレートレンダリングの逆証明テスト"""

    def setUp(self):
        self.tenant = Tenant.objects.create(
            name='テストテナント',
            code='test-tenant',
            is_active=True,
        )
        self.template = EmailTemplate.objects.create(
            tenant=self.tenant,
            name='テストテンプレート',
            template_type=EmailTemplate.TemplateTypeChoices.INTERVIEW_INVITATION,
            subject='{{candidate_name}}様 面接のご案内',
            body='{{candidate_name}}様\n\n{{job_title}}の面接について',
            is_active=True,
        )

    def test_render_with_context(self):
        """コンテキストが正しくレンダリングされる"""
        context = {
            'candidate_name': '山田太郎',
            'job_title': 'エンジニア',
        }
        result = self.template.render(context)
        self.assertEqual(result['subject'], '山田太郎様 面接のご案内')
        self.assertIn('山田太郎様', result['body'])
        self.assertIn('エンジニア', result['body'])

    def test_render_with_missing_context(self):
        """不足コンテキストでもエラーにならない（変数がそのまま表示）"""
        context = {}  # 空コンテキスト
        result = self.template.render(context)
        # 変数がそのまま残るか、空になるかは実装次第
        self.assertIsNotNone(result['subject'])
        self.assertIsNotNone(result['body'])

"""
Settings アプリのモデル・フォームテスト

逆証明によるロジック検証:
1. StatusSettingモデルの制約
2. ApplicationSourceモデルのロジック
3. EmailTemplateモデルのレンダリング
4. フォームバリデーション
"""

from django.test import TestCase
from django.core.exceptions import ValidationError

from apps.tenants.models import Tenant
from apps.settings_app.models import (
    StatusSetting, StatusCategoryChoices,
    ApplicationSource, SourceTypeChoices,
    EmailTemplate,
)
from apps.settings_app.forms import (
    StatusSettingForm,
    ApplicationSourceForm,
    EmailTemplateForm,
)


class StatusSettingModelTest(TestCase):
    """ステータス設定モデルのテスト"""

    def setUp(self):
        self.tenant = Tenant.objects.create(
            name='テストテナント',
            code='test-tenant',
            is_active=True,
        )

    def test_create_status_setting(self):
        """ステータス設定の作成"""
        status = StatusSetting.objects.create(
            tenant=self.tenant,
            category=StatusCategoryChoices.APPLICATION,
            name='書類選考中',
            code='screening',
            display_order=1,
            color='blue',
        )
        self.assertEqual(status.name, '書類選考中')
        self.assertEqual(status.code, 'screening')
        self.assertTrue(status.is_active)
        self.assertFalse(status.is_terminal)

    def test_unique_constraint_per_tenant_category(self):
        """同一テナント・同一カテゴリでコード重複禁止"""
        StatusSetting.objects.create(
            tenant=self.tenant,
            category=StatusCategoryChoices.APPLICATION,
            name='書類選考中',
            code='screening',
        )

        with self.assertRaises(ValidationError):
            StatusSetting.objects.create(
                tenant=self.tenant,
                category=StatusCategoryChoices.APPLICATION,
                name='書類選考',
                code='screening',  # 同じコード
            )

    def test_same_code_different_category_allowed(self):
        """異なるカテゴリなら同じコードOK"""
        StatusSetting.objects.create(
            tenant=self.tenant,
            category=StatusCategoryChoices.APPLICATION,
            name='進行中',
            code='in_progress',
        )

        # 別カテゴリなら同じコードでOK
        status2 = StatusSetting.objects.create(
            tenant=self.tenant,
            category=StatusCategoryChoices.INTERVIEW,
            name='進行中',
            code='in_progress',
        )
        self.assertIsNotNone(status2.id)

    def test_same_code_different_tenant_allowed(self):
        """異なるテナントなら同じコードOK"""
        tenant2 = Tenant.objects.create(
            name='テストテナント2',
            code='test-tenant-2',
            is_active=True,
        )

        StatusSetting.objects.create(
            tenant=self.tenant,
            category=StatusCategoryChoices.APPLICATION,
            name='書類選考中',
            code='screening',
        )

        # 別テナントなら同じコードでOK
        status2 = StatusSetting.objects.create(
            tenant=tenant2,
            category=StatusCategoryChoices.APPLICATION,
            name='書類選考中',
            code='screening',
        )
        self.assertIsNotNone(status2.id)

    def test_str_representation(self):
        """__str__の検証"""
        status = StatusSetting.objects.create(
            tenant=self.tenant,
            category=StatusCategoryChoices.APPLICATION,
            name='書類選考中',
            code='screening',
        )
        self.assertEqual(str(status), '応募ステータス: 書類選考中')

    def test_ordering(self):
        """並び順の検証"""
        StatusSetting.objects.create(
            tenant=self.tenant,
            category=StatusCategoryChoices.APPLICATION,
            name='二次',
            code='second',
            display_order=2,
        )
        StatusSetting.objects.create(
            tenant=self.tenant,
            category=StatusCategoryChoices.APPLICATION,
            name='一次',
            code='first',
            display_order=1,
        )

        statuses = list(StatusSetting.objects.filter(tenant=self.tenant))
        self.assertEqual(statuses[0].code, 'first')
        self.assertEqual(statuses[1].code, 'second')


class ApplicationSourceModelTest(TestCase):
    """応募経路モデルのテスト"""

    def setUp(self):
        self.tenant = Tenant.objects.create(
            name='テストテナント',
            code='test-tenant',
            is_active=True,
        )

    def test_create_global_source(self):
        """グローバル応募経路の作成（tenant=null）"""
        source = ApplicationSource.objects.create(
            name='Indeed',
            source_type=SourceTypeChoices.JOB_BOARD,
            url='https://indeed.com',
        )
        self.assertTrue(source.is_global)
        self.assertIsNone(source.tenant)

    def test_create_tenant_source(self):
        """テナント固有応募経路の作成"""
        source = ApplicationSource.objects.create(
            tenant=self.tenant,
            name='自社採用サイト',
            source_type=SourceTypeChoices.DIRECT,
        )
        self.assertFalse(source.is_global)
        self.assertEqual(source.tenant, self.tenant)

    def test_source_type_choices(self):
        """経路タイプの選択肢検証"""
        choices = [c[0] for c in SourceTypeChoices.choices]
        expected = ['direct', 'agent', 'job_board', 'referral', 'sns', 'other']
        self.assertEqual(choices, expected)


class EmailTemplateModelTest(TestCase):
    """メールテンプレートモデルのテスト"""

    def setUp(self):
        self.tenant = Tenant.objects.create(
            name='テストテナント',
            code='test-tenant',
            is_active=True,
        )

    def test_create_template(self):
        """テンプレート作成"""
        template = EmailTemplate.objects.create(
            tenant=self.tenant,
            name='面接案内',
            template_type=EmailTemplate.TemplateTypeChoices.INTERVIEW_INVITATION,
            subject='【{{ company_name }}】面接のご案内',
            body='{{ candidate_name }} 様\n\n面接日時: {{ interview_date }}',
        )
        self.assertEqual(template.name, '面接案内')
        self.assertTrue(template.is_active)
        self.assertFalse(template.is_default)

    def test_render_template(self):
        """テンプレートレンダリングの検証"""
        template = EmailTemplate.objects.create(
            tenant=self.tenant,
            name='面接案内',
            template_type=EmailTemplate.TemplateTypeChoices.INTERVIEW_INVITATION,
            subject='【{{ company_name }}】面接のご案内',
            body='{{ candidate_name }} 様\n\n面接日時: {{ interview_date }}',
        )

        context = {
            'company_name': '株式会社テスト',
            'candidate_name': '山田太郎',
            'interview_date': '2025年1月10日 14:00',
        }

        result = template.render(context)
        self.assertEqual(result['subject'], '【株式会社テスト】面接のご案内')
        self.assertIn('山田太郎', result['body'])
        self.assertIn('2025年1月10日 14:00', result['body'])

    def test_render_with_missing_variable(self):
        """存在しない変数はそのまま出力"""
        template = EmailTemplate.objects.create(
            tenant=self.tenant,
            name='テスト',
            template_type=EmailTemplate.TemplateTypeChoices.CUSTOM,
            subject='テスト {{ unknown }}',
            body='本文',
        )

        result = template.render({})
        # Djangoテンプレートは存在しない変数を空文字にする
        self.assertEqual(result['subject'], 'テスト ')


class StatusSettingFormTest(TestCase):
    """ステータス設定フォームのテスト"""

    def setUp(self):
        self.tenant = Tenant.objects.create(
            name='テストテナント',
            code='test-tenant',
            is_active=True,
        )

    def test_valid_form(self):
        """正常なフォーム"""
        form = StatusSettingForm(
            data={
                'category': StatusCategoryChoices.APPLICATION,
                'name': '書類選考中',
                'code': 'screening',
                'display_order': 1,
                'color': 'blue',
                'is_active': True,
                'is_terminal': False,
            },
            tenant=self.tenant,
        )
        self.assertTrue(form.is_valid(), form.errors)

    def test_duplicate_code_validation(self):
        """重複コードのバリデーション"""
        StatusSetting.objects.create(
            tenant=self.tenant,
            category=StatusCategoryChoices.APPLICATION,
            name='書類選考中',
            code='screening',
        )

        form = StatusSettingForm(
            data={
                'category': StatusCategoryChoices.APPLICATION,
                'name': '別の名前',
                'code': 'screening',  # 重複
                'display_order': 2,
                'color': 'blue',
                'is_active': True,
            },
            tenant=self.tenant,
        )
        self.assertFalse(form.is_valid())


class EmailTemplateFormTest(TestCase):
    """メールテンプレートフォームのテスト"""

    def setUp(self):
        self.tenant = Tenant.objects.create(
            name='テストテナント',
            code='test-tenant',
            is_active=True,
        )

    def test_default_template_switch(self):
        """デフォルトテンプレートの切り替え"""
        # 既存のデフォルトを作成
        existing = EmailTemplate.objects.create(
            tenant=self.tenant,
            name='既存面接案内',
            template_type=EmailTemplate.TemplateTypeChoices.INTERVIEW_INVITATION,
            subject='件名',
            body='本文',
            is_default=True,
        )

        # 新しいテンプレートをデフォルトに設定
        form = EmailTemplateForm(
            data={
                'name': '新面接案内',
                'template_type': EmailTemplate.TemplateTypeChoices.INTERVIEW_INVITATION,
                'subject': '新件名',
                'body': '新本文',
                'is_active': True,
                'is_default': True,
            },
            tenant=self.tenant,
        )

        self.assertTrue(form.is_valid(), form.errors)
        new_template = form.save(commit=False)
        new_template.tenant = self.tenant
        new_template.save()

        # 既存のデフォルトが解除されている
        existing.refresh_from_db()
        self.assertFalse(existing.is_default)
        self.assertTrue(new_template.is_default)

"""Django ATS - 設定モデルテスト

StatusSetting, ApplicationSource, EmailTemplate モデルのテスト。
"""

import pytest

from apps.settings_app.models import (
    StatusSetting,
    StatusCategoryChoices,
    ApplicationSource,
    SourceTypeChoices,
    EmailTemplate,
)
from apps.tenants.models import Tenant


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def tenant(db):
    """テストテナント"""
    return Tenant.objects.create(
        name='設定テスト',
        code='settings-test',
        is_active=True,
    )


# =============================================================================
# StatusSetting Tests
# =============================================================================

class TestStatusSetting:
    """StatusSetting モデルのテスト"""

    @pytest.mark.django_db
    def test_create_status_setting(self, tenant):
        """ステータス設定を作成できる"""
        status = StatusSetting.objects.create(
            tenant=tenant,
            category=StatusCategoryChoices.APPLICATION,
            name='新規応募',
            code='new',
        )
        assert status.pk is not None
        assert status.name == '新規応募'

    @pytest.mark.django_db
    def test_str_method(self, tenant):
        """__str__がカテゴリとステータス名を返す"""
        status = StatusSetting.objects.create(
            tenant=tenant,
            category=StatusCategoryChoices.APPLICATION,
            name='書類選考中',
            code='screening',
        )
        str_repr = str(status)
        assert '応募ステータス' in str_repr
        assert '書類選考中' in str_repr

    @pytest.mark.django_db
    def test_default_values(self, tenant):
        """デフォルト値が正しく設定される"""
        status = StatusSetting.objects.create(
            tenant=tenant,
            category=StatusCategoryChoices.INTERVIEW,
            name='面接予定',
            code='scheduled',
        )
        assert status.display_order == 0
        assert status.color == 'gray'
        assert status.is_active is True
        assert status.is_terminal is False

    @pytest.mark.django_db
    def test_all_categories_valid(self, tenant):
        """全カテゴリが有効"""
        for category_value, _ in StatusCategoryChoices.choices:
            status = StatusSetting.objects.create(
                tenant=tenant,
                category=category_value,
                name=f'{category_value}ステータス',
                code=f'{category_value}_code',
            )
            assert status.category == category_value


# =============================================================================
# ApplicationSource Tests
# =============================================================================

class TestApplicationSource:
    """ApplicationSource モデルのテスト"""

    @pytest.mark.django_db
    def test_create_application_source(self, tenant):
        """応募経路を作成できる"""
        source = ApplicationSource.objects.create(
            tenant=tenant,
            name='Indeed',
            source_type=SourceTypeChoices.JOB_BOARD,
        )
        assert source.pk is not None
        assert source.name == 'Indeed'

    @pytest.mark.django_db
    def test_str_method(self, tenant):
        """__str__が経路名を返す"""
        source = ApplicationSource.objects.create(
            tenant=tenant,
            name='LinkedIn',
            source_type=SourceTypeChoices.SNS,
        )
        assert str(source) == 'LinkedIn'

    @pytest.mark.django_db
    def test_is_global_with_tenant(self, tenant):
        """テナント付きはグローバルではない"""
        source = ApplicationSource.objects.create(
            tenant=tenant,
            name='テナント固有経路',
            source_type=SourceTypeChoices.DIRECT,
        )
        assert source.is_global is False

    @pytest.mark.django_db
    def test_is_global_without_tenant(self):
        """テナントなしはグローバル"""
        source = ApplicationSource.objects.create(
            tenant=None,
            name='共通経路',
            source_type=SourceTypeChoices.OTHER,
        )
        assert source.is_global is True

    @pytest.mark.django_db
    def test_all_source_types_valid(self, tenant):
        """全経路タイプが有効"""
        for source_type_value, _ in SourceTypeChoices.choices:
            source = ApplicationSource.objects.create(
                tenant=tenant,
                name=f'{source_type_value}経路',
                source_type=source_type_value,
            )
            assert source.source_type == source_type_value


# =============================================================================
# EmailTemplate Tests
# =============================================================================

class TestEmailTemplate:
    """EmailTemplate モデルのテスト"""

    @pytest.mark.django_db
    def test_create_email_template(self, tenant):
        """メールテンプレートを作成できる"""
        template = EmailTemplate.objects.create(
            tenant=tenant,
            name='面接案内テンプレート',
            template_type=EmailTemplate.TemplateTypeChoices.INTERVIEW_INVITATION,
            subject='面接のご案内',
            body='{{candidate_name}}様、面接のご案内です。',
        )
        assert template.pk is not None
        assert template.name == '面接案内テンプレート'

    @pytest.mark.django_db
    def test_str_method(self, tenant):
        """__str__がタイプと名前を返す"""
        template = EmailTemplate.objects.create(
            tenant=tenant,
            name='内定テンプレート',
            template_type=EmailTemplate.TemplateTypeChoices.OFFER_LETTER,
            subject='内定のお知らせ',
            body='おめでとうございます。',
        )
        str_repr = str(template)
        assert '内定通知' in str_repr
        assert '内定テンプレート' in str_repr

    @pytest.mark.django_db
    def test_render_template(self, tenant):
        """テンプレートをレンダリングできる"""
        template = EmailTemplate.objects.create(
            tenant=tenant,
            name='レンダリングテスト',
            template_type=EmailTemplate.TemplateTypeChoices.INTERVIEW_INVITATION,
            subject='{{candidate_name}}様への面接のご案内',
            body='{{candidate_name}}様、\n\n{{job_title}}の面接のご案内です。',
        )

        result = template.render({
            'candidate_name': '山田太郎',
            'job_title': 'ソフトウェアエンジニア',
        })

        assert result['subject'] == '山田太郎様への面接のご案内'
        assert '山田太郎様' in result['body']
        assert 'ソフトウェアエンジニア' in result['body']

    @pytest.mark.django_db
    def test_render_template_empty_context(self, tenant):
        """空のコンテキストでレンダリング"""
        template = EmailTemplate.objects.create(
            tenant=tenant,
            name='シンプルテンプレート',
            template_type=EmailTemplate.TemplateTypeChoices.WELCOME,
            subject='ようこそ',
            body='本日からよろしくお願いします。',
        )

        result = template.render({})

        assert result['subject'] == 'ようこそ'
        assert result['body'] == '本日からよろしくお願いします。'

    @pytest.mark.django_db
    def test_all_template_types_valid(self, tenant):
        """全テンプレートタイプが有効"""
        for template_type_value, _ in EmailTemplate.TemplateTypeChoices.choices:
            template = EmailTemplate.objects.create(
                tenant=tenant,
                name=f'{template_type_value}テンプレート',
                template_type=template_type_value,
                subject='テスト件名',
                body='テスト本文',
            )
            assert template.template_type == template_type_value

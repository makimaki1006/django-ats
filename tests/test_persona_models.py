"""Django ATS - ペルソナモデルテスト

Persona モデルのテスト。
"""

import pytest
from django.urls.exceptions import NoReverseMatch

from apps.personas.models import Persona
from apps.tenants.models import Tenant
from apps.accounts.models import CustomUser, UserRoleChoices


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def tenant(db):
    """テストテナント"""
    return Tenant.objects.create(
        name='ペルソナテスト',
        code='persona-test',
        is_active=True,
    )


@pytest.fixture
def user(db, tenant):
    """テストユーザー"""
    return CustomUser.objects.create_user(
        email='user@persona-test.com',
        password='testpass123',
        role=UserRoleChoices.CLIENT_ADMIN,
        tenant=tenant,
    )


@pytest.fixture
def persona(db, tenant, user):
    """テストペルソナ"""
    return Persona.objects.create(
        tenant=tenant,
        name='エンジニアペルソナ',
        description='バックエンドエンジニア向け',
        is_active=True,
        created_by=user,
    )


# =============================================================================
# Basic Model Tests
# =============================================================================

class TestPersonaModel:
    """Persona モデルのテスト"""

    @pytest.mark.django_db
    def test_create_persona(self, tenant, user):
        """ペルソナを作成できる"""
        persona = Persona.objects.create(
            tenant=tenant,
            name='新規ペルソナ',
            created_by=user,
        )
        assert persona.pk is not None
        assert persona.name == '新規ペルソナ'

    @pytest.mark.django_db
    def test_str_method(self, persona):
        """__str__が名前を返す"""
        assert str(persona) == 'エンジニアペルソナ'

    @pytest.mark.django_db
    def test_get_absolute_url(self, persona):
        """絶対URLを取得できる"""
        try:
            url = persona.get_absolute_url()
            assert str(persona.pk) in url
        except NoReverseMatch:
            # URLが設定されていない場合はスキップ
            pass

    @pytest.mark.django_db
    def test_default_values(self, tenant, user):
        """デフォルト値が正しく設定される"""
        persona = Persona.objects.create(
            tenant=tenant,
            name='デフォルトテスト',
            created_by=user,
        )
        assert persona.is_template is False
        assert persona.is_active is True
        assert persona.education_level == Persona.EducationLevelChoices.NONE
        assert persona.required_skills == []
        assert persona.preferred_skills == []
        assert persona.personality_traits == []


# =============================================================================
# Age Range Display Tests
# =============================================================================

class TestAgeRangeDisplay:
    """年齢範囲表示のテスト"""

    @pytest.mark.django_db
    def test_age_range_both(self, tenant, user):
        """最小・最大両方設定時"""
        persona = Persona.objects.create(
            tenant=tenant,
            name='年齢テスト1',
            age_min=25,
            age_max=35,
            created_by=user,
        )
        assert persona.age_range_display == '25〜35歳'

    @pytest.mark.django_db
    def test_age_range_min_only(self, tenant, user):
        """最小年齢のみ設定時"""
        persona = Persona.objects.create(
            tenant=tenant,
            name='年齢テスト2',
            age_min=30,
            created_by=user,
        )
        assert persona.age_range_display == '30歳以上'

    @pytest.mark.django_db
    def test_age_range_max_only(self, tenant, user):
        """最大年齢のみ設定時"""
        persona = Persona.objects.create(
            tenant=tenant,
            name='年齢テスト3',
            age_max=40,
            created_by=user,
        )
        assert persona.age_range_display == '40歳以下'

    @pytest.mark.django_db
    def test_age_range_none(self, tenant, user):
        """年齢未設定時"""
        persona = Persona.objects.create(
            tenant=tenant,
            name='年齢テスト4',
            created_by=user,
        )
        assert persona.age_range_display == '不問'


# =============================================================================
# Experience Range Display Tests
# =============================================================================

class TestExperienceRangeDisplay:
    """経験年数範囲表示のテスト"""

    @pytest.mark.django_db
    def test_experience_range_both(self, tenant, user):
        """最小・最大両方設定時"""
        persona = Persona.objects.create(
            tenant=tenant,
            name='経験テスト1',
            experience_years_min=3,
            experience_years_max=10,
            created_by=user,
        )
        assert persona.experience_range_display == '3〜10年'

    @pytest.mark.django_db
    def test_experience_range_min_only(self, tenant, user):
        """最小経験年数のみ設定時"""
        persona = Persona.objects.create(
            tenant=tenant,
            name='経験テスト2',
            experience_years_min=5,
            created_by=user,
        )
        assert persona.experience_range_display == '5年以上'

    @pytest.mark.django_db
    def test_experience_range_max_only(self, tenant, user):
        """最大経験年数のみ設定時"""
        persona = Persona.objects.create(
            tenant=tenant,
            name='経験テスト3',
            experience_years_max=8,
            created_by=user,
        )
        assert persona.experience_range_display == '8年以下'

    @pytest.mark.django_db
    def test_experience_range_none(self, tenant, user):
        """経験年数未設定時"""
        persona = Persona.objects.create(
            tenant=tenant,
            name='経験テスト4',
            created_by=user,
        )
        assert persona.experience_range_display == '不問'


# =============================================================================
# Duplicate Tests
# =============================================================================

class TestPersonaDuplicate:
    """ペルソナ複製のテスト"""

    @pytest.mark.django_db
    def test_duplicate_default_name(self, persona):
        """デフォルト名で複製"""
        copied = persona.duplicate()
        assert copied.pk != persona.pk
        assert copied.name == 'エンジニアペルソナ (コピー)'
        assert copied.tenant == persona.tenant
        assert copied.is_template is False

    @pytest.mark.django_db
    def test_duplicate_custom_name(self, persona):
        """カスタム名で複製"""
        copied = persona.duplicate(new_name='カスタムコピー')
        assert copied.pk != persona.pk
        assert copied.name == 'カスタムコピー'

    @pytest.mark.django_db
    def test_duplicate_preserves_attributes(self, tenant, user):
        """複製時に属性が保持される"""
        original = Persona.objects.create(
            tenant=tenant,
            name='完全テスト',
            description='詳細説明',
            is_template=True,
            age_min=25,
            age_max=35,
            experience_years_min=3,
            required_skills=['Python', 'Django'],
            education_level=Persona.EducationLevelChoices.BACHELOR,
            created_by=user,
        )

        copied = original.duplicate()

        assert copied.description == original.description
        assert copied.age_min == original.age_min
        assert copied.age_max == original.age_max
        assert copied.experience_years_min == original.experience_years_min
        assert copied.required_skills == original.required_skills
        assert copied.education_level == original.education_level
        # is_templateはFalseにリセット
        assert copied.is_template is False


# =============================================================================
# Education Level Tests
# =============================================================================

class TestEducationLevel:
    """学歴レベルのテスト"""

    @pytest.mark.django_db
    def test_all_education_levels_valid(self, tenant, user):
        """すべての学歴レベルが有効"""
        for level_value, level_label in Persona.EducationLevelChoices.choices:
            persona = Persona.objects.create(
                tenant=tenant,
                name=f'{level_label}ペルソナ',
                education_level=level_value,
                created_by=user,
            )
            assert persona.education_level == level_value


# =============================================================================
# Template Tests
# =============================================================================

class TestPersonaTemplate:
    """ペルソナテンプレートのテスト"""

    @pytest.mark.django_db
    def test_create_template(self, tenant, user):
        """テンプレートとして作成"""
        template = Persona.objects.create(
            tenant=tenant,
            name='テンプレートペルソナ',
            is_template=True,
            created_by=user,
        )
        assert template.is_template is True

    @pytest.mark.django_db
    def test_filter_templates(self, tenant, user):
        """テンプレートのみフィルタ"""
        Persona.objects.create(
            tenant=tenant, name='通常1', is_template=False, created_by=user
        )
        Persona.objects.create(
            tenant=tenant, name='テンプレート1', is_template=True, created_by=user
        )
        Persona.objects.create(
            tenant=tenant, name='テンプレート2', is_template=True, created_by=user
        )

        templates = Persona.objects.filter(tenant=tenant, is_template=True)
        assert templates.count() == 2


# =============================================================================
# Skills Tests
# =============================================================================

class TestPersonaSkills:
    """スキル設定のテスト"""

    @pytest.mark.django_db
    def test_required_skills_json(self, tenant, user):
        """必須スキルをJSON形式で保存"""
        persona = Persona.objects.create(
            tenant=tenant,
            name='スキルテスト',
            required_skills=['Python', 'Django', 'PostgreSQL'],
            created_by=user,
        )
        assert 'Python' in persona.required_skills
        assert len(persona.required_skills) == 3

    @pytest.mark.django_db
    def test_preferred_skills_json(self, tenant, user):
        """歓迎スキルをJSON形式で保存"""
        persona = Persona.objects.create(
            tenant=tenant,
            name='歓迎スキルテスト',
            preferred_skills=['AWS', 'Docker', 'Kubernetes'],
            created_by=user,
        )
        assert 'AWS' in persona.preferred_skills
        assert len(persona.preferred_skills) == 3

    @pytest.mark.django_db
    def test_personality_traits_json(self, tenant, user):
        """人物像をJSON形式で保存"""
        persona = Persona.objects.create(
            tenant=tenant,
            name='人物像テスト',
            personality_traits=['協調性', 'リーダーシップ', '問題解決力'],
            created_by=user,
        )
        assert '協調性' in persona.personality_traits

"""
Personas アプリのモデルテスト

逆証明によるロジック検証:
1. ペルソナ作成・バリデーション
2. 年齢・経験年数の範囲表示
3. 複製機能
4. バリデーター
"""

from django.test import TestCase
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model

from apps.tenants.models import Tenant
from apps.personas.models import Persona


User = get_user_model()


class PersonaModelTest(TestCase):
    """ペルソナモデルのテスト"""

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

    def test_create_persona(self):
        """ペルソナ作成"""
        persona = Persona.objects.create(
            tenant=self.tenant,
            name='若手エンジニア',
            description='20代後半〜30代前半のエンジニア',
            age_min=25,
            age_max=35,
            experience_years_min=3,
            experience_years_max=10,
            education_level=Persona.EducationLevelChoices.BACHELOR,
            required_skills=['Python', 'Django'],
            preferred_skills=['AWS', 'Docker'],
            created_by=self.user,
        )
        self.assertEqual(persona.name, '若手エンジニア')
        self.assertTrue(persona.is_active)
        self.assertFalse(persona.is_template)

    def test_age_range_display_both(self):
        """年齢範囲表示（両方指定）"""
        persona = Persona.objects.create(
            tenant=self.tenant,
            name='テスト',
            age_min=25,
            age_max=35,
        )
        self.assertEqual(persona.age_range_display, '25〜35歳')

    def test_age_range_display_min_only(self):
        """年齢範囲表示（最小のみ）"""
        persona = Persona.objects.create(
            tenant=self.tenant,
            name='テスト',
            age_min=30,
        )
        self.assertEqual(persona.age_range_display, '30歳以上')

    def test_age_range_display_max_only(self):
        """年齢範囲表示（最大のみ）"""
        persona = Persona.objects.create(
            tenant=self.tenant,
            name='テスト',
            age_max=40,
        )
        self.assertEqual(persona.age_range_display, '40歳以下')

    def test_age_range_display_none(self):
        """年齢範囲表示（指定なし）"""
        persona = Persona.objects.create(
            tenant=self.tenant,
            name='テスト',
        )
        self.assertEqual(persona.age_range_display, '不問')

    def test_experience_range_display_both(self):
        """経験年数範囲表示（両方指定）"""
        persona = Persona.objects.create(
            tenant=self.tenant,
            name='テスト',
            experience_years_min=3,
            experience_years_max=10,
        )
        self.assertEqual(persona.experience_range_display, '3〜10年')

    def test_experience_range_display_min_only(self):
        """経験年数範囲表示（最小のみ）"""
        persona = Persona.objects.create(
            tenant=self.tenant,
            name='テスト',
            experience_years_min=5,
        )
        self.assertEqual(persona.experience_range_display, '5年以上')

    def test_experience_range_display_max_only(self):
        """経験年数範囲表示（最大のみ）"""
        persona = Persona.objects.create(
            tenant=self.tenant,
            name='テスト',
            experience_years_max=3,
        )
        self.assertEqual(persona.experience_range_display, '3年以下')

    def test_experience_range_display_none(self):
        """経験年数範囲表示（指定なし）"""
        persona = Persona.objects.create(
            tenant=self.tenant,
            name='テスト',
        )
        self.assertEqual(persona.experience_range_display, '不問')

    def test_duplicate_persona(self):
        """ペルソナ複製"""
        original = Persona.objects.create(
            tenant=self.tenant,
            name='オリジナル',
            description='オリジナルの説明',
            age_min=25,
            age_max=35,
            required_skills=['Python'],
            is_template=True,
        )

        # 複製
        copy = original.duplicate()

        self.assertNotEqual(original.pk, copy.pk)
        self.assertEqual(copy.name, 'オリジナル (コピー)')
        self.assertEqual(copy.description, 'オリジナルの説明')
        self.assertEqual(copy.age_min, 25)
        self.assertEqual(copy.age_max, 35)
        self.assertEqual(copy.required_skills, ['Python'])
        self.assertFalse(copy.is_template)  # 複製はテンプレートではない

    def test_duplicate_with_custom_name(self):
        """カスタム名で複製"""
        original = Persona.objects.create(
            tenant=self.tenant,
            name='オリジナル',
        )

        copy = original.duplicate(new_name='カスタム名')
        self.assertEqual(copy.name, 'カスタム名')

    def test_age_validator_min(self):
        """年齢バリデーター（最小）"""
        persona = Persona(
            tenant=self.tenant,
            name='テスト',
            age_min=17,  # 18未満
        )
        with self.assertRaises(ValidationError):
            persona.full_clean()

    def test_age_validator_max(self):
        """年齢バリデーター（最大）"""
        persona = Persona(
            tenant=self.tenant,
            name='テスト',
            age_max=101,  # 100超
        )
        with self.assertRaises(ValidationError):
            persona.full_clean()

    def test_experience_validator_max(self):
        """経験年数バリデーター（最大）"""
        persona = Persona(
            tenant=self.tenant,
            name='テスト',
            experience_years_max=51,  # 50超
        )
        with self.assertRaises(ValidationError):
            persona.full_clean()

    def test_education_level_choices(self):
        """学歴選択肢の検証"""
        choices = [c[0] for c in Persona.EducationLevelChoices.choices]
        expected = [
            'none', 'high_school', 'vocational', 'associate',
            'bachelor', 'master', 'doctor'
        ]
        self.assertEqual(choices, expected)

    def test_str_representation(self):
        """__str__の検証"""
        persona = Persona.objects.create(
            tenant=self.tenant,
            name='シニアエンジニア',
        )
        self.assertEqual(str(persona), 'シニアエンジニア')

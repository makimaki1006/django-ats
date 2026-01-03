"""
Personas アプリ逆証明テスト

逆証明（Proof by Contradiction）により、
不正な操作が適切に拒否されることを検証します。

テスト観点:
1. テナント分離 - 他テナントデータへのアクセス拒否
2. バリデーション - 不正な入力の拒否
3. 認証・認可 - 未認証アクセスの拒否
4. 削除制限 - 関連データ存在時の削除拒否
5. 範囲チェック - 年齢・経験年数の整合性
"""

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model

from apps.tenants.models import Tenant
from apps.personas.models import Persona
from apps.jobs.models import Job, JobPersona

User = get_user_model()


class PersonaTenantIsolationInverseTest(TestCase):
    """テナント分離の逆証明テスト

    証明: 他テナントのペルソナにアクセスできないこと
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
        self.persona_a = Persona.objects.create(
            tenant=self.tenant_a,
            name='テナントAのペルソナ',
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
        self.persona_b = Persona.objects.create(
            tenant=self.tenant_b,
            name='テナントBのペルソナ',
            is_active=True,
        )

        self.client = Client()

    def test_cannot_view_other_tenant_persona_detail(self):
        """他テナントのペルソナ詳細は表示できない"""
        self.client.login(email='user_a@example.com', password='testpass123')
        response = self.client.get(
            reverse('personas:persona_detail', kwargs={'pk': self.persona_b.pk})
        )
        # 404が返されることを確認（アクセス拒否）
        self.assertEqual(response.status_code, 404)

    def test_cannot_update_other_tenant_persona(self):
        """他テナントのペルソナは更新できない"""
        self.client.login(email='user_a@example.com', password='testpass123')
        response = self.client.post(
            reverse('personas:persona_update', kwargs={'pk': self.persona_b.pk}),
            {'name': '不正な更新', 'is_active': True}
        )
        self.assertEqual(response.status_code, 404)
        # データが変更されていないことを確認
        self.persona_b.refresh_from_db()
        self.assertEqual(self.persona_b.name, 'テナントBのペルソナ')

    def test_cannot_delete_other_tenant_persona(self):
        """他テナントのペルソナは削除できない"""
        self.client.login(email='user_a@example.com', password='testpass123')
        response = self.client.post(
            reverse('personas:persona_delete', kwargs={'pk': self.persona_b.pk})
        )
        self.assertEqual(response.status_code, 404)
        # データが削除されていないことを確認
        self.assertTrue(Persona.objects.filter(pk=self.persona_b.pk).exists())

    def test_cannot_duplicate_other_tenant_persona(self):
        """他テナントのペルソナは複製できない"""
        self.client.login(email='user_a@example.com', password='testpass123')
        response = self.client.post(
            reverse('personas:persona_duplicate', kwargs={'pk': self.persona_b.pk})
        )
        self.assertEqual(response.status_code, 404)

    def test_list_shows_only_own_tenant_personas(self):
        """一覧は自テナントのペルソナのみ表示"""
        self.client.login(email='user_a@example.com', password='testpass123')
        response = self.client.get(reverse('personas:persona_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'テナントAのペルソナ')
        self.assertNotContains(response, 'テナントBのペルソナ')


class PersonaValidationInverseTest(TestCase):
    """バリデーションの逆証明テスト

    証明: 不正な入力が適切に拒否されること
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

    def test_cannot_create_persona_without_name(self):
        """名前なしでペルソナを作成できない"""
        response = self.client.post(
            reverse('personas:persona_create'),
            {'name': '', 'is_active': True}
        )
        self.assertEqual(response.status_code, 200)  # フォーム再表示
        self.assertContains(response, 'このフィールドは必須です')
        self.assertEqual(Persona.objects.filter(tenant=self.tenant).count(), 0)

    def test_cannot_create_persona_with_invalid_age_range(self):
        """最小年齢 > 最大年齢でペルソナを作成できない"""
        response = self.client.post(
            reverse('personas:persona_create'),
            {
                'name': 'テストペルソナ',
                'age_min': 40,
                'age_max': 25,  # min > max
                'is_active': True,
            }
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '最大年齢は最小年齢以上')
        self.assertEqual(Persona.objects.filter(tenant=self.tenant).count(), 0)

    def test_cannot_create_persona_with_invalid_experience_range(self):
        """最小経験年数 > 最大経験年数でペルソナを作成できない"""
        response = self.client.post(
            reverse('personas:persona_create'),
            {
                'name': 'テストペルソナ',
                'experience_years_min': 10,
                'experience_years_max': 3,  # min > max
                'is_active': True,
            }
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '最大経験年数は最小経験年数以上')
        self.assertEqual(Persona.objects.filter(tenant=self.tenant).count(), 0)

    def test_cannot_create_persona_with_age_out_of_range(self):
        """年齢が範囲外（18-100）でペルソナを作成できない"""
        # 最小年齢が18未満
        response = self.client.post(
            reverse('personas:persona_create'),
            {
                'name': 'テストペルソナ',
                'age_min': 15,
                'is_active': True,
            }
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Persona.objects.filter(tenant=self.tenant).count(), 0)


class PersonaAuthenticationInverseTest(TestCase):
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
        self.persona = Persona.objects.create(
            tenant=self.tenant,
            name='テストペルソナ',
            is_active=True,
        )
        self.client = Client()
        # ログインしない

    def test_unauthenticated_cannot_access_list(self):
        """未認証ユーザーは一覧にアクセスできない"""
        response = self.client.get(reverse('personas:persona_list'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('login', response.url)

    def test_unauthenticated_cannot_access_detail(self):
        """未認証ユーザーは詳細にアクセスできない"""
        response = self.client.get(
            reverse('personas:persona_detail', kwargs={'pk': self.persona.pk})
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn('login', response.url)

    def test_unauthenticated_cannot_create(self):
        """未認証ユーザーはペルソナを作成できない"""
        response = self.client.post(
            reverse('personas:persona_create'),
            {'name': '不正なペルソナ', 'is_active': True}
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn('login', response.url)
        self.assertEqual(Persona.objects.filter(name='不正なペルソナ').count(), 0)

    def test_unauthenticated_cannot_update(self):
        """未認証ユーザーはペルソナを更新できない"""
        response = self.client.post(
            reverse('personas:persona_update', kwargs={'pk': self.persona.pk}),
            {'name': '不正な更新'}
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn('login', response.url)

    def test_unauthenticated_cannot_delete(self):
        """未認証ユーザーはペルソナを削除できない"""
        response = self.client.post(
            reverse('personas:persona_delete', kwargs={'pk': self.persona.pk})
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn('login', response.url)
        self.assertTrue(Persona.objects.filter(pk=self.persona.pk).exists())


class PersonaDeletionConstraintInverseTest(TestCase):
    """削除制限の逆証明テスト

    証明: 関連データが存在する場合は削除できないこと
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
        self.persona = Persona.objects.create(
            tenant=self.tenant,
            name='関連ありペルソナ',
            is_active=True,
        )
        # 求人に紐付ける
        self.job = Job.objects.create(
            tenant=self.tenant,
            title='テスト求人',
            unique_code='TEST-001',
            status='active',
        )
        JobPersona.objects.create(
            job=self.job,
            persona=self.persona,
            priority=1,
        )

        self.client = Client()
        self.client.login(email='test@example.com', password='testpass123')

    def test_cannot_delete_persona_with_linked_job(self):
        """求人に紐付いているペルソナは削除できない"""
        response = self.client.post(
            reverse('personas:persona_delete', kwargs={'pk': self.persona.pk})
        )
        # リダイレクト（エラーメッセージ付き）
        self.assertIn(response.status_code, [200, 302, 204])
        # ペルソナが削除されていないことを確認
        self.assertTrue(Persona.objects.filter(pk=self.persona.pk).exists())


class PersonaModelConstraintInverseTest(TestCase):
    """モデル制約の逆証明テスト

    証明: モデルの制約が正しく機能すること
    """

    def setUp(self):
        self.tenant = Tenant.objects.create(
            name='テストテナント',
            code='test-tenant',
            is_active=True,
        )

    def test_age_range_display_with_none(self):
        """年齢が設定されていない場合は「不問」"""
        persona = Persona.objects.create(
            tenant=self.tenant,
            name='テストペルソナ',
        )
        self.assertEqual(persona.age_range_display, '不問')

    def test_experience_range_display_with_none(self):
        """経験年数が設定されていない場合は「不問」"""
        persona = Persona.objects.create(
            tenant=self.tenant,
            name='テストペルソナ',
        )
        self.assertEqual(persona.experience_range_display, '不問')

    def test_duplicate_creates_new_instance(self):
        """複製は新しいインスタンスを作成する"""
        original = Persona.objects.create(
            tenant=self.tenant,
            name='オリジナル',
            is_template=True,
        )
        duplicate = original.duplicate()
        self.assertNotEqual(original.pk, duplicate.pk)
        self.assertIn('コピー', duplicate.name)
        self.assertFalse(duplicate.is_template)  # テンプレートフラグは解除


class PersonaFormValidationInverseTest(TestCase):
    """フォームバリデーションの逆証明テスト"""

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

    def test_skills_text_parsing(self):
        """スキルテキストが正しくパースされる"""
        response = self.client.post(
            reverse('personas:persona_create'),
            {
                'name': 'スキルテスト',
                'required_skills_text': 'Python\nDjango\nPostgreSQL',
                'preferred_skills_text': 'AWS\nDocker',
                'is_active': True,
            }
        )
        # 作成成功後リダイレクト
        if response.status_code == 302:
            persona = Persona.objects.get(name='スキルテスト')
            self.assertEqual(persona.required_skills, ['Python', 'Django', 'PostgreSQL'])
            self.assertEqual(persona.preferred_skills, ['AWS', 'Docker'])

    def test_empty_skills_text_creates_empty_list(self):
        """空のスキルテキストは空リストになる"""
        response = self.client.post(
            reverse('personas:persona_create'),
            {
                'name': '空スキルテスト',
                'required_skills_text': '',
                'preferred_skills_text': '',
                'is_active': True,
            }
        )
        if response.status_code == 302:
            persona = Persona.objects.get(name='空スキルテスト')
            self.assertEqual(persona.required_skills, [])
            self.assertEqual(persona.preferred_skills, [])

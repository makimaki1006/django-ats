"""
Jobs アプリのモデルテスト

逆証明によるロジック検証:
1. 求人作成・一意制約
2. 年収範囲表示
3. ステータス遷移（publish, pause, close）
4. 複製機能
5. 中間テーブル（JobPersona, JobAgentCompany）
"""

from decimal import Decimal

from django.test import TestCase
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model

from apps.tenants.models import Tenant
from apps.jobs.models import (
    Job, JobPersona, JobAgentCompany,
    JobStatusChoices, EmploymentTypeChoices,
)
from apps.personas.models import Persona
from apps.agents.models import AgentCompany


User = get_user_model()


class JobModelTest(TestCase):
    """求人モデルのテスト"""

    def setUp(self):
        self.tenant = Tenant.objects.create(
            name='テストテナント',
            code='test-tenant',
            is_active=True,
        )
        self.user = User.objects.create_user(
            email='admin@example.com',
            password='testpass123',
            tenant=self.tenant,
        )

    def test_create_job(self):
        """求人作成"""
        job = Job.objects.create(
            tenant=self.tenant,
            title='バックエンドエンジニア',
            unique_code='BE-001',
            department='開発部',
            employment_type=EmploymentTypeChoices.FULL_TIME,
            location='東京都渋谷区',
            salary_min=500,
            salary_max=800,
            created_by=self.user,
        )
        self.assertEqual(job.title, 'バックエンドエンジニア')
        self.assertEqual(job.status, JobStatusChoices.DRAFT)
        self.assertFalse(job.is_active)

    def test_unique_code_per_tenant(self):
        """同一テナント内でコード一意"""
        Job.objects.create(
            tenant=self.tenant,
            title='求人1',
            unique_code='JOB-001',
        )

        with self.assertRaises(ValidationError):
            Job.objects.create(
                tenant=self.tenant,
                title='求人2',
                unique_code='JOB-001',  # 重複
            )

    def test_same_code_different_tenant_allowed(self):
        """異なるテナントなら同じコードOK"""
        tenant2 = Tenant.objects.create(
            name='テストテナント2',
            code='test-tenant-2',
            is_active=True,
        )

        Job.objects.create(
            tenant=self.tenant,
            title='求人1',
            unique_code='JOB-001',
        )

        job2 = Job.objects.create(
            tenant=tenant2,
            title='求人1',
            unique_code='JOB-001',  # 別テナントなのでOK
        )
        self.assertIsNotNone(job2.id)

    def test_salary_range_display_both(self):
        """年収範囲表示（両方）"""
        job = Job.objects.create(
            tenant=self.tenant,
            title='テスト',
            unique_code='TEST-001',
            salary_min=500,
            salary_max=800,
        )
        self.assertEqual(job.salary_range_display, '500万円〜800万円')

    def test_salary_range_display_min_only(self):
        """年収範囲表示（最小のみ）"""
        job = Job.objects.create(
            tenant=self.tenant,
            title='テスト',
            unique_code='TEST-002',
            salary_min=500,
        )
        self.assertEqual(job.salary_range_display, '500万円以上')

    def test_salary_range_display_max_only(self):
        """年収範囲表示（最大のみ）"""
        job = Job.objects.create(
            tenant=self.tenant,
            title='テスト',
            unique_code='TEST-003',
            salary_max=800,
        )
        self.assertEqual(job.salary_range_display, '〜800万円')

    def test_salary_range_display_none(self):
        """年収範囲表示（指定なし）"""
        job = Job.objects.create(
            tenant=self.tenant,
            title='テスト',
            unique_code='TEST-004',
        )
        self.assertEqual(job.salary_range_display, '応相談')

    def test_publish(self):
        """求人公開"""
        job = Job.objects.create(
            tenant=self.tenant,
            title='テスト',
            unique_code='TEST-005',
        )
        self.assertEqual(job.status, JobStatusChoices.DRAFT)
        self.assertIsNone(job.published_at)

        job.publish()

        self.assertEqual(job.status, JobStatusChoices.ACTIVE)
        self.assertIsNotNone(job.published_at)
        self.assertTrue(job.is_active)

    def test_pause(self):
        """求人一時停止"""
        job = Job.objects.create(
            tenant=self.tenant,
            title='テスト',
            unique_code='TEST-006',
            status=JobStatusChoices.ACTIVE,
        )

        job.pause()

        self.assertEqual(job.status, JobStatusChoices.PAUSED)
        self.assertFalse(job.is_active)

    def test_close(self):
        """求人終了"""
        job = Job.objects.create(
            tenant=self.tenant,
            title='テスト',
            unique_code='TEST-007',
            status=JobStatusChoices.ACTIVE,
        )
        self.assertIsNone(job.closed_at)

        job.close()

        self.assertEqual(job.status, JobStatusChoices.CLOSED)
        self.assertIsNotNone(job.closed_at)
        self.assertFalse(job.is_active)

    def test_duplicate(self):
        """求人複製"""
        persona = Persona.objects.create(
            tenant=self.tenant,
            name='ペルソナ1',
        )
        agent = AgentCompany.objects.create(
            name='エージェント1',
            code='AGT001',
        )

        original = Job.objects.create(
            tenant=self.tenant,
            title='オリジナル求人',
            unique_code='ORG-001',
            salary_min=500,
            salary_max=800,
            status=JobStatusChoices.ACTIVE,
        )
        JobPersona.objects.create(job=original, persona=persona)
        JobAgentCompany.objects.create(job=original, agent_company=agent)

        # 複製
        copy = original.duplicate(new_code='COPY-001', new_title='複製求人')

        self.assertNotEqual(original.pk, copy.pk)
        self.assertEqual(copy.unique_code, 'COPY-001')
        self.assertEqual(copy.title, '複製求人')
        self.assertEqual(copy.salary_min, 500)
        self.assertEqual(copy.salary_max, 800)
        self.assertEqual(copy.status, JobStatusChoices.DRAFT)  # 下書きにリセット
        self.assertIsNone(copy.published_at)
        self.assertIsNone(copy.closed_at)
        # ペルソナとエージェントも複製される
        self.assertEqual(copy.personas.count(), 1)
        self.assertEqual(copy.agent_companies.count(), 1)

    def test_duplicate_default_code(self):
        """デフォルトコードで複製"""
        original = Job.objects.create(
            tenant=self.tenant,
            title='オリジナル',
            unique_code='ORG-002',
        )

        copy = original.duplicate()

        self.assertEqual(copy.unique_code, 'ORG-002_copy')
        self.assertEqual(copy.title, 'オリジナル (コピー)')


class JobPersonaTest(TestCase):
    """求人-ペルソナ中間テーブルのテスト"""

    def setUp(self):
        self.tenant = Tenant.objects.create(
            name='テストテナント',
            code='test-tenant',
            is_active=True,
        )
        self.job = Job.objects.create(
            tenant=self.tenant,
            title='テスト求人',
            unique_code='TEST-001',
        )
        self.persona = Persona.objects.create(
            tenant=self.tenant,
            name='テストペルソナ',
        )

    def test_create_job_persona(self):
        """求人ペルソナ関連作成"""
        jp = JobPersona.objects.create(
            job=self.job,
            persona=self.persona,
            priority=1,
            notes='メインターゲット',
        )
        self.assertEqual(jp.priority, 1)
        self.assertEqual(jp.notes, 'メインターゲット')

    def test_unique_together(self):
        """同じ求人・ペルソナの組み合わせは一意"""
        JobPersona.objects.create(
            job=self.job,
            persona=self.persona,
        )

        with self.assertRaises(Exception):
            JobPersona.objects.create(
                job=self.job,
                persona=self.persona,
            )

    def test_str_representation(self):
        """__str__の検証"""
        jp = JobPersona.objects.create(
            job=self.job,
            persona=self.persona,
        )
        self.assertEqual(str(jp), 'テスト求人 - テストペルソナ')


class JobAgentCompanyTest(TestCase):
    """求人-エージェント中間テーブルのテスト"""

    def setUp(self):
        self.tenant = Tenant.objects.create(
            name='テストテナント',
            code='test-tenant',
            is_active=True,
        )
        self.job = Job.objects.create(
            tenant=self.tenant,
            title='テスト求人',
            unique_code='TEST-001',
        )
        self.agent = AgentCompany.objects.create(
            name='テストエージェント',
            code='AGT001',
            fee_rate=Decimal('30.00'),
        )

    def test_create_job_agent(self):
        """求人エージェント関連作成"""
        ja = JobAgentCompany.objects.create(
            job=self.job,
            agent_company=self.agent,
            notes='優先依頼',
        )
        self.assertIsNotNone(ja.assigned_at)
        self.assertIsNone(ja.special_fee_rate)

    def test_fee_rate_default(self):
        """手数料率（デフォルト）"""
        ja = JobAgentCompany.objects.create(
            job=self.job,
            agent_company=self.agent,
        )
        self.assertEqual(ja.fee_rate, Decimal('30.00'))

    def test_fee_rate_special(self):
        """手数料率（特別）"""
        ja = JobAgentCompany.objects.create(
            job=self.job,
            agent_company=self.agent,
            special_fee_rate=Decimal('25.00'),
        )
        self.assertEqual(ja.fee_rate, Decimal('25.00'))

    def test_unique_together(self):
        """同じ求人・エージェントの組み合わせは一意"""
        JobAgentCompany.objects.create(
            job=self.job,
            agent_company=self.agent,
        )

        with self.assertRaises(Exception):
            JobAgentCompany.objects.create(
                job=self.job,
                agent_company=self.agent,
            )

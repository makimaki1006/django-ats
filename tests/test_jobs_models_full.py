"""Django ATS - 求人モデル完全カバレッジテスト

jobs/models.pyの100%カバレッジを目指すテスト。
"""

import pytest
from django.urls import reverse

from apps.tenants.models import Tenant
from apps.accounts.models import CustomUser, UserRole
from apps.jobs.models import Job, JobStatusChoices, JobPersona, JobAgentCompany
from apps.personas.models import Persona
from apps.agents.models import AgentCompany


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def tenant(db):
    """テストテナント"""
    return Tenant.objects.create(
        name='求人モデルテスト',
        code='job-model-test',
        is_active=True,
    )


@pytest.fixture
def admin_user(db, tenant):
    """管理者ユーザー"""
    return CustomUser.objects.create_user(
        email='admin@job-model-test.com',
        password='testpass123',
        role=UserRole.CLIENT_ADMIN,
        tenant=tenant,
    )


@pytest.fixture
def job(db, tenant, admin_user):
    """テスト求人"""
    return Job.objects.create(
        tenant=tenant,
        title='テスト求人',
        unique_code='JOB-MODEL-001',
        status=JobStatusChoices.ACTIVE,
        created_by=admin_user,
    )


@pytest.fixture
def persona(db, tenant):
    """テストペルソナ"""
    return Persona.objects.create(
        tenant=tenant,
        name='テストペルソナ',
        description='テスト用ペルソナ',
    )


@pytest.fixture
def agent_company(db, tenant):
    """テストエージェント会社"""
    return AgentCompany.objects.create(
        tenant=tenant,
        name='テストエージェント',
        code='AGENT-001',
    )


# =============================================================================
# Job Model Property Tests
# =============================================================================

class TestJobModelProperties:
    """Jobモデルプロパティテスト"""

    @pytest.mark.django_db
    def test_get_absolute_url(self, job):
        """get_absolute_urlメソッド"""
        url = job.get_absolute_url()
        assert str(job.pk) in url
        assert '/jobs/' in url

    @pytest.mark.django_db
    def test_salary_range_display_both(self, tenant, admin_user):
        """年収範囲表示（両方指定）"""
        job = Job.objects.create(
            tenant=tenant,
            title='年収テスト',
            unique_code='JOB-SALARY-001',
            status=JobStatusChoices.ACTIVE,
            created_by=admin_user,
            salary_min=400,
            salary_max=600,
        )
        assert job.salary_range_display == '400万円〜600万円'

    @pytest.mark.django_db
    def test_salary_range_display_min_only(self, tenant, admin_user):
        """年収範囲表示（最低のみ）"""
        job = Job.objects.create(
            tenant=tenant,
            title='年収テスト2',
            unique_code='JOB-SALARY-002',
            status=JobStatusChoices.ACTIVE,
            created_by=admin_user,
            salary_min=500,
        )
        assert job.salary_range_display == '500万円以上'

    @pytest.mark.django_db
    def test_salary_range_display_max_only(self, tenant, admin_user):
        """年収範囲表示（最高のみ）"""
        job = Job.objects.create(
            tenant=tenant,
            title='年収テスト3',
            unique_code='JOB-SALARY-003',
            status=JobStatusChoices.ACTIVE,
            created_by=admin_user,
            salary_max=800,
        )
        assert job.salary_range_display == '〜800万円'

    @pytest.mark.django_db
    def test_salary_range_display_none(self, job):
        """年収範囲表示（指定なし）"""
        assert job.salary_range_display == '応相談'

    @pytest.mark.django_db
    def test_is_active_true(self, job):
        """is_active（募集中）"""
        assert job.is_active is True

    @pytest.mark.django_db
    def test_is_active_false(self, tenant, admin_user):
        """is_active（ドラフト）"""
        draft_job = Job.objects.create(
            tenant=tenant,
            title='ドラフト求人',
            unique_code='JOB-DRAFT-001',
            status=JobStatusChoices.DRAFT,
            created_by=admin_user,
        )
        assert draft_job.is_active is False


# =============================================================================
# Job Duplicate Tests
# =============================================================================

class TestJobDuplicate:
    """Jobの複製テスト"""

    @pytest.mark.django_db
    def test_duplicate_basic(self, job):
        """基本的な複製"""
        duplicated = job.duplicate()
        assert duplicated.pk != job.pk
        assert duplicated.title == f"{job.title} (コピー)"
        assert duplicated.status == JobStatusChoices.DRAFT

    @pytest.mark.django_db
    def test_duplicate_with_personas(self, job, persona):
        """ペルソナ付き複製"""
        JobPersona.objects.create(job=job, persona=persona)
        duplicated = job.duplicate()
        assert duplicated.personas.count() == 1
        assert duplicated.personas.first() == persona

    @pytest.mark.django_db
    def test_duplicate_with_agent_companies(self, job, agent_company):
        """エージェント会社付き複製"""
        JobAgentCompany.objects.create(job=job, agent_company=agent_company)
        duplicated = job.duplicate()
        assert duplicated.agent_companies.count() == 1
        assert duplicated.agent_companies.first() == agent_company


# =============================================================================
# JobPersona Tests
# =============================================================================

class TestJobPersona:
    """JobPersona中間テーブルテスト"""

    @pytest.mark.django_db
    def test_str(self, job, persona):
        """__str__メソッド"""
        job_persona = JobPersona.objects.create(job=job, persona=persona)
        result = str(job_persona)
        assert job.title in result
        assert persona.name in result


# =============================================================================
# JobAgentCompany Tests
# =============================================================================

class TestJobAgentCompany:
    """JobAgentCompany中間テーブルテスト"""

    @pytest.mark.django_db
    def test_str(self, job, agent_company):
        """__str__メソッド"""
        job_agent = JobAgentCompany.objects.create(job=job, agent_company=agent_company)
        result = str(job_agent)
        assert job.title in result
        assert agent_company.name in result

    @pytest.mark.django_db
    def test_fee_rate_with_special_rate(self, job, agent_company):
        """fee_rate（特別手数料率あり）"""
        from decimal import Decimal
        job_agent = JobAgentCompany.objects.create(
            job=job,
            agent_company=agent_company,
            special_fee_rate=Decimal('25.00')
        )
        assert job_agent.fee_rate == Decimal('25.00')

    @pytest.mark.django_db
    def test_fee_rate_without_special_rate(self, tenant, job):
        """fee_rate（特別手数料率なし、エージェント会社のデフォルト使用）"""
        from decimal import Decimal
        from apps.agents.models import AgentCompany

        agent = AgentCompany.objects.create(
            tenant=tenant,
            name='手数料テストエージェント',
            code='FEE-AGENT-001',
            fee_rate=Decimal('30.00')
        )
        job_agent = JobAgentCompany.objects.create(
            job=job,
            agent_company=agent,
            special_fee_rate=None
        )
        # エージェント会社のデフォルト手数料率が返される
        assert job_agent.fee_rate == Decimal('30.00')

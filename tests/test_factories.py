"""Django ATS - ファクトリテスト

factory_boyファクトリの動作確認テスト。
"""

import pytest
from django.utils import timezone
from datetime import timedelta

from apps.accounts.models import UserRoleChoices
from apps.candidates.models import GenderChoices, EmploymentStatusChoices
from apps.jobs.models import JobStatusChoices, EmploymentTypeChoices
from apps.applications.models import ApplicationStatusChoices
from apps.interviews.models import (
    InterviewTypeChoices,
    InterviewStatusChoices,
    InterviewResultChoices,
)

from tests.factories import (
    TenantFactory,
    UserFactory,
    AdminUserFactory,
    RecruiterFactory,
    InterviewerFactory,
    HiringManagerFactory,
    SystemAdminFactory,
    CandidateFactory,
    FemaleCandidateFactory,
    UnemployedCandidateFactory,
    JobFactory,
    DraftJobFactory,
    ClosedJobFactory,
    PartTimeJobFactory,
    ApplicationFactory,
    InterviewingApplicationFactory,
    OfferApplicationFactory,
    RejectedApplicationFactory,
    InterviewFactory,
    TodayInterviewFactory,
    PastInterviewFactory,
    CompletedInterviewFactory,
    CancelledInterviewFactory,
    FinalInterviewFactory,
    InPersonInterviewFactory,
    PersonaFactory,
)


# =============================================================================
# TenantFactory Tests
# =============================================================================

class TestTenantFactory:
    """テナントファクトリのテスト"""

    @pytest.mark.django_db
    def test_create_tenant(self):
        """テナントを作成できること"""
        tenant = TenantFactory()
        assert tenant.pk is not None
        assert tenant.name.startswith('テスト企業')
        assert tenant.is_active is True

    @pytest.mark.django_db
    def test_create_multiple_tenants(self):
        """複数テナントが一意のコードを持つこと"""
        tenants = TenantFactory.create_batch(3)
        codes = [t.code for t in tenants]
        assert len(codes) == len(set(codes))


# =============================================================================
# UserFactory Tests
# =============================================================================

class TestUserFactory:
    """ユーザーファクトリのテスト"""

    @pytest.mark.django_db
    def test_create_user(self):
        """ユーザーを作成できること"""
        user = UserFactory()
        assert user.pk is not None
        assert user.email.endswith('@example.com')
        assert user.tenant is not None
        assert user.check_password('testpass123')

    @pytest.mark.django_db
    def test_create_admin_user(self):
        """管理者ユーザーを作成できること"""
        admin = AdminUserFactory()
        assert admin.role == UserRoleChoices.CLIENT_ADMIN

    @pytest.mark.django_db
    def test_create_recruiter(self):
        """採用担当者を作成できること"""
        recruiter = RecruiterFactory()
        assert recruiter.role == UserRoleChoices.CLIENT_RECRUITER

    @pytest.mark.django_db
    def test_create_interviewer(self):
        """面接官を作成できること"""
        interviewer = InterviewerFactory()
        assert interviewer.role == UserRoleChoices.INTERVIEWER

    @pytest.mark.django_db
    def test_create_hiring_manager(self):
        """採用マネージャーを作成できること"""
        manager = HiringManagerFactory()
        assert manager.role == UserRoleChoices.HIRING_MANAGER

    @pytest.mark.django_db
    def test_create_system_admin(self):
        """システム管理者を作成できること"""
        sysadmin = SystemAdminFactory()
        assert sysadmin.role == UserRoleChoices.SYSTEM_ADMIN
        assert sysadmin.is_staff is True

    @pytest.mark.django_db
    def test_user_with_specific_tenant(self):
        """特定テナントに紐づくユーザーを作成できること"""
        tenant = TenantFactory(name='指定テナント')
        user = UserFactory(tenant=tenant)
        assert user.tenant.name == '指定テナント'


# =============================================================================
# CandidateFactory Tests
# =============================================================================

class TestCandidateFactory:
    """候補者ファクトリのテスト"""

    @pytest.mark.django_db
    def test_create_candidate(self):
        """候補者を作成できること"""
        candidate = CandidateFactory()
        assert candidate.pk is not None
        assert candidate.name is not None
        assert candidate.tenant is not None
        assert candidate.registered_by is not None
        # tenantが一致すること
        assert candidate.tenant == candidate.registered_by.tenant

    @pytest.mark.django_db
    def test_create_female_candidate(self):
        """女性候補者を作成できること"""
        candidate = FemaleCandidateFactory()
        assert candidate.gender == GenderChoices.FEMALE

    @pytest.mark.django_db
    def test_create_unemployed_candidate(self):
        """無職の候補者を作成できること"""
        candidate = UnemployedCandidateFactory()
        assert candidate.employment_status == EmploymentStatusChoices.UNEMPLOYED

    @pytest.mark.django_db
    def test_candidate_with_specific_tenant(self):
        """特定テナントの候補者を作成できること"""
        tenant = TenantFactory()
        candidate = CandidateFactory(tenant=tenant)
        assert candidate.tenant == tenant


# =============================================================================
# JobFactory Tests
# =============================================================================

class TestJobFactory:
    """求人ファクトリのテスト"""

    @pytest.mark.django_db
    def test_create_job(self):
        """求人を作成できること"""
        job = JobFactory()
        assert job.pk is not None
        assert job.title.startswith('エンジニア職')
        assert job.status == JobStatusChoices.ACTIVE
        assert job.tenant == job.created_by.tenant

    @pytest.mark.django_db
    def test_create_draft_job(self):
        """下書き求人を作成できること"""
        job = DraftJobFactory()
        assert job.status == JobStatusChoices.DRAFT

    @pytest.mark.django_db
    def test_create_closed_job(self):
        """終了済み求人を作成できること"""
        job = ClosedJobFactory()
        assert job.status == JobStatusChoices.CLOSED

    @pytest.mark.django_db
    def test_create_part_time_job(self):
        """パートタイム求人を作成できること"""
        job = PartTimeJobFactory()
        assert job.employment_type == EmploymentTypeChoices.PART_TIME

    @pytest.mark.django_db
    def test_job_unique_codes(self):
        """求人コードが一意であること"""
        jobs = JobFactory.create_batch(5)
        codes = [j.unique_code for j in jobs]
        assert len(codes) == len(set(codes))


# =============================================================================
# ApplicationFactory Tests
# =============================================================================

class TestApplicationFactory:
    """応募ファクトリのテスト"""

    @pytest.mark.django_db
    def test_create_application(self):
        """応募を作成できること"""
        app = ApplicationFactory()
        assert app.pk is not None
        assert app.status == ApplicationStatusChoices.DOCUMENT_SCREENING
        # すべて同じテナント
        assert app.tenant == app.candidate.tenant
        assert app.tenant == app.job.tenant
        assert app.tenant == app.registered_by.tenant

    @pytest.mark.django_db
    def test_create_interviewing_application(self):
        """面接中応募を作成できること"""
        app = InterviewingApplicationFactory()
        assert app.status == ApplicationStatusChoices.INTERVIEWING

    @pytest.mark.django_db
    def test_create_offer_application(self):
        """内定応募を作成できること"""
        app = OfferApplicationFactory()
        assert app.status == ApplicationStatusChoices.OFFER_MADE

    @pytest.mark.django_db
    def test_create_rejected_application(self):
        """不採用応募を作成できること"""
        app = RejectedApplicationFactory()
        assert app.status == ApplicationStatusChoices.REJECTED

    @pytest.mark.django_db
    def test_application_with_specific_candidate(self):
        """特定候補者の応募を作成できること"""
        tenant = TenantFactory()
        candidate = CandidateFactory(tenant=tenant, name='指定候補者')
        app = ApplicationFactory(tenant=tenant, candidate=candidate)
        assert app.candidate.name == '指定候補者'
        assert app.tenant == candidate.tenant


# =============================================================================
# InterviewFactory Tests
# =============================================================================

class TestInterviewFactory:
    """面接ファクトリのテスト"""

    @pytest.mark.django_db
    def test_create_interview(self):
        """面接を作成できること"""
        interview = InterviewFactory()
        assert interview.pk is not None
        assert interview.interview_type == InterviewTypeChoices.VIDEO
        assert interview.status == InterviewStatusChoices.SCHEDULED
        # すべて同じテナント
        assert interview.tenant == interview.application.tenant
        assert interview.tenant == interview.interviewer.tenant

    @pytest.mark.django_db
    def test_create_today_interview(self):
        """本日の面接を作成できること"""
        interview = TodayInterviewFactory()
        assert interview.scheduled_at.date() == timezone.now().date()

    @pytest.mark.django_db
    def test_create_past_interview(self):
        """過去の面接を作成できること"""
        interview = PastInterviewFactory()
        assert interview.scheduled_at < timezone.now()
        assert interview.status == InterviewStatusChoices.COMPLETED

    @pytest.mark.django_db
    def test_create_completed_interview(self):
        """完了済み面接を作成できること"""
        interview = CompletedInterviewFactory()
        assert interview.status == InterviewStatusChoices.COMPLETED
        assert interview.result == InterviewResultChoices.PASSED
        assert interview.evaluation_score == 4

    @pytest.mark.django_db
    def test_create_cancelled_interview(self):
        """キャンセル済み面接を作成できること"""
        interview = CancelledInterviewFactory()
        assert interview.status == InterviewStatusChoices.CANCELLED

    @pytest.mark.django_db
    def test_create_final_interview(self):
        """最終面接を作成できること"""
        interview = FinalInterviewFactory()
        assert interview.interview_type == InterviewTypeChoices.FINAL
        assert interview.interview_round == 3

    @pytest.mark.django_db
    def test_create_in_person_interview(self):
        """対面面接を作成できること"""
        interview = InPersonInterviewFactory()
        assert interview.interview_type == InterviewTypeChoices.IN_PERSON
        assert interview.location is not None


# =============================================================================
# PersonaFactory Tests
# =============================================================================

class TestPersonaFactory:
    """ペルソナファクトリのテスト"""

    @pytest.mark.django_db
    def test_create_persona(self):
        """ペルソナを作成できること"""
        persona = PersonaFactory()
        assert persona.pk is not None
        assert persona.name.startswith('ペルソナ')
        assert persona.is_active is True
        assert persona.tenant == persona.created_by.tenant

    @pytest.mark.django_db
    def test_persona_with_specific_tenant(self):
        """特定テナントのペルソナを作成できること"""
        tenant = TenantFactory()
        persona = PersonaFactory(tenant=tenant)
        assert persona.tenant == tenant


# =============================================================================
# Integration Tests
# =============================================================================

class TestFactoryIntegration:
    """ファクトリ統合テスト"""

    @pytest.mark.django_db
    def test_full_interview_flow(self):
        """面接フロー全体のデータ作成"""
        # 1つのテナントで全データを作成
        tenant = TenantFactory(name='統合テストテナント')
        admin = AdminUserFactory(tenant=tenant)
        recruiter = RecruiterFactory(tenant=tenant)
        interviewer = InterviewerFactory(tenant=tenant)

        candidate = CandidateFactory(tenant=tenant)
        job = JobFactory(tenant=tenant)
        application = ApplicationFactory(
            tenant=tenant,
            candidate=candidate,
            job=job,
        )
        interview = InterviewFactory(
            tenant=tenant,
            application=application,
            interviewer=interviewer,
        )

        # すべて同じテナント
        assert admin.tenant == tenant
        assert recruiter.tenant == tenant
        assert interviewer.tenant == tenant
        assert candidate.tenant == tenant
        assert job.tenant == tenant
        assert application.tenant == tenant
        assert interview.tenant == tenant

    @pytest.mark.django_db
    def test_batch_creation(self):
        """バッチ作成テスト"""
        tenant = TenantFactory()

        # 5人の候補者を一括作成
        candidates = CandidateFactory.create_batch(5, tenant=tenant)
        assert len(candidates) == 5
        for c in candidates:
            assert c.tenant == tenant

    @pytest.mark.django_db
    def test_multi_tenant_isolation(self):
        """マルチテナント分離テスト"""
        tenant1 = TenantFactory(name='テナント1')
        tenant2 = TenantFactory(name='テナント2')

        user1 = UserFactory(tenant=tenant1)
        user2 = UserFactory(tenant=tenant2)

        candidate1 = CandidateFactory(tenant=tenant1)
        candidate2 = CandidateFactory(tenant=tenant2)

        # 異なるテナント
        assert user1.tenant != user2.tenant
        assert candidate1.tenant != candidate2.tenant
        assert candidate1.tenant == tenant1
        assert candidate2.tenant == tenant2

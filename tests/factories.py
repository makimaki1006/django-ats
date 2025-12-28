"""Django ATS - テストファクトリ

factory_boy を使用したテストデータ生成ファクトリ。

使用例:
    from tests.factories import TenantFactory, UserFactory, CandidateFactory

    # 基本的な作成
    tenant = TenantFactory()
    user = UserFactory(tenant=tenant)
    candidate = CandidateFactory(tenant=tenant)

    # 属性の上書き
    admin = UserFactory(role=UserRoleChoices.CLIENT_ADMIN)

    # バッチ作成
    users = UserFactory.create_batch(10, tenant=tenant)
"""

import factory
from factory.django import DjangoModelFactory
from factory import Faker, LazyAttribute, SubFactory, Sequence
from django.utils import timezone
from datetime import timedelta

from apps.tenants.models import Tenant
from apps.accounts.models import CustomUser, UserRoleChoices
from apps.candidates.models import (
    Candidate,
    GenderChoices,
    EmploymentStatusChoices,
)
from apps.jobs.models import (
    Job,
    JobStatusChoices,
    EmploymentTypeChoices,
)
from apps.applications.models import (
    Application,
    ApplicationStatusChoices,
)
from apps.interviews.models import (
    Interview,
    InterviewTypeChoices,
    InterviewStatusChoices,
    InterviewResultChoices,
)
from apps.personas.models import Persona


# =============================================================================
# Tenants
# =============================================================================

class TenantFactory(DjangoModelFactory):
    """テナントファクトリ"""
    class Meta:
        model = Tenant

    name = Sequence(lambda n: f'テスト企業{n}')
    code = Sequence(lambda n: f'test-company-{n}')
    is_active = True


# =============================================================================
# Users
# =============================================================================

class UserFactory(DjangoModelFactory):
    """ユーザーファクトリ"""
    class Meta:
        model = CustomUser
        skip_postgeneration_save = True

    email = Sequence(lambda n: f'user{n}@example.com')
    tenant = SubFactory(TenantFactory)
    role = UserRoleChoices.INTERVIEWER
    is_active = True
    is_staff = False

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        """パスワード付きでユーザーを作成"""
        password = kwargs.pop('password', 'testpass123')
        user = super()._create(model_class, *args, **kwargs)
        user.set_password(password)
        user.save()
        return user


class AdminUserFactory(UserFactory):
    """管理者ユーザーファクトリ"""
    role = UserRoleChoices.CLIENT_ADMIN


class RecruiterFactory(UserFactory):
    """採用担当者ファクトリ"""
    role = UserRoleChoices.CLIENT_RECRUITER


class InterviewerFactory(UserFactory):
    """面接官ファクトリ"""
    role = UserRoleChoices.INTERVIEWER


class HiringManagerFactory(UserFactory):
    """採用マネージャーファクトリ"""
    role = UserRoleChoices.HIRING_MANAGER


class SystemAdminFactory(UserFactory):
    """システム管理者ファクトリ"""
    role = UserRoleChoices.SYSTEM_ADMIN
    is_staff = True


# =============================================================================
# Candidates
# =============================================================================

class CandidateFactory(DjangoModelFactory):
    """候補者ファクトリ"""
    class Meta:
        model = Candidate

    tenant = SubFactory(TenantFactory)
    name = Faker('name', locale='ja_JP')
    email = Sequence(lambda n: f'candidate{n}@example.com')
    phone = Sequence(lambda n: f'09012345{n:03d}')  # 090xxxxxxxx形式
    gender = GenderChoices.MALE
    employment_status = EmploymentStatusChoices.EMPLOYED
    registered_by = LazyAttribute(lambda o: UserFactory(tenant=o.tenant))


class FemaleCandidateFactory(CandidateFactory):
    """女性候補者ファクトリ"""
    gender = GenderChoices.FEMALE


class UnemployedCandidateFactory(CandidateFactory):
    """無職の候補者ファクトリ"""
    employment_status = EmploymentStatusChoices.UNEMPLOYED


# =============================================================================
# Jobs
# =============================================================================

class JobFactory(DjangoModelFactory):
    """求人ファクトリ"""
    class Meta:
        model = Job

    tenant = SubFactory(TenantFactory)
    title = Sequence(lambda n: f'エンジニア職{n}')
    unique_code = Sequence(lambda n: f'JOB-{n:05d}')
    status = JobStatusChoices.ACTIVE
    employment_type = EmploymentTypeChoices.FULL_TIME
    created_by = LazyAttribute(lambda o: UserFactory(tenant=o.tenant))


class DraftJobFactory(JobFactory):
    """下書き求人ファクトリ"""
    status = JobStatusChoices.DRAFT


class ClosedJobFactory(JobFactory):
    """終了済み求人ファクトリ"""
    status = JobStatusChoices.CLOSED


class PartTimeJobFactory(JobFactory):
    """パートタイム求人ファクトリ"""
    employment_type = EmploymentTypeChoices.PART_TIME


# =============================================================================
# Applications
# =============================================================================

class ApplicationFactory(DjangoModelFactory):
    """応募ファクトリ"""
    class Meta:
        model = Application

    tenant = SubFactory(TenantFactory)
    candidate = LazyAttribute(lambda o: CandidateFactory(tenant=o.tenant))
    job = LazyAttribute(lambda o: JobFactory(tenant=o.tenant))
    status = ApplicationStatusChoices.DOCUMENT_SCREENING
    registered_by = LazyAttribute(lambda o: UserFactory(tenant=o.tenant))


class InterviewingApplicationFactory(ApplicationFactory):
    """面接中応募ファクトリ"""
    status = ApplicationStatusChoices.INTERVIEWING


class OfferApplicationFactory(ApplicationFactory):
    """内定応募ファクトリ"""
    status = ApplicationStatusChoices.OFFER_MADE


class RejectedApplicationFactory(ApplicationFactory):
    """不採用応募ファクトリ"""
    status = ApplicationStatusChoices.REJECTED


# =============================================================================
# Interviews
# =============================================================================

class InterviewFactory(DjangoModelFactory):
    """面接ファクトリ"""
    class Meta:
        model = Interview

    tenant = SubFactory(TenantFactory)
    application = LazyAttribute(lambda o: ApplicationFactory(tenant=o.tenant))
    interviewer = LazyAttribute(lambda o: InterviewerFactory(tenant=o.tenant))
    interview_type = InterviewTypeChoices.VIDEO
    interview_round = 1
    scheduled_at = LazyAttribute(lambda o: timezone.now() + timedelta(days=1))
    duration_minutes = 60
    status = InterviewStatusChoices.SCHEDULED


class TodayInterviewFactory(InterviewFactory):
    """本日の面接ファクトリ"""
    scheduled_at = LazyAttribute(
        lambda o: timezone.now().replace(hour=18, minute=0, second=0)
    )


class PastInterviewFactory(InterviewFactory):
    """過去の面接ファクトリ"""
    scheduled_at = LazyAttribute(lambda o: timezone.now() - timedelta(days=1))
    status = InterviewStatusChoices.COMPLETED


class CompletedInterviewFactory(InterviewFactory):
    """完了済み面接ファクトリ"""
    status = InterviewStatusChoices.COMPLETED
    result = InterviewResultChoices.PASSED
    evaluation_score = 4


class CancelledInterviewFactory(InterviewFactory):
    """キャンセル済み面接ファクトリ"""
    status = InterviewStatusChoices.CANCELLED


class FinalInterviewFactory(InterviewFactory):
    """最終面接ファクトリ"""
    interview_type = InterviewTypeChoices.FINAL
    interview_round = 3


class InPersonInterviewFactory(InterviewFactory):
    """対面面接ファクトリ"""
    interview_type = InterviewTypeChoices.IN_PERSON
    location = '東京都千代田区丸の内1-1-1'


# =============================================================================
# Personas
# =============================================================================

class PersonaFactory(DjangoModelFactory):
    """ペルソナファクトリ"""
    class Meta:
        model = Persona

    tenant = SubFactory(TenantFactory)
    name = Sequence(lambda n: f'ペルソナ{n}')
    description = Faker('text', max_nb_chars=200, locale='ja_JP')
    is_active = True
    created_by = LazyAttribute(lambda o: UserFactory(tenant=o.tenant))
